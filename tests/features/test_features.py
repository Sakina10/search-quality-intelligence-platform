# Unit tests for Feature Store aggregations computation logic
import os
import sys
import pandas as pd
import numpy as np
import pytest

from src.features.compute_features import (
    compute_user_aggregates,
    compute_query_aggregates,
)


def test_user_and_query_feature_aggregations() -> None:
    """Verifies user and query rolling aggregations calculations."""
    df_events = pd.DataFrame(
        {
            "event_id": ["evt_1", "evt_2", "evt_3"],
            "timestamp": [
                pd.Timestamp("2026-07-15 12:00:00"),
                pd.Timestamp("2026-07-15 12:30:00"),
                pd.Timestamp("2026-07-15 13:00:00"),
            ],
            "user_id_masked": ["usr_01", "usr_01", "usr_02"],
            "search_query_masked": ["search text", "search text", "other query"],
            "search_intent": ["Informational", "Informational", "Commercial"],
            "query_category": ["Tech", "Tech", "Finance"],
            "clicks": [1, 0, 1],
            "impressions": [1, 1, 1],
            "dwell_time_sec": [60.0, 30.0, 15.0],
            "pogo_stick_flag": [0, 1, 0],
            "reformulation_flag": [0, 1, 0],
            "latency_ms": [100.0, 150.0, 200.0],
        }
    )

    df_user = compute_user_aggregates(df_events)
    assert len(df_user) == 2
    assert "user_7d_ctr" in df_user.columns
    assert "user_30d_avg_dwell_time" in df_user.columns

    df_query = compute_query_aggregates(df_events)
    assert len(df_query) == 2
    assert "query_key" in df_query.columns
    assert "query_avg_ctr" in df_query.columns
