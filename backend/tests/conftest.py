"""
EnterpriseIQ Backend — Test Configuration & Fixtures
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app


# ── Mock GCP Clients ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_firebase_init():
    """Prevent Firebase from initialising during tests."""
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.get_app", side_effect=ValueError("No app")):
        yield


@pytest.fixture
def mock_bq():
    client = MagicMock()
    client.query.return_value = []
    client.insert_rows.return_value = None
    client.update_row.return_value = None
    client.write_document_record.return_value = None
    client.write_chunk_records.return_value = None
    client.write_pipeline_run.return_value = None
    client.update_pipeline_run.return_value = None
    client.list_documents.return_value = []
    client.get_document.return_value = None
    client.list_anomalies.return_value = []
    client.get_forecast_results.return_value = []
    client.get_table_schema.return_value = {}
    client.safe_select.return_value = []
    client.write_audit_log.return_value = None
    client._ref = lambda table: f"project.dataset.{table}"
    return client


@pytest.fixture
def mock_gcs():
    client = MagicMock()
    client.upload_file.return_value = "gs://bucket/test/doc.pdf"
    client.download_file.return_value = b"sample document text content"
    client.list_files.return_value = ["file1.csv", "file2.json"]
    client.generate_signed_url.return_value = "https://signed.url/doc.pdf"
    return client


@pytest.fixture
def mock_firestore():
    client = MagicMock()
    client.get_document.return_value = None
    client.set_document.return_value = None
    client.update_document.return_value = None
    client.delete_document.return_value = None
    client.list_documents.return_value = []
    return client


@pytest.fixture
def mock_pubsub():
    client = MagicMock()
    client.publish.return_value = "msg-123"
    client.publish_document_ingested.return_value = None
    client.publish_pipeline_completed.return_value = None
    return client


@pytest.fixture
def mock_cache():
    store = {}
    client = MagicMock()
    client.get.side_effect = lambda key: store.get(key)
    client.set.side_effect = lambda key, value, ttl=None: store.update({key: value})
    client.delete.side_effect = lambda key: store.pop(key, None)
    client.delete_pattern.return_value = 0
    client.exists.side_effect = lambda key: key in store
    client.increment.return_value = 1
    return client


@pytest.fixture
def mock_ml():
    client = AsyncMock()
    client.rag_query.return_value = {
        "answer": "EnterpriseIQ is a data intelligence platform.",
        "sources": [
            {"chunk_id": "c1", "doc_id": "d1", "text": "EnterpriseIQ...", "page_number": 1, "score": 0.92}
        ],
        "confidence": 0.92,
    }
    client.anomaly_detect.return_value = {
        "job_id": "job-001",
        "anomalies": [
            {
                "anomaly_id": "a1",
                "dataset_id": "ds1",
                "detected_at": "2024-01-01T00:00:00",
                "metric_name": "revenue",
                "anomaly_score": 0.87,
                "actual_value": 1500.0,
                "expected_value": 1200.0,
                "lower_bound": 1000.0,
                "upper_bound": 1400.0,
                "is_acknowledged": False,
                "severity": "high",
            }
        ],
    }
    client.forecast_run.return_value = {
        "forecast": [
            {"ds": "2024-02-01", "yhat": 1250.0, "yhat_lower": 1100.0, "yhat_upper": 1400.0},
            {"ds": "2024-02-02", "yhat": 1260.0, "yhat_lower": 1110.0, "yhat_upper": 1410.0},
        ],
        "model_version": "prophet-1.1",
    }
    client.agent_nl2sql.return_value = {
        "sql": "SELECT product, SUM(revenue) as total FROM sales GROUP BY product",
        "chart_type": "bar",
        "explanation": "Aggregates revenue by product",
    }
    client.kg_extract.return_value = {
        "status": "processing",
        "nodes": [],
        "edges": [],
    }
    client.kg_query.return_value = {
        "nodes": [
            {"node_id": "n1", "entity_type": "Person", "entity_name": "Alice", "properties": {}, "confidence": 0.9}
        ],
        "edges": [],
        "explanation": "Found 1 matching entity",
    }
    client.kg_subgraph.return_value = {"nodes": [], "edges": []}
    return client


@pytest.fixture
def mock_firebase_user():
    """A mock authenticated user."""
    user = MagicMock()
    user.uid = "test-user-123"
    user.email = "test@enterpriseiq.com"
    user.name = "Test User"
    user.workspace_id = "ws-001"
    user.roles = ["analyst"]
    user.is_admin = False
    user.is_analyst = True
    return user


@pytest.fixture
def client(mock_bq, mock_gcs, mock_firestore, mock_pubsub, mock_cache, mock_ml, mock_firebase_user):
    """FastAPI TestClient with all dependencies overridden."""
    from app.core.auth import get_current_user
    from app.core.clients import get_bq, get_cache, get_firestore, get_gcs, get_pubsub
    from app.core.ml_client import get_ml_client
    from app.services.pipeline_service import get_pipeline_service

    app.dependency_overrides[get_bq] = lambda: mock_bq
    app.dependency_overrides[get_gcs] = lambda: mock_gcs
    app.dependency_overrides[get_firestore] = lambda: mock_firestore
    app.dependency_overrides[get_pubsub] = lambda: mock_pubsub
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_ml_client] = lambda: mock_ml
    app.dependency_overrides[get_current_user] = lambda: mock_firebase_user

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
