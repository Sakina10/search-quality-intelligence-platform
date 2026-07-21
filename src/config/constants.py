"""Global System Constants for the Google Search Quality Intelligence Platform.

Contains system-wide immutable values, schema definitions, and metric thresholds
to avoid hardcoding strings inside calculations.
"""

from typing import Final, List

# Target Variable Classification Thresholds
SQS_EXCELLENT_MIN: Final[float] = 90.0
SQS_GOOD_MIN: Final[float] = 75.0
SQS_FAIR_MIN: Final[float] = 50.0

# SQS bucket names
SQS_BUCKET_EXCELLENT: Final[str] = "Excellent"
SQS_BUCKET_GOOD: Final[str] = "Good"
SQS_BUCKET_FAIR: Final[str] = "Fair"
SQS_BUCKET_POOR: Final[str] = "Poor"

# Database Schemas & Table Names
DB_SCHEMA_STAGING: Final[str] = "staging"
DB_SCHEMA_CORE: Final[str] = "core"
DB_SCHEMA_METRICS: Final[str] = "metrics"

DB_TABLE_SEARCH_EVENTS: Final[str] = "fct_search_events"
DB_TABLE_DIM_USERS: Final[str] = "dim_users"
DB_TABLE_DIM_QUERIES: Final[str] = "dim_queries"
DB_TABLE_DIM_SYSTEMS: Final[str] = "dim_systems"
DB_TABLE_DIM_GEOGRAPHY: Final[str] = "dim_geography"

# Technical Devices List
ALLOWED_DEVICES: Final[List[str]] = ["Mobile", "Desktop", "Tablet"]
ALLOWED_BROWSERS: Final[List[str]] = ["Chrome", "Safari", "Firefox", "Edge"]
ALLOWED_OS: Final[List[str]] = ["Android", "iOS", "Windows", "macOS", "Linux"]

# Observability Constraints
ANOMALY_ZSCORE_THRESHOLD: Final[float] = 3.0
MAX_INFERENCE_LATENCY_MS: Final[float] = 50.0  # P99 SLO
SESSION_TIMEOUT_MINUTES: Final[int] = 30
