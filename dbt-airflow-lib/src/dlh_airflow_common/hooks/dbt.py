"""
DBT Hook for executing dbt commands via Python API.

This module provides a Hook for interacting with dbt-core programmatically using the
dbtRunner API, with support for Airflow Connection-based profile management.
"""

import json
import os
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from airflow.exceptions import AirflowException
from airflow.sdk.bases.hook import BaseHook
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from dlh_airflow_common.exceptions import (
    DbtCompilationException,
    DbtConnectionException,
    DbtException,
    DbtProfileException,
    DbtRuntimeException,
    classify_dbt_error,
)
from dlh_airflow_common.hooks.dbt_profiles import get_profile_adapter
from dlh_airflow_common.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DbtTaskResult:
    """
    Structured result from a dbt task execution.

    Attributes:
        success: Whether the dbt task completed successfully
        command: The dbt command that was executed (run, test, etc.)
        run_results: Detailed run results from dbt (node-level execution details)
        manifest: The dbt project manifest (DAG structure, models, etc.)
        exception: Exception object if the task failed with an unhandled error
    """

    success: bool
    command: str
    run_results: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    exception: Exception | None = None


class DbtHook(BaseHook):
    """
    Hook for interacting with dbt-core via its programmatic Python API.

    This hook supports two modes of profile configuration:
    1. Airflow Connection (recommended): Specify conn_id to use Airflow's connection
       system for centralized credential management
    2. Manual profiles.yml: Specify profiles_dir to use a traditional dbt profiles file

    The hook manages virtual environment isolation, executes dbt commands via dbtRunner,
    and provides access to dbt artifacts (manifest, run_results) for downstream tasks.

    Example with Airflow Connection:
        hook = DbtHook(
            venv_path="/opt/airflow/venvs/dbt-venv",
            dbt_project_dir="/opt/airflow/dbt",
            conn_id="dbt_postgres_prod",
            target="prod",
        )
        result = hook.run_dbt_task("run", select=["tag:daily"])

    Example with manual profiles.yml:
        hook = DbtHook(
            venv_path="/opt/airflow/venvs/dbt-venv",
            dbt_project_dir="/opt/airflow/dbt",
            profiles_dir="/opt/airflow/dbt/profiles",
            target="dev",
        )
        result = hook.run_dbt_task("test", select=["my_model"])
    """

    def __init__(
        self,
        venv_path: str,
        dbt_project_dir: str,
        conn_id: str | None = None,
        target: str | None = None,
        profiles_dir: str | None = None,
        env_vars: dict[str, str] | None = None,
        retry_limit: int = 0,
        retry_delay: int = 1,
        target_path: str | None = None,
    ):
        """
        Initialize the DbtHook.

        Args:
            venv_path: Path to Python virtual environment with dbt-core installed
            dbt_project_dir: Path to the dbt project directory
            conn_id: Airflow connection ID for dbt profile (takes precedence over profiles_dir)
            target: dbt target environment (e.g., 'dev', 'prod')
            profiles_dir: Path to directory containing profiles.yml (fallback if no conn_id)
            env_vars: Additional environment variables to set during dbt execution
            retry_limit: Maximum retry attempts for retryable errors (default: 0 - disabled).
                Use Airflow's native task retries instead. Only enable for advanced use cases
                like long-running jobs that need fast recovery from transient network issues.
            retry_delay: Initial delay between retries in seconds (default: 1)
            target_path: Custom target path for dbt artifacts. If provided, this will be used
                instead of the default 'target/' directory. Used for artifact isolation between
                concurrent tasks.

        Raises:
            ValueError: If neither conn_id nor profiles_dir is provided
        """
        super().__init__()
        self.venv_path = venv_path
        self.dbt_project_dir = dbt_project_dir
        self.conn_id = conn_id
        self.target = target
        self.profiles_dir = profiles_dir
        self.env_vars = env_vars or {}
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay
        self.target_path = target_path

        # Internal state
        self._dbt_runner: Any = None
        self._dbt_runner_result: Any = None
        self._profiles_yml_path: str | None = None
        self._temp_profiles_dir: tempfile.TemporaryDirectory | None = None

        # Validate configuration
        if not self.conn_id and not self.profiles_dir:
            raise ValueError(
                "Either conn_id or profiles_dir must be provided for dbt profile configuration"
            )

    def _setup_dbt_environment(self) -> None:
        """
        Set up Python environment to import dbt-core from the virtual environment.

        Modifies sys.path to prioritize the venv's site-packages, allowing dbt-core
        to be imported from the venv rather than system Python.

        Raises:
            FileNotFoundError: If the venv path or site-packages directory doesn't exist
            ImportError: If dbt-core cannot be imported from the venv
        """
        if not Path(self.venv_path).exists():
            raise FileNotFoundError(f"Virtual environment not found at: {self.venv_path}")

        # Determine Python version for site-packages path
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        venv_site_packages = (
            Path(self.venv_path) / "lib" / f"python{python_version}" / "site-packages"
        )

        if not venv_site_packages.exists():
            raise FileNotFoundError(f"Site-packages not found in venv: {venv_site_packages}")

        # Insert venv site-packages at the beginning of sys.path for highest priority
        venv_site_packages_str = str(venv_site_packages)
        if venv_site_packages_str not in sys.path:
            logger.info(f"Adding venv site-packages to sys.path: {venv_site_packages_str}")
            sys.path.insert(0, venv_site_packages_str)

        # Verify dbt can be imported
        try:
            from dbt.cli.main import dbtRunner  # noqa: F401

            logger.info("Successfully imported dbtRunner from venv")
        except ImportError as e:
            raise ImportError(
                f"Failed to import dbt from venv at {self.venv_path}. "
                f"Ensure dbt-core is installed in the venv. Error: {e}"
            ) from e

    def _load_profile_from_connection(self) -> dict[str, Any]:
        """
        Load dbt profile configuration from an Airflow Connection.

        Uses the profile adapter pattern to convert Airflow Connection objects
        into dbt target configurations based on the connection type.

        Returns:
            Dictionary representing a dbt target configuration

        Raises:
            AirflowException: If the connection cannot be retrieved or converted

        Example return value:
            {
                "type": "postgres",
                "host": "localhost",
                "user": "dbt_user",
                "password": "****",
                "database": "analytics",
                "port": 5432,
                "schema": "public",
                "threads": 4,
            }
        """
        if not self.conn_id:
            raise AirflowException("conn_id must be set to load profile from connection")

        try:
            conn = BaseHook.get_connection(self.conn_id)
            logger.info(f"Retrieved Airflow connection: {self.conn_id} (type: {conn.conn_type})")
        except Exception as e:
            raise AirflowException(
                f"Failed to retrieve Airflow connection '{self.conn_id}': {e}"
            ) from e

        try:
            adapter = get_profile_adapter(conn.conn_type)
            target_config = adapter.to_dbt_target(conn)
            logger.info(f"Converted connection to dbt target (type: {target_config['type']})")
            return target_config
        except Exception as e:
            raise AirflowException(
                f"Failed to convert connection '{self.conn_id}' to dbt profile: {e}"
            ) from e

    def _get_or_create_profiles_yml(self) -> str:
        """
        Get the path to profiles.yml file.

        If conn_id is provided: Generates a temporary profiles.yml from the Airflow Connection
        If profiles_dir is provided: Uses the existing profiles.yml in that directory

        Returns:
            Path to the profiles.yml file

        Raises:
            FileNotFoundError: If profiles_dir is specified but profiles.yml doesn't exist
            AirflowException: If profile generation fails
        """
        # Case 1: Use Airflow Connection to generate profiles.yml
        if self.conn_id:
            logger.info(f"Generating temporary profiles.yml from connection: {self.conn_id}")

            # Get target configuration from connection
            target_config = self._load_profile_from_connection()

            # Get project name from dbt_project.yml
            project_file = Path(self.dbt_project_dir) / "dbt_project.yml"
            if not project_file.exists():
                raise FileNotFoundError(f"dbt_project.yml not found at: {project_file}")

            with open(project_file) as f:
                dbt_project = yaml.safe_load(f)
                project_name = dbt_project.get("name", "dbt_project")

            # Determine target name
            target_name = self.target or "default"

            # Create profiles.yml structure
            profiles_yml = {
                project_name: {
                    "target": target_name,
                    "outputs": {
                        target_name: target_config,
                    },
                }
            }

            # Create temporary directory for profiles.yml
            self._temp_profiles_dir = tempfile.TemporaryDirectory(prefix="dbt_profiles_")
            profiles_path = Path(self._temp_profiles_dir.name) / "profiles.yml"

            # Write profiles.yml
            with open(profiles_path, "w") as f:
                yaml.dump(profiles_yml, f, default_flow_style=False)

            logger.info(f"Created temporary profiles.yml at: {profiles_path}")
            self._profiles_yml_path = str(profiles_path.parent)
            return str(profiles_path.parent)

        # Case 2: Use existing profiles.yml from profiles_dir
        if self.profiles_dir:
            profiles_path = Path(self.profiles_dir) / "profiles.yml"
            if not profiles_path.exists():
                raise FileNotFoundError(f"profiles.yml not found at: {profiles_path}")

            logger.info(f"Using existing profiles.yml from: {profiles_path}")
            self._profiles_yml_path = self.profiles_dir
            return self.profiles_dir

        raise AirflowException(
            "Neither conn_id nor profiles_dir provided for profile configuration"
        )

    def _is_retryable_error(self, exception: Exception) -> bool:
        """
        Classify if an error is retryable (transient) vs terminal.

        Uses the classify_dbt_error function to determine if an exception
        represents a transient failure that should trigger retry logic.

        Args:
            exception: The exception to classify

        Returns:
            True if the error should be retried, False otherwise

        Examples:
            Connection errors -> True (retryable)
            Compilation errors -> False (requires code fix)
            Timeout errors -> True (retryable)
            Profile errors -> False (requires config fix)
        """
        # Use the exception classifier
        _, is_retryable = classify_dbt_error(exception)

        # Additional check for DbtException subclasses
        if isinstance(exception, DbtConnectionException):
            return True
        elif isinstance(exception, DbtRuntimeException):
            return exception.is_retryable
        elif isinstance(exception, (DbtCompilationException, DbtProfileException)):
            return False

        return is_retryable

    def _log_retry_attempt(self, retry_state: RetryCallState) -> None:
        """
        Log retry attempt information.

        Args:
            retry_state: Tenacity retry state with attempt number and exception
        """
        attempt_number = retry_state.attempt_number
        exception = retry_state.outcome.exception() if retry_state.outcome else None

        if exception:
            logger.warning(
                f"dbt execution failed (attempt {attempt_number}/{self.retry_limit}): {exception}"
            )
            if retry_state.next_action:
                logger.info(f"Retrying in {retry_state.next_action.sleep} seconds...")

    def _log_node_results(self, run_results: dict[str, Any]) -> None:
        """
        Log structured information for each dbt node execution.

        Provides operator-level visibility into model execution without
        parsing raw dbt logs.

        Args:
            run_results: The dbt run_results.json content
        """
        results = run_results.get("results", [])

        if not results:
            logger.info("No node results to log")
            return

        # Summary statistics
        status_counts = Counter(r.get("status") for r in results)
        total_time = sum(r.get("execution_time", 0) for r in results)

        logger.info("=" * 60)
        logger.info("dbt Execution Summary")
        logger.info("=" * 60)
        logger.info(f"Total nodes: {len(results)}")
        logger.info(f"Total time: {total_time:.2f}s")

        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")

        # Log failed nodes with details
        failed = [r for r in results if r.get("status") in ["error", "fail"]]
        if failed:
            logger.error(f"\n{len(failed)} node(s) failed:")
            for result in failed:
                node = result.get("unique_id", "unknown")
                message = result.get("message", "No error message")
                execution_time = result.get("execution_time", 0)
                logger.error(f"  ❌ {node} ({execution_time:.2f}s)")
                logger.error(f"     {message}")

        # Log warned nodes
        warned = [r for r in results if r.get("status") == "warn"]
        if warned:
            logger.warning(f"\n{len(warned)} node(s) with warnings:")
            for result in warned:
                node = result.get("unique_id", "unknown")
                message = result.get("message", "No warning message")
                logger.warning(f"  ⚠️  {node}")
                logger.warning(f"     {message}")

        # Log slowest nodes (top 5)
        if len(results) > 1:
            slowest = sorted(results, key=lambda r: r.get("execution_time", 0), reverse=True)[:5]
            logger.info("\nSlowest nodes:")
            for result in slowest:
                node = result.get("unique_id", "unknown").split(".")[-1]  # Just the name
                time_sec = result.get("execution_time", 0)
                status = result.get("status", "unknown")
                logger.info(f"  🐌 {node}: {time_sec:.2f}s ({status})")

        logger.info("=" * 60)

    def run_dbt_task(
        self,
        command: Literal["run", "test", "snapshot", "seed", "compile", "deps"],
        select: list[str] | None = None,
        exclude: list[str] | None = None,
        selector: str | None = None,
        vars: dict[str, Any] | None = None,
        full_refresh: bool = False,
        fail_fast: bool = False,
        **kwargs: Any,
    ) -> DbtTaskResult:
        """
        Execute a dbt task using the dbtRunner Python API with retry logic.

        Args:
            command: dbt command to execute (run, test, snapshot, seed, compile, deps)
            select: List of models or selectors to include (e.g., ["my_model", "tag:daily"])
            exclude: List of models or selectors to exclude (e.g., ["tag:deprecated"])
            selector: Named selector from selectors.yml
            vars: Variables to pass to dbt (--vars)
            full_refresh: Force full refresh of incremental models (--full-refresh)
            fail_fast: Stop execution on first failure (--fail-fast)
            **kwargs: Additional keyword arguments passed to dbtRunner

        Returns:
            DbtTaskResult with success status, run_results, and manifest

        Raises:
            DbtException: If dbt execution fails (specific subclass based on error type)

        Example:
            result = hook.run_dbt_task(
                "run",
                select=["tag:daily", "my_model"],
                exclude=["tag:deprecated"],
                vars={"start_date": "2024-01-01"},
                full_refresh=True,
            )
        """
        logger.info(f"Executing dbt {command} command")

        # Wrap the execution in retry logic
        retry_decorator = retry(
            stop=stop_after_attempt(self.retry_limit),
            wait=wait_exponential(multiplier=self.retry_delay, min=1, max=60),
            retry=retry_if_exception(self._is_retryable_error),  # type: ignore[arg-type]
            before_sleep=self._log_retry_attempt,
            reraise=True,
        )

        # Apply retry logic to the execution function
        retrying_execution = retry_decorator(self._run_dbt_task_impl)

        return retrying_execution(
            command=command,
            select=select,
            exclude=exclude,
            selector=selector,
            vars=vars,
            full_refresh=full_refresh,
            fail_fast=fail_fast,
            **kwargs,
        )

    def _run_dbt_task_impl(
        self,
        command: str,
        select: list[str] | None,
        exclude: list[str] | None,
        selector: str | None,
        vars: dict[str, Any] | None,
        full_refresh: bool,
        fail_fast: bool,
        **kwargs: Any,
    ) -> DbtTaskResult:
        """
        Internal implementation of dbt task execution.

        This method contains the actual execution logic and is wrapped
        by retry logic in run_dbt_task.
        """
        logger.info(f"Starting dbt {command} execution")

        # Step 1: Setup dbt environment
        self._setup_dbt_environment()

        # Import dbtRunner after environment setup
        from dbt.cli.main import dbtRunner, dbtRunnerResult

        # Step 2: Prepare profiles.yml
        profiles_dir = self._get_or_create_profiles_yml()

        # Step 3: Build dbt command arguments
        args: list[str] = [command]

        # Add selection arguments
        if select:
            args.extend(["--select", " ".join(select)])
        if exclude:
            args.extend(["--exclude", " ".join(exclude)])
        if selector:
            args.extend(["--selector", selector])

        # Add configuration arguments
        if self.target:
            args.extend(["--target", self.target])
        if profiles_dir:
            args.extend(["--profiles-dir", profiles_dir])

        # Add behavior flags
        if full_refresh and command in ["run", "build"]:
            args.append("--full-refresh")
        if fail_fast and command == "test":
            args.append("--fail-fast")

        # Add variables
        if vars:
            vars_json = json.dumps(vars)
            args.extend(["--vars", vars_json])

        # Set project directory
        args.extend(["--project-dir", self.dbt_project_dir])

        # Set custom target path if provided
        if self.target_path:
            args.extend(["--target-path", self.target_path])

        logger.info(f"dbt command: dbt {' '.join(args)}")

        # Step 4: Prepare environment variables
        env = os.environ.copy()
        env["DBT_PROJECT_DIR"] = self.dbt_project_dir
        env.update(self.env_vars)

        # Set environment variables for subprocess
        for key, value in env.items():
            if key not in os.environ or os.environ[key] != value:
                os.environ[key] = value

        # Step 5: Execute dbt command
        try:
            runner = dbtRunner()
            result: dbtRunnerResult = runner.invoke(args)

            # Store result for artifact access
            self._dbt_runner_result = result

            # Check success
            success = result.success if hasattr(result, "success") else not result.exception

            if success:
                logger.info(f"dbt {command} completed successfully")
            else:
                logger.error(f"dbt {command} failed")
                if result.exception:
                    # Classify the exception and raise appropriate type
                    exception_class, is_retryable = classify_dbt_error(result.exception)  # type: ignore[arg-type]
                    if exception_class == DbtRuntimeException:
                        raise DbtRuntimeException(
                            f"dbt {command} failed: {result.exception}",
                            is_retryable=is_retryable,
                        )
                    else:
                        raise exception_class(f"dbt {command} failed: {result.exception}")

            # Step 6: Load artifacts and log node-level results
            run_results = self.get_run_results()
            manifest = self.get_manifest()

            # Log structured node results
            if run_results:
                self._log_node_results(run_results)

            exception_val = (
                result.exception
                if hasattr(result, "exception") and isinstance(result.exception, Exception)
                else None
            )

            return DbtTaskResult(
                success=success,
                command=command,
                run_results=run_results,
                manifest=manifest,
                exception=exception_val,
            )

        except DbtException:
            # Re-raise dbt-specific exceptions (already classified)
            raise

        except Exception as e:
            # Classify generic exceptions into dbt exception types
            logger.error(f"dbt {command} execution failed: {e}")
            exception_class, is_retryable = classify_dbt_error(e)

            if exception_class == DbtRuntimeException:
                raise DbtRuntimeException(
                    f"dbt {command} failed: {e}", is_retryable=is_retryable
                ) from e
            else:
                raise exception_class(f"dbt {command} failed: {e}") from e

        finally:
            # Cleanup temporary profiles directory if created
            if self._temp_profiles_dir:
                try:
                    self._temp_profiles_dir.cleanup()
                    self._temp_profiles_dir = None
                except Exception as e:
                    logger.warning(f"Failed to cleanup temporary profiles directory: {e}")

    def get_manifest(self) -> dict[str, Any]:
        """
        Get the parsed dbt manifest (DAG structure, models, etc.).

        The manifest contains the full dbt project structure including models, tests,
        sources, and their relationships.

        Returns:
            Dictionary containing the dbt manifest, or empty dict if not found

        Example:
            manifest = hook.get_manifest()
            models = manifest.get("nodes", {})
            for node_id, node in models.items():
                if node["resource_type"] == "model":
                    print(f"Model: {node['name']}")
        """
        target_dir = self.target_path if self.target_path else "target"
        manifest_path = Path(self.dbt_project_dir) / target_dir / "manifest.json"

        if not manifest_path.exists():
            logger.warning(f"Manifest file not found at: {manifest_path}")
            return {}

        try:
            with open(manifest_path) as f:
                manifest: dict[str, Any] = json.load(f)
            logger.info(f"Loaded manifest from: {manifest_path}")
            return manifest
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            return {}

    def get_run_results(self) -> dict[str, Any]:
        """
        Get the latest run results with node-level execution details.

        Run results contain detailed information about the execution of each node
        (model, test, etc.) including timing, status, and error messages.

        Returns:
            Dictionary containing the dbt run results, or empty dict if not found

        Example:
            run_results = hook.get_run_results()
            for result in run_results.get("results", []):
                print(f"{result['node']['name']}: {result['status']}")
                if result['status'] == 'error':
                    print(f"  Error: {result.get('message')}")
        """
        target_dir = self.target_path if self.target_path else "target"
        run_results_path = Path(self.dbt_project_dir) / target_dir / "run_results.json"

        if not run_results_path.exists():
            logger.warning(f"Run results file not found at: {run_results_path}")
            return {}

        try:
            with open(run_results_path) as f:
                run_results: dict[str, Any] = json.load(f)
            logger.info(f"Loaded run results from: {run_results_path}")
            return run_results
        except Exception as e:
            logger.error(f"Failed to load run results: {e}")
            return {}

    def __del__(self) -> None:
        """Cleanup temporary resources on object destruction."""
        if self._temp_profiles_dir:
            try:
                self._temp_profiles_dir.cleanup()
            except Exception:
                pass  # Ignore cleanup errors during destruction
