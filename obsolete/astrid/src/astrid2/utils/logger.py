"""
Astrid Compiler Logging Utilities
"""

import logging
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for the given module name."""
    logger = logging.getLogger(f"astrid2.{name}")

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Default to warnings only

    return logger


def set_log_level(level: str):
    """Set the global log level for all Astrid loggers."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Set level for all astrid2 loggers
    logger = logging.getLogger("astrid2")
    logger.setLevel(numeric_level)

    # Also set for root logger if no handlers configured
    if not logger.handlers:
        logging.basicConfig(level=numeric_level)


def enable_debug_logging():
    """Enable debug logging for development."""
    set_log_level("DEBUG")


def enable_verbose_logging():
    """Enable verbose info logging."""
    set_log_level("INFO")
