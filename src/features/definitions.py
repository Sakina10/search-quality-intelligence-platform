# Feast feature definitions for Google Search Quality Platform
# MLOps Layer definitions

from datetime import timedelta

from feast import (
    Entity,
    FeatureView,
    Field,
    FileSource,
    ValueType,
)
from feast.types import Float32, Int64

# 1. Define Entities
user_entity = Entity(
    name="user_id_masked",
    value_type=ValueType.STRING,
    join_keys=["user_id_masked"],
    description="Unique user identification code (hashed).",
)

query_entity = Entity(
    name="query_key",
    value_type=ValueType.STRING,
    join_keys=["query_key"],
    description="Surrogate identifier of a unique query classification.",
)

import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
USER_PARQUET_PATH = os.path.join(
    PROJECT_ROOT, "data", "features", "user_features.parquet"
)
QUERY_PARQUET_PATH = os.path.join(
    PROJECT_ROOT, "data", "features", "query_features.parquet"
)

# 2. Define FileSources pointing to conformed Parquet files
user_source = FileSource(
    name="user_features_source",
    path=USER_PARQUET_PATH,
    event_timestamp_column="event_timestamp",
    created_timestamp_column=None,
)

query_source = FileSource(
    name="query_features_source",
    path=QUERY_PARQUET_PATH,
    event_timestamp_column="event_timestamp",
    created_timestamp_column=None,
)

# 3. Define Feature Views
user_feature_view = FeatureView(
    name="fv_user_metrics",
    entities=[user_entity],
    ttl=timedelta(days=365),
    schema=[
        Field(name="user_7d_ctr", dtype=Float32),
        Field(name="user_30d_avg_dwell_time", dtype=Float32),
        Field(name="user_pogo_sticking_count", dtype=Int64),
    ],
    online=True,
    source=user_source,
    tags={"team": "search_quality_mlops"},
)

query_feature_view = FeatureView(
    name="fv_query_metrics",
    entities=[query_entity],
    ttl=timedelta(days=365),
    schema=[
        Field(name="query_avg_ctr", dtype=Float32),
        Field(name="query_95p_latency_ms", dtype=Float32),
        Field(name="query_reformulation_rate", dtype=Float32),
    ],
    online=True,
    source=query_source,
    tags={"team": "search_quality_mlops"},
)
