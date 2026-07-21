# System Design & Data Flow Architecture

This document describes the technical architecture, data flows, and component structure for the Google Search Quality Intelligence Platform.

---

## 1. High-Level System Architecture

Our platform follows a modular, decoupled batch-processing design patterns. While real-world Google search logs require streaming ingestion (Kappa pattern), this platform uses an **orchestrated batch-lakehouse architecture** built around Docker container services for reliability, scalability, and ease of local development.

```mermaid
graph TD
    subgraph Ingestion Layer
        A["Raw Search Logs (Parquet)"] --> B["Python Ingestion Engine"]
        B --> C["Great Expectations Validator"]
    end

    subgraph Storage & Analytics Warehouse (PostgreSQL & dbt)
        C --> D["Staging Schema (Views)"]
        D --> E["Core Dimensional Schema (Star Schema)"]
        E --> F["Aggregated Metrics (Incremental Tables)"]
    end

    subgraph Orchestration & Pipelines (Airflow)
        G["Scheduler DAGs"] -.->|Trigger Ingest| B
        G -.->|Trigger Transformations| E
        G -.->|Trigger Training| H["Model Retrain Pipe"]
    end

    subgraph ML & Inference Serving
        F --> I["Feature Store Registry"]
        I --> J["FastAPI Predictor (XGBoost/Isolation Forest)"]
    end

    subgraph Visualization & Alerting
        F --> K["Streamlit Dashboard"]
        J --> K
        J --> L["Slack/Email Alerter"]
    end

    style A fill:#f9f,stroke:#333
    style D fill:#bbf,stroke:#333
    style J fill:#bfb,stroke:#333
    style K fill:#ff9,stroke:#333
```

---

## 2. Technical Stack Selection & Tradeoffs

To ensure our project feels premium, production-grade, and reproducible, we select the following technologies:

| Component | Selected Tech | Alternatives Evaluated | Google Internal Equivalent | Tradeoff / Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion Pipeline** | Python (Pandas / PyArrow) | Apache Spark | Cloud Dataflow (Apache Beam) | Python + PyArrow is highly efficient for local datasets up to 10M rows and has low Docker setup overhead compared to Spark. |
| **Data Warehouse** | PostgreSQL | DuckDB / SQLite | Google BigQuery | PostgreSQL supports complete ACID constraints, complex indexing (B-Tree/Hash), and integrates natively with standard dbt profiles. |
| **Transformations** | dbt (Data Build Tool) | Custom SQL scripts | Google PLX / SQLRunner | dbt provides native lineage, testing, documentation, and version control for SQL models. |
| **Orchestrator** | Apache Airflow | Prefect / Cron | Google Cloud Composer | Airflow is the industry standard for metadata-driven DAG orchestration and dependency management. |
| **Machine Learning** | XGBoost / LightGBM | PyTorch / Scikit-Learn | Vertex AI / TF Ranking | Gradient Boosting Decision Trees (GBDTs) consistently beat deep learning models on structured tabular event logs. |
| **Inference Server** | FastAPI (ASGI) | Flask (WSGI) | Triton Inference Server | FastAPI is asynchronous, automatically generates OpenAPI documentation, and has Pydantic validation. |
| **Dashboard Layer** | Streamlit | Dash / React | Plx / Looker | Streamlit allows fast, interactive UI development entirely in Python with native support for charting libraries. |

---

## 3. Data Flow Stages

The platform processes data through five distinct stages:

### Stage 1: Generation & Ingestion
- Synthetic log generators write daily search events to raw Parquet files.
- The Python ingestion script reads files, executes validation checks via Great Expectations, and performs cryptographic salting and hashing on PII fields.
- Validated records are loaded into the database staging schema.

### Stage 2: Transform & Modeling
- dbt transforms raw rows into clean, typed staging views.
- Models join staging views to construct the Star Schema (Fact and Dimension tables).
- Window functions run sessionization logic to calculate dwell times, pogo-sticking flags, and query reformulation indices.
- Data is materialized into aggregated daily metrics tables.

### Stage 3: Feature Extraction & Registry
- The Feature Store pulls metrics from the daily tables to compute rolling aggregates (e.g., user-level 7-day average latency).
- Features are registered and serialized in Parquet format for model training.

### Stage 4: Modeling & Scoring (ML)
- XGBoost/LightGBM regressors predict the query-level Search Quality Score (SQS).
- Isolation Forest unsupervised pipelines flag multi-dimensional outliers.
- SHAP explainability engines generate attribution values for anomalous records.

### Stage 5: Serving & Visualization
- Streamlit queries aggregated metrics tables to render trend charts and operational logs.
- When an anomaly is flagged, the app makes an API request to the FastAPI serving container to fetch SHAP details and posts alert payloads to Slack webhooks.

---

## 4. Component Encapsulation & Decoupling

To prevent monolithic dependencies, the system enforces **component isolation**:
1.  **Database Separation**: Staging tables, core warehouse tables, and metric views reside in separate schemas inside PostgreSQL.
2.  **API Decoupling**: The FastAPI inference service is completely stateless. It loads model weights and runs predictions entirely in RAM, communicating with other components only via standard JSON request payloads.
3.  **State-Free Orchestration**: Airflow does not move or store data internally. It only issues execution commands to dbt, the python loader, and the model trainer, keeping worker nodes lightweight.
