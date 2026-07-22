#!/usr/bin/env python3
"""Data validation suite using Great Expectations for search quality logs.

Verifies schema constraints, column type safety, missing values, categorical
ranges, and metric bounds on generated Parquet datasets.
"""

import json
import os
import sys
import time

# Disable Great Expectations telemetry to avoid exit latency / network hangs
os.environ["GX_ANALYTICS_ENABLED"] = "False"
os.environ["GE_USAGE_STATS"] = "False"

from typing import Any, Dict, List
import pandas as pd
import great_expectations as ge

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.config.config_loader import settings
from src.utils.logging_setup import logger


def load_partitioned_dataset(data_dir: str) -> pd.DataFrame:
    """Loads all partitioned parquet files from the target directory into a single DataFrame."""
    if not os.path.exists(data_dir):
        logger.error(f"Target data directory does not exist: {data_dir}")
        raise FileNotFoundError(f"Missing directory: {data_dir}")

    logger.info(f"Scanning data directory: {data_dir}")
    try:
        df = pd.read_parquet(data_dir)
        logger.info(f"Successfully loaded dataset with {len(df):,} records.")
        return df
    except Exception as e:
        logger.error(f"Failed to load Parquet files: {e}")
        raise e


def run_validation_suite(df: pd.DataFrame) -> Dict[str, Any]:
    """Wraps DataFrame and executes Great Expectations validations suite checks."""
    logger.info("Initializing Great Expectations validation suite...")
    ge_df = ge.from_pandas(df)

    # 1. Null Checks (Primary Keys and Timestamps must be fully populated)
    ge_df.expect_column_values_to_not_be_null("event_id")
    ge_df.expect_column_values_to_not_be_null("timestamp")
    ge_df.expect_column_values_to_not_be_null("user_id_masked")
    ge_df.expect_column_values_to_not_be_null("session_id")

    # 2. Categorical Values Constraints
    expected_countries = ["United States", "Japan", "United Kingdom", "Germany"]
    expected_devices = ["Mobile", "Desktop", "Tablet"]
    expected_intents = ["Commercial", "Informational", "Navigational"]

    ge_df.expect_column_values_to_be_in_set("country", expected_countries)
    ge_df.expect_column_values_to_be_in_set("device_type", expected_devices)
    ge_df.expect_column_values_to_be_in_set("search_intent", expected_intents)

    # 3. Numeric Metric Bounds
    # Clicks must be strictly binary
    ge_df.expect_column_values_to_be_in_set("clicks", [0, 1])
    # Impressions must be strictly 1
    ge_df.expect_column_values_to_be_in_set("impressions", [1])
    # Position must be between 1 and 10
    ge_df.expect_column_values_to_be_between("position", min_value=1, max_value=10)
    # Latency must be positive and under reasonable timeouts (15 seconds)
    ge_df.expect_column_values_to_be_between(
        "latency_ms", min_value=0.0, max_value=15000.0
    )
    # Page Speed Score must be between 0 and 100
    ge_df.expect_column_values_to_be_between(
        "page_speed_score", min_value=0.0, max_value=100.0
    )
    # Bounce Rate must be between 0 and 1
    ge_df.expect_column_values_to_be_between(
        "bounce_rate", min_value=0.0, max_value=1.0
    )
    # Search Quality Score must be between 0 and 100
    ge_df.expect_column_values_to_be_between(
        "search_quality_score", min_value=0.0, max_value=100.0
    )

    # 4. Trigger validation checks and return results object
    validation_results = ge_df.validate()
    return dict(validation_results)


def format_results_report(results: Dict[str, Any]) -> None:
    """Formats and prints validation result summaries to the terminal."""
    stats = results.get("statistics", {})
    success = results.get("success", False)

    evaluated = stats.get("evaluated_expectations", 0)
    successful = stats.get("successful_expectations", 0)
    failed = stats.get("unsuccessful_expectations", 0)
    success_pct = stats.get("success_percent", 0.0)

    logger.info("=" * 60)
    logger.info("DATA VALIDATION RUN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Overall Status: {'PASSED' if success else 'FAILED'}")
    logger.info(f"Evaluated Checks Count: {evaluated}")
    logger.info(f"Successful Checks: {successful}")
    logger.info(f"Failed Checks: {failed}")
    logger.info(f"Success Rate: {success_pct:.2f}%")
    logger.info("=" * 60)

    if failed > 0:
        logger.warning("VALIDATION FAILURE DETAILS:")
        for r in results.get("results", []):
            if not r.get("success", False):
                exp = r.get("expectation_config", {})
                kwargs = exp.get("kwargs", {})
                col = kwargs.get("column", "Unknown")
                check_type = exp.get("expectation_type", "Unknown")
                unexpected_count = r.get("result", {}).get("unexpected_count", 0)
                logger.warning(
                    f"  * Column '{col}' failed '{check_type}' checks. Unexpected values count: {unexpected_count}"
                )
        logger.info("=" * 60)


def main() -> None:
    data_dir = os.path.join(BASE_DIR, "data/search_events")

    try:
        # Load dataset
        df = load_partitioned_dataset(data_dir)

        # Run validations
        results = run_validation_suite(df)

        # Format metrics report
        format_results_report(results)

        # Export validation report to JSON logs
        report_path = os.path.join(BASE_DIR, "reports/validations/ge_run_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        # Strip complex pandas type structures from reports
        report_json = json.loads(json.dumps(results, default=str))
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2)

        logger.info(f"Validation report saved to: {report_path}")

        # Exit with error status if validation failed
        if not results.get("success", False):
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during validation process run: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
