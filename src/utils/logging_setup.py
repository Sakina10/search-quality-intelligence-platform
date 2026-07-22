"""Centralized Logging Configuration Module for the Search Quality Platform.

Provides structured formatting, level controls, and console/file output options
integrated with the Pydantic settings configuration engine.
"""

import logging
import os
import sys

from src.config.config_loader import settings


def configure_logger() -> logging.Logger:
    """Configures and returns the central logger instance (Singleton configuration)."""
    logger = logging.getLogger("SearchQualityPlatform")

    # Avoid duplicate handlers if logger is re-initialized
    if logger.handlers:
        return logger

    # 1. Set global logging level from settings config
    level_str = settings.logging.level.upper()
    log_level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(log_level)

    # 2. Define structured formatter
    formatter = logging.Formatter(settings.logging.format)

    # 3. Console Handler (Stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 4. File Handler (Optional based on configuration settings)
    if settings.logging.log_to_file:
        log_path = settings.logging.log_path
        log_dir = os.path.dirname(log_path)

        # Ensure log target directory exists
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create logs directory: {log_dir}. Error: {e}")
                return logger

        try:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(
                f"Failed to bind file logging handler to: {log_path}. Error: {e}"
            )

    return logger


# Export the singleton logger instance
logger: logging.Logger = configure_logger()
