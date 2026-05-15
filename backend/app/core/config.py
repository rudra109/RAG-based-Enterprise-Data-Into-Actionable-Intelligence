"""
EnterpriseIQ Backend — Shared Configuration
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_workers: int = 4
    api_debug: bool = False
    api_secret_key: str = "change-me"
    cors_origins: str = "http://localhost:3000"

    # ── Google Cloud ─────────────────────────────────────────
    gcp_project_id: str = "enterpriseiq-dev"
    gcp_region: str = "us-central1"
    google_application_credentials: str = ""

    # ── Firebase Auth ────────────────────────────────────────
    firebase_project_id: str = "enterpriseiq-dev"
    firebase_service_account_path: str = ""
    firebase_service_account_b64: str = ""

    # ── BigQuery ─────────────────────────────────────────────
    bigquery_project: str = "enterpriseiq-dev"
    bigquery_dataset: str = "enterpriseiq_core"

    # ── Cloud Storage ────────────────────────────────────────
    gcs_raw_bucket: str = "enterpriseiq-raw-uploads"
    gcs_processed_bucket: str = "enterpriseiq-processed-docs"
    gcs_ml_artifacts_bucket: str = "enterpriseiq-ml-artifacts"

    # ── Firestore ────────────────────────────────────────────
    firestore_project: str = "enterpriseiq-dev"

    # ── Pub/Sub ──────────────────────────────────────────────
    pubsub_project: str = "enterpriseiq-dev"
    pubsub_topic_document_ingested: str = "enterpriseiq.document.ingested"
    pubsub_topic_anomaly_detected: str = "enterpriseiq.anomaly.detected"
    pubsub_topic_pipeline_completed: str = "enterpriseiq.pipeline.completed"
    pubsub_topic_forecast_ready: str = "enterpriseiq.forecast.ready"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600

    # ── ML Service URLs ──────────────────────────────────────
    ml_service_base_url: str = "http://localhost:8000"
    rag_service_url: str = "http://localhost:8001"
    anomaly_service_url: str = "http://localhost:8002"
    forecast_service_url: str = "http://localhost:8003"
    agent_service_url: str = "http://localhost:8004"
    kg_service_url: str = "http://localhost:8005"

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 20

    # ── Email ────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    notification_from_email: str = "noreply@enterpriseiq.com"

    # ── Dataflow ─────────────────────────────────────────────
    dataflow_temp_location: str = "gs://enterpriseiq-pipeline-temp/tmp"
    dataflow_staging_location: str = "gs://enterpriseiq-pipeline-temp/staging"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
