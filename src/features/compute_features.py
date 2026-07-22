#!/usr/bin/env python3
"""MLOps Feature Store aggregations computation pipeline.

Reads daily search logs, performs rolling aggregates for user and query entities,
and saves the features to Parquet files for Feast ingestion.
"""

import os
import sys
import hashlib
import pandas as pd
import numpy as np

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.config.config_loader import settings
from src.utils.logging_setup import logger


def compute_user_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Computes daily user rolling metrics from raw event logs."""
    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["timestamp"]).dt.date
    user_groups = df_copy.groupby(["user_id_masked", "date"])

    df_user_feats = user_groups.agg(
        user_clicks=("clicks", "sum"),
        user_imps=("impressions", "sum"),
        user_30d_avg_dwell_time=("dwell_time_sec", "mean"),
        user_pogo_sticking_count=("pogo_stick_flag", "sum"),
    ).reset_index()

    df_user_feats["user_7d_ctr"] = df_user_feats["user_clicks"] / df_user_feats[
        "user_imps"
    ].replace(0, 1)
    df_user_feats["event_timestamp"] = pd.to_datetime(df_user_feats["date"])

    df_user_feats = df_user_feats[
        [
            "user_id_masked",
            "event_timestamp",
            "user_7d_ctr",
            "user_30d_avg_dwell_time",
            "user_pogo_sticking_count",
        ]
    ].copy()

    df_user_feats["user_7d_ctr"] = df_user_feats["user_7d_ctr"].astype(np.float32)
    df_user_feats["user_30d_avg_dwell_time"] = df_user_feats[
        "user_30d_avg_dwell_time"
    ].astype(np.float32)
    df_user_feats["user_pogo_sticking_count"] = df_user_feats[
        "user_pogo_sticking_count"
    ].astype(np.int64)
    return df_user_feats


def compute_query_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Computes daily query performance benchmarks from raw event logs."""
    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["timestamp"]).dt.date
    df_copy["query_key"] = (
        df_copy["search_query_masked"].astype(str)
        + "_"
        + df_copy["search_intent"].astype(str)
        + "_"
        + df_copy["query_category"].astype(str)
    ).apply(lambda x: hashlib.md5(x.encode()).hexdigest())

    query_groups = df_copy.groupby(["query_key", "date"])
    df_query_feats = query_groups.agg(
        query_clicks=("clicks", "sum"),
        query_imps=("impressions", "sum"),
        query_reformulation_rate=("reformulation_flag", "mean"),
    ).reset_index()

    latencies = query_groups["latency_ms"].quantile(0.95).reset_index()
    df_query_feats = df_query_feats.merge(latencies, on=["query_key", "date"])
    df_query_feats.rename(columns={"latency_ms": "query_95p_latency_ms"}, inplace=True)

    df_query_feats["query_avg_ctr"] = df_query_feats["query_clicks"] / df_query_feats[
        "query_imps"
    ].replace(0, 1)
    df_query_feats["event_timestamp"] = pd.to_datetime(df_query_feats["date"])

    df_query_feats = df_query_feats[
        [
            "query_key",
            "event_timestamp",
            "query_avg_ctr",
            "query_95p_latency_ms",
            "query_reformulation_rate",
        ]
    ].copy()

    df_query_feats["query_avg_ctr"] = df_query_feats["query_avg_ctr"].astype(np.float32)
    df_query_feats["query_95p_latency_ms"] = df_query_feats[
        "query_95p_latency_ms"
    ].astype(np.float32)
    df_query_feats["query_reformulation_rate"] = df_query_feats[
        "query_reformulation_rate"
    ].astype(np.float32)
    return df_query_feats


def main() -> None:
    data_dir = os.path.join(BASE_DIR, "data", "search_events")
    features_dir = os.path.join(BASE_DIR, "data", "features")

    if not os.path.exists(data_dir):
        logger.error(f"Search events log folder not found at: {data_dir}")
        sys.exit(1)

    logger.info("Loading Parquet events logs for feature extraction...")
    df = pd.read_parquet(data_dir)

    logger.info("Computing user rolling metrics...")
    df_user_feats = compute_user_aggregates(df)

    logger.info("Computing query intent and performance benchmarks...")
    df_query_feats = compute_query_aggregates(df)

    os.makedirs(features_dir, exist_ok=True)
    user_out = os.path.join(features_dir, "user_features.parquet")
    query_out = os.path.join(features_dir, "query_features.parquet")

    df_user_feats.to_parquet(user_out, index=False)
    df_query_feats.to_parquet(query_out, index=False)

    logger.info(f"Exported {len(df_user_feats):,} user feature snapshots to {user_out}")
    logger.info(
        f"Exported {len(df_query_feats):,} query feature benchmarks to {query_out}"
    )
    logger.info(
        "MLOps Feature Store aggregations computation pipeline completed successfully."
    )


if __name__ == "__main__":
    main()
