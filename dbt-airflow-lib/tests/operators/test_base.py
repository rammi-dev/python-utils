"""Tests for base operator re-export."""

from airflow.models import BaseOperator as AirflowBaseOperator

from dlh_airflow_common.operators.base import BaseOperator


class TestBaseOperator:
    """Test suite for BaseOperator re-export."""

    def test_base_operator_is_airflow_base_operator(self) -> None:
        """Test that BaseOperator is the same as Airflow's BaseOperator."""
        assert BaseOperator is AirflowBaseOperator

    def test_base_operator_has_log_property(self) -> None:
        """Test that BaseOperator instances have a log property."""
        operator = BaseOperator(task_id="test_task")
        assert hasattr(operator, "log")
