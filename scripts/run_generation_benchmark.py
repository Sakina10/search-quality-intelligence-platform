#!/usr/bin/env python3
"""Execution benchmark runner for data generation scalability profiling.

Executes a million-row data generation, measuring throughput rates and peak
RAM footprints to validate scaling limits.
"""

import json
import os
import sys
import time

# Resolve path mapping
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Force production environment configurations to load 1M rows setting
os.environ["PLATFORM_ENV"] = "prod"

import psutil  # Standard resource checking helper
from src.config.config_loader import settings
from src.data.generate_logs import run_partitioned_generation
from src.utils.logging_setup import logger


def get_peak_memory_mb() -> float:
    """Returns memory footprint of the current process in Megabytes."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / (1024 * 1024)


def main() -> None:
    logger.info("=" * 60)
    logger.info("Starting Million-Row Scalability Benchmark...")
    logger.info("=" * 60)

    rows_to_gen = settings.data_generation.total_rows
    output_dir = os.path.join(BASE_DIR, "data/search_events")

    # Track performance parameters
    start_time = time.perf_counter()
    start_mem = get_peak_memory_mb()

    logger.info(f"Target row count: {rows_to_gen:,} rows")
    logger.info(f"Initial process memory usage: {start_mem:.2f} MB")

    # Run the partitioned generation engine
    run_partitioned_generation(rows_to_gen, output_dir)

    end_time = time.perf_counter()
    end_mem = get_peak_memory_mb()

    duration = end_time - start_time
    throughput = rows_to_gen / duration if duration > 0 else 0
    memory_growth = end_mem - start_mem

    logger.info("=" * 60)
    logger.info("Benchmark Completed.")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Throughput: {throughput:,.2f} rows/sec")
    logger.info(
        f"Peak memory footprint: {end_mem:.2f} MB (Growth: {memory_growth:+.2f} MB)"
    )
    logger.info("=" * 60)

    # Save statistics report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_rows": rows_to_gen,
        "duration_seconds": round(duration, 4),
        "throughput_rows_per_second": round(throughput, 2),
        "initial_memory_mb": round(start_mem, 2),
        "peak_memory_mb": round(end_mem, 2),
        "memory_growth_mb": round(memory_growth, 2),
        "output_directory": output_dir,
    }

    report_path = os.path.join(
        BASE_DIR, "reports/benchmarks/generation_performance.json"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Performance report exported to: {report_path}")


if __name__ == "__main__":
    main()
