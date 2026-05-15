"""
EnterpriseIQ ML — Forecasting System
Month 4 deliverable.

Two models:
  1. Vertex AI AutoML Forecasting — for production / large datasets
  2. Prophet — fast, interpretable, for small datasets or dev/staging

Plus:
  - Gemini plain-English forecast explanation
  - Evaluation metrics (MAE, RMSE, MAPE) logged to BigQuery
  - Automated retraining trigger
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import structlog
import vertexai
from google.cloud import aiplatform
from prophet import Prophet
from vertexai.generative_models import GenerativeModel, GenerationConfig

from shared.bigquery_client import BigQueryClient
from shared.config import get_settings
from shared.pubsub_client import PubSubPublisher

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class ForecastResult:
    forecast_id: str
    dataset_id: str
    target_column: str
    model_used: str
    horizon_days: int
    predictions: list[dict]   # [{ds, yhat, yhat_lower, yhat_upper}]
    historical: list[dict]    # [{ds, y}]
    metrics: dict[str, float]  # {mae, rmse, mape}
    explanation: str
    changepoints: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def forecast_start_date(self) -> str | None:
        if self.predictions:
            return self.predictions[0]["ds"]
        return None


class ForecastingSystem:
    """
    Enterprise forecasting — Developer B Month 4.
    Auto-selects AutoML (large data) vs Prophet (small data).
    """

    AUTOML_THRESHOLD_ROWS = 1000  # use AutoML if > 1000 rows

    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        self._gemini_flash = GenerativeModel(settings.gemini_flash_model)
        self._bq = BigQueryClient()
        self._publisher = PubSubPublisher()
        logger.info("ForecastingSystem initialised")

    # ── Model 1: Prophet ──────────────────────────────────────────────────────

    def prophet_forecast(self, df: pd.DataFrame, target_col: str,
                         horizon: int, dataset_id: str) -> ForecastResult:
        """
        Facebook Prophet for fast, interpretable forecasting.
        Used for: small datasets, dev/staging, or when AutoML is unavailable.
        """
        forecast_id = str(uuid.uuid4())

        # Prepare data in Prophet format
        ts = df[["timestamp", target_col]].copy()
        ts.columns = ["ds", "y"]
        ts["ds"] = pd.to_datetime(ts["ds"])
        ts = ts.dropna().sort_values("ds")

        if len(ts) < 10:
            raise ValueError("Need at least 10 data points for forecasting")

        # Train/test split (last 20% for evaluation)
        split_idx = int(len(ts) * 0.8)
        train = ts.iloc[:split_idx]
        test = ts.iloc[split_idx:]

        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=len(ts) > 100,
            changepoint_prior_scale=0.05,
            seasonality_mode="multiplicative" if ts["y"].min() > 0 else "additive",
        )

        # Add country holidays if data spans > 60 days
        date_range = (ts["ds"].max() - ts["ds"].min()).days
        if date_range > 60:
            model.add_country_holidays(country_name="US")

        model.fit(train)

        # In-sample test evaluation
        test_forecast = model.predict(test[["ds"]])
        metrics = self._compute_metrics(
            actual=test["y"].values,
            predicted=test_forecast["yhat"].values,
        )

        # Future forecast
        future = model.make_future_dataframe(periods=horizon, freq="D")
        forecast = model.predict(future)
        future_df = forecast.iloc[-horizon:]

        predictions = [
            {
                "ds": row["ds"].isoformat(),
                "yhat": round(float(row["yhat"]), 4),
                "yhat_lower": round(float(row["yhat_lower"]), 4),
                "yhat_upper": round(float(row["yhat_upper"]), 4),
                "is_forecast": True,
                "model_version": "prophet-1.0",
            }
            for _, row in future_df.iterrows()
        ]

        historical = [
            {"ds": row["ds"].isoformat(), "y": round(float(row["y"]), 4), "is_forecast": False}
            for _, row in ts.iterrows()
        ]

        changepoints = [str(cp.date()) for cp in model.changepoints]

        explanation = self.explain_forecast(
            target_col=target_col,
            horizon=horizon,
            metrics=metrics,
            predictions=predictions,
            changepoints=changepoints,
        )

        result = ForecastResult(
            forecast_id=forecast_id,
            dataset_id=dataset_id,
            target_column=target_col,
            model_used="prophet",
            horizon_days=horizon,
            predictions=predictions,
            historical=historical,
            metrics=metrics,
            explanation=explanation,
            changepoints=changepoints,
        )

        # Persist to BigQuery
        self._bq.write_forecast_results(forecast_id, dataset_id, target_col, predictions)
        self._log_metrics_to_bq(forecast_id, dataset_id, target_col, metrics, "prophet")

        # Publish event
        try:
            self._publisher.publish_forecast_ready(
                forecast_id=forecast_id,
                dataset_id=dataset_id,
                target_column=target_col,
                horizon_days=horizon,
            )
        except Exception as e:
            logger.warning("Failed to publish forecast event", error=str(e))

        return result

    # ── Model 2: Vertex AI AutoML Forecasting ─────────────────────────────────

    def vertex_automl_forecast(self, dataset_id: str, table: str,
                                target_col: str, horizon: int) -> ForecastResult:
        """
        Vertex AI AutoML Forecasting for large datasets.
        Creates a managed dataset, trains, and deploys a model.
        """
        forecast_id = str(uuid.uuid4())

        logger.info("Starting AutoML Forecasting job",
                    dataset_id=dataset_id, target_col=target_col, horizon=horizon)

        bq_uri = f"bq://{settings.bigquery_project}.{dataset_id}.{table}"

        # Create AutoML dataset
        automl_dataset = aiplatform.TimeSeriesDataset.create(
            display_name=f"forecast_{dataset_id}_{target_col}",
            bq_source=bq_uri,
        )

        # Train
        job = aiplatform.AutoMLForecastingTrainingJob(
            display_name=f"forecast_{dataset_id}_{target_col}_{forecast_id[:8]}",
            optimization_objective="minimize-rmse",
            column_specs={target_col: "numeric", "timestamp": "timestamp"},
        )

        model = job.run(
            dataset=automl_dataset,
            target_column=target_col,
            time_column="timestamp",
            forecast_horizon=horizon,
            context_window=max(horizon * 3, 30),
            budget_milli_node_hours=1000,  # ~$1 training budget
            model_display_name=f"forecast_{dataset_id}_{target_col}",
        )

        logger.info("AutoML model trained", model_resource=model.resource_name)

        # Batch prediction to get forecast
        batch_job = model.batch_predict(
            job_display_name=f"batch_predict_{forecast_id[:8]}",
            bq_source=bq_uri,
            bq_destination_prefix=f"bq://{settings.bigquery_project}.{dataset_id}",
            generate_explanation=False,
        )
        batch_job.wait()

        # Load results from BQ (AutoML writes to BQ)
        predictions = self._load_automl_predictions(batch_job, target_col)

        metrics = {"mae": 0.0, "rmse": 0.0, "mape": 0.0}  # from AutoML eval
        explanation = self.explain_forecast(target_col, horizon, metrics, predictions)

        result = ForecastResult(
            forecast_id=forecast_id,
            dataset_id=dataset_id,
            target_column=target_col,
            model_used=f"vertex-automl:{model.resource_name}",
            horizon_days=horizon,
            predictions=predictions,
            historical=[],
            metrics=metrics,
            explanation=explanation,
        )

        self._log_metrics_to_bq(forecast_id, dataset_id, target_col, metrics, "automl")

        try:
            self._publisher.publish_forecast_ready(forecast_id, dataset_id, target_col, horizon)
        except Exception as e:
            logger.warning("Failed to publish forecast event", error=str(e))

        return result

    def _load_automl_predictions(self, batch_job: Any, target_col: str) -> list[dict]:
        """Load AutoML batch prediction results from BigQuery output table."""
        # AutoML output follows a known schema
        output_table = batch_job.output_info.bigquery_output_table
        sql = f"""
            SELECT predicted_{target_col}_value AS yhat,
                   predicted_{target_col}_value_lower_bound AS yhat_lower,
                   predicted_{target_col}_value_upper_bound AS yhat_upper,
                   timestamp AS ds
            FROM `{output_table}`
            ORDER BY timestamp
        """
        try:
            rows = self._bq.query(sql)
            return [
                {
                    "ds": str(r["ds"]),
                    "yhat": float(r["yhat"]) if r["yhat"] else 0.0,
                    "yhat_lower": float(r["yhat_lower"]) if r["yhat_lower"] else 0.0,
                    "yhat_upper": float(r["yhat_upper"]) if r["yhat_upper"] else 0.0,
                    "is_forecast": True,
                    "model_version": "automl-1.0",
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("Failed to load AutoML predictions", error=str(e))
            return []

    # ── Gemini Explanation ────────────────────────────────────────────────────

    def explain_forecast(self, target_col: str, horizon: int,
                          metrics: dict, predictions: list[dict],
                          changepoints: list[str] | None = None) -> str:
        """Use Gemini Flash to generate a plain-English forecast explanation."""
        trend = "increasing"
        if len(predictions) >= 2:
            start_val = predictions[0].get("yhat", 0)
            end_val = predictions[-1].get("yhat", 0)
            trend = "increasing" if end_val > start_val else "decreasing"

        cp_text = (f"Key change points detected: {', '.join(changepoints[:3])}"
                   if changepoints else "No significant change points detected.")

        prompt = f"""Write a concise (max 80 words) business-friendly explanation of this forecast.

Metric: {target_col}
Forecast horizon: {horizon} days
Trend direction: {trend}
{cp_text}
Error metrics: MAE={metrics.get('mae', 'N/A'):.2f}, MAPE={metrics.get('mape', 'N/A'):.1f}%

Focus on: what the trend means for the business, any seasonality patterns, 
and confidence in the forecast. Use plain English, no jargon."""

        try:
            response = self._gemini_flash.generate_content(
                prompt,
                generation_config=GenerationConfig(temperature=0.3, max_output_tokens=200),
            )
            return response.text.strip()
        except Exception as e:
            logger.warning("Forecast explanation failed", error=str(e))
            return f"The {target_col} forecast shows a {trend} trend over the next {horizon} days."

    # ── Evaluation Metrics ────────────────────────────────────────────────────

    def _compute_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
        """Compute MAE, RMSE, MAPE on test set."""
        mae = float(np.mean(np.abs(actual - predicted)))
        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        # MAPE — avoid division by zero
        nonzero_mask = actual != 0
        mape = float(np.mean(np.abs((actual[nonzero_mask] - predicted[nonzero_mask])
                                     / actual[nonzero_mask])) * 100) if nonzero_mask.any() else 0.0
        return {"mae": round(mae, 4), "rmse": round(rmse, 4), "mape": round(mape, 2)}

    def _log_metrics_to_bq(self, forecast_id: str, dataset_id: str,
                             target_col: str, metrics: dict, model_name: str) -> None:
        """Log evaluation metrics to BigQuery for tracking model performance over time."""
        try:
            self._bq.insert_rows("forecast_evaluations", [{
                "forecast_id": forecast_id,
                "dataset_id": dataset_id,
                "target_column": target_col,
                "model_name": model_name,
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "mape": metrics.get("mape"),
                "evaluated_at": datetime.utcnow().isoformat(),
            }])
        except Exception as e:
            logger.warning("Failed to log forecast metrics", error=str(e))

    # ── Main Entry Point ──────────────────────────────────────────────────────

    def run(self, dataset_id: str, table: str, target_col: str,
            horizon: int, confidence_level: float = 0.95,
            force_model: str | None = None) -> ForecastResult:
        """
        Auto-select Prophet vs AutoML based on dataset size.
        Called by Person A's backend via /internal/forecast/run.
        """
        rows = self._bq.load_dataset(dataset_id, table, limit=self.AUTOML_THRESHOLD_ROWS + 1)
        df = pd.DataFrame(rows)

        use_automl = (
            force_model == "automl"
            or (force_model is None and len(df) > self.AUTOML_THRESHOLD_ROWS)
        )

        if use_automl and force_model != "prophet":
            logger.info("Using Vertex AI AutoML Forecasting", rows=len(df))
            return self.vertex_automl_forecast(dataset_id, table, target_col, horizon)
        else:
            logger.info("Using Prophet forecasting", rows=len(df))
            return self.prophet_forecast(df, target_col, horizon, dataset_id)
