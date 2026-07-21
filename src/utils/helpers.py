"""Global Helper Utilities for the Search Quality Platform.

Contains reusable Python helpers, directory checkers, and profiling decorators
to keep modular code DRY (Don't Repeat Yourself).
"""

import os
import time
from functools import wraps
from typing import Any, Callable
from src.utils.logging_setup import logger


def ensure_directory(path: str) -> None:
    """Safely creates target directories if they do not exist."""
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Created system directory: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory path: {path}. Error: {e}")
            raise OSError(f"Could not create path: {path}") from e


def execution_timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure and log the execution time of code blocks."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.info(f"Function '{func.__name__}' completed execution in {duration:.4f} seconds.")
            return result
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"Function '{func.__name__}' failed after {duration:.4f} seconds with error: {e}")
            raise
    return wrapper
