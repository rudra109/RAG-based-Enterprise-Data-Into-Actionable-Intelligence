"""
Tests for Pipeline API endpoints (/v1/pipeline/*)
"""

import pytest


class TestPipelineCreate:
    def test_create_pipeline(self, client, mock_firestore):
        resp = client.post("/v1/pipeline", json={
            "name": "Daily Ingestion",
            "pipeline_type": "document_ingestion",
            "description": "Ingests documents daily",
            "schedule": "0 2 * * *",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Daily Ingestion"
        assert data["pipeline_type"] == "document_ingestion"
        assert data["status"] == "active"
        assert "pipeline_id" in data
        mock_firestore.set_document.assert_called_once()

    def test_list_pipelines(self, client, mock_firestore):
        mock_firestore.list_documents.return_value = [
            {
                "id": "p1",
                "pipeline_id": "p1",
                "name": "Test Pipeline",
                "pipeline_type": "data_validator",
                "description": "",
                "status": "active",
                "schedule": None,
                "created_at": "2024-01-01",
                "last_run_id": None,
                "owner_uid": "test-user-123",
            }
        ]
        resp = client.get("/v1/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_create_pipeline_multi_source(self, client, mock_firestore):
        resp = client.post("/v1/pipeline", json={
            "name": "Salesforce Connector",
            "pipeline_type": "multi_source",
            "config": {"source_type": "rest_api", "url": "https://api.example.com/data"},
        })
        assert resp.status_code == 201
        assert resp.json()["pipeline_type"] == "multi_source"


class TestPipelineTrigger:
    def test_trigger_pipeline(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "pipeline_id": "p1",
            "name": "Test Pipeline",
            "pipeline_type": "document_ingestion",
            "owner_uid": "test-user-123",
            "config": {},
        }
        resp = client.post("/v1/pipeline/p1/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "run_id" in data

    def test_trigger_pipeline_not_found(self, client, mock_firestore):
        mock_firestore.get_document.return_value = None
        resp = client.post("/v1/pipeline/missing/trigger")
        assert resp.status_code == 404

    def test_trigger_pipeline_access_denied(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "pipeline_id": "p1",
            "owner_uid": "other-user",
            "config": {},
        }
        resp = client.post("/v1/pipeline/p1/trigger")
        assert resp.status_code == 403

    def test_delete_pipeline(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "pipeline_id": "p1",
            "owner_uid": "test-user-123",
        }
        resp = client.delete("/v1/pipeline/p1")
        assert resp.status_code == 200
        mock_firestore.delete_document.assert_called_once()


class TestPipelineService:
    @pytest.mark.asyncio
    async def test_chunk_text(self):
        from app.services.pipeline_service import PipelineService
        from unittest.mock import MagicMock
        svc = PipelineService(MagicMock(), MagicMock(), MagicMock())
        text = " ".join(["word"] * 1000)
        chunks = svc._chunk_text(text, max_tokens=100, overlap=10)
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk.split()) <= 100

    @pytest.mark.asyncio
    async def test_validate_row(self):
        from app.services.pipeline_service import PipelineService
        from unittest.mock import MagicMock
        svc = PipelineService(MagicMock(), MagicMock(), MagicMock())
        schema = {
            "name": {"required": True, "type": "string"},
            "age": {"required": True, "type": "number"},
        }
        # Valid row
        errors = svc._validate_row({"name": "Alice", "age": 30}, schema)
        assert errors == []
        # Missing required
        errors = svc._validate_row({"name": "Bob"}, schema)
        assert any("age" in e for e in errors)
        # Wrong type
        errors = svc._validate_row({"name": 123, "age": 30}, schema)
        assert any("name" in e for e in errors)

    @pytest.mark.asyncio
    async def test_extract_text_txt(self):
        from app.services.pipeline_service import PipelineService
        from unittest.mock import MagicMock
        svc = PipelineService(MagicMock(), MagicMock(), MagicMock())
        text = svc._extract_text(b"Hello world from TXT", "txt", "test.txt")
        assert "Hello world" in text

    @pytest.mark.asyncio
    async def test_extract_text_json(self):
        import json
        from app.services.pipeline_service import PipelineService
        from unittest.mock import MagicMock
        svc = PipelineService(MagicMock(), MagicMock(), MagicMock())
        data = json.dumps({"key": "value"}).encode()
        text = svc._extract_text(data, "json", "test.json")
        assert "key" in text
