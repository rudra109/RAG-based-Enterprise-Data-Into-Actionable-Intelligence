"""
Tests for RAG API endpoints (/v1/rag/*)
"""

import io
import pytest


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "EnterpriseIQ" in resp.json()["name"]


class TestRAGCorpus:
    def test_create_corpus(self, client, mock_firestore):
        mock_firestore.get_document.return_value = None
        resp = client.post("/v1/rag/corpus", json={"name": "Test Corpus", "description": "Unit test"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Corpus"
        assert "corpus_id" in data
        mock_firestore.set_document.assert_called_once()

    def test_list_corpora(self, client, mock_firestore):
        mock_firestore.list_documents.return_value = [
            {"id": "c1", "corpus_id": "c1", "name": "Corpus 1", "description": "", "owner_uid": "u1", "created_at": "2024-01-01", "document_count": 0}
        ]
        resp = client.get("/v1/rag/corpus")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_get_corpus(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "corpus_id": "c1",
            "name": "My Corpus",
            "description": "",
            "owner_uid": "test-user-123",
            "created_at": "2024-01-01",
            "document_count": 5,
        }
        resp = client.get("/v1/rag/corpus/c1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Corpus"

    def test_delete_corpus(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "corpus_id": "c1",
            "owner_uid": "test-user-123",
            "name": "Corpus",
        }
        resp = client.delete("/v1/rag/corpus/c1")
        assert resp.status_code == 200
        mock_firestore.delete_document.assert_called_once()

    def test_delete_corpus_not_found(self, client, mock_firestore):
        mock_firestore.get_document.return_value = None
        resp = client.delete("/v1/rag/corpus/missing")
        assert resp.status_code == 404


class TestRAGDocuments:
    def test_ingest_document(self, client, mock_gcs, mock_bq, mock_pubsub):
        mock_gcs.upload_file.return_value = "gs://bucket/corpus-1/doc-id/test.txt"
        file_content = b"This is a test document for the RAG system."
        resp = client.post(
            "/v1/rag/ingest",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={"corpus_id": "corpus-1", "metadata": "{}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "ingesting"
        assert data["corpus_id"] == "corpus-1"
        assert "doc_id" in data
        mock_gcs.upload_file.assert_called_once()
        mock_bq.write_document_record.assert_called_once()

    def test_list_documents(self, client, mock_bq):
        mock_bq.list_documents.return_value = [
            {"doc_id": "d1", "filename": "report.pdf", "status": "indexed", "corpus_id": "c1", "size_bytes": 1024}
        ]
        resp = client.get("/v1/rag/documents?corpus_id=c1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["documents"][0]["doc_id"] == "d1"

    def test_get_document(self, client, mock_bq):
        mock_bq.get_document.return_value = {
            "doc_id": "d1", "filename": "report.pdf", "status": "indexed", "corpus_id": "c1"
        }
        resp = client.get("/v1/rag/documents/d1")
        assert resp.status_code == 200

    def test_get_document_not_found(self, client, mock_bq):
        mock_bq.get_document.return_value = None
        resp = client.get("/v1/rag/documents/missing")
        assert resp.status_code == 404

    def test_delete_document(self, client, mock_bq, mock_gcs):
        mock_bq.get_document.return_value = {"doc_id": "d1", "corpus_id": "c1", "gcs_uri": "gs://bucket/d1"}
        resp = client.delete("/v1/rag/documents/d1")
        assert resp.status_code == 200
        assert resp.json()["doc_id"] == "d1"


class TestRAGQuery:
    def test_query_rag(self, client, mock_ml, mock_cache):
        resp = client.post("/v1/rag/query", json={
            "question": "What is EnterpriseIQ?",
            "corpus_id": "c1",
            "top_k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert data["confidence"] > 0
        assert data["cached"] is False

    def test_query_rag_cache_hit(self, client, mock_cache, mock_ml):
        cached_data = {
            "answer": "Cached answer",
            "sources": [],
            "confidence": 0.85,
            "cached": True,
            "question": "What is EnterpriseIQ?",
            "corpus_id": "c1",
        }
        mock_cache.get.return_value = cached_data
        resp = client.post("/v1/rag/query", json={
            "question": "What is EnterpriseIQ?",
            "corpus_id": "c1",
        })
        assert resp.status_code == 200
        assert resp.json()["cached"] is True
        mock_ml.rag_query.assert_not_called()

    def test_query_rag_ml_unavailable(self, client, mock_ml, mock_cache):
        import httpx
        mock_ml.rag_query.side_effect = httpx.ConnectError("Connection refused")
        resp = client.post("/v1/rag/query", json={
            "question": "What is this?",
            "corpus_id": "c1",
        })
        assert resp.status_code == 503
