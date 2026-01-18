"""DBT operator for running dbt commands using dbt's Python API via DbtHook."""

from collections.abc import Sequence
from typing import Any, Literal

from airflow.utils.context import Context

from dlh_airflow_common.hooks.dbt import DbtHook, DbtTaskResult
from dlh_airflow_common.operators.base import BaseOperator


class DbtOperator(BaseOperator):
    """
    Operator to run dbt commands using dbt's programmatic Python API.

    This operator executes dbt commands (run, test) via the DbtHook, which uses
    dbt's dbtRunner API for direct Python integration. Supports two profile modes:
    1. Airflow Connection (recommended): Centralized credential management via conn_id
    2. Manual profiles.yml: Traditional dbt profiles file via profiles_dir

    Args:
        task_id: Unique task identifier
        venv_path: Path to the virtual environment with dbt-core installed
        dbt_project_dir: Path to the dbt project directory
        dbt_command: DBT command to execute ('run' or 'test')
        conn_id: Airflow connection ID for dbt profile (NEW - recommended)
        dbt_tags: List of tags to filter dbt models (optional)
        dbt_models: List of specific models to run (optional)
        exclude_tags: List of tags to exclude (optional)
        dbt_vars: Dictionary of variables to pass to dbt (optional)
        full_refresh: Whether to perform a full refresh (default: False)
        fail_fast: Stop on first test failure (default: False)
        target: DBT target to use (optional)
        profiles_dir: Path to dbt profiles directory (fallback if no conn_id)
        env_vars: Additional environment variables (optional)
        push_artifacts: Push manifest and run_results to XCom (default: True)
        **kwargs: Additional arguments passed to BaseOperator

    Example (with Airflow Connection):
        >>> dbt_run = DbtOperator(
        ...     task_id='dbt_run_daily',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='run',
        ...     conn_id='dbt_postgres_prod',  # NEW: Use Airflow Connection
        ...     dbt_tags=['daily', 'core'],
        ...     target='prod',
        ...     push_artifacts=True,  # NEW: Push to XCom
        ... )

    Example (with manual profiles.yml - backward compatible):
        >>> dbt_test = DbtOperator(
        ...     task_id='dbt_test',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='test',
        ...     profiles_dir='/opt/airflow/dbt/profiles',  # OLD WAY
        ...     dbt_models=['my_model'],
        ...     target='dev',
        ... )
    """

    template_fields: Sequence[str] = (
        "venv_path",
        "dbt_project_dir",
        "conn_id",  # NEW: templatable connection ID
        "dbt_tags",
        "dbt_models",
        "dbt_vars",
        "target",
    )

    def __init__(
        self,
        *,
        task_id: str,
        venv_path: str,
        dbt_project_dir: str,
        dbt_command: Literal["run", "test"] = "run",
        conn_id: str | None = None,  # NEW
        dbt_tags: list[str] | None = None,
        dbt_models: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        dbt_vars: dict[str, Any] | None = None,
        full_refresh: bool = False,
        fail_fast: bool = False,
        target: str | None = None,
        profiles_dir: str | None = None,
        env_vars: dict[str, str] | None = None,
        push_artifacts: bool = True,  # NEW
        **kwargs: Any,
    ) -> None:
        """Initialize the DBT operator."""
        super().__init__(task_id=task_id, **kwargs)

        self.venv_path = venv_path
        self.dbt_project_dir = dbt_project_dir
        self.dbt_command = dbt_command
        self.conn_id = conn_id  # NEW
        self.dbt_tags = dbt_tags or []
        self.dbt_models = dbt_models or []
        self.exclude_tags = exclude_tags or []
        self.dbt_vars = dbt_vars or {}
        self.full_refresh = full_refresh
        self.fail_fast = fail_fast
        self.target = target
        self.profiles_dir = profiles_dir
        self.env_vars = env_vars or {}
        self.push_artifacts = push_artifacts  # NEW

    def execute(self, context: Context) -> dict[str, Any]:
        """
        Execute the dbt command using DbtHook.

        Args:
            context: Airflow task context

        Returns:
            Dictionary containing execution results with manifest and run_results

        Raises:
            AirflowException: If dbt command fails
        """
        self.logger.info(f"Starting DBT {self.dbt_command} command")
        self.logger.info(f"Virtual environment: {self.venv_path}")
        self.logger.info(f"DBT project directory: {self.dbt_project_dir}")

        # Log configuration mode
        if self.conn_id:
            self.logger.info(f"Using Airflow Connection: {self.conn_id}")
        elif self.profiles_dir:
            self.logger.info(f"Using profiles.yml from: {self.profiles_dir}")

        # Create DbtHook
        hook = DbtHook(
            venv_path=self.venv_path,
            dbt_project_dir=self.dbt_project_dir,
            conn_id=self.conn_id,  # NEW
            target=self.target,
            profiles_dir=self.profiles_dir,
            env_vars=self.env_vars,
        )

        # Build select list (combine models and tags)
        select: list[str] = []
        if self.dbt_models:
            select.extend(self.dbt_models)
            self.logger.info(f"Models: {', '.join(self.dbt_models)}")

        if self.dbt_tags:
            select.extend([f"tag:{tag}" for tag in self.dbt_tags])
            self.logger.info(f"Tags: {', '.join(self.dbt_tags)}")

        # Build exclude list
        exclude: list[str] | None = None
        if self.exclude_tags:
            exclude = [f"tag:{tag}" for tag in self.exclude_tags]
            self.logger.info(f"Exclude tags: {', '.join(self.exclude_tags)}")

        if self.target:
            self.logger.info(f"Target: {self.target}")

        # Execute via hook
        result: DbtTaskResult = hook.run_dbt_task(
            command=self.dbt_command,
            select=select or None,
            exclude=exclude,
            vars=self.dbt_vars,
            full_refresh=self.full_refresh,
            fail_fast=self.fail_fast,
        )

        # Push artifacts to XCom for downstream tasks (NEW)
        if self.push_artifacts:
            if result.manifest:
                self.logger.info("Pushing manifest to XCom")
                context["ti"].xcom_push(key="manifest", value=result.manifest)

            if result.run_results:
                self.logger.info("Pushing run_results to XCom")
                context["ti"].xcom_push(key="run_results", value=result.run_results)

        self.logger.info(f"DBT {self.dbt_command} completed successfully")

        # Return structured result (NEW: includes manifest and run_results)
        return {
            "success": result.success,
            "command": result.command,
            "run_results": result.run_results,
            "manifest": result.manifest,
        }

    def on_kill(self) -> None:
        """
        Handle task termination.

        Called when the task is killed. Logs termination event.
        """
        self.logger.warning(f"Task {self.task_id} is being killed")
