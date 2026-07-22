from src.data.generate_logs import generate_search_logs


def test_search_logs_generator_shapes() -> None:
    """Verifies that the generated DataFrame matches required row counts and contains all 26 columns."""
    rows = 1000
    df = generate_search_logs(rows)

    assert len(df) == rows
    assert df.shape[1] == 29

    # Check key columns exist
    expected_cols = [
        "event_id",
        "timestamp",
        "user_id_masked",
        "session_id",
        "country",
        "region",
        "language",
        "device_type",
        "browser_name",
        "os_name",
        "position",
        "clicks",
        "impressions",
        "serp_features",
        "latency_ms",
        "page_speed_score",
        "bounce_rate",
        "pogo_stick_flag",
        "reformulation_flag",
        "dwell_time_sec",
        "scroll_depth",
        "search_intent",
        "query_category",
        "search_query_masked",
        "revenue_estimate_usd",
        "search_quality_score",
    ]
    for col in expected_cols:
        assert col in df.columns


def test_metrics_logical_boundaries() -> None:
    """Checks that numerical features conform strictly to defined statistical bounds."""
    df = generate_search_logs(500)

    assert (df["clicks"].isin([0, 1])).all()
    assert (df["impressions"] == 1).all()
    assert (df["position"] >= 1).all()
    assert (df["position"] <= 10).all()
    assert (df["page_speed_score"] >= 0.0).all()
    assert (df["page_speed_score"] <= 100.0).all()
    assert (df["bounce_rate"] >= 0.05).all()
    assert (df["bounce_rate"] <= 0.95).all()
    assert (df["search_quality_score"] >= 0.0).all()
    assert (df["search_quality_score"] <= 100.0).all()

    # Dwell time must be 0 if there was no click
    no_click_df = df[df["clicks"] == 0]
    assert (no_click_df["dwell_time_sec"] == 0.0).all()
    assert (no_click_df["scroll_depth"] == 0.0).all()


def test_geography_conditional_integrity() -> None:
    """Verifies that regional language mapping corresponds to joint conditional probability rules."""
    df = generate_search_logs(200)

    jp_df = df[df["country"] == "Japan"]
    if not jp_df.empty:
        assert jp_df["language"].isin(["ja", "en"]).all()

    de_df = df[df["country"] == "Germany"]
    if not de_df.empty:
        assert de_df["language"].isin(["de", "en"]).all()
