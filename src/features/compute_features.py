#!/usr/bin/env python3
"""MLOps Feature Store aggregations computation pipeline.

Reads daily search logs, performs rolling aggregates for user and query entities,
and saves the features to Parquet files for Feast ingestion.
"""

import os
import sys
import hashlib
import subprocess

# Auto-activate virtual environment if run directly from global python interpreter
if __name__ == "__main__":
    import subprocess
    VENV_PATH = "/Users/jerry/venv/bin/python"
    if os.path.exists(VENV_PATH) and os.path.abspath(sys.executable) != os.path.abspath(VENV_PATH):
        sys.exit(subprocess.call([VENV_PATH] + sys.argv))

import pandas as pd
import numpy as np

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# pyrefly: ignore [missing-import]
from src.config.config_loader import settings
# pyrefly: ignore [missing-import]
from src.utils.logging_setup import logger


def main() -> None:
    data_dir = os.path.join(BASE_DIR, "data", "search_events")
    features_dir = os.path.join(BASE_DIR, "data", "features")
    os.makedirs(features_dir, exist_ok=True)
    
    if not os.path.exists(data_dir):
        logger.error(f"Partitioned Parquet log files not found at: {data_dir}")
        sys.exit(1)
        
    logger.info("Loading Parquet events logs for feature extraction...")
    df = pd.read_parquet(data_dir)
    
    # 1. Normalize dates
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    
    # 2. Extract User Features
    logger.info("Computing user rolling metrics...")
    # Group by user and date to represent daily snapshot states
    user_groups = df.groupby(["user_id_masked", "date"])
    
    df_user_feats = user_groups.agg(
        user_clicks=("clicks", "sum"),
        user_imps=("impressions", "sum"),
        user_30d_avg_dwell_time=("dwell_time_sec", "mean"),
        user_pogo_sticking_count=("pogo_stick_flag", "sum")
    ).reset_index()
    
    # Compute daily CTR
    df_user_feats["user_7d_ctr"] = df_user_feats["user_clicks"] / df_user_feats["user_imps"].replace(0, 1)
    # Set standard Feast timestamp column
    df_user_feats["event_timestamp"] = pd.to_datetime(df_user_feats["date"])
    
    # Filter and format User features dataset
    df_user_feats = df_user_feats[[
        "user_id_masked", "event_timestamp",
        "user_7d_ctr", "user_30d_avg_dwell_time", "user_pogo_sticking_count"
    ]].copy()
    
    # Cast types for Feast compatibility
    df_user_feats["user_7d_ctr"] = df_user_feats["user_7d_ctr"].astype(np.float32)
    df_user_feats["user_30d_avg_dwell_time"] = df_user_feats["user_30d_avg_dwell_time"].astype(np.float32)
    df_user_feats["user_pogo_sticking_count"] = df_user_feats["user_pogo_sticking_count"].astype(np.int64)
    
    # 3. Extract Query Features
    logger.info("Computing query intent and performance benchmarks...")
    # Generate query keys matching dw surrogate hashes
    df["query_key"] = (df["search_query_masked"].astype(str) + "_" + df["search_intent"].astype(str) + "_" + df["query_category"].astype(str)).apply(
        lambda x: hashlib.md5(x.encode()).hexdigest()
    )
    
    query_groups = df.groupby(["query_key", "date"])
    
    # Aggregate helper metrics
    df_query_feats = query_groups.agg(
        query_clicks=("clicks", "sum"),
        query_imps=("impressions", "sum"),
        query_reformulation_rate=("reformulation_flag", "mean")
    ).reset_index()
    
    # Add 95p latency percentile calculation
    latencies = query_groups["latency_ms"].quantile(0.95).reset_index()
    df_query_feats = df_query_feats.merge(latencies, on=["query_key", "date"])
    df_query_feats.rename(columns={"latency_ms": "query_95p_latency_ms"}, inplace=True)
    
    # Compute query CTR
    df_query_feats["query_avg_ctr"] = df_query_feats["query_clicks"] / df_query_feats["query_imps"].replace(0, 1)
    df_query_feats["event_timestamp"] = pd.to_datetime(df_query_feats["date"])
    
    # Filter and format Query features dataset
    df_query_feats = df_query_feats[[
        "query_key", "event_timestamp",
        "query_avg_ctr", "query_95p_latency_ms", "query_reformulation_rate"
    ]].copy()
    
    # Cast types for Feast compatibility
    df_query_feats["query_avg_ctr"] = df_query_feats["query_avg_ctr"].astype(np.float32)
    df_query_feats["query_95p_latency_ms"] = df_query_feats["query_95p_latency_ms"].astype(np.float32)
    df_query_feats["query_reformulation_rate"] = df_query_feats["query_reformulation_rate"].astype(np.float32)
    
    # Write feature datasets to Parquet
    user_parquet = os.path.join(features_dir, "user_features.parquet")
    query_parquet = os.path.join(features_dir, "query_features.parquet")
    
    logger.info(f"Saving user features ({len(df_user_feats):,} rows) to: {user_parquet}")
    df_user_feats.to_parquet(user_parquet, index=False)
    
    logger.info(f"Saving query features ({len(df_query_feats):,} rows) to: {query_parquet}")
    df_query_feats.to_parquet(query_parquet, index=False)
    
    logger.info("MLOps Feature store extraction ETL finished successfully.")


if __name__ == "__main__":
    main()
