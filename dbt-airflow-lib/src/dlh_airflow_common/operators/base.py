"""Base operator for common functionality."""

from typing import Any, Optional

from airflow.models import BaseOperator as AirflowBaseOperator
from airflow.utils.context import Context

from dlh_airflow_common.utils.logging import get_logger


class BaseOperator(AirflowBaseOperator):
    """Base operator with common functionality for DLH Airflow operators.

    This operator extends Airflow's BaseOperator with common utilities
    and standardized logging.

    Args:
        task_id: Unique task identifier
        log_level: Logging level (default: INFO)
        **kwargs: Additional arguments passed to BaseOperator
    """

    def __init__(
        self,
        task_id: str,
        log_level: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Initialize the base operator."""
        super().__init__(task_id=task_id, **kwargs)
        self.log_level = log_level
        self.logger = get_logger(self.__class__.__name__, log_level)

    def execute(self, context: Context) -> Any:
        """Execute the operator.

        Args:
            context: Airflow task context

        Returns:
            Result of the operation

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement execute method")

    def pre_execute(self, context: Context) -> None:
        """Hook called before execute.

        Args:
            context: Airflow task context
        """
        self.logger.info(f"Starting execution of task: {self.task_id}")

    def post_execute(self, context: Context, result: Optional[Any] = None) -> None:
        """Hook called after execute.

        Args:
            context: Airflow task context
            result: Result from execute method
        """
        self.logger.info(f"Completed execution of task: {self.task_id}")
