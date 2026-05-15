"""
EnterpriseIQ ML — Anomaly Detection System
Month 3 deliverable.

Three detection models:
  1. Statistical (Z-score + IQR) — real-time, no model needed
  2. Isolation Forest — Vertex AI trained + deployed
  3. Gemini semantic anomaly — for qualitative outliers

Ensemble voting produces final AnomalyReport.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

import numpy as np
import pandas as pd
import structlog
from scipy import stats
from sklearn.ensemble import IsolationForest
from vertexai.generative_models import GenerativeModel, GenerationConfig

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings
from shared.pubsub_client import PubSubPublisher

logger = structlog.get_logger(__name__)
settings = get_settings()

Severity = Literal["low", "medium", "high", "critical"]
DetectionMethod = Literal["statistical", "isolation_forest", "semantic"]


@dataclass
class Anomaly:
    index: int
    actual_value: float
    method: DetectionMethod
    metric_name: str = ""
    anomaly_score: float = 0.0
    expected_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    reason: str = ""
    severity: Severity = "medium"
    anomaly_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class AnomalyReport:
    dataset_id: str
    metric_columns: list[str]
    anomalies: list[Anomaly]
    total_records: int
    detection_methods_used: list[str]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == "critical")


class AnomalyDetectionSystem:
    """
    Enterprise anomaly detection — Developer B Month 3.
    Ensemble of 3 models for maximum coverage.
    """

    def __init__(self) -> None:
        self._gemini_flash = GenerativeModel(settings.gemini_flash_model)
        self._bq = BigQueryClient()
        self._publisher = PubSubPublisher()
        self._threshold = settings.anomaly_threshold
        logger.info("AnomalyDetectionSystem initialised")

    # ── Model 1: Statistical ──────────────────────────────────────────────────

    def statistical_detection(self, series: pd.Series,
                               metric_name: str) -> list[Anomaly]:
        """
        Combined Z-score and IQR method.
        Fast, no model training required — used for real-time streaming.
        """
        if len(series) < 4:
            return []

        # Z-score
        z_scores = np.abs(stats.zscore(series.dropna()))

        # IQR
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        anomalies: list[Anomaly] = []
        for i, (idx, value) in enumerate(series.items()):
            if pd.isna(value):
                continue

            is_z_anomaly = i < len(z_scores) and z_scores[i] > 3
            is_iqr_anomaly = value < lower or value > upper

            if is_z_anomaly or is_iqr_anomaly:
                z = float(z_scores[i]) if i < len(z_scores) else 0.0
                score = min(z / 6.0, 1.0)  # normalise to 0-1
                anomalies.append(Anomaly(
                    index=int(idx) if isinstance(idx, (int, np.integer)) else i,
                    actual_value=float(value),
                    method="statistical",
                    metric_name=metric_name,
                    anomaly_score=round(score, 4),
                    expected_value=float(series.mean()),
                    lower_bound=float(lower),
                    upper_bound=float(upper),
                    severity=self._score_to_severity(score),
                ))

        logger.debug("Statistical detection done",
                     metric=metric_name, found=len(anomalies))
        return anomalies

    # ── Model 2: Isolation Forest ─────────────────────────────────────────────

    def isolation_forest_detection(self, df: pd.DataFrame,
                                    metric_columns: list[str]) -> list[Anomaly]:
        """
        Multivariate anomaly detection using scikit-learn Isolation Forest.
        In production, the trained model is deployed on Vertex AI Endpoints
        and called via predict(). Here we also support local inference for dev.
        """
        if df.empty or not metric_columns:
            return []

        feature_df = df[metric_columns].fillna(df[metric_columns].median())
        if feature_df.shape[0] < 10:
            return []

        clf = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(feature_df)

        scores = clf.score_samples(feature_df)  # negative; lower = more anomalous
        predictions = clf.predict(feature_df)    # -1 = anomaly, 1 = normal

        anomalies: list[Anomaly] = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                normalised_score = float(np.clip(-score, 0, 1))
                row = df.iloc[i]
                primary_metric = metric_columns[0]
                anomalies.append(Anomaly(
                    index=i,
                    actual_value=float(row.get(primary_metric, 0)),
                    method="isolation_forest",
                    metric_name=primary_metric,
                    anomaly_score=round(normalised_score, 4),
                    severity=self._score_to_severity(normalised_score),
                ))

        logger.debug("Isolation Forest detection done", found=len(anomalies))
        return anomalies

    # ── Model 3: Gemini Semantic ──────────────────────────────────────────────

    def semantic_anomaly_detection(self, records: list[dict],
                                    metric_name: str = "value") -> list[Anomaly]:
        """
        Use Gemini Flash to detect qualitative / semantic anomalies.
        Useful for categorical data, text fields, or context-dependent outliers.
        """
        if not records:
            return []

        sample = records[:50]  # API token limit
        prompt = f"""Analyze these data records and identify any that appear
anomalous, suspicious, or inconsistent with the typical pattern.
Focus on outliers, impossible values, suspicious sequences, or data quality issues.

Records (JSON):
{json.dumps(sample, indent=2, default=str)}

Return ONLY valid JSON array (no explanation outside JSON):
[
  {{"index": 0, "reason": "Explanation of why this is anomalous", "severity": "low|medium|high|critical"}}
]

If no anomalies found, return: []"""

        try:
            response = self._gemini_flash.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.0, max_output_tokens=1024),
            )

            match = re.search(r"\[.*\]", response.text, re.DOTALL)
            if not match:
                return []

            parsed = json.loads(match.group())
            anomalies: list[Anomaly] = []
            for item in parsed:
                idx = int(item.get("index", 0))
                if idx < len(records):
                    rec = records[idx]
                    value = float(rec.get(metric_name, 0)) if isinstance(
                        rec.get(metric_name), (int, float)) else 0.0
                    sev = item.get("severity", "medium")
                    sev = sev if sev in ("low", "medium", "high", "critical") else "medium"
                    anomalies.append(Anomaly(
                        index=idx,
                        actual_value=value,
                        method="semantic",
                        metric_name=metric_name,
                        anomaly_score={"low": 0.3, "medium": 0.6,
                                       "high": 0.8, "critical": 1.0}[sev],
                        reason=item.get("reason", ""),
                        severity=sev,
                    ))
            return anomalies
        except Exception as e:
            logger.warning("Semantic detection failed", error=str(e))
            return []

    # ── Ensemble ──────────────────────────────────────────────────────────────

    def _ensemble_vote(self, all_anomalies: list[Anomaly]) -> list[Anomaly]:
        """
        Deduplicate and merge anomalies from multiple methods.
        If 2+ methods agree on index → elevate severity.
        """
        by_index: dict[int, list[Anomaly]] = {}
        for a in all_anomalies:
            by_index.setdefault(a.index, []).append(a)

        merged: list[Anomaly] = []
        for idx, group in by_index.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Consensus anomaly — take highest score, elevate severity
                best = max(group, key=lambda a: a.anomaly_score)
                best.anomaly_score = min(
                    sum(a.anomaly_score for a in group) / len(group) * 1.2, 1.0
                )
                best.severity = self._score_to_severity(best.anomaly_score)
                merged.append(best)

        return sorted(merged, key=lambda a: a.anomaly_score, reverse=True)

    # ── Main detection entry point ────────────────────────────────────────────

    def detect(self, dataset_id: str, table: str,
               time_column: str, metric_columns: list[str],
               sensitivity: Literal["low", "medium", "high"] = "medium",
               use_statistical: bool = True,
               use_ml: bool = True,
               use_semantic: bool = True) -> AnomalyReport:
        """
        Full anomaly detection pipeline.
        Called by Person A's backend via /internal/anomaly/detect.
        """
        logger.info("Anomaly detection started", dataset_id=dataset_id,
                    metrics=metric_columns, sensitivity=sensitivity)

        # Adjust threshold by sensitivity
        threshold_map = {"low": 0.7, "medium": 0.5, "high": 0.3}
        self._threshold = threshold_map[sensitivity]

        rows = self._bq.load_dataset(dataset_id, table)
        df = pd.DataFrame(rows)

        if df.empty:
            return AnomalyReport(
                dataset_id=dataset_id,
                metric_columns=metric_columns,
                anomalies=[],
                total_records=0,
                detection_methods_used=[],
            )

        all_anomalies: list[Anomaly] = []
        methods_used: list[str] = []

        if use_statistical:
            for col in metric_columns:
                if col in df.columns:
                    series = pd.to_numeric(df[col], errors="coerce")
                    all_anomalies += self.statistical_detection(series, col)
            methods_used.append("statistical")

        if use_ml:
            all_anomalies += self.isolation_forest_detection(df, metric_columns)
            methods_used.append("isolation_forest")

        if use_semantic:
            sample_records = df.head(50).to_dict("records")
            all_anomalies += self.semantic_anomaly_detection(
                sample_records, metric_columns[0] if metric_columns else "value"
            )
            methods_used.append("semantic")

        final_anomalies = self._ensemble_vote(all_anomalies)

        # Persist to BigQuery
        bq_rows = [
            {
                "anomaly_id": a.anomaly_id,
                "dataset_id": dataset_id,
                "metric_name": a.metric_name,
                "anomaly_score": a.anomaly_score,
                "actual_value": a.actual_value,
                "expected_value": a.expected_value,
                "lower_bound": a.lower_bound,
                "upper_bound": a.upper_bound,
                "is_acknowledged": False,
                "severity": a.severity,
            }
            for a in final_anomalies
        ]
        if bq_rows:
            self._bq.write_anomaly_results(bq_rows)

        # Publish critical/high anomalies to Pub/Sub
        for a in final_anomalies:
            if a.severity in ("high", "critical"):
                try:
                    self._publisher.publish_anomaly_detected(
                        anomaly_id=a.anomaly_id,
                        dataset_id=dataset_id,
                        severity=a.severity,
                        metric_name=a.metric_name,
                        anomaly_score=a.anomaly_score,
                    )
                except Exception as e:
                    logger.warning("Failed to publish anomaly event", error=str(e))

        logger.info("Anomaly detection complete",
                    total=len(final_anomalies),
                    critical=sum(1 for a in final_anomalies if a.severity == "critical"))

        return AnomalyReport(
            dataset_id=dataset_id,
            metric_columns=metric_columns,
            anomalies=final_anomalies,
            total_records=len(df),
            detection_methods_used=methods_used,
        )

    def _score_to_severity(self, score: float) -> Severity:
        if score >= 0.9:
            return "critical"
        elif score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        return "low"
