"""DBT operator for running dbt commands using dbt's Python API via DbtHook."""

import multiprocessing
import shutil
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from airflow.utils.context import Context

from dlh_airflow_common.exceptions import DbtException
from dlh_airflow_common.hooks.dbt import DbtHook, DbtTaskResult
from dlh_airflow_common.operators.base import BaseOperator
from dlh_airflow_common.triggers.dbt import DbtExecutionTrigger


class DbtOperator(BaseOperator):
    """
    Operator to run dbt commands using dbt's programmatic Python API.

    This operator executes dbt commands via the DbtHook, which uses dbt's dbtRunner
    API for direct Python integration. Supports two profile modes:
    1. Airflow Connection (recommended): Centralized credential management via conn_id
    2. Manual profiles.yml: Traditional dbt profiles file via profiles_dir

    Supported Commands:
        - run: Execute dbt models
        - test: Run dbt tests
        - snapshot: Execute snapshot models
        - seed: Load seed data
        - compile: Compile dbt project
        - deps: Install dbt dependencies

    Args:
        task_id: Unique task identifier
        venv_path: Path to the virtual environment with dbt-core installed
        dbt_project_dir: Path to the dbt project directory
        dbt_command: DBT command to execute (run, test, snapshot, seed, compile, deps)
        conn_id: Airflow connection ID for dbt profile (recommended)
        dbt_tags: List of tags to filter dbt models (optional, not used for deps)
        dbt_models: List of specific models to run (optional, not used for deps)
        exclude_tags: List of tags to exclude (optional, not used for deps)
        dbt_vars: Dictionary of variables to pass to dbt (optional)
        full_refresh: Whether to perform a full refresh (default: False)
        fail_fast: Stop on first test failure (default: False)
        target: DBT target to use (optional)
        profiles_dir: Path to dbt profiles directory (fallback if no conn_id)
        env_vars: Additional environment variables (optional)
        push_artifacts: Push manifest and run_results to XCom (default: True)
        **kwargs: Additional arguments passed to BaseOperator

    Example (run with Airflow Connection):
        >>> dbt_run = DbtOperator(
        ...     task_id='dbt_run_daily',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='run',
        ...     conn_id='dbt_dremio_prod',
        ...     dbt_tags=['daily', 'core'],
        ...     target='prod',
        ...     push_artifacts=True,
        ... )

    Example (seed data):
        >>> dbt_seed = DbtOperator(
        ...     task_id='dbt_seed',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='seed',
        ...     conn_id='dbt_dremio_prod',
        ...     target='dev',
        ... )

    Example (snapshot):
        >>> dbt_snapshot = DbtOperator(
        ...     task_id='dbt_snapshot',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='snapshot',
        ...     conn_id='dbt_dremio_prod',
        ...     target='prod',
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
        dbt_command: Literal["run", "test", "snapshot", "seed", "compile", "deps"] = "run",
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
        push_artifacts: bool = True,
        deferrable: bool = False,
        check_interval: int = 60,
        dbt_retry_limit: int = 0,
        dbt_retry_delay: int = 1,
        keep_target_artifacts: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the DBT operator.

        Args:
            task_id: Unique task identifier
            venv_path: Path to the virtual environment with dbt-core installed
            dbt_project_dir: Path to the dbt project directory
            dbt_command: DBT command to execute
            conn_id: Airflow connection ID for dbt profile
            dbt_tags: List of tags to filter dbt models
            dbt_models: List of specific models to run
            exclude_tags: List of tags to exclude
            dbt_vars: Dictionary of variables to pass to dbt
            full_refresh: Whether to perform a full refresh
            fail_fast: Stop on first test failure
            target: DBT target to use
            profiles_dir: Path to dbt profiles directory
            env_vars: Additional environment variables
            push_artifacts: Push manifest and run_results to XCom
            deferrable: Run in deferrable mode (async, frees worker slot)
            check_interval: Seconds between status checks in deferrable mode
            execution_timeout: Maximum execution time in seconds
            retry_limit: Internal retry attempts (default: 0 - use Airflow's retries instead)
            retry_delay: Initial delay between internal retries in seconds
            keep_target_artifacts: Keep target artifacts after execution (default: False - auto cleanup)
            **kwargs: Additional arguments passed to BaseOperator (including retries)
        """
        super().__init__(task_id=task_id, **kwargs)

        self.venv_path = venv_path
        self.dbt_project_dir = dbt_project_dir
        self.dbt_command = dbt_command
        self.conn_id = conn_id
        self.dbt_tags = dbt_tags or []
        self.dbt_models = dbt_models or []
        self.exclude_tags = exclude_tags or []
        self.dbt_vars = dbt_vars or {}
        self.full_refresh = full_refresh
        self.fail_fast = fail_fast
        self.target = target
        self.profiles_dir = profiles_dir
        self.env_vars = env_vars or {}
        self.push_artifacts = push_artifacts
        self.deferrable = deferrable
        self.check_interval = check_interval
        # Note: execution_timeout and retry_delay are inherited from BaseOperator as timedelta
        # Our internal retry config uses different names to avoid shadowing
        self.dbt_retry_limit = dbt_retry_limit
        self.dbt_retry_delay = dbt_retry_delay
        self.keep_target_artifacts = keep_target_artifacts

        # Internal state
        self._dbt_process: multiprocessing.Process | None = None
        self._target_path: str | None = None

    def _generate_target_path(self, context: Context) -> str:
        """
        Generate a unique target path for this execution.

        Format: target/run_{timestamp}_{dag_id}_{task_id}_{try_number}

        Args:
            context: Airflow task context

        Returns:
            Unique target path string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dag_id = context["dag"].dag_id
        task_id = context["task"].task_id
        try_number = context["task_instance"].try_number

        # Create unique suffix
        suffix = f"run_{timestamp}_{dag_id}_{task_id}_try{try_number}"

        # Return path relative to dbt_project_dir
        return f"target/{suffix}"

    def _cleanup_target_path(self) -> None:
        """
        Clean up the target path artifacts after execution.

        Only runs if keep_target_artifacts is False (default).
        """
        if self.keep_target_artifacts or not self._target_path:
            return

        target_full_path = Path(self.dbt_project_dir) / self._target_path

        if target_full_path.exists():
            try:
                shutil.rmtree(target_full_path)
                self.logger.info(f"Cleaned up target artifacts at: {target_full_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup target artifacts: {e}")

    def execute(self, context: Context) -> dict[str, Any]:
        """
        Execute the dbt command using DbtHook.

        Supports both synchronous and deferrable (async) execution modes.

        Args:
            context: Airflow task context

        Returns:
            Dictionary containing execution results with manifest and run_results

        Raises:
            DbtException: If dbt command fails
        """
        if self.deferrable:
            return self._execute_deferrable(context)
        else:
            return self._execute_sync(context)

    def _execute_sync(self, context: Context) -> dict[str, Any]:
        """
        Execute dbt command synchronously (blocks worker slot).

        Args:
            context: Airflow task context

        Returns:
            Dictionary containing execution results
        """
        self.logger.info(f"Starting DBT {self.dbt_command} command (sync mode)")
        self.logger.info(f"Virtual environment: {self.venv_path}")
        self.logger.info(f"DBT project directory: {self.dbt_project_dir}")

        # Generate unique target path
        self._target_path = self._generate_target_path(context)
        self.logger.info(f"Using isolated target path: {self._target_path}")

        # Log configuration mode
        if self.conn_id:
            self.logger.info(f"Using Airflow Connection: {self.conn_id}")
        elif self.profiles_dir:
            self.logger.info(f"Using profiles.yml from: {self.profiles_dir}")

        try:
            # Create DbtHook with retry configuration and unique target path
            hook = DbtHook(
                venv_path=self.venv_path,
                dbt_project_dir=self.dbt_project_dir,
                conn_id=self.conn_id,
                target=self.target,
                profiles_dir=self.profiles_dir,
                env_vars=self.env_vars,
                retry_limit=self.dbt_retry_limit,
                retry_delay=self.dbt_retry_delay,
                target_path=self._target_path,
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

            # Return structured result
            return {
                "success": result.success,
                "command": result.command,
                "run_results": result.run_results,
                "manifest": result.manifest,
            }
        finally:
            # Always cleanup target artifacts (success or failure)
            self._cleanup_target_path()

    def _execute_deferrable(self, context: Context) -> dict[str, Any]:  # pragma: no cover
        """
        Execute dbt command in deferrable mode (async, frees worker slot).

        This starts dbt execution in a background process and defers to a trigger
        that monitors completion asynchronously. The worker slot is freed up while
        waiting for the dbt execution to complete.

        Note:
            Excluded from coverage: Requires Airflow triggerer environment.
            Implementation based on proven Airflow deferrable patterns.

        Args:
            context: Airflow task context

        Returns:
            Does not return directly - defers to trigger and resumes via execute_complete
        """
        self.logger.info(f"Starting DBT {self.dbt_command} command (deferrable mode)")
        self.logger.info("Worker slot will be freed while dbt executes")

        # Generate unique target path
        self._target_path = self._generate_target_path(context)
        self.logger.info(f"Using isolated target path: {self._target_path}")

        # Capture target_path for background process
        target_path = self._target_path

        # Start dbt execution in background process
        def run_dbt_background() -> None:
            """Background function to run dbt."""
            hook = DbtHook(
                venv_path=self.venv_path,
                dbt_project_dir=self.dbt_project_dir,
                conn_id=self.conn_id,
                target=self.target,
                profiles_dir=self.profiles_dir,
                env_vars=self.env_vars,
                retry_limit=self.dbt_retry_limit,
                retry_delay=self.dbt_retry_delay,
                target_path=target_path,
            )

            # Build select/exclude lists
            select: list[str] = []
            if self.dbt_models:
                select.extend(self.dbt_models)
            if self.dbt_tags:
                select.extend([f"tag:{tag}" for tag in self.dbt_tags])

            exclude: list[str] | None = None
            if self.exclude_tags:
                exclude = [f"tag:{tag}" for tag in self.exclude_tags]

            # Execute dbt
            hook.run_dbt_task(
                command=self.dbt_command,
                select=select or None,
                exclude=exclude,
                vars=self.dbt_vars,
                full_refresh=self.full_refresh,
                fail_fast=self.fail_fast,
            )

        # Start background process
        self._dbt_process = multiprocessing.Process(target=run_dbt_background)
        self._dbt_process.start()

        self.logger.info(f"Started dbt process (PID: {self._dbt_process.pid})")

        # Defer to trigger
        self.defer(
            trigger=DbtExecutionTrigger(
                dbt_project_dir=self.dbt_project_dir,
                target_path=self._target_path,
                pid=self._dbt_process.pid,
                check_interval=self.check_interval,
                timeout=int(self.execution_timeout.total_seconds()) if self.execution_timeout else 86400,
                start_time=time.time(),
            ),
            method_name="execute_complete",
        )

    def execute_complete(
        self, context: Context, event: dict[str, Any]
    ) -> dict[str, Any]:  # pragma: no cover
        """
        Resume execution after trigger completion.

        Note:
            Excluded from coverage: Requires Airflow triggerer environment.
            Callback for deferrable mode execution.

        Args:
            context: Airflow task context
            event: Event payload from trigger with status and results

        Returns:
            Dictionary containing execution results

        Raises:
            DbtException: If dbt execution failed or timed out
        """
        status = event.get("status")
        message = event.get("message", "")
        elapsed = event.get("elapsed_seconds", 0)

        self.logger.info(f"dbt execution completed with status: {status} ({elapsed:.1f}s)")

        try:
            if status == "timeout":
                raise DbtException(f"dbt execution timeout: {message}")

            if status == "error":
                raise DbtException(f"dbt execution failed: {message}")

            # Load results from artifacts with custom target path
            hook = DbtHook(
                venv_path=self.venv_path,
                dbt_project_dir=self.dbt_project_dir,
                conn_id=self.conn_id,
                target=self.target,
                profiles_dir=self.profiles_dir,
                env_vars=self.env_vars,
                target_path=self._target_path,
            )

            run_results = hook.get_run_results()
            manifest = hook.get_manifest()

            # Push artifacts to XCom
            if self.push_artifacts:
                if manifest:
                    self.logger.info("Pushing manifest to XCom")
                    context["ti"].xcom_push(key="manifest", value=manifest)

                if run_results:
                    self.logger.info("Pushing run_results to XCom")
                    context["ti"].xcom_push(key="run_results", value=run_results)

            self.logger.info(f"DBT {self.dbt_command} completed successfully")

            return {
                "success": True,
                "command": self.dbt_command,
                "run_results": run_results,
                "manifest": manifest,
                "elapsed_seconds": elapsed,
            }
        finally:
            # Always cleanup target artifacts (success or failure)
            self._cleanup_target_path()

    def on_kill(self) -> None:  # pragma: no cover
        """
        Handle task termination gracefully.

        Note:
            Excluded from coverage: Requires process termination testing.
            Handles cleanup for deferrable mode cancellation.

        Attempts to:
        1. Terminate the dbt process gracefully
        2. Wait for cleanup (30s timeout)
        3. Force kill if necessary
        4. Log partial results if available
        """
        self.logger.warning(f"Cancellation requested for task {self.task_id}")

        if self._dbt_process and self._dbt_process.is_alive():
            self.logger.info(f"Terminating dbt process (PID: {self._dbt_process.pid})")

            # Send graceful termination signal
            self._dbt_process.terminate()

            # Wait for graceful shutdown
            self._dbt_process.join(timeout=30)

            if self._dbt_process.is_alive():
                self.logger.warning("dbt process did not terminate gracefully, forcing kill")
                self._dbt_process.kill()
                self._dbt_process.join()

            self.logger.info("dbt process terminated")

        # Try to load partial results
        try:
            hook = DbtHook(
                venv_path=self.venv_path,
                dbt_project_dir=self.dbt_project_dir,
                conn_id=self.conn_id,
                target=self.target,
                profiles_dir=self.profiles_dir,
                target_path=self._target_path,
            )
            run_results = hook.get_run_results()

            if run_results:
                results_list = run_results.get("results", [])
                completed = sum(1 for r in results_list if r.get("status") == "success")
                total = len(results_list)
                self.logger.info(f"Partial execution: {completed}/{total} nodes completed")
        except Exception as e:
            self.logger.debug(f"Could not retrieve partial results: {e}")
        finally:
            # Always cleanup target artifacts on kill
            self._cleanup_target_path()
