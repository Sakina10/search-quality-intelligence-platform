# MLOps Design: Feature Store & Model Serving Architecture

This document describes the Machine Learning Operations (MLOps) architecture, covering the Feature Store, Model Registry, and Model Serving framework for the Google Search Quality Intelligence Platform.

---

## 1. MLOps Data Flow Architecture

To prevent **training-serving skew** (the primary cause of machine learning failures in production search networks), the platform separates the data flow into two parallel pipelines:
1.  **Offline Batch Pipeline (Training)**: Reads historical events from the PostgreSQL Data Warehouse, calculates 100+ aggregated features, registers them in the offline feature store, and exports them in bulk for training/validation.
2.  **Online Real-Time Pipeline (Inference)**: Accepts live API requests, queries the low-latency online feature store (simulated by PostgreSQL/Redis) to retrieve historical user and query attributes, merges them with request-time signals (e.g., live query latency), and runs inference via the model serving API.

```
[Offline Path: Training]
Postgres Data Warehouse ➔ Feast Offline Store ➔ Feature Registry ➔ XGBoost Training
                                                                         │
                                                                         ▼
                                                                  Model Registry
                                                                         │
                                                                         ▼
[Online Path: Inference]                                                 │
User Query ➔ FastAPI Serving ➔ Feast Online Store ➔ Model Inference ◄────┘
                     │
                     ▼
             Predicted Score
```

---

## 2. Feature Store Architecture

Our feature store manages features across two main entities: **Users** and **Queries**.

### 1. Entities
*   **User (`entity_user`)**: Keyed by `user_id_masked`. Used to track rolling behavioral aggregates (e.g., 7-day average bounce rate).
*   **Query (`entity_query`)**: Keyed by `query_key`. Used to track query-specific characteristics (e.g., intent class, mean historic CTR).

### 2. Feature Views
Feature views define the source datasets, entities, and feature columns managed by the store:

*   **User Feature View (`fv_user_metrics`)**:
    *   *Source*: `fct_search_events` joined with `dim_users`.
    *   *Features*: `user_7d_ctr`, `user_30d_avg_dwell_time`, `user_pogo_sticking_count`.
    *   *TTL (Time-to-Live)*: 30 days.
*   **Query Feature View (`fv_query_metrics`)**:
    *   *Source*: `fct_search_events` joined with `dim_queries`.
    *   *Features*: `query_avg_ctr`, `query_95p_latency_ms`, `query_reformulation_rate`.
    *   *TTL*: 90 days.

### 3. Registry & Synching
We use **Feast** configuration patterns:
- **Registry**: A central metadata database (`metadata.db` or Google Cloud Storage) mapping views to physical columns.
- **Materialization**: An automated daily job (orchestrated by Airflow) that reads new staging data from the offline warehouse (PostgreSQL) and writes the latest feature values to the online lookup store (PostgreSQL/Redis index).

---

## 3. Model Serving Architecture (API)

The inference service is implemented as a containerized FastAPI application.

```mermaid
sequenceDiagram
    participant User as Client/Dashboard
    participant API as FastAPI Inference Server
    participant FS as Feast Online Store
    participant Model as Registered Model (XGBoost)

    User->>API: POST /predict {user_id, query_key, current_latency}
    activate API
    API->>FS: Fetch features for user_id and query_key
    activate FS
    FS-->>API: Return historical aggregates (e.g. user_ctr, query_avg_ctr)
    deallocate FS
    API->>API: Combine input metrics with historical features
    API->>Model: Run model.predict(feature_vector)
    activate Model
    Model-->>API: Return Predicted Search Quality Score (SQS)
    deallocate Model
    API-->>User: Return JSON Response {sqs_score, status: success}
    deactivate API
```

### API Endpoint Contracts

#### 1. Predict Endpoint (`POST /predict`)
Receives live search events and predicts the SQS.
- **Request Payload**:
  ```json
  {
    "user_id_masked": "usr_948f219b2",
    "query_key": "qry_883a12ffb",
    "current_query_latency_ms": 145.2,
    "current_page_speed_score": 92.0
  }
  ```
- **Response Payload**:
  ```json
  {
    "prediction_timestamp": "2026-07-20T16:15:00Z",
    "predicted_search_quality_score": 88.42,
    "inference_latency_ms": 1.25,
    "status": "SUCCESS"
  }
  ```

#### 2. Anomaly Detection Endpoint (`POST /anomaly`)
Evaluates if a segment (e.g., mobile users in region US-West) shows anomalous quality metrics.
- **Request Payload**:
  ```json
  {
    "segment_dimensions": {
      "device_type": "Mobile",
      "country": "United States",
      "region": "California"
    },
    "metrics": {
      "avg_latency_ms": 420.5,
      "avg_ctr": 0.22,
      "avg_pogo_stick_rate": 0.18
    }
  }
  ```
- **Response Payload**:
  ```json
  {
    "is_anomaly": 1,
    "anomaly_score": -0.158,
    "contamination_threshold": -0.05,
    "flagged_timestamp": "2026-07-20T16:15:00Z"
  }
  ```

---

## 4. Model Registry Framework

To manage model lifecycle transitions, we construct a lightweight, local model registry:
1.  **Storage**: Versioned directory structure under `models/` (e.g., `models/v1_baseline/`, `models/v2_production/`).
2.  **Metadata File (`models/model_registry.json`)**: Tracks active models:
    ```json
    {
      "active_models": {
        "sqs_predictor": {
          "version": "1.2.0",
          "model_path": "models/sqs_predictor_v1_2_0.pkl",
          "framework": "XGBoost",
          "metrics": {
            "validation_mae": 1.84,
            "validation_rmse": 2.31
          },
          "deployed_at": "2026-07-20T12:00:00Z"
        },
        "anomaly_detector": {
          "version": "1.0.1",
          "model_path": "models/anomaly_detector_v1_0_1.pkl",
          "framework": "IsolationForest",
          "deployed_at": "2026-07-20T12:00:00Z"
        }
      }
    }
    ```
3.  **Promotion Policy**: During automated Airflow retraining (`Milestone 35`), a new model is registered but marked as `shadow`. It is promoted to `active` only if its validation metrics outperform the current model on the test suite.
