"""DBT operator for running dbt commands in a virtual environment."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from airflow.exceptions import AirflowException
from airflow.utils.context import Context

from dlh_airflow_common.operators.base import BaseOperator


class DbtOperator(BaseOperator):
    """Operator to run dbt commands in a pre-existing virtual environment.

    This operator allows execution of dbt run and test commands with tag-based
    filtering in an isolated virtual environment on the Airflow worker.

    Args:
        task_id: Unique task identifier
        venv_path: Path to the virtual environment (e.g., '/path/to/venv')
        dbt_project_dir: Path to the dbt project directory
        dbt_command: DBT command to execute ('run' or 'test')
        dbt_tags: List of tags to filter dbt models (optional)
        dbt_models: List of specific models to run (optional)
        exclude_tags: List of tags to exclude (optional)
        dbt_vars: Dictionary of variables to pass to dbt (optional)
        full_refresh: Whether to perform a full refresh (default: False)
        fail_fast: Stop on first test failure (default: False)
        target: DBT target to use (optional)
        profiles_dir: Path to dbt profiles directory (optional)
        additional_args: Additional dbt command arguments (optional)
        env_vars: Additional environment variables (optional)
        **kwargs: Additional arguments passed to BaseOperator

    Example:
        >>> dbt_run = DbtOperator(
        ...     task_id='dbt_run_daily',
        ...     venv_path='/opt/airflow/venvs/dbt-venv',
        ...     dbt_project_dir='/opt/airflow/dbt/my_project',
        ...     dbt_command='run',
        ...     dbt_tags=['daily', 'core'],
        ...     target='prod'
        ... )
    """

    template_fields: Sequence[str] = (
        "venv_path",
        "dbt_project_dir",
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
        dbt_command: str = "run",
        dbt_tags: Optional[List[str]] = None,
        dbt_models: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        dbt_vars: Optional[Dict[str, Any]] = None,
        full_refresh: bool = False,
        fail_fast: bool = False,
        target: Optional[str] = None,
        profiles_dir: Optional[str] = None,
        additional_args: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the DBT operator."""
        super().__init__(task_id=task_id, **kwargs)

        self.venv_path = venv_path
        self.dbt_project_dir = dbt_project_dir
        self.dbt_command = dbt_command
        self.dbt_tags = dbt_tags or []
        self.dbt_models = dbt_models or []
        self.exclude_tags = exclude_tags or []
        self.dbt_vars = dbt_vars or {}
        self.full_refresh = full_refresh
        self.fail_fast = fail_fast
        self.target = target
        self.profiles_dir = profiles_dir
        self.additional_args = additional_args or []
        self.env_vars = env_vars or {}

    def _validate_inputs(self) -> None:
        """Validate operator inputs.

        Raises:
            AirflowException: If validation fails
        """
        # Validate virtual environment path
        venv_path = Path(self.venv_path)
        if not venv_path.exists():
            raise AirflowException(f"Virtual environment not found: {self.venv_path}")

        # Check for dbt executable in venv
        dbt_bin = venv_path / "bin" / "dbt"
        if not dbt_bin.exists():
            raise AirflowException(f"dbt executable not found in venv: {dbt_bin}")

        # Validate dbt project directory
        project_path = Path(self.dbt_project_dir)
        if not project_path.exists():
            raise AirflowException(f"DBT project directory not found: {self.dbt_project_dir}")

        dbt_project_yml = project_path / "dbt_project.yml"
        if not dbt_project_yml.exists():
            raise AirflowException(f"dbt_project.yml not found in: {self.dbt_project_dir}")

        # Validate command
        valid_commands = ["run", "test"]
        if self.dbt_command not in valid_commands:
            raise AirflowException(
                f"Invalid dbt command: {self.dbt_command}. "
                f"Must be one of: {', '.join(valid_commands)}"
            )

    def _build_dbt_command(self) -> List[str]:
        """Build the dbt command with all arguments.

        Returns:
            List of command arguments
        """
        dbt_bin = str(Path(self.venv_path) / "bin" / "dbt")
        cmd = [dbt_bin, self.dbt_command]

        # Add models if specified
        if self.dbt_models:
            cmd.extend(["--select", " ".join(self.dbt_models)])

        # Add tags if specified
        if self.dbt_tags:
            for tag in self.dbt_tags:
                cmd.extend(["--select", f"tag:{tag}"])

        # Add exclude tags if specified
        if self.exclude_tags:
            for tag in self.exclude_tags:
                cmd.extend(["--exclude", f"tag:{tag}"])

        # Add target if specified
        if self.target:
            cmd.extend(["--target", self.target])

        # Add profiles directory if specified
        if self.profiles_dir:
            cmd.extend(["--profiles-dir", self.profiles_dir])

        # Add full refresh for run command
        if self.dbt_command == "run" and self.full_refresh:
            cmd.append("--full-refresh")

        # Add fail fast for test command
        if self.dbt_command == "test" and self.fail_fast:
            cmd.append("--fail-fast")

        # Add variables if specified
        if self.dbt_vars:
            import json

            vars_str = json.dumps(self.dbt_vars)
            cmd.extend(["--vars", vars_str])

        # Add additional arguments
        cmd.extend(self.additional_args)

        return cmd

    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment variables for dbt execution.

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        # Set DBT project directory
        env["DBT_PROJECT_DIR"] = self.dbt_project_dir

        # Add custom environment variables
        env.update(self.env_vars)

        return env

    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute the dbt command.

        Args:
            context: Airflow task context

        Returns:
            Dictionary containing execution results

        Raises:
            AirflowException: If dbt command fails
        """
        self.logger.info(f"Starting DBT {self.dbt_command} command")
        self.logger.info(f"Virtual environment: {self.venv_path}")
        self.logger.info(f"DBT project directory: {self.dbt_project_dir}")

        # Validate inputs
        self._validate_inputs()

        # Build command
        cmd = self._build_dbt_command()
        self.logger.info(f"Executing command: {' '.join(cmd)}")

        # Log configuration
        if self.dbt_tags:
            self.logger.info(f"Tags: {', '.join(self.dbt_tags)}")
        if self.dbt_models:
            self.logger.info(f"Models: {', '.join(self.dbt_models)}")
        if self.exclude_tags:
            self.logger.info(f"Exclude tags: {', '.join(self.exclude_tags)}")
        if self.target:
            self.logger.info(f"Target: {self.target}")

        # Prepare environment
        env = self._prepare_environment()

        # Execute command
        try:
            result = subprocess.run(
                cmd,
                cwd=self.dbt_project_dir,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            # Log output
            if result.stdout:
                self.logger.info("DBT stdout:")
                for line in result.stdout.split("\n"):
                    if line.strip():
                        self.logger.info(line)

            if result.stderr:
                self.logger.warning("DBT stderr:")
                for line in result.stderr.split("\n"):
                    if line.strip():
                        self.logger.warning(line)

            self.logger.info(f"DBT {self.dbt_command} completed successfully")

            return {
                "command": self.dbt_command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"DBT {self.dbt_command} failed with return code {e.returncode}")

            if e.stdout:
                self.logger.error("DBT stdout:")
                for line in e.stdout.split("\n"):
                    if line.strip():
                        self.logger.error(line)

            if e.stderr:
                self.logger.error("DBT stderr:")
                for line in e.stderr.split("\n"):
                    if line.strip():
                        self.logger.error(line)

            raise AirflowException(f"DBT {self.dbt_command} failed: {e.stderr or e.stdout}") from e

    def on_kill(self) -> None:
        """Handle task termination.

        Called when the task is killed. Can be used to clean up resources.
        """
        self.logger.warning(f"Task {self.task_id} is being killed")
