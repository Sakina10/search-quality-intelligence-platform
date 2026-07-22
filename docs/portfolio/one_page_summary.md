# One-Page Technical Summary

**Platform Name**: Google Search Quality Intelligence Platform  
**Target Domain**: Search Quality Analytics, MLOps, Silent Degradation Detection  
**Tech Stack**: Python 3.10-3.12, PostgreSQL, dbt Core, Feast Feature Store, XGBoost, Optuna, SHAP, Great Expectations, FastAPI, Streamlit, Docker Compose, Pytest  

---

## Architecture Blueprint

```
[Raw Event Generator] ➔ [Great Expectations Schema Check]
                                  │
                                  ▼
                     [PostgreSQL Data Warehouse]
                                  │
                                  ▼
                       [dbt Dimensional Marts]
                                  │
                                  ▼
                     [Feast MLOps Feature Store]
                        │                    │
            (Offline Parquet)           (Online SQLite)
                        │                    │
                        ▼                    ▼
             [XGBoost & Optuna]      [FastAPI Microservice]
                        │                    │
                        └─────────┬──────────┘
                                  ▼
                   [Streamlit Operations Center]
```

---

## Technical Highlights

- **Data Engineering**: Vectorized multi-dimensional log generator produces partitioned Parquet datasets with embedded anomalies. Great Expectations asserts schema constraints.
- **Warehouse & Transformation**: PostgreSQL star schema modeling (`fct_search_events`, `dim_users`, `dim_queries`, `dim_systems`, `dim_geography`) with dbt transformations.
- **MLOps & Serving**: Feast online/offline feature store materialization eliminates training-serving skew. XGBoost regressor predicts SQS scores with sub-25ms inference.
- **Developer Experience**: Single-command container deployment (`docker compose up --build`), 100% type-checked codebase (`mypy`), automated tests (`pytest`), and standard `Makefile` shortcuts.
