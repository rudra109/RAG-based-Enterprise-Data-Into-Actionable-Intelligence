"""
EnterpriseIQ ML — Shared BigQuery Client
Thin wrapper around google-cloud-bigquery with helpers used by all 5 services.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import structlog
from google.cloud import bigquery

from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class BigQueryClient:
    """Thread-safe BigQuery client shared across ML services."""

    def __init__(self) -> None:
        self._client = bigquery.Client(project=settings.bigquery_project)
        self._dataset = settings.bigquery_dataset
        logger.info("BigQueryClient initialised", dataset=self._dataset)

    # ── Generic helpers ──────────────────────────────────────────────

    def _table_ref(self, table: str) -> str:
        return f"{settings.bigquery_project}.{self._dataset}.{table}"

    def query(self, sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict]:
        """Execute a SELECT query and return rows as dicts."""
        job_config = bigquery.QueryJobConfig(query_parameters=params or [])
        job = self._client.query(sql, job_config=job_config)
        rows = job.result()
        return [dict(row) for row in rows]

    def insert_rows(self, table: str, rows: list[dict]) -> None:
        """Stream-insert rows into a BigQuery table."""
        table_ref = self._table_ref(table)
        errors = self._client.insert_rows_json(table_ref, rows)
        if errors:
            logger.error("BigQuery insert errors", table=table, errors=errors)
            raise RuntimeError(f"BigQuery insert failed for {table}: {errors}")
        logger.debug("Rows inserted", table=table, count=len(rows))

    # ── RAG helpers ──────────────────────────────────────────────────

    def get_chunks(self, chunk_ids: list[str]) -> list[dict]:
        """Fetch chunk text + metadata by chunk_ids (used by RAG retrieve)."""
        if not chunk_ids:
            return []
        ids_str = ", ".join(f"'{c}'" for c in chunk_ids)
        sql = f"""
            SELECT chunk_id, chunk_text, doc_id, page_number, token_count
            FROM `{self._table_ref("doc_chunks")}`
            WHERE chunk_id IN ({ids_str})
        """
        return self.query(sql)

    def full_text_search(self, query: str, corpus_id: str, limit: int = 10) -> list[dict]:
        """BM25-style keyword search via BigQuery SEARCH function."""
        sql = f"""
            SELECT chunk_id, chunk_text, doc_id,
                   SEARCH(chunk_text, @query) AS score
            FROM `{self._table_ref("doc_chunks")}`
            WHERE corpus_id = @corpus_id
              AND SEARCH(chunk_text, @query)
            ORDER BY score DESC
            LIMIT {limit}
        """
        params = [
            bigquery.ScalarQueryParameter("query", "STRING", query),
            bigquery.ScalarQueryParameter("corpus_id", "STRING", corpus_id),
        ]
        return self.query(sql, params)

    def get_dataset_schema(self, dataset_id: str) -> dict:
        """Return schema info for tables in a registered dataset."""
        sql = f"""
            SELECT table_name, column_name, data_type
            FROM `{settings.bigquery_project}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            ORDER BY table_name, ordinal_position
        """
        rows = self.query(sql)
        schema: dict[str, list[dict]] = {}
        for row in rows:
            schema.setdefault(row["table_name"], []).append(
                {"column": row["column_name"], "type": row["data_type"]}
            )
        return schema

    def load_dataset(self, dataset_id: str, table: str, limit: int = 10_000) -> list[dict]:
        """Load rows from a user dataset for ML processing."""
        sql = f"SELECT * FROM `{settings.bigquery_project}.{dataset_id}.{table}` LIMIT {limit}"
        return self.query(sql)

    # ── Anomaly helpers ──────────────────────────────────────────────

    def write_anomaly_results(self, anomalies: list[dict]) -> None:
        rows = [
            {
                "anomaly_id": a.get("anomaly_id", str(uuid.uuid4())),
                "dataset_id": a["dataset_id"],
                "detected_at": datetime.utcnow().isoformat(),
                "metric_name": a["metric_name"],
                "anomaly_score": a["anomaly_score"],
                "actual_value": a.get("actual_value"),
                "expected_value": a.get("expected_value"),
                "lower_bound": a.get("lower_bound"),
                "upper_bound": a.get("upper_bound"),
                "is_acknowledged": False,
                "severity": a.get("severity", "medium"),
            }
            for a in anomalies
        ]
        self.insert_rows("anomaly_results", rows)

    # ── Forecast helpers ─────────────────────────────────────────────

    def write_forecast_results(self, forecast_id: str, dataset_id: str,
                                target_col: str, rows: list[dict]) -> None:
        records = [
            {
                "forecast_id": forecast_id,
                "dataset_id": dataset_id,
                "target_column": target_col,
                "forecast_timestamp": r["ds"],
                "predicted_value": r["yhat"],
                "lower_bound": r["yhat_lower"],
                "upper_bound": r["yhat_upper"],
                "confidence_level": 0.95,
                "model_version": r.get("model_version", "1.0"),
            }
            for r in rows
        ]
        self.insert_rows("forecast_results", records)

    # ── KG helpers ───────────────────────────────────────────────────

    def write_kg_nodes(self, nodes: list[dict]) -> None:
        self.insert_rows("kg_nodes", nodes)

    def write_kg_edges(self, edges: list[dict]) -> None:
        self.insert_rows("kg_edges", edges)
