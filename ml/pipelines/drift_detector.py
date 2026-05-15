"""
EnterpriseIQ ML — Model Drift Detection (Month 9)
Monitors Isolation Forest and forecasting models for data drift.
Uses Population Stability Index (PSI) + KL Divergence.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import structlog
from vertexai.generative_models import GenerationConfig, GenerativeModel

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ModelDriftDetector:
    """
    Detects data drift and concept drift in deployed ML models.
    Month 9 MLOps deliverable.
    """

    PSI_LOW_THRESHOLD = 0.1     # No action needed
    PSI_MEDIUM_THRESHOLD = 0.2  # Warning — monitor closely
    PSI_HIGH_THRESHOLD = 0.25   # Retrain required

    def __init__(self) -> None:
        self._bq = BigQueryClient()
        self._gemini_flash = GenerativeModel(settings.gemini_flash_model)

    # ── Population Stability Index ────────────────────────────────────────────

    def compute_psi(self, baseline: pd.Series, current: pd.Series,
                    n_bins: int = 10) -> float:
        """
        Compute PSI between baseline and current distributions.
        PSI < 0.1: No significant change
        PSI 0.1-0.2: Some change — monitor
        PSI > 0.2: Significant change — retrain
        """
        # Create bins from baseline
        _, bin_edges = np.histogram(baseline.dropna(), bins=n_bins)
        bin_edges[0] -= 1e-8  # include min value
        bin_edges[-1] += 1e-8

        baseline_counts = np.histogram(baseline.dropna(), bins=bin_edges)[0]
        current_counts = np.histogram(current.dropna(), bins=bin_edges)[0]

        # Add small value to avoid log(0)
        baseline_pct = (baseline_counts + 1e-4) / (len(baseline) + 1e-4)
        current_pct = (current_counts + 1e-4) / (len(current) + 1e-4)

        psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
        return float(psi)

    def compute_kl_divergence(self, baseline: pd.Series,
                               current: pd.Series, n_bins: int = 20) -> float:
        """KL Divergence as an additional drift metric."""
        _, bin_edges = np.histogram(
            pd.concat([baseline, current]).dropna(), bins=n_bins
        )
        p = np.histogram(baseline.dropna(), bins=bin_edges)[0] + 1e-8
        q = np.histogram(current.dropna(), bins=bin_edges)[0] + 1e-8
        p_norm = p / p.sum()
        q_norm = q / q.sum()
        return float(np.sum(p_norm * np.log(p_norm / q_norm)))

    # ── Drift Check for All Features ─────────────────────────────────────────

    def check_feature_drift(self, dataset_id: str, table: str,
                             feature_columns: list[str],
                             baseline_days: int = 30) -> dict[str, Any]:
        """
        Check drift for all model features.
        Returns report with per-feature PSI scores and recommendations.
        """
        # Load baseline data (historical)
        baseline_sql = f"""
            SELECT {', '.join(feature_columns)}
            FROM `{settings.bigquery_project}.{dataset_id}.{table}`
            WHERE timestamp BETWEEN 
                TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {baseline_days * 2} DAY)
                AND TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {baseline_days} DAY)
        """

        current_sql = f"""
            SELECT {', '.join(feature_columns)}
            FROM `{settings.bigquery_project}.{dataset_id}.{table}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {baseline_days} DAY)
        """

        try:
            baseline_df = pd.DataFrame(self._bq.query(baseline_sql))
            current_df = pd.DataFrame(self._bq.query(current_sql))
        except Exception as e:
            logger.error("Failed to load drift data", error=str(e))
            return {"error": str(e), "should_retrain": False}

        if baseline_df.empty or current_df.empty:
            return {"error": "Insufficient data", "should_retrain": False}

        feature_results: dict[str, dict] = {}
        max_psi = 0.0

        for col in feature_columns:
            if col not in baseline_df.columns or col not in current_df.columns:
                continue
            try:
                baseline_series = pd.to_numeric(baseline_df[col], errors="coerce")
                current_series = pd.to_numeric(current_df[col], errors="coerce")

                psi = self.compute_psi(baseline_series, current_series)
                kl = self.compute_kl_divergence(baseline_series, current_series)

                status = (
                    "stable" if psi < self.PSI_LOW_THRESHOLD else
                    "warning" if psi < self.PSI_MEDIUM_THRESHOLD else
                    "drift_detected"
                )
                feature_results[col] = {"psi": round(psi, 4), "kl": round(kl, 4), "status": status}
                max_psi = max(max_psi, psi)
            except Exception as e:
                feature_results[col] = {"error": str(e)}

        should_retrain = max_psi > self.PSI_HIGH_THRESHOLD
        report = {
            "drift_check_id": str(uuid.uuid4()),
            "dataset_id": dataset_id,
            "max_psi": round(max_psi, 4),
            "should_retrain": should_retrain,
            "features": feature_results,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # Log to BigQuery
        try:
            self._bq.insert_rows("model_drift_logs", [{
                **report, "features": json.dumps(feature_results)
            }])
        except Exception:
            pass

        logger.info("Drift check complete", max_psi=max_psi, retrain=should_retrain)
        return report

    # ── Anomaly Root Cause Analysis (Month 9) ────────────────────────────────

    def explain_anomaly_root_cause(self, anomaly_id: str, dataset_id: str,
                                    context_records: list[dict]) -> str:
        """
        Use Gemini to provide root cause analysis for detected anomalies.
        Month 9 advanced anomaly feature.
        """
        prompt = f"""You are an expert data analyst performing root cause analysis (RCA).

An anomaly has been detected in dataset '{dataset_id}' (anomaly_id: {anomaly_id}).
Analyze the surrounding data records and provide a detailed root cause analysis.

Surrounding data records (before and after the anomaly):
{json.dumps(context_records[:20], indent=2, default=str)}

Provide:
1. Most likely root cause (1-2 sentences)
2. Contributing factors (bullet list)
3. Business impact assessment (low/medium/high)
4. Recommended immediate actions (bullet list)
5. Preventive measures for the future

Keep response under 300 words. Be specific and actionable."""

        try:
            response = self._gemini_flash.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.2, max_output_tokens=600),
            )
            return response.text
        except Exception as e:
            logger.error("RCA generation failed", error=str(e))
            return f"Root cause analysis unavailable: {str(e)}"
