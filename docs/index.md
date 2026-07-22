# Google Search Quality Intelligence Platform

> **Predicting Search Quality Degradation Before Users Notice**

![Platform Logo Banner](assets/images/logo_banner.png)

Welcome to the documentation for the **Google Search Quality Intelligence Platform**, a production-grade analytics engineering and MLOps platform designed to detect micro-degradations in Google Search quality.

---

## Key Capabilities

- **Synthetic Log Generation**: Multi-dimensional search logs engine with embedded micro-degradation anomalies.
- **Data Quality & Validation**: Great Expectations automated schema and metric distribution verification suite.
- **Data Warehouse**: PostgreSQL star-schema analytical warehouse managed with dbt Core transformations.
- **Feature Store**: Feast MLOps offline Parquet storage and low-latency online SQLite materialization.
- **ML & Interpretability**: XGBoost Search Quality Score (SQS) regressor, Optuna tuning, SHAP explainers, and Isolation Forest anomaly detection.
- **Low-Latency Serving**: FastAPI microservice serving predictions under 25ms.
- **Operations Dashboard**: Multi-page Streamlit portal providing live operational telemetry and model playgrounds.

---

## Architecture Overview

```mermaid
graph TD
    A[Logs Generator] -->|Raw Parquet logs| B[Great Expectations Validator]
    B -->|Validated logs| C[DW Bulk Ingestor]
    C -->|Relational tables| D[(PostgreSQL Data Warehouse)]
    D -->|dbt Core SQL| E[Analytical Marts]
    E -->|Offline feature views| F[Feast Feature Store]
    F -->|get_historical_features| G[XGBoost Train & Optuna Tune]
    G -->|Trained weights| H[SHAP Explainer & Isolation Forest]
    H -->|Serialize binaries| I[Local Promotions Registry]
    I -->|Promote models| J[FastAPI Serving Microservice]
    F -->|get_online_features| J
    J -->|Real-time predict| K[Streamlit Operations Dashboard]
```

---

## Quickstart Guide

Launch the full stack with single-command Docker Compose:

```bash
docker compose up --build
```

Access endpoints:
- **FastAPI OpenAPI UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Streamlit Operations Dashboard**: [http://localhost:8501](http://localhost:8501)
