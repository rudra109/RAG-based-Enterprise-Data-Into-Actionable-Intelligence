"""
EnterpriseIQ ML — Shared Configuration
Loads environment variables and provides a singleton config object.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # ── Google Cloud ────────────────────────────────────────
    gcp_project_id: str = "enterpriseiq-dev"
    gcp_region: str = "us-central1"
    gcp_location: str = "us-central1"

    # ── Gemini / Vertex AI ──────────────────────────────────
    gemini_pro_model: str = "gemini-1.5-pro"
    gemini_flash_model: str = "gemini-1.5-flash"
    embedding_model: str = "text-embedding-004"
    vertex_ai_index_id: str = ""
    vertex_ai_index_endpoint_id: str = ""

    # ── BigQuery ────────────────────────────────────────────
    bigquery_dataset: str = "enterpriseiq_core"
    bigquery_project: str = "enterpriseiq-dev"

    # ── Spanner ─────────────────────────────────────────────
    spanner_instance_id: str = "enterpriseiq-kg"
    spanner_database_id: str = "knowledge-graph"

    # ── Pub/Sub ─────────────────────────────────────────────
    pubsub_project: str = "enterpriseiq-dev"
    pubsub_topic_document_ingested: str = "enterpriseiq.document.ingested"
    pubsub_topic_anomaly_detected: str = "enterpriseiq.anomaly.detected"
    pubsub_topic_forecast_ready: str = "enterpriseiq.forecast.ready"

    # ── ML Hyper-parameters ─────────────────────────────────
    anomaly_threshold: float = 0.5
    embedding_dimensions: int = 768
    max_chunk_tokens: int = 512
    chunk_overlap_tokens: int = 50
    default_top_k: int = 5
    rag_confidence_threshold: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
