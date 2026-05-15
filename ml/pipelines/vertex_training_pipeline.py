"""
EnterpriseIQ ML — Vertex AI Training Pipeline (Kubeflow Pipelines)
Month 7 MLOps deliverable.

Defines end-to-end Vertex AI Pipeline for Isolation Forest model training:
  1. Data extraction from BigQuery
  2. Feature engineering
  3. Model training
  4. Model evaluation
  5. Model registration in Vertex AI Model Registry
  6. Conditional deployment (if metrics pass thresholds)
"""

from __future__ import annotations

import json
from typing import NamedTuple

from kfp import dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output
from google.cloud import aiplatform

# ── Pipeline Components ────────────────────────────────────────────────────────

@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["google-cloud-bigquery", "pandas", "pyarrow"],
)
def extract_training_data(
    project_id: str,
    dataset_id: str,
    table: str,
    metric_columns: list,
    output_dataset: Output[Dataset],
) -> None:
    """Extract labelled training data from BigQuery."""
    from google.cloud import bigquery
    import pandas as pd

    client = bigquery.Client(project=project_id)
    cols = ", ".join(metric_columns + ["is_anomaly"])
    sql = f"SELECT {cols} FROM `{project_id}.{dataset_id}.{table}` WHERE is_anomaly IS NOT NULL"

    df = client.query(sql).to_dataframe()
    df.to_parquet(output_dataset.path, index=False)
    print(f"Extracted {len(df)} rows")


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["pandas", "scikit-learn", "pyarrow"],
)
def train_isolation_forest(
    input_dataset: Input[Dataset],
    contamination: float,
    n_estimators: int,
    output_model: Output[Model],
    metrics: Output[Metrics],
) -> None:
    """Train Isolation Forest and evaluate."""
    import pickle
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import precision_score, recall_score, f1_score

    df = pd.read_parquet(input_dataset.path)
    X = df.drop(columns=["is_anomaly"], errors="ignore")
    y = df["is_anomaly"].astype(int) if "is_anomaly" in df else None

    clf = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X)

    if y is not None:
        preds = (clf.predict(X) == -1).astype(int)
        precision = precision_score(y, preds, zero_division=0)
        recall = recall_score(y, preds, zero_division=0)
        f1 = f1_score(y, preds, zero_division=0)

        metrics.log_metric("precision", precision)
        metrics.log_metric("recall", recall)
        metrics.log_metric("f1_score", f1)
        print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")

    with open(output_model.path, "wb") as f:
        pickle.dump(clf, f)

    output_model.metadata["framework"] = "scikit-learn"
    output_model.metadata["model_type"] = "IsolationForest"


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["google-cloud-aiplatform"],
)
def register_model(
    project_id: str,
    location: str,
    model_display_name: str,
    input_model: Input[Model],
    precision_threshold: float,
    recall_threshold: float,
    metrics: Input[Metrics],
) -> NamedTuple("Outputs", [("should_deploy", bool), ("model_resource_name", str)]):
    """Register model in Vertex AI Model Registry if metrics pass."""
    from collections import namedtuple
    from google.cloud import aiplatform

    Outputs = namedtuple("Outputs", ["should_deploy", "model_resource_name"])

    precision = metrics.metadata.get("precision", 0.0)
    recall = metrics.metadata.get("recall", 0.0)

    if precision < precision_threshold or recall < recall_threshold:
        print(f"Model did not meet thresholds. P={precision:.4f} R={recall:.4f}")
        return Outputs(should_deploy=False, model_resource_name="")

    aiplatform.init(project=project_id, location=location)
    model = aiplatform.Model.upload(
        display_name=model_display_name,
        artifact_uri=input_model.uri,
        serving_container_image_uri=(
            "us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-5:latest"
        ),
    )
    print(f"Model registered: {model.resource_name}")
    return Outputs(should_deploy=True, model_resource_name=model.resource_name)


@dsl.component(
    base_image="python:3.12-slim",
    packages_to_install=["google-cloud-aiplatform"],
)
def deploy_model_to_endpoint(
    project_id: str,
    location: str,
    model_resource_name: str,
    endpoint_display_name: str,
) -> None:
    """Deploy the registered model to a Vertex AI Endpoint."""
    from google.cloud import aiplatform

    aiplatform.init(project=project_id, location=location)
    model = aiplatform.Model(model_name=model_resource_name)

    # Get or create endpoint
    endpoints = aiplatform.Endpoint.list(
        filter=f'display_name="{endpoint_display_name}"',
        project=project_id,
        location=location,
    )
    endpoint = endpoints[0] if endpoints else aiplatform.Endpoint.create(
        display_name=endpoint_display_name
    )

    model.deploy(
        endpoint=endpoint,
        machine_type="n1-standard-4",
        min_replica_count=1,
        max_replica_count=3,
        traffic_percentage=100,
    )
    print(f"Model deployed to endpoint: {endpoint.resource_name}")


# ── Pipeline Definition ────────────────────────────────────────────────────────

@dsl.pipeline(
    name="enterpriseiq-anomaly-training",
    description="Train and deploy Isolation Forest anomaly detection model",
)
def anomaly_training_pipeline(
    project_id: str = "enterpriseiq-dev",
    location: str = "us-central1",
    dataset_id: str = "enterpriseiq_core",
    table: str = "anomaly_training_data",
    metric_columns: list = ["value", "rolling_mean", "rolling_std"],
    contamination: float = 0.05,
    n_estimators: int = 200,
    model_display_name: str = "isolation-forest-v1",
    endpoint_display_name: str = "anomaly-detection-endpoint",
    precision_threshold: float = 0.90,
    recall_threshold: float = 0.85,
) -> None:
    # Step 1: Extract data
    extract_task = extract_training_data(
        project_id=project_id,
        dataset_id=dataset_id,
        table=table,
        metric_columns=metric_columns,
    )

    # Step 2: Train
    train_task = train_isolation_forest(
        input_dataset=extract_task.outputs["output_dataset"],
        contamination=contamination,
        n_estimators=n_estimators,
    )

    # Step 3: Register (conditional)
    register_task = register_model(
        project_id=project_id,
        location=location,
        model_display_name=model_display_name,
        input_model=train_task.outputs["output_model"],
        metrics=train_task.outputs["metrics"],
        precision_threshold=precision_threshold,
        recall_threshold=recall_threshold,
    )

    # Step 4: Deploy only if registration succeeded
    with dsl.Condition(register_task.outputs["should_deploy"] == True, name="deploy-if-ready"):
        deploy_model_to_endpoint(
            project_id=project_id,
            location=location,
            model_resource_name=register_task.outputs["model_resource_name"],
            endpoint_display_name=endpoint_display_name,
        )


def compile_and_submit_pipeline(run_immediately: bool = False) -> str:
    """Compile pipeline YAML and optionally submit to Vertex AI."""
    from kfp import compiler

    output_path = "pipelines/anomaly_training_pipeline.yaml"
    compiler.Compiler().compile(anomaly_training_pipeline, output_path)
    print(f"Pipeline compiled to: {output_path}")

    if run_immediately:
        aiplatform.init(project="enterpriseiq-dev", location="us-central1")
        job = aiplatform.PipelineJob(
            display_name="anomaly-training-run",
            template_path=output_path,
            pipeline_root="gs://enterpriseiq-ml-artifacts/pipelines",
        )
        job.run(sync=True)
        return job.resource_name

    return output_path
