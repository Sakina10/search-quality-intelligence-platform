.PHONY: install bootstrap build up down lint type-check test generate validate ingest features train explain dbt-run dbt-test clean help

# Project Variables
PYTHON ?= python3
COMPOSE_DEV = docker compose -f docker-compose.yml

help:
	@echo "Google Search Quality Intelligence Platform - Automation Commands:"
	@echo "  make install       - Install Python package dependencies from requirements.txt"
	@echo "  make bootstrap     - Run environment checks and verify configurations"
	@echo "  make build         - Build Docker containers"
	@echo "  make up            - Launch PostgreSQL, API and Dashboard containers"
	@echo "  make down          - Tear down docker containers and purge volumes"
	@echo "  make lint          - Check styling and formatting using Ruff/Black"
	@echo "  make type-check    - Check type hints validity using Mypy"
	@echo "  make test          - Run python automated unit and integration tests"
	@echo "  make generate      - Generate synthetic search log events Parquet files"
	@echo "  make validate      - Run Great Expectations data quality validation suite"
	@echo "  make ingest        - Run python pipeline to load Parquet files to DB"
	@echo "  make features      - Compile and materialize Feast Feature Store metrics"
	@echo "  make train         - Train XGBoost regressor with Optuna tuning sweeps"
	@echo "  make explain       - Generate SHAP attributions and train Isolation Forest"
	@echo "  make dbt-run       - Execute dbt transformation models"
	@echo "  make dbt-test      - Execute dbt tests on tables and keys"
	@echo "  make clean         - Clear python cache files, test records, and target artifacts"

install:
	$(PYTHON) -m pip install -r requirements.txt

bootstrap:
	$(PYTHON) scripts/bootstrap.py

build: bootstrap
	$(COMPOSE_DEV) build

up: bootstrap
	$(COMPOSE_DEV) up --build -d

down:
	$(COMPOSE_DEV) down -v

lint:
	ruff check . || $(PYTHON) -m ruff check . || true
	black --check . || $(PYTHON) -m black --check . || true

type-check:
	mypy --ignore-missing-imports --explicit-package-bases src/

test:
	pytest

generate:
	$(PYTHON) src/data/generate_logs.py

validate:
	$(PYTHON) src/data/validate_data.py

ingest:
	$(PYTHON) src/data/ingest_dw.py

features:
	$(PYTHON) src/features/register_features.py

train:
	$(PYTHON) src/models/train_model.py

explain:
	$(PYTHON) src/models/explain_model.py

dbt-run:
	dbt run --profiles-dir .

dbt-test:
	dbt test --profiles-dir .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf target/ Target/
