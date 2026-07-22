#!/usr/bin/env python3
"""Feast Feature Store registration, materialization, and retrieval validation pipeline.

Automates offline aggregations compute, runs feast apply schema compile,
materializes features, and validates low-latency online retrieval.
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

import pandas as pd

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.utils.logging_setup import logger


def run_command(args: list[str], cwd: str) -> None:
    """Executes a system shell process with logs routing."""
    logger.info(f"Running command: {' '.join(args)}")
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with exit code {result.returncode}")
        logger.error(f"STDOUT:\n{result.stdout}")
        logger.error(f"STDERR:\n{result.stderr}")
        raise RuntimeError(f"Command failed: {args[0]}")
    logger.info(result.stdout.strip())


def main() -> None:
    feature_dir = os.path.join(BASE_DIR, "src", "features")

    # 1. Run compute aggregations script to generate the offline parquet files
    logger.info("Step 1: Running feature store daily aggregations compute pipeline...")
    compute_script = os.path.join(feature_dir, "compute_features.py")
    run_command([sys.executable, compute_script], cwd=BASE_DIR)

    # 2. Run feast apply to compile registry definitions metadata schema
    logger.info("Step 2: Compiling registry schema definitions via feast apply...")
    run_command([sys.executable, "-m", "feast", "apply"], cwd=feature_dir)

    # 3. Materialize features to the online sqlite lookup store
    logger.info("Step 3: Ingesting offline Parquet features into online store index...")
    # Materialize features from Epoch to now
    now_iso = datetime.utcnow().isoformat()
    run_command(
        [sys.executable, "-m", "feast", "materialize-incremental", now_iso],
        cwd=feature_dir,
    )

    # 4. Connect to online store and run latency audits
    logger.info("Step 4: Validating low-latency features retrieval from SQLite...")
    from feast import FeatureStore

    store = FeatureStore(repo_path=feature_dir)

    # Load first user and query keys from calculated files to run real retrieval
    features_dir = os.path.join(BASE_DIR, "data", "features")
    user_parquet = os.path.join(features_dir, "user_features.parquet")
    query_parquet = os.path.join(features_dir, "query_features.parquet")

    df_user = pd_read_sample(user_parquet, "user_id_masked")
    df_query = pd_read_sample(query_parquet, "query_key")

    sample_user = "usr_sample"
    sample_query = "query_sample"
    if df_user is not None and not df_user.empty:
        sample_user = str(df_user.iloc[0]["user_id_masked"])
    if df_query is not None and not df_query.empty:
        sample_query = str(df_query.iloc[0]["query_key"])

    # Single entity lookup check
    entity_rows = [{"user_id_masked": sample_user, "query_key": sample_query}]
    features_list = [
        "fv_user_metrics:user_7d_ctr",
        "fv_user_metrics:user_30d_avg_dwell_time",
        "fv_user_metrics:user_pogo_sticking_count",
        "fv_query_metrics:query_avg_ctr",
        "fv_query_metrics:query_95p_latency_ms",
        "fv_query_metrics:query_reformulation_rate",
    ]

    start_time = time.perf_counter()
    response = store.get_online_features(
        features=features_list, entity_rows=entity_rows
    ).to_dict()
    latency_ms = (time.perf_counter() - start_time) * 1000

    logger.info("=" * 60)
    logger.info("ONLINE FEATURE RETRIEVAL RESULTS:")
    logger.info("=" * 60)
    logger.info(f"Target User:        {sample_user}")
    logger.info(f"Target Query Key:   {sample_query}")
    logger.info(f"Inference Latency:  {latency_ms:.3f} ms")
    logger.info("-" * 60)

    for feat in features_list:
        val = response[feat.split(":")[1]][0]
        logger.info(f"  * {feat:<40}: {val}")
    logger.info("=" * 60)

    # Assert performance threshold
    assert latency_ms < 10.0, f"Retrieval latency too high: {latency_ms:.2f} ms"
    logger.info("MLOps Feast Feature Store successfully configured and verified.")


def pd_read_sample(path: str, col: str) -> Optional[pd.DataFrame]:
    """Safely reads first row details from target Parquet file."""
    try:
        return pd.read_parquet(path, columns=[col])
    except Exception:
        return None


if __name__ == "__main__":
    main()
