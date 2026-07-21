# Changelog

All notable changes to the **Google Search Quality Intelligence Platform** will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-07-21
### Added
- Created `CONTRIBUTING.md` contribution guidelines.
- Created `CODE_OF_CONDUCT.md` contributor standards.
- Created `SECURITY.md` private vulnerability reporting policy.
- Created `ROADMAP.md` detailed releases and milestones path.
- Created PR and bug/feature issue templates under `.github/`.
- Created `.github/workflows/ci.yml` platform continuous integration workflow pipeline.
- Created `src/data/validate_data.py` data validation script utilizing Great Expectations to assert structural rules.
- Created `sql/dw_schema.sql` database schema scripts implementing the Star Schema warehouse modeling and range partition rules.
- Modified `task.md` and `walkthrough.md` to map to the new Open Source release roadmap structure.

---

## [0.1.0] - 2026-07-20
### Added
- Scaffolding of core codebase files (`Dockerfile`, `docker-compose.yml`, `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`).
- केन्द्रीय `config_loader.py` module parsing YAML configuration files and environment overrides.
- Centrale `logging_setup.py` singleton logger.
- Custom exceptions module `exceptions.py` defining system-wide domain error boundaries.
- Vectorized daily partitioned synthetic log generator script `generate_logs.py`.
- Automated Pytest suites verifying `config`, `data`, and `utils` packages.
- Scalability execution test runner `run_generation_benchmark.py` profiling throughput metrics and peak memory usage.
