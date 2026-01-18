"""Logging utilities for Airflow operators."""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def log_execution_time(logger: logging.Logger | None = None) -> Callable[[F], F]:
    """Decorator to log execution time of functions.

    Args:
        logger: Optional logger instance

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            start_time = time.time()
            logger.info(f"Starting {func.__name__}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Completed {func.__name__} in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Failed {func.__name__} after {elapsed:.2f}s: {e}")
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
