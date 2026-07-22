#!/usr/bin/env python3
"""Machine Learning training pipeline with Feast features and Optuna tuning.

Constructs training dataset, queries Feast offline feature store, runs
hyperparameter optimization sweeps using Optuna, and trains the final
XGBoost regressor for Search Quality Score prediction.
"""

import os
import sys
import hashlib
import pickle
from typing import Any, Dict, List, Tuple
import pandas as pd
import numpy as np
import xgboost as xgb
import optuna
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.config.config_loader import settings
from src.utils.logging_setup import logger


def load_training_dataset() -> Tuple[pd.DataFrame, pd.Series]:
    """Retrieves events logs and joins Feast offline feature views to build training matrix."""
    data_dir = os.path.join(BASE_DIR, "data", "search_events")
    feature_store_dir = os.path.join(BASE_DIR, "src", "features")

    if not os.path.exists(data_dir):
        logger.error(f"Raw log events parquet files missing: {data_dir}")
        raise FileNotFoundError(f"Missing data: {data_dir}")

    logger.info("Loading search log events for ML training...")
    df_raw = pd.read_parquet(data_dir)
    if len(df_raw) > 50000:
        logger.info(
            f"Sampling training events from {len(df_raw):,} to 50,000 rows for local training loop performance..."
        )
        df_raw = df_raw.sample(50000, random_state=42).copy()

    # Generate query keys for Feast offline join matching
    df_raw["query_key"] = (
        df_raw["search_query_masked"].astype(str)
        + "_"
        + df_raw["search_intent"].astype(str)
        + "_"
        + df_raw["query_category"].astype(str)
    ).apply(lambda x: hashlib.md5(x.encode()).hexdigest())

    # 1. Prepare Feast entity dataframe
    entity_df = df_raw[["user_id_masked", "query_key", "timestamp"]].copy()
    entity_df.rename(columns={"timestamp": "event_timestamp"}, inplace=True)
    entity_df["event_timestamp"] = pd.to_datetime(entity_df["event_timestamp"])

    # 2. Retrieve offline features from Feast
    logger.info("Retrieving historical aggregates from Feast offline feature store...")
    from feast import FeatureStore

    store = FeatureStore(repo_path=feature_store_dir)

    features_list = [
        "fv_user_metrics:user_7d_ctr",
        "fv_user_metrics:user_30d_avg_dwell_time",
        "fv_user_metrics:user_pogo_sticking_count",
        "fv_query_metrics:query_avg_ctr",
        "fv_query_metrics:query_95p_latency_ms",
        "fv_query_metrics:query_reformulation_rate",
    ]

    training_features = store.get_historical_features(
        entity_df=entity_df, features=features_list
    ).to_df()

    # 3. Merge request-time indicators with offline conformed features
    logger.info("Building model input feature matrix...")
    df_raw.rename(columns={"timestamp": "event_timestamp"}, inplace=True)

    # Standardize timezones to naive format to prevent merge value type mismatches
    training_features["event_timestamp"] = pd.to_datetime(
        training_features["event_timestamp"]
    ).dt.tz_localize(None)
    df_raw["event_timestamp"] = pd.to_datetime(
        df_raw["event_timestamp"]
    ).dt.tz_localize(None)

    training_matrix = training_features.merge(
        df_raw[
            [
                "user_id_masked",
                "query_key",
                "event_timestamp",
                "latency_ms",
                "page_speed_score",
                "bounce_rate",
                "position",
                "search_quality_score",
            ]
        ],
        on=["user_id_masked", "query_key", "event_timestamp"],
        how="inner",
    )

    # Clean nulls (usually due to TTL limits or init boundaries)
    training_matrix.dropna(inplace=True)
    logger.info(f"Feature matrix compiled. Final rows: {len(training_matrix):,}")

    # Define features and label split
    feature_cols = [
        "user_7d_ctr",
        "user_30d_avg_dwell_time",
        "user_pogo_sticking_count",
        "query_avg_ctr",
        "query_95p_latency_ms",
        "query_reformulation_rate",
        "latency_ms",
        "page_speed_score",
        "bounce_rate",
        "position",
    ]

    X = training_matrix[feature_cols].copy()
    y = training_matrix["search_quality_score"].copy()

    return X, y


def train_xgboost(
    X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series
) -> Dict[str, Any]:
    """Runs Optuna hyperparameter optimization sweeps to find the best XGBoost parameters."""
    logger.info("Initializing Optuna study to optimize hyperparameters...")
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15),
            "n_estimators": trial.suggest_int("n_estimators", 50, 150),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "n_jobs": -1,
            "random_state": 42,
        }

        model = xgb.XGBRegressor(**params)
        model.fit(X_train, y_train)
        preds = model.predict(X_val)
        return float(mean_absolute_error(y_val, preds))

    study = optuna.create_study(direction="minimize")
    # Run 5 fast trials locally for swift code verification
    study.optimize(objective, n_trials=5)

    logger.info(f"Optuna optimization completed. Best MAE: {study.best_value:.4f}")
    return dict(study.best_params)


def main() -> None:
    models_dir = os.path.join(BASE_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. Compile historical training matrix
    X, y = load_training_dataset()

    # 2. Split dataset into Train and Validation
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 3. Optimize parameters
    best_params = train_xgboost(X_train, y_train, X_val, y_val)

    # 4. Train final optimized model
    logger.info(f"Training final XGBoost model with best parameters: {best_params}")
    final_model = xgb.XGBRegressor(**best_params, random_state=42)
    final_model.fit(X_train, y_train)

    # Evaluate final metrics
    preds = final_model.predict(X_val)
    mae = mean_absolute_error(y_val, preds)
    r2 = r2_score(y_val, preds)

    logger.info(f"Final Model Metrics: MAE = {mae:.4f}, R2 Score = {r2:.4f}")

    # Save final trained XGBoost model binary to disk
    model_path = os.path.join(models_dir, "sqs_predictor.pkl")
    logger.info(f"Saving trained XGBoost predictor binary model to: {model_path}")
    with open(model_path, "wb") as f:
        pickle.dump(final_model, f)

    # Write feature column metadata for downstream consistency
    meta_path = os.path.join(models_dir, "feature_metadata.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump(list(X.columns), f)

    logger.info("ML training pipeline execution completed successfully.")


if __name__ == "__main__":
    main()
