"""
EnterpriseIQ ML — RAG Engine Core
Month 2 deliverable: Full RAG pipeline with:
  - text-embedding-004 via Vertex AI
  - Vertex AI Vector Search indexing + retrieval
  - Gemini 1.5 Pro grounded generation
  - Hybrid search (vector + BQ keyword)
  - Conversational RAG (session history)
  - Re-ranking with Gemini
  - Streaming SSE support
  - RAGAS evaluation logging
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from collections import defaultdict
from typing import AsyncGenerator

import structlog
import vertexai
from google.cloud.aiplatform.matching_engine import MatchingEngineIndex, MatchingEngineIndexEndpoint
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings
from rag.schemas import RAGResponse, Source

logger = structlog.get_logger(__name__)
settings = get_settings()

# Conversation history store (in-memory; production should use Firestore/Redis)
_session_history: dict[str, list[dict]] = defaultdict(list)


class ChunkResult:
    """Holds a retrieved chunk with its metadata."""

    def __init__(self, chunk_id: str, text: str, doc_id: str,
                 page_number: int | None, score: float) -> None:
        self.chunk_id = chunk_id
        self.text = text
        self.doc_id = doc_id
        self.page_number = page_number
        self.score = score


class EnterpriseRAGEngine:
    """
    Core RAG engine — Developer B Month 2.

    Lifecycle:
      1. embed_and_index(chunks)  — called by Pub/Sub trigger after doc ingestion
      2. query(question, corpus)  — called by Person A's backend via /internal/rag/query
    """

    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)

        self._embedding_model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
        self._gemini_pro = GenerativeModel(settings.gemini_pro_model)
        self._gemini_flash = GenerativeModel(settings.gemini_flash_model)
        self._bq = BigQueryClient()

        # Vector Search index endpoint (stream update mode)
        if settings.vertex_ai_index_endpoint_id:
            self._index_endpoint = MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.vertex_ai_index_endpoint_id
            )
        else:
            self._index_endpoint = None
            logger.warning("Vector Search index endpoint not configured — retrieval disabled")

        logger.info("EnterpriseRAGEngine initialised")

    # ── Step 1: Embedding ─────────────────────────────────────────────────────

    def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """
        Embed text chunks using text-embedding-004.
        Batches in groups of 250 (API limit).
        """
        all_embeddings: list[list[float]] = []
        batch_size = 250

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            embeddings = self._embedding_model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])
            logger.debug("Embeddings computed", batch_start=i, count=len(batch))

        return all_embeddings

    # ── Step 2: Indexing ──────────────────────────────────────────────────────

    def index_chunks(self, chunk_ids: list[str], embeddings: list[list[float]],
                     corpus_id: str) -> None:
        """
        Upsert chunk embeddings into Vertex AI Vector Search.
        deployed_index_id naming convention: corpus_<corpus_id>
        """
        if not self._index_endpoint:
            logger.warning("Skipping indexing — endpoint not configured")
            return

        datapoints = [
            {"datapoint_id": cid, "feature_vector": emb, "restricts": [
                {"namespace": "corpus", "allow_list": [corpus_id]}
            ]}
            for cid, emb in zip(chunk_ids, embeddings)
        ]

        # Upsert in batches of 100
        for i in range(0, len(datapoints), 100):
            self._index_endpoint.upsert_datapoints(datapoints[i : i + 100])

        logger.info("Chunks indexed", count=len(chunk_ids), corpus_id=corpus_id)

    # ── Combined embed + index (called after Pub/Sub event) ──────────────────

    def embed_and_index(self, chunks: list[str], chunk_ids: list[str],
                        corpus_id: str) -> int:
        """Public entry point: embed then index. Returns count of indexed chunks."""
        embeddings = self.embed_chunks(chunks)
        self.index_chunks(chunk_ids, embeddings, corpus_id)
        return len(chunk_ids)

    # ── Step 3: Retrieval ─────────────────────────────────────────────────────

    def retrieve(self, question: str, corpus_id: str, top_k: int) -> list[ChunkResult]:
        """Vector similarity search in Vertex AI Vector Search."""
        if not self._index_endpoint:
            logger.warning("Retrieval skipped — endpoint not configured")
            return []

        embeddings = self.embed_chunks([question])
        if not embeddings:
            return []
        query_emb = embeddings[0]

        neighbors = self._index_endpoint.find_neighbors(
            deployed_index_id=f"corpus_{corpus_id}",
            queries=[query_emb],
            num_neighbors=top_k,
            filter=[f"corpus = {corpus_id}"],
        )

        if not neighbors:
            return []

        chunk_ids = [n.datapoint.datapoint_id for n in neighbors[0]]
        scores = {n.datapoint.datapoint_id: n.distance for n in neighbors[0]}

        rows = self._bq.get_chunks(chunk_ids)
        return [
            ChunkResult(
                chunk_id=r["chunk_id"],
                text=r["chunk_text"],
                doc_id=r["doc_id"],
                page_number=r.get("page_number"),
                score=scores.get(r["chunk_id"], 0.0),
            )
            for r in rows
        ]

    def hybrid_search(self, question: str, corpus_id: str,
                      top_k: int) -> list[ChunkResult]:
        """
        Combine Vector Search (semantic) + BigQuery full-text (keyword).
        Uses Reciprocal Rank Fusion (RRF) to merge rankings.
        """
        vector_results = self.retrieve(question, corpus_id, top_k * 2)
        kw_rows = self._bq.full_text_search(question, corpus_id, limit=top_k * 2)

        keyword_results = [
            ChunkResult(
                chunk_id=r["chunk_id"],
                text=r["chunk_text"],
                doc_id=r["doc_id"],
                page_number=None,
                score=float(r.get("score", 0)),
            )
            for r in kw_rows
        ]

        return self._reciprocal_rank_fusion(vector_results, keyword_results, top_k=top_k)

    def _reciprocal_rank_fusion(self, list_a: list[ChunkResult],
                                 list_b: list[ChunkResult],
                                 top_k: int, k: int = 60) -> list[ChunkResult]:
        """Standard RRF: score = Σ 1/(k + rank)."""
        scores: dict[str, float] = {}
        chunk_map: dict[str, ChunkResult] = {}

        for rank, chunk in enumerate(list_a):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        for rank, chunk in enumerate(list_b):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (k + rank + 1)
            chunk_map[chunk.chunk_id] = chunk

        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
        for cid in sorted_ids:
            chunk_map[cid].score = scores[cid]

        return [chunk_map[cid] for cid in sorted_ids]

    # ── Step 4: Re-ranking with Gemini Flash ─────────────────────────────────

    def rerank(self, question: str, chunks: list[ChunkResult]) -> list[ChunkResult]:
        """Use Gemini Flash to re-rank retrieved chunks by relevance."""
        if len(chunks) <= 1:
            return chunks

        snippets = "\n".join(
            [f"[{i}] {c.text[:300]}" for i, c in enumerate(chunks)]
        )
        prompt = f"""You are a relevance ranker. Given the question and candidate passages,
output ONLY a JSON array of passage indices in descending order of relevance.
Example: [2, 0, 4, 1, 3]

Question: {question}

Passages:
{snippets}

Ranking (JSON array only):"""

        response = self._gemini_flash.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.0, max_output_tokens=100),
        )
        try:
            # Extract JSON array from response
            match = re.search(r"\[[\d,\s]+\]", response.text)
            if match:
                order = [int(x) for x in re.findall(r"\d+", match.group())]
                reranked = [chunks[i] for i in order if i < len(chunks)]
                # Preserve any chunks not mentioned
                seen = set(order)
                reranked += [c for i, c in enumerate(chunks) if i not in seen]
                return reranked
        except Exception as e:
            logger.warning("Re-ranking parse failed", error=str(e))

        return chunks  # fall back to original order

    # ── Step 5: Generation ────────────────────────────────────────────────────

    def generate(self, question: str, chunks: list[ChunkResult],
                 session_id: str | None = None) -> RAGResponse:
        """Grounded generation with Gemini 1.5 Pro."""
        t0 = time.monotonic()

        context = "\n\n".join(
            [f"[Source {i+1}] (doc: {c.doc_id}, page: {c.page_number})\n{c.text}"
             for i, c in enumerate(chunks)]
        )

        # Build conversation history if session exists
        history_text = ""
        if session_id and _session_history[session_id]:
            history_text = "\n".join(
                [f"{m['role'].upper()}: {m['content']}"
                 for m in _session_history[session_id][-6:]]  # last 3 turns
            )
            history_text = f"\nConversation History:\n{history_text}\n"

        prompt = f"""You are an enterprise intelligence assistant with access to proprietary documents.
Answer the question using ONLY the provided context. If the answer is not in the context,
respond with: "I don't have enough information in the provided documents to answer this."
Always cite which source number ([Source 1], [Source 2], etc.) supports each claim.
Be concise and professional.
{history_text}
Context:
{context}

Question: {question}

Answer:"""

        response = self._gemini_pro.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=1024),
        )

        answer = response.text
        confidence = self._calculate_confidence(chunks, answer)
        latency_ms = int((time.monotonic() - t0) * 1000)

        # Update session history
        if session_id:
            _session_history[session_id].append({"role": "user", "content": question})
            _session_history[session_id].append({"role": "assistant", "content": answer})

        sources = [
            Source(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                text_snippet=c.text[:200],
                page_number=c.page_number,
                score=round(c.score, 4),
            )
            for c in chunks
        ]

        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            model_used=settings.gemini_pro_model,
            latency_ms=latency_ms,
            session_id=session_id,
        )

    async def stream_generate(self, question: str, chunks: list[ChunkResult],
                               session_id: str | None = None) -> AsyncGenerator[str, None]:
        """Streaming generation via Gemini (yields text chunks for SSE)."""
        context = "\n\n".join([f"[Source {i+1}]\n{c.text}" for i, c in enumerate(chunks)])
        prompt = f"""Answer the question using ONLY the context. Cite sources.
Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"""

        response = self._gemini_pro.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=1024),
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
                await asyncio.sleep(0)  # yield control to event loop

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _calculate_confidence(self, chunks: list[ChunkResult], answer: str) -> float:
        """
        Heuristic confidence score:
        - Average retrieval score of top chunks
        - Penalise if answer contains "don't have enough information"
        """
        if not chunks:
            return 0.0
        avg_score = sum(c.score for c in chunks[:3]) / min(3, len(chunks))
        if "don't have enough information" in answer.lower():
            avg_score *= 0.3
        return round(min(max(avg_score, 0.0), 1.0), 4)

    # ── Main query entry point ────────────────────────────────────────────────

    def query(self, question: str, corpus_id: str, top_k: int = 5,
              use_hybrid: bool = True, session_id: str | None = None) -> RAGResponse:
        """
        Full RAG pipeline: retrieve → rerank → generate.
        This is called by Person A's backend via /internal/rag/query.
        """
        logger.info("RAG query started", corpus_id=corpus_id, top_k=top_k)

        if use_hybrid:
            chunks = self.hybrid_search(question, corpus_id, top_k)
        else:
            chunks = self.retrieve(question, corpus_id, top_k)

        if chunks:
            chunks = self.rerank(question, chunks)

        return self.generate(question, chunks, session_id)
