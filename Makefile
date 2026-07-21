.PHONY: build up down test lint type-check clean dbt-run dbt-test ingest bootstrap help

# Project Variables
COMPOSE_DEV = docker-compose -f docker-compose.yml

help:
	@echo "Google Search Quality Intelligence Platform - Automation Commands:"
	@echo "  make bootstrap     - Run environment checks and verify configurations"
	@echo "  make build         - Build Docker containers"
	@echo "  make up            - Launch PostgreSQL, API and Dashboard containers"
	@echo "  make down          - Tear down docker containers and purge volumes"
	@echo "  make lint          - Check styling and formatting using Ruff/Black"
	@echo "  make type-check    - Check type hints validity using Mypy"
	@echo "  make test          - Run python automated unit and integration tests"
	@echo "  make ingest        - Run python pipeline to load Parquet files to DB"
	@echo "  make dbt-run       - Execute dbt transformation models"
	@echo "  make dbt-test      - Execute dbt tests on tables and keys"
	@echo "  make clean         - Clear python cache files and test records"

bootstrap:
	python scripts/bootstrap.py

build: bootstrap
	$(COMPOSE_DEV) build --target dev

up: bootstrap
	$(COMPOSE_DEV) up --build -d

down:
	$(COMPOSE_DEV) down -v

lint:
	ruff check .
	black --check .

type-check:
	mypy --ignore-missing-imports --explicit-package-bases src/

test:
	docker compose run --rm api pytest -v tests/ --cov=src/

ingest:
	docker compose run --rm api python3 src/db/ingest_data.py

dbt-run:
	docker compose run --rm api dbt run --profiles-dir configs/dbt_profiles/

dbt-test:
	docker compose run --rm api dbt test --profiles-dir configs/dbt_profiles/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf target/ Target/
