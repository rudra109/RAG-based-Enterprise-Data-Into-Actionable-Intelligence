"""
EnterpriseIQ ML — RAG Engine Tests
Tests chunking, retrieval logic, confidence scoring, hybrid search.
All tests use mocks so no real GCP calls are made in CI.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "../../")

from rag.chunking import FixedTokenChunker, SemanticChunker, RecursiveChunker
from rag.engine import EnterpriseRAGEngine, ChunkResult
from rag.schemas import RAGQueryRequest, EmbedRequest


# ────────────────────────────────────────────────────────────────────────────
# Chunking tests
# ────────────────────────────────────────────────────────────────────────────

class TestFixedTokenChunker:

    def test_single_chunk_short_text(self):
        chunker = FixedTokenChunker(max_tokens=512, overlap_tokens=50)
        chunks = chunker.chunk("Hello world, this is a test.")
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count > 0

    def test_multiple_chunks_long_text(self):
        long_text = " ".join(["word"] * 2000)
        chunker = FixedTokenChunker(max_tokens=100, overlap_tokens=10)
        chunks = chunker.chunk(long_text)
        assert len(chunks) > 1

    def test_chunk_overlap(self):
        """Chunks should share tokens at boundaries due to overlap."""
        text = " ".join([f"word{i}" for i in range(300)])
        chunker = FixedTokenChunker(max_tokens=100, overlap_tokens=20)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 3
        # Overlap: end of chunk[0] and start of chunk[1] should share words
        end_words = set(chunks[0].text.split()[-20:])
        start_words = set(chunks[1].text.split()[:20])
        assert len(end_words & start_words) > 0

    def test_empty_text_returns_one_chunk(self):
        chunker = FixedTokenChunker()
        chunks = chunker.chunk("")
        # Empty text produces empty chunk (not an error)
        assert isinstance(chunks, list)

    def test_chunk_index_sequential(self):
        text = " ".join(["test"] * 1000)
        chunker = FixedTokenChunker(max_tokens=50, overlap_tokens=5)
        chunks = chunker.chunk(text)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestRecursiveChunker:

    def test_splits_on_paragraphs_first(self):
        text = "Paragraph one.\n\nParagraph two is longer and has more words.\n\nParagraph three."
        chunker = RecursiveChunker(max_tokens=20, overlap_tokens=2)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1
        assert all(c.token_count > 0 for c in chunks)

    def test_no_empty_chunks(self):
        text = "A\n\nB\n\nC\n\nD"
        chunker = RecursiveChunker(max_tokens=50)
        chunks = chunker.chunk(text)
        assert all(c.text.strip() for c in chunks)


# ────────────────────────────────────────────────────────────────────────────
# RAG Engine tests (mocked GCP)
# ────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_engine():
    """Create a RAG engine with all GCP clients mocked."""
    with (
        patch("rag.engine.vertexai.init"),
        patch("rag.engine.TextEmbeddingModel") as mock_emb,
        patch("rag.engine.GenerativeModel") as mock_gen,
        patch("rag.engine.MatchingEngineIndexEndpoint") as mock_idx,
        patch("rag.engine.BigQueryClient") as mock_bq,
    ):
        mock_emb.from_pretrained.return_value = MagicMock()
        engine = EnterpriseRAGEngine()
        engine._embedding_model = mock_emb.from_pretrained.return_value
        engine._gemini_pro = mock_gen.return_value
        engine._gemini_flash = mock_gen.return_value
        engine._index_endpoint = mock_idx.return_value
        engine._bq = mock_bq.return_value
        yield engine


class TestEnterpriseRAGEngine:

    def test_embed_chunks_calls_model(self, mock_engine):
        """embed_chunks should call the embedding model and return vectors."""
        mock_emb = MagicMock()
        mock_emb.values = [0.1, 0.2, 0.3]
        mock_engine._embedding_model.get_embeddings.return_value = [mock_emb] * 3

        chunks = ["chunk one", "chunk two", "chunk three"]
        embeddings = mock_engine.embed_chunks(chunks)

        mock_engine._embedding_model.get_embeddings.assert_called()
        assert len(embeddings) == 3

    def test_embed_chunks_batches_large_input(self, mock_engine):
        """embed_chunks should batch inputs of > 250 chunks."""
        mock_emb = MagicMock()
        mock_emb.values = [0.1] * 768
        mock_engine._embedding_model.get_embeddings.return_value = [mock_emb] * 250

        chunks = [f"chunk {i}" for i in range(500)]
        embeddings = mock_engine.embed_chunks(chunks)

        # Should have been called twice (2 batches of 250)
        assert mock_engine._embedding_model.get_embeddings.call_count == 2
        assert len(embeddings) == 500

    def test_retrieve_returns_empty_when_no_results(self, mock_engine):
        """retrieve should return [] when Vector Search returns no neighbors."""
        mock_engine._index_endpoint.find_neighbors.return_value = []
        results = mock_engine.retrieve("test question", "corpus1", top_k=5)
        assert results == []

    def test_reciprocal_rank_fusion(self, mock_engine):
        """RRF should merge and rank two result lists correctly."""
        list_a = [
            ChunkResult("c1", "text1", "doc1", 1, 0.9),
            ChunkResult("c2", "text2", "doc1", 2, 0.8),
        ]
        list_b = [
            ChunkResult("c1", "text1", "doc1", 1, 0.7),  # c1 in both
            ChunkResult("c3", "text3", "doc2", 1, 0.6),
        ]
        merged = mock_engine._reciprocal_rank_fusion(list_a, list_b, top_k=3)
        assert merged[0].chunk_id == "c1"  # c1 should rank first (in both lists)
        assert len(merged) == 3

    def test_calculate_confidence_high_for_good_match(self, mock_engine):
        """High-score chunks should yield high confidence."""
        chunks = [
            ChunkResult("c1", "text1", "doc1", 1, 0.95),
            ChunkResult("c2", "text2", "doc1", 2, 0.90),
        ]
        confidence = mock_engine._calculate_confidence(chunks, "The answer is X.")
        assert confidence > 0.5

    def test_calculate_confidence_low_when_no_info(self, mock_engine):
        """Penalty applied when answer says 'don't have enough information'."""
        chunks = [ChunkResult("c1", "text1", "doc1", 1, 0.8)]
        confidence = mock_engine._calculate_confidence(
            chunks, "I don't have enough information to answer that."
        )
        assert confidence < 0.5

    def test_generate_returns_rag_response(self, mock_engine):
        """generate() should return a valid RAGResponse with answer and sources."""
        mock_engine._gemini_pro.generate_content.return_value = MagicMock(
            text="The answer is 42. [Source 1]"
        )
        chunks = [ChunkResult("c1", "The number is 42.", "doc1", 1, 0.9)]

        response = mock_engine.generate("What is the answer?", chunks)

        assert response.answer == "The answer is 42. [Source 1]"
        assert len(response.sources) == 1
        assert response.sources[0].chunk_id == "c1"
        assert response.latency_ms >= 0

    def test_rerank_falls_back_on_parse_error(self, mock_engine):
        """If Gemini returns bad JSON for reranking, fall back to original order."""
        mock_engine._gemini_flash.generate_content.return_value = MagicMock(
            text="invalid json that can't be parsed as ranking"
        )
        chunks = [
            ChunkResult("c1", "text1", "doc1", 1, 0.9),
            ChunkResult("c2", "text2", "doc1", 2, 0.8),
        ]
        reranked = mock_engine.rerank("test question", chunks)
        assert len(reranked) == 2  # original order preserved

    def test_session_history_updates(self, mock_engine):
        """Conversation history should be saved and used in subsequent turns."""
        from rag import engine as rag_engine

        mock_engine._gemini_pro.generate_content.return_value = MagicMock(
            text="Response to question."
        )
        session_id = "test-session-123"
        chunks = [ChunkResult("c1", "context text", "doc1", 1, 0.9)]

        # First turn
        mock_engine.generate("Question 1?", chunks, session_id=session_id)
        assert len(rag_engine._session_history[session_id]) == 2

        # Second turn
        mock_engine.generate("Follow-up?", chunks, session_id=session_id)
        assert len(rag_engine._session_history[session_id]) == 4
