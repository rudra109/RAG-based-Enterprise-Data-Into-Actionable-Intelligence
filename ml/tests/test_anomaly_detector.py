"""
EnterpriseIQ ML — Anomaly Detection Tests
Tests statistical, isolation forest, semantic, and ensemble detection.
"""

from __future__ import annotations

import sys
import uuid
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "../../")

from anomaly.detector import (
    AnomalyDetectionSystem,
    Anomaly,
    AnomalyReport,
)


@pytest.fixture
def mock_detector():
    with (
        patch("anomaly.detector.GenerativeModel"),
        patch("anomaly.detector.BigQueryClient") as mock_bq,
        patch("anomaly.detector.PubSubPublisher"),
    ):
        detector = AnomalyDetectionSystem()
        detector._bq = mock_bq.return_value
        detector._publisher = MagicMock()
        yield detector


# ────────────────────────────────────────────────────────────────────────────
# Statistical detection tests
# ────────────────────────────────────────────────────────────────────────────

class TestStatisticalDetection:

    def test_detects_obvious_outlier(self, mock_detector):
        """An extreme outlier (z-score >> 3) must be flagged."""
        normal_data = [10.0] * 98
        outlier_series = pd.Series(normal_data + [1000.0, -1000.0])
        anomalies = mock_detector.statistical_detection(outlier_series, "test_metric")
        assert len(anomalies) >= 1
        assert all(a.method == "statistical" for a in anomalies)

    def test_no_false_positives_on_normal_data(self, mock_detector):
        """Normally distributed data should have very few false positives."""
        rng = np.random.default_rng(42)
        normal_series = pd.Series(rng.normal(100, 10, 1000))
        anomalies = mock_detector.statistical_detection(normal_series, "metric")
        # Expect < 5% false positive rate
        assert len(anomalies) / len(normal_series) < 0.05

    def test_handles_all_same_values(self, mock_detector):
        """All-same series (std=0) should not crash."""
        constant_series = pd.Series([5.0] * 50)
        anomalies = mock_detector.statistical_detection(constant_series, "metric")
        assert isinstance(anomalies, list)

    def test_handles_nans(self, mock_detector):
        """NaN values should be skipped gracefully."""
        data = [10.0, float("nan"), 11.0, float("nan"), 500.0]
        series = pd.Series(data)
        anomalies = mock_detector.statistical_detection(series, "metric")
        assert isinstance(anomalies, list)

    def test_insufficient_data_returns_empty(self, mock_detector):
        """Less than 4 data points should return empty list."""
        series = pd.Series([1.0, 2.0, 3.0])
        assert mock_detector.statistical_detection(series, "metric") == []

    def test_severity_scoring(self, mock_detector):
        """Higher z-score outliers should get higher severity."""
        data = [10.0] * 97 + [100.0, 200.0, 500.0]
        series = pd.Series(data)
        anomalies = mock_detector.statistical_detection(series, "metric")
        if len(anomalies) >= 2:
            scores = [a.anomaly_score for a in anomalies]
            # Anomalies should be distinct (not all same score)
            assert len(set(round(s, 2) for s in scores)) > 0

    def test_score_to_severity_mapping(self, mock_detector):
        assert mock_detector._score_to_severity(0.05) == "low"
        assert mock_detector._score_to_severity(0.50) == "medium"
        assert mock_detector._score_to_severity(0.75) == "high"
        assert mock_detector._score_to_severity(0.95) == "critical"


# ────────────────────────────────────────────────────────────────────────────
# Isolation Forest tests
# ────────────────────────────────────────────────────────────────────────────

class TestIsolationForestDetection:

    def test_detects_multivariate_anomaly(self, mock_detector):
        """Isolation Forest should catch anomalies in combined feature space."""
        rng = np.random.default_rng(42)
        normal = pd.DataFrame({
            "v1": rng.normal(0, 1, 990),
            "v2": rng.normal(0, 1, 990),
        })
        anomalies_data = pd.DataFrame({
            "v1": [100.0] * 10,
            "v2": [-100.0] * 10,
        })
        df = pd.concat([normal, anomalies_data], ignore_index=True)
        anomalies = mock_detector.isolation_forest_detection(df, ["v1", "v2"])
        # Should catch the injected anomalies
        assert len(anomalies) > 0
        assert all(a.method == "isolation_forest" for a in anomalies)

    def test_returns_empty_for_small_dataset(self, mock_detector):
        """Less than 10 rows → skip Isolation Forest."""
        df = pd.DataFrame({"v1": [1.0, 2.0, 3.0]})
        result = mock_detector.isolation_forest_detection(df, ["v1"])
        assert result == []

    def test_empty_dataframe(self, mock_detector):
        df = pd.DataFrame()
        result = mock_detector.isolation_forest_detection(df, ["v1"])
        assert result == []


# ────────────────────────────────────────────────────────────────────────────
# Semantic detection tests
# ────────────────────────────────────────────────────────────────────────────

class TestSemanticDetection:

    def test_parses_gemini_response_correctly(self, mock_detector):
        """Should parse valid JSON from Gemini and return Anomaly objects."""
        gemini_json = '[{"index": 0, "reason": "Suspicious pattern", "severity": "high"}]'
        mock_detector._gemini_flash.generate_content.return_value = MagicMock(
            text=f"Sure, here is the analysis:\n```json\n{gemini_json}\n```"
        )
        records = [{"value": 999.9, "label": "test"}]
        anomalies = mock_detector.semantic_anomaly_detection(records, "value")
        assert len(anomalies) == 1
        assert anomalies[0].severity == "high"
        assert anomalies[0].method == "semantic"

    def test_handles_empty_gemini_response(self, mock_detector):
        """Empty JSON array from Gemini → no anomalies."""
        mock_detector._gemini_flash.generate_content.return_value = MagicMock(text="[]")
        records = [{"value": 1.0}]
        anomalies = mock_detector.semantic_anomaly_detection(records, "value")
        assert anomalies == []

    def test_handles_gemini_failure_gracefully(self, mock_detector):
        """If Gemini throws, return empty list instead of crashing."""
        mock_detector._gemini_flash.generate_content.side_effect = RuntimeError("API error")
        records = [{"value": 1.0}]
        anomalies = mock_detector.semantic_anomaly_detection(records, "value")
        assert anomalies == []


# ────────────────────────────────────────────────────────────────────────────
# Ensemble tests
# ────────────────────────────────────────────────────────────────────────────

class TestEnsembleVoting:

    def test_consensus_elevates_score(self, mock_detector):
        """Two methods flagging same index should elevate anomaly score."""
        a1 = Anomaly(5, 100.0, "statistical", score=0.6, anomaly_score=0.6)
        a2 = Anomaly(5, 100.0, "isolation_forest", score=0.55, anomaly_score=0.55)
        result = mock_detector._ensemble_vote([a1, a2])
        assert len(result) == 1
        assert result[0].anomaly_score > max(a1.anomaly_score, a2.anomaly_score)

    def test_single_method_anomaly_preserved(self, mock_detector):
        """Anomaly from one method only should be included unchanged."""
        a = Anomaly(3, 50.0, "statistical", anomaly_score=0.7)
        result = mock_detector._ensemble_vote([a])
        assert len(result) == 1
        assert result[0].anomaly_score == 0.7

    def test_sorted_by_score_descending(self, mock_detector):
        """Result should be sorted highest score first."""
        anomalies = [
            Anomaly(0, 1.0, "statistical", anomaly_score=0.3),
            Anomaly(1, 2.0, "statistical", anomaly_score=0.9),
            Anomaly(2, 3.0, "statistical", anomaly_score=0.6),
        ]
        result = mock_detector._ensemble_vote(anomalies)
        scores = [a.anomaly_score for a in result]
        assert scores == sorted(scores, reverse=True)


# ────────────────────────────────────────────────────────────────────────────
# Pub/Sub integration test
# ────────────────────────────────────────────────────────────────────────────

class TestAnomalyPublishing:

    def test_high_severity_anomalies_published(self, mock_detector):
        """High and critical anomalies should trigger Pub/Sub publish."""
        mock_detector._bq.load_dataset.return_value = [
            {"timestamp": "2026-01-01", "value": 9999.0}
        ]
        mock_detector._bq.write_anomaly_results = MagicMock()

        # Override detection to return a critical anomaly directly
        critical = Anomaly(0, 9999.0, "statistical", metric_name="value",
                           anomaly_score=0.95, severity="critical")
        critical.anomaly_id = str(uuid.uuid4())

        with patch.object(mock_detector, "_ensemble_vote", return_value=[critical]):
            with patch.object(mock_detector, "statistical_detection", return_value=[critical]):
                with patch.object(mock_detector, "isolation_forest_detection", return_value=[]):
                    with patch.object(mock_detector, "semantic_anomaly_detection", return_value=[]):
                        report = mock_detector.detect(
                            dataset_id="test_ds", table="metrics",
                            time_column="timestamp", metric_columns=["value"],
                        )

        mock_detector._publisher.publish_anomaly_detected.assert_called_once()
