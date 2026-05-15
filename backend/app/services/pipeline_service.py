"""
EnterpriseIQ Backend — Pipeline Service
Implements document ingestion, data validation, and multi-source connector logic.
"""

from __future__ import annotations

import io
import json
import uuid
from datetime import datetime
from typing import Any, Optional

import structlog

from app.core.clients import (
    BigQueryClient,
    GCSClient,
    PubSubClient,
    get_bq,
    get_gcs,
    get_pubsub,
)
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class PipelineService:
    """Executes data ingestion pipelines without Cloud Dataflow dependency in dev mode."""

    def __init__(
        self,
        bq: BigQueryClient,
        gcs: GCSClient,
        pubsub: PubSubClient,
    ) -> None:
        self._bq = bq
        self._gcs = gcs
        self._pubsub = pubsub

    async def execute_pipeline(
        self,
        pipeline_id: str,
        run_id: str,
        pipeline_config: dict,
    ) -> None:
        """Dispatch to the correct pipeline handler based on pipeline_type."""
        pipeline_type = pipeline_config.get("pipeline_type", "")
        started_at = datetime.utcnow()

        # Record pipeline start
        run_record = {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_config.get("name", ""),
            "status": "running",
            "started_at": started_at.isoformat(),
            "completed_at": None,
            "records_processed": 0,
            "records_failed": 0,
            "error_message": None,
        }
        try:
            self._bq.write_pipeline_run(run_record)
        except Exception as e:
            logger.warning("Could not write pipeline run to BQ", error=str(e))

        try:
            if pipeline_type == "document_ingestion":
                stats = await self._run_document_ingestion(run_id, pipeline_config.get("config", {}))
            elif pipeline_type == "data_validator":
                stats = await self._run_data_validator(run_id, pipeline_config.get("config", {}))
            elif pipeline_type == "multi_source":
                stats = await self._run_multi_source(run_id, pipeline_config.get("config", {}))
            else:
                raise ValueError(f"Unknown pipeline_type: {pipeline_type}")

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Update run status
            try:
                self._bq.update_pipeline_run(run_id, {
                    "status": "success",
                    "completed_at": completed_at.isoformat(),
                    "records_processed": str(stats.get("records_processed", 0)),
                    "records_failed": str(stats.get("records_failed", 0)),
                })
            except Exception as e:
                logger.warning("Could not update pipeline run in BQ", error=str(e))

            # Publish completion event
            try:
                self._pubsub.publish_pipeline_completed(
                    pipeline_id=pipeline_id,
                    run_id=run_id,
                    status="success",
                    records_processed=stats.get("records_processed", 0),
                    duration_seconds=duration,
                )
            except Exception as e:
                logger.warning("Could not publish pipeline completion event", error=str(e))

            logger.info(
                "Pipeline completed",
                pipeline_id=pipeline_id,
                run_id=run_id,
                duration=duration,
                **stats,
            )

        except Exception as exc:
            logger.error("Pipeline failed", pipeline_id=pipeline_id, run_id=run_id, error=str(exc))
            try:
                self._bq.update_pipeline_run(run_id, {
                    "status": "failed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "error_message": str(exc)[:1000],
                })
            except Exception:
                pass

    async def _run_document_ingestion(self, run_id: str, config: dict) -> dict:
        """
        Document Ingestion Pipeline:
        GCS → extract text → chunk → write to BigQuery → publish event
        """
        gcs_uri = config.get("gcs_uri", "")
        corpus_id = config.get("corpus_id", "")
        doc_id = config.get("doc_id", str(uuid.uuid4()))

        if not gcs_uri:
            logger.warning("No gcs_uri in pipeline config, skipping extraction")
            return {"records_processed": 0, "records_failed": 0}

        # Parse bucket and blob from gs:// URI
        parts = gcs_uri.replace("gs://", "").split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""

        try:
            raw_bytes = self._gcs.download_file(bucket_name, blob_name)
        except Exception as e:
            raise RuntimeError(f"GCS download failed: {e}")

        # Extract text based on file type
        file_type = blob_name.rsplit(".", 1)[-1].lower()
        text = self._extract_text(raw_bytes, file_type, blob_name)

        # Chunk the text
        chunks = self._chunk_text(text, max_tokens=512, overlap=50)

        # Write chunks to BigQuery
        chunk_records = [
            {
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "corpus_id": corpus_id,
                "chunk_text": chunk,
                "chunk_index": i,
                "embedding_id": "",
                "page_number": None,
                "token_count": len(chunk.split()),
                "created_at": datetime.utcnow().isoformat(),
            }
            for i, chunk in enumerate(chunks)
        ]

        if chunk_records:
            self._bq.write_chunk_records(chunk_records)

        # Update document status
        try:
            self._bq.update_row("documents", "doc_id", doc_id, {"status": "indexed", "embedding_count": str(len(chunks))})
        except Exception as e:
            logger.warning("Could not update document status", error=str(e))

        # Publish ingestion event
        try:
            self._pubsub.publish_document_ingested(doc_id, corpus_id, gcs_uri, file_type)
        except Exception as e:
            logger.warning("PubSub publish failed", error=str(e))

        return {"records_processed": len(chunks), "records_failed": 0}

    async def _run_data_validator(self, run_id: str, config: dict) -> dict:
        """
        Data Validator Pipeline:
        BigQuery source → validate schema → write valid/invalid records
        """
        source_dataset = config.get("source_dataset", "")
        source_table = config.get("source_table", "")
        target_table = config.get("target_table", "")
        error_table = config.get("error_table", "pipeline_errors")

        if not all([source_dataset, source_table]):
            return {"records_processed": 0, "records_failed": 0}

        from google.cloud import bigquery as bq_lib
        sql = f"SELECT * FROM `{settings.bigquery_project}.{source_dataset}.{source_table}` LIMIT 10000"
        rows = self._bq.query(sql)

        valid_rows, invalid_rows = [], []
        for row in rows:
            errors = self._validate_row(row, config.get("schema", {}))
            if errors:
                invalid_rows.append({**row, "_validation_errors": json.dumps(errors), "_run_id": run_id})
            else:
                valid_rows.append(row)

        if valid_rows and target_table:
            self._bq.insert_rows(target_table, valid_rows)
        if invalid_rows:
            self._bq.insert_rows(error_table, invalid_rows)

        return {"records_processed": len(valid_rows), "records_failed": len(invalid_rows)}

    async def _run_multi_source(self, run_id: str, config: dict) -> dict:
        """
        Multi-Source Connector Pipeline:
        REST API / GCS / BigQuery → normalized records → staging table
        """
        source_type = config.get("source_type", "gcs")
        records_processed = 0

        if source_type == "gcs":
            bucket = config.get("bucket", settings.gcs_raw_bucket)
            prefix = config.get("prefix", "")
            blobs = self._gcs.list_files(bucket, prefix=prefix)
            records_processed = len(blobs)
            logger.info("Multi-source: GCS files found", count=records_processed)

        elif source_type == "rest_api":
            import httpx
            url = config.get("url", "")
            headers = config.get("headers", {})
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=30.0)
                data = resp.json()
            records = data if isinstance(data, list) else data.get("data", data.get("results", []))
            records_processed = len(records) if isinstance(records, list) else 1

        return {"records_processed": records_processed, "records_failed": 0}

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _extract_text(self, raw: bytes, file_type: str, filename: str) -> str:
        """Extract plain text from various file formats."""
        try:
            if file_type == "pdf":
                from pdfminer.high_level import extract_text as pdf_extract
                return pdf_extract(io.BytesIO(raw)) or ""
            elif file_type in ("docx", "doc"):
                from docx import Document
                doc = Document(io.BytesIO(raw))
                return "\n".join(p.text for p in doc.paragraphs)
            elif file_type == "csv":
                import pandas as pd
                df = pd.read_csv(io.BytesIO(raw))
                return df.to_string()
            elif file_type == "json":
                data = json.loads(raw)
                return json.dumps(data, indent=2)
            else:
                return raw.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("Text extraction failed", file_type=file_type, error=str(e))
            return raw.decode("utf-8", errors="replace")

    def _chunk_text(self, text: str, max_tokens: int = 512, overlap: int = 50) -> list[str]:
        """Simple word-based chunking with overlap."""
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max_tokens - overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i: i + max_tokens])
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def _validate_row(self, row: dict, schema: dict) -> list[str]:
        """Validate a row against a schema definition."""
        errors = []
        for field, rules in schema.items():
            value = row.get(field)
            if rules.get("required") and value is None:
                errors.append(f"Missing required field: {field}")
            if value is not None and "type" in rules:
                expected_type = rules["type"]
                if expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be numeric, got {type(value).__name__}")
                elif expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field} must be string, got {type(value).__name__}")
        return errors


# ── Dependency ────────────────────────────────────────────────────────────────

_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    global _service
    if _service is None:
        _service = PipelineService(
            bq=get_bq(),
            gcs=get_gcs(),
            pubsub=get_pubsub(),
        )
    return _service
