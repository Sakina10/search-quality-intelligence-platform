#!/usr/bin/env python3
"""Apache Airflow DAG for orchestrating the Google Search Quality Intelligence Platform.

Schedules and monitors:
1. Daily DW extraction and delta load ingestion (PostgreSQL).
2. Feast Feature Store rolling metrics computations and materialization.
3. XGBoost model retraining sweeps and local Promotions registry serialization.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# Default arguments for the pipeline tasks
default_args = {
    "owner": "search_quality_ops",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "search_quality_pipeline_orchestration",
    default_args=default_args,
    description="End-to-end Daily DW Ingestion, MLOps Feast compilation, and ML retraining pipeline.",
    schedule_interval="@daily",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["google_search_quality", "mlops"],
) as dag:

    # Task 1: Ingest log events and delta load dimensional warehouse
    ingest_dw = BashOperator(
        task_id="ingest_search_logs_dw",
        bash_command="python3 src/data/ingest_dw.py",
        env={"PYTHONPATH": "."},
    )

    # Task 2: Compute daily feature views and materialize to Feast online SQLite
    materialize_feature_store = BashOperator(
        task_id="materialize_feast_feature_store",
        bash_command="python3 src/features/register_features.py",
        env={"PYTHONPATH": "."},
    )

    # Task 3: Retrain XGBoost model regressor via Optuna tuning sweeps
    retrain_ml_model = BashOperator(
        task_id="retrain_xgboost_predictor",
        bash_command="python3 src/models/train_model.py",
        env={"PYTHONPATH": "."},
    )

    # Task 4: Generate SHAP attributions and serialize promotions registry metadata
    promote_model_registry = BashOperator(
        task_id="generate_shap_and_promote_registry",
        bash_command="python3 src/models/explain_model.py",
        env={"PYTHONPATH": "."},
    )

    # Define orchestration task sequence
    ingest_dw >> materialize_feature_store >> retrain_ml_model >> promote_model_registry
