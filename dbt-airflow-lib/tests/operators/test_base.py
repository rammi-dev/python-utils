"""Tests for base operator."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from dlh_airflow_common.operators.base import BaseOperator


class ConcreteOperator(BaseOperator):
    """Concrete implementation for testing."""

    def execute(self, context: Dict[str, Any]) -> str:
        """Execute the operator."""
        return "success"


class TestBaseOperator:
    """Test suite for BaseOperator."""

    def test_initialization(self) -> None:
        """Test operator initialization."""
        operator = ConcreteOperator(task_id="test_task")
        assert operator.task_id == "test_task"
        assert operator.log_level == "INFO"

    def test_initialization_with_log_level(self) -> None:
        """Test operator initialization with custom log level."""
        operator = ConcreteOperator(task_id="test_task", log_level="DEBUG")
        assert operator.log_level == "DEBUG"

    @patch("dlh_airflow_common.operators.base.get_logger")
    def test_execute_calls_hooks(self, mock_get_logger: MagicMock) -> None:
        """Test that pre_execute and post_execute hooks are called."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        operator = ConcreteOperator(task_id="test_task")
        context: Dict[str, Any] = {"task_instance": MagicMock()}

        operator.pre_execute(context)
        result = operator.execute(context)
        operator.post_execute(context, result)

        assert result == "success"
        assert mock_logger.info.call_count == 2

    def test_base_execute_not_implemented(self) -> None:
        """Test that base execute raises NotImplementedError."""
        operator = BaseOperator(task_id="test_task")
        context: Dict[str, Any] = {}

        with pytest.raises(NotImplementedError):
            operator.execute(context)

    def test_pre_execute_logs(self) -> None:
        """Test pre_execute logging."""
        operator = ConcreteOperator(task_id="test_task")
        operator.logger = MagicMock()
        context: Dict[str, Any] = {}

        operator.pre_execute(context)
        operator.logger.info.assert_called_once()

    def test_post_execute_logs(self) -> None:
        """Test post_execute logging."""
        operator = ConcreteOperator(task_id="test_task")
        operator.logger = MagicMock()
        context: Dict[str, Any] = {}

        operator.post_execute(context, "result")
        operator.logger.info.assert_called_once()
