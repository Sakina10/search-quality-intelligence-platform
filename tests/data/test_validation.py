import pandas as pd
import pytest

ge = pytest.importorskip("great_expectations")

from src.data.validate_data import generate_summary_report, run_ge_validations


def test_ge_validations_sample_dataframe() -> None:
    """Verifies that Great Expectations validation suite checks log attributes."""
    df = pd.DataFrame(
        {
            "event_id": ["evt_1", "evt_2"],
            "timestamp": [
                pd.Timestamp("2026-07-15 12:00:00"),
                pd.Timestamp("2026-07-15 13:00:00"),
            ],
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
            "search_quality_score": [92.0, 78.5],
        }
    )

    results = run_ge_validations(df)
    assert results is not None
    assert "success" in results
    assert results["success"] is True


def test_generate_summary_report() -> None:
    """Verifies report JSON structure generation."""
    mock_results = {
        "success": True,
        "statistics": {
            "evaluated_expectations": 10,
            "successful_expectations": 10,
            "unsuccessful_expectations": 0,
            "success_percent": 100.0,
        },
        "results": [],
    }

    report = generate_summary_report(mock_results, total_rows=100)
    assert report["validation_success"] is True
    assert report["total_records_validated"] == 100
