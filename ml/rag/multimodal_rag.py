"""
EnterpriseIQ ML — Multi-Modal RAG (Month 8)
Extends RAG engine to handle images + text documents using Gemini Vision.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import BinaryIO

import structlog
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    Image,
    Part,
)

from shared.config import get_settings
from rag.engine import EnterpriseRAGEngine
from rag.schemas import RAGResponse

logger = structlog.get_logger(__name__)
settings = get_settings()

SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}


class MultiModalRAGEngine(EnterpriseRAGEngine):
    """
    Extends EnterpriseRAGEngine with image + document visual understanding.
    Month 8: Multi-modal RAG using Gemini 1.5 Pro Vision.
    """

    def __init__(self) -> None:
        super().__init__()
        # Gemini 1.5 Pro natively handles images, PDFs, audio, video
        self._gemini_vision = GenerativeModel("gemini-1.5-pro")
        logger.info("MultiModalRAGEngine initialised")

    def describe_image(self, image_bytes: bytes, mime_type: str,
                        context_question: str | None = None) -> str:
        """
        Use Gemini Vision to extract rich text description from an image.
        Output is then treated as a text chunk for embedding.
        """
        prompt_parts = [
            Part.from_data(data=image_bytes, mime_type=mime_type),
            Part.from_text(
                context_question or
                """Provide a comprehensive, detailed description of this image for a 
                document intelligence system. Include:
                - All text visible in the image (OCR)
                - Charts/graphs: axis labels, values, trends
                - Tables: headers and key data points
                - Key entities, concepts, and relationships visible
                Format as dense, searchable text."""
            ),
        ]

        response = self._gemini_vision.generate_content(
            prompt_parts,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=2048),
        )
        return response.text

    def process_document_with_vision(self, file_bytes: bytes,
                                      filename: str) -> list[str]:
        """
        Process a mixed-content document (PDF with images, slides, etc.)
        Returns list of text chunks ready for embedding.
        """
        suffix = Path(filename).suffix.lower()

        if suffix == ".pdf":
            # Send entire PDF to Gemini (up to 1000 pages supported)
            mime_type = "application/pdf"
        elif suffix in (".png", ".jpg", ".jpeg"):
            mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        else:
            # Fallback: treat as text
            try:
                return [file_bytes.decode("utf-8", errors="replace")]
            except Exception:
                return []

        prompt_parts = [
            Part.from_data(data=file_bytes, mime_type=mime_type),
            Part.from_text("""Extract ALL text content from this document/image.
Include:
- All body text in reading order
- Table contents (as structured text)
- Chart/graph descriptions with values
- Captions and footnotes
- Headers and section titles
Format for optimal semantic search."""),
        ]

        try:
            response = self._gemini_vision.generate_content(
                prompt_parts,
                generation_config=GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                ),
            )
            full_text = response.text
            # Chunk the extracted text using fixed chunker
            from rag.chunking import FixedTokenChunker
            chunker = FixedTokenChunker()
            chunks = chunker.chunk(full_text)
            return [c.text for c in chunks]
        except Exception as e:
            logger.error("Multi-modal extraction failed", filename=filename, error=str(e))
            return []

    def query_with_image(self, question: str, corpus_id: str,
                          image_bytes: bytes, mime_type: str,
                          top_k: int = 5) -> RAGResponse:
        """
        RAG query where the question includes a reference image.
        E.g., 'What does this chart show compared to our historical data?'
        """
        # First, get text context from corpus
        chunks = self.hybrid_search(question, corpus_id, top_k)

        # Build multi-modal prompt
        context = "\n\n".join(
            [f"[Source {i+1}]\n{c.text}" for i, c in enumerate(chunks)]
        )

        prompt_parts = [
            Part.from_data(data=image_bytes, mime_type=mime_type),
            Part.from_text(f"""You are an enterprise intelligence assistant.
The user is asking about the attached image in the context of their document corpus.

Document Context:
{context}

Question: {question}

Answer based on BOTH the image content and the document context.
Cite sources with [Source N] when referencing documents."""),
        ]

        from time import monotonic
        t0 = monotonic()
        response = self._gemini_vision.generate_content(
            prompt_parts,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=1024),
        )
        latency_ms = int((monotonic() - t0) * 1000)

        from rag.schemas import Source
        return RAGResponse(
            answer=response.text,
            sources=[
                Source(
                    chunk_id=c.chunk_id,
                    doc_id=c.doc_id,
                    text_snippet=c.text[:200],
                    page_number=c.page_number,
                    score=round(c.score, 4),
                )
                for c in chunks
            ],
            confidence=0.8,
            model_used="gemini-1.5-pro-vision",
            latency_ms=latency_ms,
        )
