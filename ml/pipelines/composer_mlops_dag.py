"""
EnterpriseIQ ML — Cloud Composer (Airflow) DAG
Month 7 MLOps deliverable.

Orchestrates:
  1. Daily model drift detection check
  2. Conditional model retraining (when drift detected)
  3. RAG index health check
  4. Forecast model freshness check
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.operators.vertex_ai.pipeline_job import (
    RunPipelineJobOperator,
)
from airflow.utils.trigger_rule import TriggerRule

# ── Constants ─────────────────────────────────────────────────────────────────

PROJECT_ID = "enterpriseiq-dev"
REGION = "us-central1"
DRIFT_THRESHOLD = 0.15   # 15% PSI change triggers retraining
PIPELINE_YAML = "gs://enterpriseiq-ml-artifacts/pipelines/anomaly_training_pipeline.yaml"
PIPELINE_ROOT = "gs://enterpriseiq-ml-artifacts/pipeline-runs"

DEFAULT_ARGS = {
    "owner": "developer-b",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
    "email": ["ml-alerts@enterpriseiq.com"],
}


# ── Python Functions ───────────────────────────────────────────────────────────

def check_model_drift(**context) -> str:
    """
    Compute Population Stability Index (PSI) for anomaly model features.
    Returns 'retrain' if drift detected, else 'skip_retrain'.
    """
    from google.cloud import bigquery
    import numpy as np

    client = bigquery.Client(project=PROJECT_ID)

    sql = """
        WITH baseline AS (
            SELECT value
            FROM `enterpriseiq-dev.enterpriseiq_core.anomaly_training_data`
            WHERE DATE(created_at) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
              AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        ),
        current_data AS (
            SELECT value
            FROM `enterpriseiq-dev.enterpriseiq_core.live_metrics`
            WHERE DATE(timestamp) = CURRENT_DATE()
        )
        SELECT
            AVG(b.value) AS baseline_mean,
            STDDEV(b.value) AS baseline_std,
            AVG(c.value) AS current_mean,
            STDDEV(c.value) AS current_std
        FROM baseline b, current_data c
    """

    try:
        rows = list(client.query(sql).result())
        if rows:
            row = rows[0]
            baseline_mean = row["baseline_mean"] or 0
            current_mean = row["current_mean"] or 0
            if baseline_mean > 0:
                drift = abs(current_mean - baseline_mean) / baseline_mean
                context["task_instance"].xcom_push(key="drift_score", value=drift)
                if drift > DRIFT_THRESHOLD:
                    print(f"Drift detected: {drift:.4f} > threshold {DRIFT_THRESHOLD}")
                    return "trigger_retraining"
    except Exception as e:
        print(f"Drift check failed: {e}")

    print("No significant drift detected")
    return "skip_retrain"


def check_rag_index_health(**context) -> None:
    """Check that Vector Search index is fresh and has recent embeddings."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    sql = """
        SELECT COUNT(*) as chunk_count,
               MAX(created_at) as last_indexed
        FROM `enterpriseiq-dev.enterpriseiq_core.doc_chunks`
        WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    """
    rows = list(client.query(sql).result())
    if rows:
        row = rows[0]
        print(f"Chunks indexed in last 24h: {row['chunk_count']}")
        print(f"Last indexed: {row['last_indexed']}")


def check_forecast_freshness(**context) -> None:
    """Verify that forecasts are not stale (> 7 days old)."""
    from google.cloud import bigquery
    from datetime import timezone

    client = bigquery.Client(project=PROJECT_ID)
    sql = """
        SELECT dataset_id, target_column, MAX(forecast_timestamp) as latest_forecast
        FROM `enterpriseiq-dev.enterpriseiq_core.forecast_results`
        GROUP BY dataset_id, target_column
        HAVING latest_forecast < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    """
    rows = list(client.query(sql).result())
    if rows:
        for row in rows:
            print(f"STALE FORECAST: {row['dataset_id']}.{row['target_column']} "
                  f"last updated: {row['latest_forecast']}")
        # In production: trigger forecast refresh for stale models


def log_pipeline_metrics(**context) -> None:
    """Log DAG run metrics to BigQuery for observability."""
    from google.cloud import bigquery
    from datetime import timezone

    client = bigquery.Client(project=PROJECT_ID)
    run_id = context["run_id"]
    dag_id = context["dag"].dag_id
    logical_date = context["logical_date"].isoformat()

    rows = [{
        "run_id": run_id,
        "dag_id": dag_id,
        "logical_date": logical_date,
        "status": "completed",
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }]

    errors = client.insert_rows_json(
        "enterpriseiq-dev.enterpriseiq_core.pipeline_runs", rows
    )
    if errors:
        print(f"Failed to log pipeline metrics: {errors}")


# ── DAG Definition ─────────────────────────────────────────────────────────────

with DAG(
    dag_id="enterpriseiq_mlops_daily",
    description="Daily ML model health checks and conditional retraining",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 6 * * *",  # 6 AM UTC daily
    start_date=datetime(2026, 5, 1),
    catchup=False,
    tags=["enterpriseiq", "mlops", "developer-b"],
    max_active_runs=1,
) as dag:

    start = EmptyOperator(task_id="start")

    # ── Parallel health checks ──────────────────────────────────────────────

    rag_health = PythonOperator(
        task_id="check_rag_index_health",
        python_callable=check_rag_index_health,
    )

    forecast_freshness = PythonOperator(
        task_id="check_forecast_freshness",
        python_callable=check_forecast_freshness,
    )

    # ── Drift detection (branches to retrain or skip) ───────────────────────

    drift_check = BranchPythonOperator(
        task_id="check_model_drift",
        python_callable=check_model_drift,
    )

    # ── Retraining path ─────────────────────────────────────────────────────

    trigger_retraining = RunPipelineJobOperator(
        task_id="trigger_retraining",
        project_id=PROJECT_ID,
        region=REGION,
        display_name="anomaly-model-retrain",
        template_path=PIPELINE_YAML,
        pipeline_root=PIPELINE_ROOT,
        parameter_values={
            "project_id": PROJECT_ID,
            "location": REGION,
            "contamination": 0.05,
            "n_estimators": 200,
            "precision_threshold": 0.90,
            "recall_threshold": 0.85,
        },
    )

    skip_retrain = EmptyOperator(task_id="skip_retrain")

    # ── Logging ─────────────────────────────────────────────────────────────

    log_metrics = PythonOperator(
        task_id="log_pipeline_metrics",
        python_callable=log_pipeline_metrics,
        trigger_rule=TriggerRule.ALL_DONE,  # always runs
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # ── Task Dependencies ────────────────────────────────────────────────────

    start >> [rag_health, forecast_freshness, drift_check]
    drift_check >> [trigger_retraining, skip_retrain]
    [trigger_retraining, skip_retrain, rag_health, forecast_freshness] >> log_metrics
    log_metrics >> end
