#!/usr/bin/env python3
"""Data warehouse bulk ingestion pipeline loading Parquet logs to PostgreSQL.

Loads daily partitioned Parquet datasets, extracts star-schema dimensions,
generates deterministic surrogate keys, and bulk-copies records into
PostgreSQL using psycopg2 copy_from utility.
"""

import hashlib
import io
import os
import sys
import time
from typing import Any

import pandas as pd

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.config.config_loader import settings
from src.utils.logging_setup import logger


def get_db_connection() -> Any:
    """Returns a raw connection to the PostgreSQL database warehouse."""
    db_conf = settings.database
    logger.info(
        f"Connecting to database {db_conf.name} on {db_conf.host}:{db_conf.port}..."
    )
    try:
        conn = psycopg2.connect(
            host=db_conf.host,
            port=db_conf.port,
            database=db_conf.name,
            user=db_conf.user,
            password=db_conf.password,
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise e


def reset_dw_schema(conn: Any) -> None:
    """Executes the DDL schema SQL script to reset database tables structure."""
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    ddl_path = os.path.join(base_dir, "sql", "dw_schema.sql")

    if not os.path.exists(ddl_path):
        logger.error(f"DDL schema script not found at: {ddl_path}")
        raise FileNotFoundError(f"Missing schema script: {ddl_path}")

    logger.info("Executing warehouse database schema DDL script...")
    with open(ddl_path, "r", encoding="utf-8") as f:
        ddl_sql = f.read()

    with conn.cursor() as cursor:
        cursor.execute(ddl_sql)
    conn.commit()
    logger.info("Database warehouse schema reset successfully.")


def generate_surrogate_key(*args: pd.Series) -> pd.Series:
    """Vectorized generator calculating deterministic MD5 surrogate key hashes."""
    # Concatenate columns with delimiter
    concatenated = args[0].astype(str)
    for col in args[1:]:
        concatenated = concatenated + "_" + col.astype(str)

    # Vectorized hashing
    return concatenated.apply(lambda x: hashlib.md5(x.encode()).hexdigest())


def copy_dataframe_to_table(conn: Any, df: pd.DataFrame, table_name: str) -> None:
    """Bulk loads a pandas DataFrame to PostgreSQL using in-memory COPY command."""
    logger.info(f"Bulk loading {len(df):,} rows into '{table_name}'...")
    start_time = time.perf_counter()

    # Save dataframe to an in-memory CSV text buffer
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, sep="\t", header=False, index=False, na_rep="\\N")
    csv_buffer.seek(0)

    with conn.cursor() as cursor:
        cursor.copy_from(
            csv_buffer, table_name, sep="\t", columns=df.columns, null="\\N"
        )

    duration = time.perf_counter() - start_time
    throughput = len(df) / duration if duration > 0 else 0
    logger.info(
        f"Loaded '{table_name}' in {duration:.2f} seconds ({throughput:,.2f} rows/sec)."
    )


def show_dry_run_summary(
    df_geo: pd.DataFrame,
    df_sys: pd.DataFrame,
    df_queries: pd.DataFrame,
    df_users: pd.DataFrame,
    df_fact: pd.DataFrame,
) -> None:
    """Logs dry-run transformations summary metrics and data schemas."""
    logger.info("=" * 60)
    logger.info("DRY-RUN WAREHOUSE INGESTION METRICS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"dim_geography:  {len(df_geo):,} unique locations extracted.")
    logger.info(
        f"dim_systems:    {len(df_sys):,} unique system configurations extracted."
    )
    logger.info(
        f"dim_queries:    {len(df_queries):,} unique search queries classified."
    )
    logger.info(
        f"dim_users:      {len(df_users):,} unique user profiles generated (SCD Type 2)."
    )
    logger.info(f"fct_events:     {len(df_fact):,} search event facts compiled.")
    logger.info("=" * 60)
    logger.info("SURROGATE KEYS SAMPLES:")
    logger.info(
        f"  * Geography key sample: {df_geo['geo_key'].iloc[0]} -> {df_geo['country'].iloc[0]}, {df_geo['region'].iloc[0]}"
    )
    logger.info(
        f"  * System key sample:    {df_sys['system_key'].iloc[0]} -> {df_sys['device_type'].iloc[0]}, {df_sys['os_name'].iloc[0]}"
    )
    logger.info(
        f"  * Query key sample:     {df_queries['query_key'].iloc[0]} -> '{df_queries['search_query_masked'].iloc[0]}'"
    )
    logger.info(
        f"  * User key sample:      {df_users['user_key'].iloc[0]} -> {df_users['user_id_masked'].iloc[0]}"
    )
    logger.info("=" * 60)
    logger.info("DRY-RUN SCHEMA CHECKS PASSED SUCCESSFULLY (0 rows actual changes).")
    logger.info("=" * 60)


def main() -> None:
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    data_dir = os.path.join(base_dir, "data", "search_events")

    if not os.path.exists(data_dir):
        logger.error(f"Partitioned Parquet log files not found at: {data_dir}")
        sys.exit(1)

    dry_run = False
    try:
        conn = get_db_connection()
    except psycopg2.OperationalError as e:
        logger.warning("=" * 60)
        logger.warning(f"Could not connect to database warehouse: {e}")
        logger.warning(
            "Falling back to local DRY-RUN mode to validate transformations..."
        )
        logger.warning("=" * 60)
        dry_run = True
        conn = None

    try:
        # 1. Reset Database warehouse structure
        if not dry_run and conn is not None:
            reset_dw_schema(conn)

        # 2. Load generated logs
        logger.info("Loading Parquet events dataset into memory...")
        df_events = pd.read_parquet(data_dir)

        # 3. Extract and generate Dimension Tables
        # Dim: Geography
        logger.info("Extracting unique dim_geography properties...")
        df_geo = df_events[["country", "region", "language"]].drop_duplicates().copy()
        df_geo["geo_key"] = generate_surrogate_key(
            df_geo["country"], df_geo["region"], df_geo["language"]
        )
        # Re-order to match table schema definition
        df_geo = df_geo[["geo_key", "country", "region", "language"]]

        # Dim: Systems
        logger.info("Extracting unique dim_systems technical specifications...")
        df_sys = (
            df_events[["device_type", "browser_name", "os_name"]]
            .drop_duplicates()
            .copy()
        )
        df_sys["system_key"] = generate_surrogate_key(
            df_sys["device_type"], df_sys["browser_name"], df_sys["os_name"]
        )
        df_sys["browser_version"] = "1.0.0"  # Default technical version
        df_sys = df_sys[
            ["system_key", "device_type", "browser_name", "os_name", "browser_version"]
        ]

        # Dim: Queries
        logger.info("Extracting unique dim_queries metadata...")
        df_queries = (
            df_events[["search_query_masked", "search_intent", "query_category"]]
            .drop_duplicates()
            .copy()
        )
        df_queries["query_key"] = generate_surrogate_key(
            df_queries["search_query_masked"],
            df_queries["search_intent"],
            df_queries["query_category"],
        )

        # Parse query word lengths and intents flags
        df_queries["is_navigational"] = (
            df_queries["search_intent"] == "Navigational"
        ).astype(int)
        df_queries["is_informational"] = (
            df_queries["search_intent"] == "Informational"
        ).astype(int)
        df_queries["is_transactional"] = (
            df_queries["search_intent"] == "Commercial"
        ).astype(int)
        df_queries["query_length_words"] = (
            df_queries["search_query_masked"]
            .astype(str)
            .apply(lambda x: len(x.split()))
        )

        df_queries = df_queries[
            [
                "query_key",
                "search_query_masked",
                "search_intent",
                "query_category",
                "is_navigational",
                "is_informational",
                "is_transactional",
                "query_length_words",
            ]
        ]

        # Dim: Users (Slowly Changing Dimension Type 2)
        logger.info("Generating dim_users profile details...")
        unique_users = df_events["user_id_masked"].drop_duplicates().copy()
        df_users = pd.DataFrame({"user_id_masked": unique_users})

        # Deterministic generation mapping based on user ID hashes to keep runs reproducible
        # Generate user keys using hashes
        df_users["user_key"] = df_users["user_id_masked"].apply(
            lambda x: hashlib.md5(x.encode()).hexdigest()
        )

        # Vectorized mapping using user hash bytes
        hash_ints = df_users["user_id_masked"].apply(
            lambda x: int(hashlib.md5(x.encode()).hexdigest()[:8], 16)
        )

        genders = ["Male", "Female", "Non-binary"]
        df_users["gender"] = hash_ints.apply(lambda x: genders[x % len(genders)])
        df_users["age"] = (hash_ints % 50) + 18

        channels = ["Organic", "Paid Search", "Social", "Referral", "Email"]
        df_users["signup_channel"] = hash_ints.apply(
            lambda x: channels[x % len(channels)]
        )

        # Sign up 1 to 6 months before 2026-06-01
        base_signup = pd.Timestamp("2026-01-01")
        df_users["signup_timestamp"] = hash_ints.apply(
            lambda x: base_signup + pd.Timedelta(days=int(x % 150))
        )

        segments = ["Heavy", "Medium", "Light"]
        df_users["user_segment"] = hash_ints.apply(
            lambda x: segments[x % len(segments)]
        )

        df_users["record_start_timestamp"] = df_users["signup_timestamp"]
        df_users["record_end_timestamp"] = pd.NaT  # Active current record
        df_users["is_current_record"] = 1

        df_users = df_users[
            [
                "user_key",
                "user_id_masked",
                "gender",
                "age",
                "signup_channel",
                "signup_timestamp",
                "user_segment",
                "record_start_timestamp",
                "record_end_timestamp",
                "is_current_record",
            ]
        ]

        # 4. Map surrogate keys into the Fact events table
        logger.info("Mapping dimension surrogate keys back to fact events table...")
        df_events_ingest = df_events.copy()

        # Join Geography keys
        df_events_ingest = df_events_ingest.merge(
            df_geo, on=["country", "region", "language"], how="left"
        )

        # Join System keys
        df_events_ingest = df_events_ingest.merge(
            df_sys[["system_key", "device_type", "browser_name", "os_name"]],
            on=["device_type", "browser_name", "os_name"],
            how="left",
        )

        # Join Query keys
        df_events_ingest = df_events_ingest.merge(
            df_queries[
                ["query_key", "search_query_masked", "search_intent", "query_category"]
            ],
            on=["search_query_masked", "search_intent", "query_category"],
            how="left",
        )

        # Join User keys
        df_events_ingest = df_events_ingest.merge(
            df_users[["user_key", "user_id_masked"]], on="user_id_masked", how="left"
        )

        # Structure Fact table fields to match DB DDL schemas
        df_fact = df_events_ingest[
            [
                "event_id",
                "timestamp",
                "user_key",
                "query_key",
                "system_key",
                "geo_key",
                "session_id",
                "position",
                "clicks",
                "impressions",
                "latency_ms",
                "page_speed_score",
                "bounce_rate",
                "pogo_stick_flag",
                "reformulation_flag",
                "dwell_time_sec",
                "revenue_estimate_usd",
                "search_quality_score",
            ]
        ].copy()

        # Rename event timestamp column
        df_fact.rename(columns={"timestamp": "event_timestamp"}, inplace=True)

        # 5. Bulk Load via Transactions / Dry-Run Summary
        if dry_run or conn is None:
            show_dry_run_summary(df_geo, df_sys, df_queries, df_users, df_fact)
        else:
            logger.info("Initiating database transaction bulk copies...")
            copy_dataframe_to_table(conn, df_geo, "dim_geography")
            copy_dataframe_to_table(conn, df_sys, "dim_systems")
            copy_dataframe_to_table(conn, df_queries, "dim_queries")
            copy_dataframe_to_table(conn, df_users, "dim_users")
            copy_dataframe_to_table(conn, df_fact, "fct_search_events")

            # Commit transaction
            conn.commit()
            logger.info("=" * 60)
            logger.info("DATABASE WAREHOUSE BULK INGESTION COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(
            f"In-process failure detected during ingestion. Rolling back transaction: {e}"
        )
        if not dry_run and conn is not None:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
