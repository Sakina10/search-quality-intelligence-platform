import os

import pytest

from src.utils.exceptions import ConfigurationError, SearchQualityBaseError
from src.utils.helpers import ensure_directory, execution_timer
from src.utils.logging_setup import logger


def test_custom_exceptions() -> None:
    """Verifies exception classes compile and carry custom error payloads."""
    with pytest.raises(ConfigurationError) as exc_info:
        raise ConfigurationError("Database credentials missing")

    assert exc_info.value.message == "Database credentials missing"
    assert isinstance(exc_info.value, SearchQualityBaseError)


def test_directory_helper(tmp_path) -> None:
    """Ensures helper creates directories safely and handles edge cases."""
    target_dir = os.path.join(tmp_path, "logs_test_dir")
    assert not os.path.exists(target_dir)

    ensure_directory(target_dir)
    assert os.path.exists(target_dir)


def test_execution_timer_decorator() -> None:
    """Checks that the timer decorator wraps execution and returns correct outputs."""

    @execution_timer
    def add_numbers(a: int, b: int) -> int:
        return a + b

    res = add_numbers(10, 20)
    assert res == 30


def test_logger_setup() -> None:
    """Asserts that the exported singleton logger is correctly configured."""
    assert logger is not None
    assert logger.name == "SearchQualityPlatform"
