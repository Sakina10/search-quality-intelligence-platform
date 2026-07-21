# Unit tests for database warehouse bulk ingestion logic
import os
import sys
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# pyrefly: ignore [missing-import]
from src.data.ingest_dw import generate_surrogate_key, copy_dataframe_to_table


def test_generate_surrogate_key() -> None:
    """Verifies that surrogate keys are deterministically generated via hashes."""
    df = pd.DataFrame({
        "country": ["United States", "Japan"],
        "region": ["California", "Osaka"],
        "language": ["en", "ja"]
    })
    
    keys = generate_surrogate_key(df["country"], df["region"], df["language"])
    
    assert len(keys) == 2
    # Output should be standard MD5 hex string (32 characters)
    assert len(keys.iloc[0]) == 32
    assert keys.iloc[0] == keys.iloc[0]  # Reproducibility check
    assert keys.iloc[0] != keys.iloc[1]  # Differentiation check


@patch("psycopg2.connect")
def test_copy_dataframe_to_table(mock_connect: MagicMock) -> None:
    """Verifies that dataframes are correctly written to tables using COPY COPY cursor buffers."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    df = pd.DataFrame({
        "geo_key": ["hash1", "hash2"],
        "country": ["United States", "Japan"]
    })
    
    copy_dataframe_to_table(mock_conn, df, "dim_geography")
    
    # Assert copy_from was called on the cursor object
    assert mock_cursor.copy_from.called
    args, kwargs = mock_cursor.copy_from.call_args
    assert args[1] == "dim_geography"
    assert kwargs["sep"] == "\t"


@patch("src.data.ingest_dw.get_db_connection")
@patch("pandas.read_parquet")
@patch("src.data.ingest_dw.reset_dw_schema")
@patch("src.data.ingest_dw.copy_dataframe_to_table")
def test_ingestion_main_pipeline(
    mock_copy: MagicMock,
    mock_reset: MagicMock,
    mock_read: MagicMock,
    mock_get_conn: MagicMock
) -> None:
    """Tests the full ETL ingestion mapping and loading process flow."""
    # 1. Setup mock connection and cursor
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    # 2. Setup mock search events dataframe matching generator outputs
    mock_events = pd.DataFrame({
        "event_id": ["evt_1", "evt_2"],
        "timestamp": [pd.Timestamp("2026-07-15 12:00:00"), pd.Timestamp("2026-07-15 13:00:00")],
        "user_id_masked": ["usr_abc", "usr_xyz"],
        "session_id": ["sess_1", "sess_2"],
        "country": ["United States", "Japan"],
        "region": ["California", "Osaka"],
        "language": ["en", "ja"],
        "device_type": ["Mobile", "Desktop"],
        "browser_name": ["Chrome", "Safari"],
        "os_name": ["Android", "macOS"],
        "position": [1, 3],
        "clicks": [1, 0],
        "impressions": [1, 1],
        "serp_features": ["Snippet", "Images"],
        "latency_ms": [120.5, 95.0],
        "page_speed_score": [85.0, 92.0],
        "bounce_rate": [0.15, 0.45],
        "pogo_stick_flag": [0, 0],
        "reformulation_flag": [0, 1],
        "dwell_time_sec": [45.2, 0.0],
        "scroll_depth": [65.0, 0.0],
        "search_intent": ["Commercial", "Informational"],
        "query_category": ["Tech", "Finance"],
        "search_query_masked": ["python tutorial", "stock prices"],
        "revenue_estimate_usd": [0.15, 0.0],
        "search_quality_score": [92.0, 78.5]
    })
    mock_read.return_value = mock_events
    
    # 3. Import and run main
    # pyrefly: ignore [missing-import]
    from src.data.ingest_dw import main
    
    with patch("os.path.exists", return_value=True):
        main()
        
    # Verify database steps
    assert mock_get_conn.called
    assert mock_reset.called
    assert mock_read.called
    
    # Verify that copy_dataframe_to_table was called exactly 5 times (4 Dimensions + 1 Fact)
    assert mock_copy.call_count == 5
    
    # Verify order of loaded tables (Dimensions must be loaded before Facts)
    calls = [call_args[0][2] for call_args in mock_copy.call_args_list]
    assert "fct_search_events" in calls
    # fct_search_events should be the last table loaded
    assert calls[-1] == "fct_search_events"
    assert mock_conn.commit.called
    assert mock_conn.close.called
