#!/usr/bin/env python3
"""Low-latency FastAPI serving endpoints for Google Search Quality predictions.

Integrates Feast online feature store to retrieve historical indicators in real
time, feeds inputs to the trained XGBoost regressor, and runs unsupervised
Isolation Forest anomaly detection checks.
"""

import hashlib
import os
import pickle
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Map import path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.utils.logging_setup import logger

# Paths to models
MODELS_DIR = os.path.join(BASE_DIR, "models")
PREDICTOR_PATH = os.path.join(MODELS_DIR, "sqs_predictor.pkl")
ANOMALY_PATH = os.path.join(MODELS_DIR, "anomaly_detector.pkl")
FEATURE_STORE_DIR = os.path.join(BASE_DIR, "src", "features")

# Global models holders
predictor: Optional[Any] = None
anomaly_detector: Optional[Any] = None
feast_store: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Loads predictor regressor, isolation forest anomaly model, and Feast store instance."""
    global predictor, anomaly_detector, feast_store

    logger.info("Initializing serving API dependencies...")
    try:
        # Load XGBoost SQS model
        if os.path.exists(PREDICTOR_PATH):
            with open(PREDICTOR_PATH, "rb") as f:
                predictor = pickle.load(f)
            logger.info("XGBoost predictor model loaded successfully.")
        else:
            logger.warning(f"Predictor binary not found at: {PREDICTOR_PATH}")

        # Load Anomaly Detector
        if os.path.exists(ANOMALY_PATH):
            with open(ANOMALY_PATH, "rb") as f:
                anomaly_detector = pickle.load(f)
            logger.info("Isolation Forest anomaly detector model loaded successfully.")
        else:
            logger.warning(f"Anomaly detector binary not found at: {ANOMALY_PATH}")

        # Initialize Feast Online Store client
        try:
            from feast import FeatureStore

            if os.path.exists(os.path.join(FEATURE_STORE_DIR, "feature_store.yaml")):
                feast_store = FeatureStore(repo_path=FEATURE_STORE_DIR)
                logger.info("Feast Feature Store client connected successfully.")
            else:
                logger.warning(
                    f"Feast feature_store.yaml not found at {FEATURE_STORE_DIR}"
                )
        except Exception as fe:
            logger.warning(f"Feast feature store initialization skipped: {str(fe)}")

    except Exception as e:
        logger.error(f"Error initializing serving API dependencies: {str(e)}")

    yield

    logger.info("Shutting down serving API microservice.")


app = FastAPI(
    title="Google Search Quality Intelligence Platform serving API",
    description="Real-time inference and anomaly detection microservice.",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictRequest(BaseModel):
    user_id_masked: str = Field(..., min_length=1)
    search_query: str = Field(..., min_length=1)
    search_intent: str = Field(..., min_length=1)
    query_category: str = Field(..., min_length=1)
    latency_ms: float = Field(..., ge=0.0)
    page_speed_score: float = Field(..., ge=0.0, le=100.0)
    bounce_rate: float = Field(..., ge=0.0, le=1.0)
    position: int = Field(..., ge=1)


class PredictResponse(BaseModel):
    user_id_masked: str
    query_key: str
    predicted_search_quality_score: float
    feast_retrieval_latency_ms: float
    inference_latency_ms: float
    total_serving_latency_ms: float


class AnomalyRequest(BaseModel):
    latency_ms: float = Field(..., ge=0.0)
    bounce_rate: float = Field(..., ge=0.0, le=1.0)
    user_7d_ctr: float = Field(..., ge=0.0, le=1.0)


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    anomaly_score: float


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Simple API health probe."""
    return {"status": "healthy"}


@app.post("/predict", response_model=PredictResponse)
def predict_quality(request: PredictRequest) -> Dict[str, Any]:
    """Runs quality predictions joining Feast online store aggregates in real-time."""
    start_total = time.perf_counter()

    if predictor is None:
        raise HTTPException(status_code=503, detail="Predictor model not initialized.")

    # 1. Compute query classification key
    raw_query = (
        f"{request.search_query}_{request.search_intent}_{request.query_category}"
    )
    query_key = hashlib.md5(raw_query.encode()).hexdigest()

    # 2. Retrieve online features from Feast SQLite if available
    online_response: Dict[str, List[Any]] = {}
    feast_retrieval_ms = 0.0

    if feast_store is not None:
        start_feast = time.perf_counter()
        entity_row = {
            "user_id_masked": [request.user_id_masked],
            "query_key": [query_key],
        }

        features_list = [
            "fv_user_metrics:user_7d_ctr",
            "fv_user_metrics:user_30d_avg_dwell_time",
            "fv_user_metrics:user_pogo_sticking_count",
            "fv_query_metrics:query_avg_ctr",
            "fv_query_metrics:query_95p_latency_ms",
            "fv_query_metrics:query_reformulation_rate",
        ]

        try:
            online_response = feast_store.get_online_features(
                features=features_list, entity_rows=[entity_row]
            ).to_dict()
        except Exception as e:
            logger.error(f"Feast online feature lookup failed: {str(e)}")
            online_response = {}

        feast_retrieval_ms = (time.perf_counter() - start_feast) * 1000.0

    # Extract feature values, filling defaults for cold starts
    user_7d_ctr = online_response.get("user_7d_ctr", [None])[0]
    user_30d_avg_dwell = online_response.get("user_30d_avg_dwell_time", [None])[0]
    user_pogo = online_response.get("user_pogo_sticking_count", [None])[0]
    query_avg_ctr = online_response.get("query_avg_ctr", [None])[0]
    query_95p_lat = online_response.get("query_95p_latency_ms", [None])[0]
    query_reform = online_response.get("query_reformulation_rate", [None])[0]

    # Default fill strategy for cold targets
    user_7d_ctr = float(user_7d_ctr) if user_7d_ctr is not None else 0.0
    user_30d_avg_dwell = (
        float(user_30d_avg_dwell) if user_30d_avg_dwell is not None else 0.0
    )
    user_pogo = int(user_pogo) if user_pogo is not None else 0
    query_avg_ctr = float(query_avg_ctr) if query_avg_ctr is not None else 0.0
    query_95p_lat = float(query_95p_lat) if query_95p_lat is not None else 100.0
    query_reform = float(query_reform) if query_reform is not None else 0.0

    # 3. Form model features inputs list
    # Must preserve exact training columns sequence:
    # ["user_7d_ctr", "user_30d_avg_dwell_time", "user_pogo_sticking_count",
    #  "query_avg_ctr", "query_95p_latency_ms", "query_reformulation_rate",
    #  "latency_ms", "page_speed_score", "bounce_rate", "position"]
    features_input = np.array(
        [
            [
                user_7d_ctr,
                user_30d_avg_dwell,
                float(user_pogo),
                query_avg_ctr,
                query_95p_lat,
                query_reform,
                request.latency_ms,
                request.page_speed_score,
                request.bounce_rate,
                float(request.position),
            ]
        ],
        dtype=np.float32,
    )

    # 4. Predict Search Quality Score using XGBoost
    start_infer = time.perf_counter()
    pred_val = float(predictor.predict(features_input)[0])
    inference_ms = (time.perf_counter() - start_infer) * 1000.0

    # Clip quality score values between 0 and 100
    pred_val = max(0.0, min(100.0, pred_val))

    total_ms = (time.perf_counter() - start_total) * 1000.0

    return {
        "user_id_masked": request.user_id_masked,
        "query_key": query_key,
        "predicted_search_quality_score": pred_val,
        "feast_retrieval_latency_ms": feast_retrieval_ms,
        "inference_latency_ms": inference_ms,
        "total_serving_latency_ms": total_ms,
    }


@app.post("/anomaly", response_model=AnomalyResponse)
def detect_anomaly(request: AnomalyRequest) -> Dict[str, Any]:
    """Runs unsupervised Isolation Forest anomaly detection checks."""
    if anomaly_detector is None:
        raise HTTPException(
            status_code=503, detail="Anomaly detector model not initialized."
        )

    input_features = np.array(
        [[request.latency_ms, request.bounce_rate, request.user_7d_ctr]],
        dtype=np.float32,
    )

    # Isolation Forest: -1 for outlier/anomaly, 1 for normal
    pred_label = int(anomaly_detector.predict(input_features)[0])
    decision_score = float(anomaly_detector.decision_function(input_features)[0])

    is_anomaly = pred_label == -1

    return {"is_anomaly": is_anomaly, "anomaly_score": decision_score}
