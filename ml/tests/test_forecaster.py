"""
EnterpriseIQ ML — Forecasting Tests
Tests Prophet forecasting, metrics computation, and Gemini explanation.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "../../")

from forecast.forecaster import ForecastingSystem


@pytest.fixture
def mock_forecaster():
    with (
        patch("forecast.forecaster.vertexai.init"),
        patch("forecast.forecaster.GenerativeModel") as mock_gen,
        patch("forecast.forecaster.BigQueryClient") as mock_bq,
        patch("forecast.forecaster.PubSubPublisher"),
    ):
        forecaster = ForecastingSystem()
        forecaster._gemini_flash = mock_gen.return_value
        forecaster._bq = mock_bq.return_value
        forecaster._publisher = MagicMock()
        yield forecaster


def make_time_series(n: int = 200, trend: float = 0.5,
                      noise: float = 5.0) -> pd.DataFrame:
    """Create synthetic time series data for testing."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    values = (np.arange(n) * trend + np.random.default_rng(42).normal(0, noise, n) + 100)
    return pd.DataFrame({"timestamp": dates, "revenue": values})


class TestProphetForecast:

    def test_returns_valid_forecast_result(self, mock_forecaster):
        """Prophet forecast should return a ForecastResult with predictions."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(
            text="Revenue is expected to increase steadily over the next 30 days."
        )
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=200)
        result = mock_forecaster.prophet_forecast(
            df=df, target_col="revenue", horizon=30, dataset_id="test_ds"
        )

        assert result.forecast_id is not None
        assert len(result.predictions) == 30
        assert result.model_used == "prophet"
        assert all("yhat" in p for p in result.predictions)
        assert all("yhat_lower" in p for p in result.predictions)
        assert all("yhat_upper" in p for p in result.predictions)

    def test_confidence_interval_ordering(self, mock_forecaster):
        """Lower bound must always be <= yhat <= upper bound."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(text="Forecast ready.")
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=200)
        result = mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                                   horizon=14, dataset_id="ds")

        for p in result.predictions:
            assert p["yhat_lower"] <= p["yhat"] + 0.01  # tiny tolerance for float
            assert p["yhat"] <= p["yhat_upper"] + 0.01

    def test_raises_on_insufficient_data(self, mock_forecaster):
        """Less than 10 rows should raise ValueError."""
        df = make_time_series(n=5)
        with pytest.raises(ValueError, match="at least 10"):
            mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                              horizon=7, dataset_id="ds")

    def test_gemini_explanation_called(self, mock_forecaster):
        """Gemini flash should be called to generate explanation."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(
            text="Revenue will grow."
        )
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=150)
        result = mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                                   horizon=7, dataset_id="ds")

        mock_forecaster._gemini_flash.generate_content.assert_called()
        assert result.explanation != ""

    def test_metrics_within_expected_range(self, mock_forecaster):
        """MAE, RMSE, MAPE should be non-negative floats."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(text="OK")
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=200)
        result = mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                                   horizon=30, dataset_id="ds")

        assert result.metrics["mae"] >= 0
        assert result.metrics["rmse"] >= 0
        assert result.metrics["mape"] >= 0
        assert result.metrics["mape"] < 1000  # sanity check

    def test_historical_data_in_result(self, mock_forecaster):
        """ForecastResult should include historical data for chart rendering."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(text="OK")
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=100)
        result = mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                                   horizon=7, dataset_id="ds")

        assert len(result.historical) > 0
        assert all("ds" in h and "y" in h for h in result.historical)

    def test_pubsub_published_after_forecast(self, mock_forecaster):
        """forecast.ready Pub/Sub event should be published."""
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(text="OK")
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        df = make_time_series(n=150)
        mock_forecaster.prophet_forecast(df=df, target_col="revenue",
                                          horizon=7, dataset_id="ds")

        mock_forecaster._publisher.publish_forecast_ready.assert_called_once()


class TestMetricsComputation:

    def test_mae_computation(self, mock_forecaster):
        actual = np.array([10.0, 20.0, 30.0])
        predicted = np.array([12.0, 18.0, 33.0])
        metrics = mock_forecaster._compute_metrics(actual, predicted)
        expected_mae = np.mean(np.abs(actual - predicted))
        assert abs(metrics["mae"] - expected_mae) < 1e-6

    def test_rmse_computation(self, mock_forecaster):
        actual = np.array([10.0, 20.0, 30.0])
        predicted = np.array([10.0, 20.0, 30.0])  # perfect
        metrics = mock_forecaster._compute_metrics(actual, predicted)
        assert metrics["rmse"] == 0.0
        assert metrics["mae"] == 0.0

    def test_mape_avoids_division_by_zero(self, mock_forecaster):
        actual = np.array([0.0, 10.0, 20.0])  # has zero
        predicted = np.array([1.0, 11.0, 21.0])
        metrics = mock_forecaster._compute_metrics(actual, predicted)
        assert metrics["mape"] >= 0
        assert not np.isnan(metrics["mape"])

    def test_model_auto_selection_prophet_for_small(self, mock_forecaster):
        """Small dataset should use Prophet, not AutoML."""
        small_rows = [{"timestamp": f"2024-01-{i+1:02d}", "revenue": float(i * 10)}
                      for i in range(50)]
        mock_forecaster._bq.load_dataset.return_value = small_rows
        mock_forecaster._gemini_flash.generate_content.return_value = MagicMock(text="OK")
        mock_forecaster._bq.write_forecast_results = MagicMock()
        mock_forecaster._bq.insert_rows = MagicMock()

        with patch.object(mock_forecaster, "prophet_forecast") as mock_prophet:
            with patch.object(mock_forecaster, "vertex_automl_forecast") as mock_automl:
                mock_prophet.return_value = MagicMock()
                mock_forecaster.run("ds", "metrics", "revenue", 7)
                mock_prophet.assert_called_once()
                mock_automl.assert_not_called()
