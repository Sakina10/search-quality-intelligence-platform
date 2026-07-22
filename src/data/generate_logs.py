import os
import sys

import random
import shutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from faker import Faker

from src.config.config_loader import settings

# Initialize Faker and fix seed for reproducible user records
fake = Faker()
Faker.seed(settings.data_generation.random_seed)
random.seed(settings.data_generation.random_seed)
np.random.seed(settings.data_generation.random_seed)

# Define geographic mappings (Country -> Regions, Languages)
GEOGRAPHY_MAP: Dict[str, Dict[str, Any]] = {
    "United States": {
        "regions": ["California", "Texas", "New York", "Washington", "Illinois"],
        "languages": ["en", "es"],
        "lang_probs": [0.92, 0.08],
    },
    "Japan": {
        "regions": ["Tokyo", "Osaka", "Kyoto", "Hokkaido", "Fukuoka"],
        "languages": ["ja", "en"],
        "lang_probs": [0.98, 0.02],
    },
    "United Kingdom": {
        "regions": ["Greater London", "Scotland", "Wales", "Northern Ireland"],
        "languages": ["en"],
        "lang_probs": [1.0],
    },
    "Germany": {
        "regions": ["Bavaria", "Berlin", "Hamburg", "North Rhine-Westphalia"],
        "languages": ["de", "en"],
        "lang_probs": [0.95, 0.05],
    },
}

# Define technical device details
SYSTEMS_MAP: Dict[str, Dict[str, Any]] = {
    "Mobile": {
        "OS": ["Android", "iOS"],
        "OS_probs": [0.70, 0.30],
        "browsers": ["Chrome", "Safari", "Firefox"],
        "browser_probs": [0.65, 0.30, 0.05],
    },
    "Desktop": {
        "OS": ["Windows", "macOS", "Linux"],
        "OS_probs": [0.75, 0.20, 0.05],
        "browsers": ["Chrome", "Edge", "Firefox", "Safari"],
        "browser_probs": [0.60, 0.20, 0.15, 0.05],
    },
    "Tablet": {
        "OS": ["Android", "iOS"],
        "OS_probs": [0.45, 0.55],
        "browsers": ["Safari", "Chrome"],
        "browser_probs": [0.55, 0.45],
    },
}

# Define query categories and sample keywords
QUERY_CATEGORIES: Dict[str, List[str]] = {
    "Tech": [
        "python tutorial",
        "buy cell phone",
        "best laptop 2026",
        "how to install linux",
        "cloud server hosting",
    ],
    "Finance": [
        "stock prices today",
        "how to invest in index funds",
        "mortgage calculator",
        "bitcoin market cap",
        "best credit card rewards",
    ],
    "Health": [
        "symptoms of flu",
        "healthy diet plans",
        "benefits of running",
        "why does my head hurt",
        "yoga exercises for back pain",
    ],
    "Navigational": [
        "facebook login",
        "gmail sign in",
        "youtube music",
        "amazon prime deals",
        "netflix stream",
    ],
    "Informational": [
        "what is the capital of France",
        "why is the sky blue",
        "how photosynthesis works",
        "history of Rome",
        "Albert Einstein biography",
    ],
}

# Map categories to search intents
INTENT_MAP: Dict[str, str] = {
    "Tech": "Commercial",
    "Finance": "Commercial",
    "Health": "Informational",
    "Navigational": "Navigational",
    "Informational": "Informational",
}


def generate_diurnal_volumes_for_day(
    target_date: datetime, base_hourly_volume: int
) -> pd.DataFrame:
    """Generates hourly target volumes for a single day incorporating a diurnal cycle."""
    hours = [target_date + timedelta(hours=i) for i in range(24)]

    # Calculate diurnal multiplier: Peak at 14:00 UTC (phase shift = 8), Amplitude 0.4
    hour_values = np.array([h.hour for h in hours])
    multipliers = 1.0 + 0.4 * np.sin(2 * np.pi * (hour_values - 8) / 24)

    # Apply Poisson distribution to calculate actual hourly rows volume
    hourly_volumes = np.random.poisson(base_hourly_volume * multipliers)

    # Enforce at least 1 row per hour to keep data stable
    hourly_volumes = np.maximum(hourly_volumes, 1)

    return pd.DataFrame({"timestamp": hours, "volume": hourly_volumes})


def generate_search_logs_for_day(
    target_date: datetime, daily_rows: int
) -> pd.DataFrame:
    """Generates realistic search logs for a single day using vectorized calculations."""
    base_hourly_volume = int(daily_rows / 24)
    if base_hourly_volume == 0:
        base_hourly_volume = 1

    volume_df = generate_diurnal_volumes_for_day(target_date, base_hourly_volume)

    # Expand timestamps list to create rows
    timestamps = np.repeat(volume_df["timestamp"].values, volume_df["volume"].values)

    # Handle zero-row edge cases safely
    if len(timestamps) == 0:
        timestamps = np.array(
            [
                target_date + timedelta(hours=random.randint(0, 23))
                for _ in range(daily_rows)
            ]
        )

    # Clamp generated size to daily_rows if needed
    if len(timestamps) > daily_rows:
        timestamps = timestamps[:daily_rows]
    elif len(timestamps) < daily_rows:
        extra = np.random.choice(timestamps, daily_rows - len(timestamps))
        timestamps = np.concatenate([timestamps, extra])

    actual_rows = len(timestamps)

    # 2. Generate Dimension Attributes (Categorical vectors)
    countries = list(GEOGRAPHY_MAP.keys())
    country_choices = np.random.choice(countries, actual_rows, p=[0.4, 0.2, 0.2, 0.2])

    regions: List[str] = []
    languages: List[str] = []

    # Apply conditional geography rules
    for country in country_choices:
        geo = GEOGRAPHY_MAP[country]
        regions.append(random.choice(geo["regions"]))
        languages.append(np.random.choice(geo["languages"], p=geo["lang_probs"]))

    # System parameters
    devices = ["Mobile", "Desktop", "Tablet"]
    device_choices = np.random.choice(devices, actual_rows, p=[0.55, 0.35, 0.10])

    operating_systems: List[str] = []
    browsers: List[str] = []

    for dev in device_choices:
        sys = SYSTEMS_MAP[dev]
        operating_systems.append(np.random.choice(sys["OS"], p=sys["OS_probs"]))
        browsers.append(np.random.choice(sys["browsers"], p=sys["browser_probs"]))

    # Query details
    categories = list(QUERY_CATEGORIES.keys())
    category_choices = np.random.choice(
        categories, actual_rows, p=[0.25, 0.20, 0.20, 0.15, 0.20]
    )

    queries: List[str] = []
    intents: List[str] = []
    query_lengths: List[int] = []

    for cat in category_choices:
        q = random.choice(QUERY_CATEGORIES[cat])
        queries.append(q)
        intents.append(INTENT_MAP[cat])
        query_lengths.append(len(q.split()))

    # User IDs and Session IDs creation
    # Generating 50,000 distinct mock user hashes
    user_pool = [f"usr_{random.getrandbits(32):08x}" for _ in range(50000)]
    user_ids = np.random.choice(user_pool, actual_rows)

    # Grouping queries into session keys based on timestamps
    session_pool = [f"sess_{random.getrandbits(32):08x}" for _ in range(100000)]
    session_ids = np.random.choice(session_pool, actual_rows)

    # 3. Generate Metrics (Numeric vectors using probability distributions)
    # Positions: skewed heavily to top ranks (exponential decay)
    positions = np.random.geometric(p=0.45, size=actual_rows)
    positions = np.clip(positions, 1, 10)  # Max position 10 on first page

    # Baseline CTR calculation: decays exponentially based on position
    ctr_bases = 0.45 * np.exp(-0.35 * (positions - 1))
    # Bernoulli trial to determine click status
    clicks = np.random.binomial(n=1, p=ctr_bases)
    impressions = np.ones(actual_rows, dtype=int)

    # Latency: Lognormal skewed by Device type
    # Mobiles show higher latency (+80ms) than desktops
    latency_bases = np.random.lognormal(mean=4.8, sigma=0.5, size=actual_rows)
    latency_offsets = np.where(
        device_choices == "Mobile",
        80.0,
        np.where(device_choices == "Tablet", 40.0, 0.0),
    )
    latency_ms = latency_bases + latency_offsets

    # Page Speed Score: Beta distribution, Mobile skewed lower
    page_speed_bases = np.random.beta(a=8.0, b=2.0, size=actual_rows) * 100
    page_speed_score = np.where(
        device_choices == "Mobile", page_speed_bases - 15.0, page_speed_bases
    )
    page_speed_score = np.clip(page_speed_score, 0.0, 100.0)

    # Bounce Rate: Beta distribution skewed by latency
    # If latency > 500ms, bounce rates rise
    bounce_bases = np.random.beta(a=2.0, b=5.0, size=actual_rows)
    latency_penalty_bounce = np.where(
        latency_ms > 200, 0.25 * np.log(latency_ms / 200), 0.0
    )
    bounce_rates = np.clip(bounce_bases + latency_penalty_bounce, 0.05, 0.95)

    # Pogo-sticking (only possible if clicks == 1)
    # Rises if latency_ms is high or position is low
    pogo_stick_probs = np.where(
        clicks == 1, np.clip(0.1 + 0.15 * np.log(latency_ms / 100), 0.05, 0.90), 0.0
    )
    pogo_stick_flag = np.random.binomial(n=1, p=pogo_stick_probs)

    # Reformulation rate: high if query category is Informational
    reformulation_probs = np.where(category_choices == "Informational", 0.22, 0.08)
    reformulation_flag = np.random.binomial(n=1, p=reformulation_probs)

    # Dwell Time: Gamma distribution, affected by Intent
    dwell_bases = np.random.gamma(shape=2.0, scale=30.0, size=actual_rows)
    dwell_time = np.where(
        intents == "Navigational",
        dwell_bases * 0.2,
        np.where(intents == "Informational", dwell_bases * 3.0, dwell_bases),
    )
    # Ensure zero dwell if no click occurred
    dwell_time = np.where(clicks == 0, 0.0, dwell_time)

    # Scroll depth
    scroll_depth = np.where(
        clicks == 1, np.random.beta(a=5.0, b=2.0, size=actual_rows) * 100, 0.0
    )

    # SERP features presence list
    serp_features_pool = [
        "Featured Snippet",
        "Knowledge Graph",
        "Ad Blocks",
        "Local Pack",
        "Images Card",
    ]
    serp_features = [
        ", ".join(random.sample(serp_features_pool, k=random.randint(1, 3)))
        for _ in range(actual_rows)
    ]

    # Ad Revenue Estimate
    revenue_estimate = np.where(
        clicks == 1, np.random.exponential(scale=0.4, size=actual_rows), 0.0
    )
    revenue_estimate = np.round(np.clip(revenue_estimate, 0.0, 5.0), 4)

    # 4. Inject Anomaly (Load dynamically from configs)
    config_gen = settings.data_generation
    if config_gen.anomaly_simulation:
        anomaly_date_val = datetime.strptime(config_gen.anomaly_date, "%Y-%m-%d").date()

        if target_date.date() == anomaly_date_val:
            ts_datetime = pd.to_datetime(timestamps)
            # Identify indices: matching target country, device, and outage window (12:00 to 15:00 UTC)
            anomaly_mask = (
                (country_choices == config_gen.anomaly_country)
                & (device_choices == config_gen.anomaly_device)
                & (ts_datetime.hour >= 12)
                & (ts_datetime.hour <= 15)
            )

            # Apply degradation factors
            multiplier = config_gen.anomaly_latency_multiplier
            latency_ms[anomaly_mask] *= multiplier
            page_speed_score[anomaly_mask] *= 1.0 / multiplier
            bounce_rates[anomaly_mask] = np.clip(
                bounce_rates[anomaly_mask] + 0.35, 0.05, 0.95
            )
            clicks[anomaly_mask] = np.random.binomial(
                n=1, p=ctr_bases[anomaly_mask] * 0.4
            )
            pogo_stick_flag[anomaly_mask] = np.where(clicks[anomaly_mask] == 1, 1, 0)

    # 5. Target Variable Calculation (SQS) - Non-linear interactions
    # Latency penalty interacts with Search Intent
    latency_penalty_sqs = np.where(
        latency_ms > 150, 8.0 * np.log(latency_ms / 150), 0.0
    )
    intent_penalty_multiplier = np.where(intents == "Commercial", 1.8, 1.0)

    sqs_raw = (
        100.0
        - (positions * 2.2)
        - (reformulation_flag * 12.0)
        - (pogo_stick_flag * 18.0)
        - (latency_penalty_sqs * intent_penalty_multiplier)
    )

    # Add normal noise
    noise = np.random.normal(loc=0.0, scale=2.0, size=actual_rows)
    search_quality_score = np.clip(sqs_raw + noise, 0.0, 100.0)

    # 6. Compile DataFrame
    df = pd.DataFrame(
        {
            "event_id": [
                f"evt_{random.getrandbits(64):016x}" for _ in range(actual_rows)
            ],
            "timestamp": timestamps,
            "user_id_masked": user_ids,
            "session_id": session_ids,
            "country": country_choices,
            "region": regions,
            "language": languages,
            "device_type": device_choices,
            "browser_name": browsers,
            "os_name": operating_systems,
            "position": positions,
            "clicks": clicks,
            "impressions": impressions,
            "serp_features": serp_features,
            "latency_ms": np.round(latency_ms, 2),
            "page_speed_score": np.round(page_speed_score, 1),
            "bounce_rate": np.round(bounce_rates, 4),
            "pogo_stick_flag": pogo_stick_flag,
            "reformulation_flag": reformulation_flag,
            "dwell_time_sec": np.round(dwell_time, 2),
            "scroll_depth": np.round(scroll_depth, 1),
            "search_intent": intents,
            "query_category": category_choices,
            "search_query_masked": queries,
            "revenue_estimate_usd": revenue_estimate,
            "search_quality_score": np.round(search_quality_score, 2),
        }
    )

    # Extract date columns for partitioning folder structure
    dt_index = pd.DatetimeIndex(df["timestamp"])
    df["year"] = dt_index.year
    df["month"] = dt_index.strftime("%m")
    df["day"] = dt_index.strftime("%d")

    return df


def generate_search_logs(total_rows: int) -> pd.DataFrame:
    """Legacy wrapper matching unit tests signatures.

    Runs chunked generation and compiles the entire list back into a single dataframe in memory.
    """
    config_gen = settings.data_generation
    start_dt = config_gen.start_date
    end_dt = config_gen.end_date

    start_date = datetime.strptime(start_dt, "%Y-%m-%d")
    end_date = datetime.strptime(end_dt, "%Y-%m-%d")
    total_days = (end_date - start_date).days

    if total_days <= 0:
        return generate_search_logs_for_day(start_date, total_rows)

    daily_volume = int(total_rows / total_days)
    remainder = total_rows - (daily_volume * total_days)

    dfs = []
    current_date = start_date
    day_idx = 0
    while current_date < end_date:
        volume = daily_volume + (1 if day_idx < remainder else 0)
        dfs.append(generate_search_logs_for_day(current_date, volume))
        current_date += timedelta(days=1)
        day_idx += 1

    full_df = pd.concat(dfs, ignore_index=True)
    return full_df


def run_partitioned_generation(total_rows: int, output_dir: str) -> None:
    """Scalable production generation.

    Generates data day-by-day and writes each day directly to partitioned parquet files.
    """
    config_gen = settings.data_generation
    start_date = datetime.strptime(config_gen.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(config_gen.end_date, "%Y-%m-%d")
    total_days = (end_date - start_date).days

    if total_days <= 0:
        total_days = 1

    daily_volume = int(total_rows / total_days)
    remainder = total_rows - (daily_volume * total_days)

    print(
        f"Executing chunked generation: {total_days} days, {daily_volume} rows/day (remainder: {remainder})."
    )

    # Clear directory if it exists to prevent index overlaps
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    start_time = time.time()
    generated_rows = 0

    current_date = start_date
    day_idx = 0
    while current_date < end_date:
        volume = daily_volume + (1 if day_idx < remainder else 0)
        # 1. Generate single day logs in RAM
        day_df = generate_search_logs_for_day(current_date, volume)

        # 2. Save using pyarrow partitioning
        day_df.to_parquet(
            output_dir,
            partition_cols=["year", "month", "day"],
            index=False,
            compression="snappy",
        )

        generated_rows += len(day_df)
        current_date += timedelta(days=1)
        day_idx += 1

    duration = time.time() - start_time
    print(f"Generated {generated_rows} rows in {duration:.2f} seconds.")


if __name__ == "__main__":
    print("Launching production search logs generator...")
    rows = settings.data_generation.total_rows
    target_dir = "data/search_events"
    run_partitioned_generation(rows, target_dir)
