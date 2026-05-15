"""
Tests for Analytics Agent, Anomaly, Forecast, and KG API endpoints
"""

import pytest


# ════════════════════════════════════════════════════════
# Analytics Agent
# ════════════════════════════════════════════════════════

class TestAgentQuery:
    def test_nl_query_success(self, client, mock_bq, mock_ml, mock_cache):
        mock_bq.get_table_schema.return_value = {
            "sales": [{"column": "product", "type": "STRING"}, {"column": "revenue", "type": "FLOAT64"}]
        }
        mock_bq.safe_select.return_value = [
            {"product": "Widget A", "total": 12500.0},
            {"product": "Widget B", "total": 8300.0},
        ]
        resp = client.post("/v1/agent/query", json={
            "question": "Show me revenue by product",
            "dataset_id": "sales_dataset",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "sql_generated" in data
        assert data["row_count"] == 2
        assert data["chart_suggestion"] == "bar"
        assert "explanation" in data

    def test_nl_query_cached(self, client, mock_cache, mock_ml, mock_bq):
        mock_cache.get.return_value = {
            "sql_generated": "SELECT * FROM sales",
            "results": [],
            "chart_suggestion": "table",
            "explanation": "All sales",
            "row_count": 0,
            "execution_time_ms": 5.0,
            "cached": True,
        }
        resp = client.post("/v1/agent/query", json={
            "question": "Show all sales",
            "dataset_id": "sales_dataset",
        })
        assert resp.status_code == 200
        assert resp.json()["cached"] is True
        mock_ml.agent_nl2sql.assert_not_called()

    def test_nl_query_unsafe_sql(self, client, mock_bq, mock_ml, mock_cache):
        mock_bq.get_table_schema.return_value = {"sales": []}
        mock_ml.agent_nl2sql.return_value = {
            "sql": "DROP TABLE sales",
            "chart_type": "table",
            "explanation": "Dangerous",
        }
        resp = client.post("/v1/agent/query", json={
            "question": "Delete everything",
            "dataset_id": "sales_dataset",
        })
        assert resp.status_code == 400
        assert "safety validation" in resp.json()["detail"]

    def test_sql_validator(self):
        from app.routers.agent import validate_sql
        assert validate_sql("SELECT * FROM orders") is True
        assert validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte") is True
        assert validate_sql("DROP TABLE orders") is False
        assert validate_sql("DELETE FROM users") is False
        assert validate_sql("INSERT INTO foo VALUES (1)") is False
        assert validate_sql("UPDATE users SET name='x'") is False
        assert validate_sql("  select id from table") is False  # lowercase select is fine, but not "select" not starting word
        assert validate_sql("SELECT id FROM t; DROP TABLE t") is False  # contains DROP


class TestDatasetRegistry:
    def test_register_dataset(self, client, mock_bq, mock_firestore):
        mock_bq.get_table_schema.return_value = {"orders": [{"column": "id", "type": "STRING"}]}
        resp = client.post("/v1/agent/datasets", json={
            "dataset_id": "my_dataset",
            "display_name": "My Dataset",
            "description": "Sales data",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["dataset_id"] == "my_dataset"
        assert "schema" in data

    def test_list_datasets(self, client, mock_firestore):
        mock_firestore.list_documents.return_value = [
            {"id": "d1", "dataset_id": "ds1", "display_name": "DS1", "description": "",
             "tables": [], "tags": [], "registered_at": "2024-01-01", "owner_uid": "u1", "schema": {}}
        ]
        resp = client.get("/v1/agent/datasets")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_delete_dataset(self, client, mock_firestore):
        resp = client.delete("/v1/agent/datasets/ds1")
        assert resp.status_code == 200
        mock_firestore.delete_document.assert_called_once()


# ════════════════════════════════════════════════════════
# Anomaly Detection
# ════════════════════════════════════════════════════════

class TestAnomalyDetection:
    def test_detect_anomalies(self, client, mock_ml, mock_bq):
        resp = client.post("/v1/anomaly/detect", json={
            "dataset_id": "sensor_data",
            "time_column": "timestamp",
            "metric_columns": ["temperature", "pressure"],
            "sensitivity": "high",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_anomalies"] == 1
        assert data["anomalies"][0]["severity"] == "high"
        assert "job_id" in data

    def test_detect_anomalies_service_down(self, client, mock_ml):
        mock_ml.anomaly_detect.side_effect = Exception("Connection refused")
        resp = client.post("/v1/anomaly/detect", json={
            "dataset_id": "ds1",
            "time_column": "ts",
            "metric_columns": ["value"],
        })
        assert resp.status_code == 503

    def test_list_anomalies(self, client, mock_bq, mock_cache):
        mock_bq.list_anomalies.return_value = [
            {"anomaly_id": "a1", "dataset_id": "ds1", "severity": "high", "detected_at": "2024-01-01", "is_acknowledged": False}
        ]
        resp = client.get("/v1/anomaly/list?dataset_id=ds1")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_acknowledge_anomaly(self, client, mock_bq, mock_cache):
        resp = client.post("/v1/anomaly/acknowledge", json={"anomaly_id": "a1", "note": "Fixed"})
        assert resp.status_code == 200
        assert resp.json()["anomaly_id"] == "a1"
        mock_bq.update_row.assert_called_once()

    def test_anomaly_summary(self, client, mock_bq, mock_cache):
        mock_bq.query.return_value = [
            {"severity": "high", "count": 3, "avg_score": 0.85, "latest_detected": "2024-01-10"}
        ]
        resp = client.get("/v1/anomaly/summary?dataset_id=ds1")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data


# ════════════════════════════════════════════════════════
# Forecasting
# ════════════════════════════════════════════════════════

class TestForecasting:
    def test_run_forecast(self, client, mock_ml, mock_bq):
        resp = client.post("/v1/forecast/run", json={
            "dataset_id": "sales_data",
            "target_column": "revenue",
            "horizon_days": 30,
            "confidence_level": 0.95,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast_id" in data
        assert len(data["points"]) == 2
        assert data["model_version"] == "prophet-1.1"
        assert data["status"] == "completed"

    def test_run_forecast_service_down(self, client, mock_ml):
        mock_ml.forecast_run.side_effect = Exception("Service unavailable")
        resp = client.post("/v1/forecast/run", json={
            "dataset_id": "ds1",
            "target_column": "value",
            "horizon_days": 7,
        })
        assert resp.status_code == 503

    def test_get_forecast_results(self, client, mock_bq, mock_cache):
        mock_bq.get_forecast_results.return_value = [
            {
                "forecast_id": "f1",
                "dataset_id": "ds1",
                "target_column": "revenue",
                "forecast_timestamp": "2024-02-01T00:00:00",
                "predicted_value": 1250.0,
                "lower_bound": 1100.0,
                "upper_bound": 1400.0,
            }
        ]
        resp = client.get("/v1/forecast/results?forecast_id=f1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_points"] == 1
        assert data["points"][0]["predicted_value"] == 1250.0

    def test_get_forecast_results_not_found(self, client, mock_bq, mock_cache):
        mock_bq.get_forecast_results.return_value = []
        resp = client.get("/v1/forecast/results?forecast_id=missing")
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════
# Knowledge Graph
# ════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_create_graph(self, client, mock_firestore):
        resp = client.post("/v1/kg/graphs", json={
            "graph_id": "g1",
            "name": "Product Relations",
            "description": "KG of product relationships",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["graph_id"] == "g1"
        mock_firestore.set_document.assert_called_once()

    def test_list_graphs(self, client, mock_firestore):
        mock_firestore.list_documents.return_value = [
            {"id": "g1", "graph_id": "g1", "name": "KG1", "owner_uid": "u1", "created_at": "2024-01-01"}
        ]
        resp = client.get("/v1/kg/graphs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_extract_kg(self, client, mock_ml, mock_bq):
        resp = client.post("/v1/kg/extract", json={
            "document_ids": ["d1", "d2"],
            "graph_id": "g1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["graph_id"] == "g1"
        assert data["document_count"] == 2
        assert data["status"] == "processing"

    def test_extract_kg_service_down(self, client, mock_ml):
        mock_ml.kg_extract.side_effect = Exception("KG service down")
        resp = client.post("/v1/kg/extract", json={
            "document_ids": ["d1"],
            "graph_id": "g1",
        })
        assert resp.status_code == 503

    def test_query_kg(self, client, mock_ml, mock_cache):
        resp = client.post("/v1/kg/query", json={
            "graph_id": "g1",
            "query": "Who is Alice connected to?",
            "query_type": "natural_language",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_count"] == 1
        assert data["nodes"][0]["entity_name"] == "Alice"

    def test_subgraph(self, client, mock_ml, mock_cache):
        mock_ml.kg_subgraph.return_value = {
            "nodes": [{"node_id": "n1", "entity_type": "Person", "entity_name": "Alice", "properties": {}, "confidence": 0.9}],
            "edges": [],
        }
        resp = client.get("/v1/kg/subgraph?entity_id=n1&depth=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 1
        assert data["total_edges"] == 0
