"""
EnterpriseIQ Backend — Shared Infrastructure Clients
BigQuery, GCS, Firestore, Pub/Sub, Redis
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

import redis as _redis
import structlog
from google.cloud import bigquery, firestore, pubsub_v1, storage

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ══════════════════════════════════════════════════════════════════════════════
# BigQuery Client
# ══════════════════════════════════════════════════════════════════════════════

class BigQueryClient:
    """Thread-safe BigQuery wrapper for the API layer."""

    def __init__(self) -> None:
        self._client = bigquery.Client(project=settings.bigquery_project)
        self._dataset = settings.bigquery_dataset
        logger.info("BigQueryClient ready", dataset=self._dataset)

    def _ref(self, table: str) -> str:
        return f"{settings.bigquery_project}.{self._dataset}.{table}"

    def query(
        self,
        sql: str,
        params: list[bigquery.ScalarQueryParameter] | None = None,
        timeout: float = 30.0,
    ) -> list[dict]:
        cfg = bigquery.QueryJobConfig(query_parameters=params or [])
        job = self._client.query(sql, job_config=cfg)
        return [dict(row) for row in job.result(timeout=timeout)]

    def insert_rows(self, table: str, rows: list[dict]) -> None:
        errors = self._client.insert_rows_json(self._ref(table), rows)
        if errors:
            raise RuntimeError(f"BQ insert failed [{table}]: {errors}")
        logger.debug("BQ rows inserted", table=table, count=len(rows))

    def update_row(self, table: str, row_id_col: str, row_id: str, updates: dict) -> None:
        set_clause = ", ".join(f"{k} = @{k}" for k in updates)
        params = [bigquery.ScalarQueryParameter(row_id_col, "STRING", row_id)]
        for k, v in updates.items():
            params.append(bigquery.ScalarQueryParameter(k, "STRING", str(v)))
        sql = f"UPDATE `{self._ref(table)}` SET {set_clause} WHERE {row_id_col} = @{row_id_col}"
        self._client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()

    def get_table_schema(self, dataset_id: str) -> dict[str, list[dict]]:
        sql = f"""
            SELECT table_name, column_name, data_type
            FROM `{settings.bigquery_project}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            ORDER BY table_name, ordinal_position
        """
        rows = self.query(sql)
        schema: dict = {}
        for r in rows:
            schema.setdefault(r["table_name"], []).append(
                {"column": r["column_name"], "type": r["data_type"]}
            )
        return schema

    def safe_select(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute only SELECT statements (safety guard)."""
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
            raise ValueError("Only SELECT queries are allowed")
        return self.query(sql, params)

    def write_document_record(self, doc: dict) -> None:
        self.insert_rows("documents", [doc])

    def write_chunk_records(self, chunks: list[dict]) -> None:
        self.insert_rows("doc_chunks", chunks)

    def write_pipeline_run(self, run: dict) -> None:
        self.insert_rows("pipeline_runs", [run])

    def update_pipeline_run(self, run_id: str, updates: dict) -> None:
        self.update_row("pipeline_runs", "run_id", run_id, updates)

    def list_documents(self, corpus_id: str, limit: int = 100) -> list[dict]:
        sql = f"""
            SELECT doc_id, filename, gcs_uri, corpus_id, upload_timestamp,
                   file_type, size_bytes, status, embedding_count
            FROM `{self._ref("documents")}`
            WHERE corpus_id = @corpus_id
            ORDER BY upload_timestamp DESC
            LIMIT {limit}
        """
        return self.query(sql, [bigquery.ScalarQueryParameter("corpus_id", "STRING", corpus_id)])

    def get_document(self, doc_id: str) -> Optional[dict]:
        sql = f"SELECT * FROM `{self._ref('documents')}` WHERE doc_id = @doc_id LIMIT 1"
        rows = self.query(sql, [bigquery.ScalarQueryParameter("doc_id", "STRING", doc_id)])
        return rows[0] if rows else None

    def list_anomalies(self, dataset_id: str, start_time: str | None = None, limit: int = 500) -> list[dict]:
        sql = f"""
            SELECT * FROM `{self._ref("anomaly_results")}`
            WHERE dataset_id = @dataset_id
            {"AND detected_at >= @start_time" if start_time else ""}
            ORDER BY detected_at DESC
            LIMIT {limit}
        """
        params = [bigquery.ScalarQueryParameter("dataset_id", "STRING", dataset_id)]
        if start_time:
            params.append(bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_time))
        return self.query(sql, params)

    def get_forecast_results(self, forecast_id: str) -> list[dict]:
        sql = f"""
            SELECT * FROM `{self._ref("forecast_results")}`
            WHERE forecast_id = @forecast_id
            ORDER BY forecast_timestamp
        """
        return self.query(sql, [bigquery.ScalarQueryParameter("forecast_id", "STRING", forecast_id)])

    def write_audit_log(self, entry: dict) -> None:
        self.insert_rows("audit_log", [entry])


# ══════════════════════════════════════════════════════════════════════════════
# GCS Client
# ══════════════════════════════════════════════════════════════════════════════

class GCSClient:
    """Google Cloud Storage wrapper."""

    def __init__(self) -> None:
        self._client = storage.Client(project=settings.gcp_project_id)
        logger.info("GCSClient ready")

    def upload_file(self, bucket_name: str, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)
        gcs_uri = f"gs://{bucket_name}/{blob_name}"
        logger.info("File uploaded to GCS", uri=gcs_uri)
        return gcs_uri

    def download_file(self, bucket_name: str, blob_name: str) -> bytes:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    def delete_file(self, bucket_name: str, blob_name: str) -> None:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.delete()
        logger.info("GCS file deleted", bucket=bucket_name, blob=blob_name)

    def list_files(self, bucket_name: str, prefix: str = "") -> list[str]:
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [b.name for b in blobs]

    def generate_signed_url(self, bucket_name: str, blob_name: str, expiration_minutes: int = 15) -> str:
        from datetime import timedelta
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes))


# ══════════════════════════════════════════════════════════════════════════════
# Firestore Client
# ══════════════════════════════════════════════════════════════════════════════

class FirestoreClient:
    """Cloud Firestore wrapper for metadata, config, and user data."""

    def __init__(self) -> None:
        self._db = firestore.Client(project=settings.firestore_project)
        logger.info("FirestoreClient ready")

    def set_document(self, collection: str, doc_id: str, data: dict) -> None:
        self._db.collection(collection).document(doc_id).set(data, merge=True)

    def get_document(self, collection: str, doc_id: str) -> Optional[dict]:
        doc = self._db.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    def delete_document(self, collection: str, doc_id: str) -> None:
        self._db.collection(collection).document(doc_id).delete()

    def list_documents(self, collection: str, filters: list[tuple] | None = None) -> list[dict]:
        ref = self._db.collection(collection)
        if filters:
            for field, op, value in filters:
                ref = ref.where(field, op, value)
        return [{"id": d.id, **d.to_dict()} for d in ref.stream()]

    def update_document(self, collection: str, doc_id: str, updates: dict) -> None:
        self._db.collection(collection).document(doc_id).update(updates)


# ══════════════════════════════════════════════════════════════════════════════
# Pub/Sub Client
# ══════════════════════════════════════════════════════════════════════════════

class PubSubClient:
    """Cloud Pub/Sub publisher wrapper."""

    def __init__(self) -> None:
        self._publisher = pubsub_v1.PublisherClient()
        self._project = settings.pubsub_project
        logger.info("PubSubClient ready", project=self._project)

    def _topic_path(self, topic_name: str) -> str:
        return self._publisher.topic_path(self._project, topic_name)

    def publish(self, topic_name: str, data: dict, attributes: dict | None = None) -> str:
        payload = json.dumps(data).encode("utf-8")
        future = self._publisher.publish(
            self._topic_path(topic_name),
            payload,
            **(attributes or {}),
        )
        msg_id = future.result(timeout=10)
        logger.debug("Pub/Sub message published", topic=topic_name, msg_id=msg_id)
        return msg_id

    def publish_document_ingested(self, doc_id: str, corpus_id: str, gcs_uri: str, file_type: str, triggered_by: str = "api") -> None:
        self.publish(
            settings.pubsub_topic_document_ingested,
            {
                "event_type": "document.ingested",
                "doc_id": doc_id,
                "corpus_id": corpus_id,
                "gcs_uri": gcs_uri,
                "file_type": file_type,
                "timestamp": datetime.utcnow().isoformat(),
                "triggered_by": triggered_by,
            },
        )

    def publish_pipeline_completed(self, pipeline_id: str, run_id: str, status: str, records_processed: int, duration_seconds: float) -> None:
        self.publish(
            settings.pubsub_topic_pipeline_completed,
            {
                "event_type": "pipeline.completed",
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "status": status,
                "records_processed": records_processed,
                "duration_seconds": duration_seconds,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# ══════════════════════════════════════════════════════════════════════════════
# Redis Cache Client
# ══════════════════════════════════════════════════════════════════════════════

class CacheClient:
    """Redis caching layer."""

    def __init__(self) -> None:
        self._r = _redis.from_url(settings.redis_url, decode_responses=True)
        self._default_ttl = settings.redis_ttl_seconds
        logger.info("CacheClient ready", url=settings.redis_url)

    def get(self, key: str) -> Optional[Any]:
        raw = self._r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        payload = json.dumps(value) if not isinstance(value, str) else value
        self._r.setex(key, ttl or self._default_ttl, payload)

    def delete(self, key: str) -> None:
        self._r.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        keys = self._r.keys(pattern)
        if keys:
            return self._r.delete(*keys)
        return 0

    def exists(self, key: str) -> bool:
        return bool(self._r.exists(key))

    def increment(self, key: str, ttl: int = 60) -> int:
        pipe = self._r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = pipe.execute()
        return results[0]


# ══════════════════════════════════════════════════════════════════════════════
# Singleton factories (used via FastAPI Depends)
# ══════════════════════════════════════════════════════════════════════════════

_bq: Optional[BigQueryClient] = None
_gcs: Optional[GCSClient] = None
_fs: Optional[FirestoreClient] = None
_ps: Optional[PubSubClient] = None
_cache: Optional[CacheClient] = None


def get_bq() -> BigQueryClient:
    global _bq
    if _bq is None:
        _bq = BigQueryClient()
    return _bq


def get_gcs() -> GCSClient:
    global _gcs
    if _gcs is None:
        _gcs = GCSClient()
    return _gcs


def get_firestore() -> FirestoreClient:
    global _fs
    if _fs is None:
        _fs = FirestoreClient()
    return _fs


def get_pubsub() -> PubSubClient:
    global _ps
    if _ps is None:
        _ps = PubSubClient()
    return _ps


def get_cache() -> CacheClient:
    global _cache
    if _cache is None:
        _cache = CacheClient()
    return _cache
