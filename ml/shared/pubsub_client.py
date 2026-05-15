"""
EnterpriseIQ ML — Shared Pub/Sub Publisher
Publishes domain events to Pub/Sub topics per the agreed schema contracts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from google.cloud import pubsub_v1

from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class PubSubPublisher:
    """Thin wrapper around google-cloud-pubsub for publishing ML domain events."""

    def __init__(self) -> None:
        self._publisher = pubsub_v1.PublisherClient()
        self._project = settings.pubsub_project

    def _topic_path(self, topic_name: str) -> str:
        return self._publisher.topic_path(self._project, topic_name)

    def _publish(self, topic_name: str, data: dict) -> str:
        """Publish a JSON message; returns message ID."""
        topic_path = self._topic_path(topic_name)
        payload = json.dumps(data).encode("utf-8")
        future = self._publisher.publish(topic_path, data=payload)
        msg_id = future.result(timeout=10)
        logger.info("Pub/Sub message published", topic=topic_name, msg_id=msg_id)
        return msg_id

    # ── Typed event publishers ───────────────────────────────────────

    def publish_anomaly_detected(self, anomaly_id: str, dataset_id: str,
                                  severity: str, metric_name: str,
                                  anomaly_score: float) -> str:
        return self._publish(
            settings.pubsub_topic_anomaly_detected,
            {
                "event_type": "anomaly.detected",
                "anomaly_id": anomaly_id,
                "dataset_id": dataset_id,
                "severity": severity,
                "metric_name": metric_name,
                "anomaly_score": anomaly_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def publish_forecast_ready(self, forecast_id: str, dataset_id: str,
                                target_column: str, horizon_days: int) -> str:
        return self._publish(
            settings.pubsub_topic_forecast_ready,
            {
                "event_type": "forecast.ready",
                "forecast_id": forecast_id,
                "dataset_id": dataset_id,
                "target_column": target_column,
                "horizon_days": horizon_days,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
