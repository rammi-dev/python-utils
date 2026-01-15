"""Tests for logging utilities."""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from dlh_airflow_common.utils.logging import get_logger, log_execution_time


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_default_level(self) -> None:
        """Test getting logger with default level."""
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO

    def test_get_logger_custom_level(self) -> None:
        """Test getting logger with custom level."""
        logger = get_logger("test_logger_debug", "DEBUG")
        assert logger.level == logging.DEBUG

    def test_get_logger_with_handler(self) -> None:
        """Test that logger has handlers configured."""
        logger = get_logger("test_logger_handler")
        assert len(logger.handlers) > 0


class TestLogExecutionTime:
    """Test suite for log_execution_time decorator."""

    def test_decorator_logs_execution(self) -> None:
        """Test that decorator logs function execution."""
        mock_logger = MagicMock()

        @log_execution_time(mock_logger)
        def sample_function() -> str:
            return "done"

        result = sample_function()

        assert result == "done"
        assert mock_logger.info.call_count == 2
        assert "Starting" in mock_logger.info.call_args_list[0][0][0]
        assert "Completed" in mock_logger.info.call_args_list[1][0][0]

    def test_decorator_logs_errors(self) -> None:
        """Test that decorator logs errors."""
        mock_logger = MagicMock()

        @log_execution_time(mock_logger)
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        mock_logger.error.assert_called_once()
        assert "Failed" in mock_logger.error.call_args[0][0]

    def test_decorator_without_logger(self) -> None:
        """Test decorator without explicit logger."""

        @log_execution_time()
        def sample_function() -> str:
            return "done"

        result = sample_function()
        assert result == "done"

    def test_decorator_measures_time(self) -> None:
        """Test that decorator measures execution time."""
        mock_logger = MagicMock()

        @log_execution_time(mock_logger)
        def slow_function() -> None:
            time.sleep(0.1)

        slow_function()

        # Check that time was logged
        log_message = mock_logger.info.call_args_list[1][0][0]
        assert "Completed" in log_message
        assert "0.1" in log_message or "0.0" in log_message
