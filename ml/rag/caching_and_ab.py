"""
EnterpriseIQ ML — Gemini Context Caching (Month 8)
Implements Gemini Context Caching for large, repeated document corpora.
Reduces API cost and latency for frequently-queried corpora.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview import caching

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class GeminiContextCache:
    """
    Manages Gemini context caches for large document corpora.
    Cache stores the document context so it doesn't need to be sent
    on every query (significant cost reduction for large corpora).
    """

    # Cache TTL: 1 hour (Gemini minimum is 1 hour)
    CACHE_TTL_HOURS = 1
    # Minimum context length to benefit from caching (in chars)
    MIN_CACHE_CONTEXT_LENGTH = 32_000

    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        self._bq = BigQueryClient()
        self._cache_registry: dict[str, str] = {}  # corpus_id → cache_name
        logger.info("GeminiContextCache initialised")

    def _context_hash(self, context: str) -> str:
        """Compute SHA-256 hash of context for cache invalidation."""
        return hashlib.sha256(context.encode()).hexdigest()[:16]

    def get_or_create_cache(self, corpus_id: str, context: str) -> caching.CachedContent | None:
        """
        Get existing cache for corpus, or create a new one.
        Only caches contexts longer than MIN_CACHE_CONTEXT_LENGTH.
        """
        if len(context) < self.MIN_CACHE_CONTEXT_LENGTH:
            logger.debug("Context too short for caching", length=len(context))
            return None

        context_hash = self._context_hash(context)
        cache_key = f"{corpus_id}_{context_hash}"

        # Check if we already have a valid cache
        if cache_key in self._cache_registry:
            try:
                cached = caching.CachedContent(
                    cached_content_name=self._cache_registry[cache_key]
                )
                logger.debug("Cache hit", corpus_id=corpus_id)
                return cached
            except Exception:
                # Cache expired or deleted
                del self._cache_registry[cache_key]

        # Create new cache
        try:
            cached = caching.CachedContent.create(
                model_name=f"publishers/google/models/{settings.gemini_pro_model}",
                system_instruction=(
                    "You are an enterprise intelligence assistant. "
                    "Answer questions using ONLY the provided document context. "
                    "Always cite source numbers."
                ),
                contents=[context],
                ttl=timedelta(hours=self.CACHE_TTL_HOURS),
                display_name=f"enterpriseiq-corpus-{corpus_id[:8]}",
            )
            self._cache_registry[cache_key] = cached.name
            logger.info("Context cache created", corpus_id=corpus_id,
                        cache_name=cached.name, ttl_hours=self.CACHE_TTL_HOURS)
            return cached
        except Exception as e:
            logger.warning("Cache creation failed — falling back to standard RAG", error=str(e))
            return None

    def generate_with_cache(self, cached: caching.CachedContent,
                             question: str) -> str:
        """Use a cached context to generate an answer."""
        model = GenerativeModel.from_cached_content(cached_content=cached)
        response = model.generate_content(
            f"Question: {question}\n\nAnswer (cite sources):"
        )
        return response.text

    def invalidate_corpus_cache(self, corpus_id: str) -> None:
        """Remove all cached contexts for a corpus (call when corpus is updated)."""
        keys_to_remove = [k for k in self._cache_registry if k.startswith(corpus_id)]
        for key in keys_to_remove:
            try:
                cached = caching.CachedContent(cached_content_name=self._cache_registry[key])
                cached.delete()
            except Exception:
                pass
            del self._cache_registry[key]
        logger.info("Corpus cache invalidated", corpus_id=corpus_id,
                    removed=len(keys_to_remove))


class PromptABTester:
    """
    A/B testing framework for Gemini prompt versions.
    Month 8: Test different prompts and track which performs better.
    """

    def __init__(self) -> None:
        self._bq = BigQueryClient()
        self._gemini = GenerativeModel(settings.gemini_pro_model)

    PROMPT_VARIANTS = {
        "control": """You are an enterprise intelligence assistant.
Answer the question using ONLY the provided context. Cite sources.
Context: {context}
Question: {question}
Answer:""",
        "treatment_a": """As an expert analyst with access to proprietary documents,
provide a precise answer to the question below. Reference specific sources.
Every factual claim must cite [Source N].
Context: {context}
Question: {question}
Concise Answer:""",
        "treatment_b": """TASK: Answer the question using document context.
FORMAT: Start with a 1-sentence direct answer, then elaborate with evidence.
RULE: Only use information from the provided sources. Use [Source N] citations.
Context: {context}
Question: {question}
Answer:""",
    }

    def test_prompt(self, question: str, context: str,
                    variant: str = "control") -> dict[str, Any]:
        """Test a specific prompt variant and log to BigQuery."""
        import time, uuid
        from vertexai.generative_models import GenerationConfig

        if variant not in self.PROMPT_VARIANTS:
            variant = "control"

        prompt = self.PROMPT_VARIANTS[variant].format(
            context=context[:8000], question=question
        )

        t0 = time.monotonic()
        response = self._gemini.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=1024),
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        result = {
            "test_id": str(uuid.uuid4()),
            "variant": variant,
            "question": question,
            "answer": response.text,
            "latency_ms": latency_ms,
            "token_count": response.usage_metadata.total_token_count,
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }

        # Log to BigQuery for analysis
        try:
            self._bq.insert_rows("prompt_ab_tests", [result])
        except Exception as e:
            logger.warning("AB test logging failed", error=str(e))

        return result

    def get_winning_variant(self, metric: str = "user_rating") -> str:
        """Query BigQuery to find the best performing prompt variant."""
        sql = f"""
            SELECT variant, AVG({metric}) as avg_score, COUNT(*) as sample_size
            FROM `{self._bq._table_ref("prompt_ab_tests")}`
            WHERE {metric} IS NOT NULL
              AND tested_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            GROUP BY variant
            HAVING sample_size >= 30
            ORDER BY avg_score DESC
            LIMIT 1
        """
        try:
            rows = self._bq.query(sql)
            if rows:
                return rows[0]["variant"]
        except Exception as e:
            logger.warning("Failed to get winning variant", error=str(e))
        return "control"
