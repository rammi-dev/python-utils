"""
Triggers for deferrable dbt operators.

This module provides async triggers for monitoring dbt execution completion
without blocking worker slots.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from airflow.triggers.base import BaseTrigger, TriggerEvent

from dlh_airflow_common.utils.logging import get_logger

logger = get_logger(__name__)


class DbtExecutionTrigger(BaseTrigger):
    """
    Async trigger for monitoring dbt execution completion.

    This trigger polls for dbt execution completion by monitoring the run_results.json
    file. It checks periodically if the execution has finished and returns control
    to the operator when complete.

    The trigger runs asynchronously in the triggerer process, freeing up the worker
    slot while waiting for the long-running dbt execution to complete.

    Args:
        dbt_project_dir: Path to the dbt project directory
        target_path: Custom target path for dbt artifacts (optional)
        pid: Process ID of the dbt execution (for monitoring)
        check_interval: Seconds between status checks (default: 60)
        timeout: Maximum seconds to wait before timeout (default: 86400 = 24 hours)
        start_time: Unix timestamp when execution started

    Example:
        trigger = DbtExecutionTrigger(
            dbt_project_dir="/opt/airflow/dbt/my_project",
            target_path="target/run_20260119_123456_dag_task",
            pid=12345,
            check_interval=30,
            timeout=3600,
            start_time=time.time(),
        )
    """

    def __init__(
        self,
        dbt_project_dir: str,
        target_path: str | None = None,
        pid: int | None = None,
        check_interval: int = 60,
        timeout: int = 86400,
        start_time: float | None = None,
    ):
        """Initialize the trigger."""
        super().__init__()
        self.dbt_project_dir = dbt_project_dir
        self.target_path = target_path
        self.pid = pid
        self.check_interval = check_interval
        self.timeout = timeout
        self.start_time = start_time or time.time()

    def serialize(self) -> tuple[str, dict[str, Any]]:
        """
        Serialize trigger for storage.

        Returns:
            Tuple of (module path, init parameters)
        """
        return (
            "dlh_airflow_common.triggers.dbt.DbtExecutionTrigger",
            {
                "dbt_project_dir": self.dbt_project_dir,
                "target_path": self.target_path,
                "pid": self.pid,
                "check_interval": self.check_interval,
                "timeout": self.timeout,
                "start_time": self.start_time,
            },
        )

    async def run(self) -> AsyncIterator[TriggerEvent]:  # pragma: no cover
        """
        Poll for dbt execution completion.

        Note:
            Excluded from coverage: Async method requires triggerer environment.
            Monitors dbt execution by polling run_results.json file.

        Yields:
            TriggerEvent with status and results when execution completes

        Event payload:
            {
                "status": "success" | "error" | "timeout",
                "message": str,
                "results": dict (run_results.json content),
                "elapsed_seconds": float,
            }
        """
        target_dir = self.target_path if self.target_path else "target"
        run_results_path = Path(self.dbt_project_dir) / target_dir / "run_results.json"
        last_modified: float | None = None

        logger.info(
            f"Starting dbt execution monitoring (target_path={target_dir}, "
            f"timeout={self.timeout}s, interval={self.check_interval}s)"
        )

        while True:
            current_time = time.time()
            elapsed = current_time - self.start_time

            # Check timeout
            if elapsed > self.timeout:
                logger.error(f"dbt execution exceeded {self.timeout}s timeout")
                yield TriggerEvent(
                    {
                        "status": "timeout",
                        "message": f"dbt execution exceeded {self.timeout}s timeout",
                        "elapsed_seconds": elapsed,
                    }
                )
                return

            # Check if process is still running (if PID provided)
            if self.pid:
                try:
                    import os

                    # Check if process exists (doesn't actually send signal)
                    os.kill(self.pid, 0)
                except OSError:
                    # Process no longer exists - check for results
                    logger.info(f"Process {self.pid} has terminated, checking for results")

            # Check if run_results.json exists and has been updated
            if run_results_path.exists():
                try:
                    current_modified = run_results_path.stat().st_mtime

                    # Only process if file has been modified since last check
                    if last_modified is None or current_modified > last_modified:
                        last_modified = current_modified

                        # Read and parse results
                        with open(run_results_path) as f:
                            results = json.load(f)

                        # Check if execution is complete
                        # dbt marks completed runs in metadata
                        metadata = results.get("metadata", {})
                        generated_at = metadata.get("generated_at")

                        if generated_at:
                            # Check all node statuses
                            node_results = results.get("results", [])

                            if node_results:
                                statuses = [r.get("status") for r in node_results]

                                # Check if any nodes are still running
                                if "running" not in statuses:
                                    # Execution complete - determine success
                                    failed = any(
                                        s in ["error", "fail", "skipped"] for s in statuses
                                    )

                                    if failed:
                                        logger.error("dbt execution completed with failures")
                                        yield TriggerEvent(
                                            {
                                                "status": "error",
                                                "message": "dbt execution completed with failures",
                                                "results": results,
                                                "elapsed_seconds": elapsed,
                                            }
                                        )
                                    else:
                                        logger.info("dbt execution completed successfully")
                                        yield TriggerEvent(
                                            {
                                                "status": "success",
                                                "message": "dbt execution completed successfully",
                                                "results": results,
                                                "elapsed_seconds": elapsed,
                                            }
                                        )
                                    return

                except json.JSONDecodeError as e:
                    # File might still be being written
                    logger.debug(f"Could not parse run_results.json (still writing?): {e}")
                except Exception as e:
                    logger.warning(f"Error reading run results: {e}")

            # Log progress
            if elapsed > 0 and int(elapsed) % 300 == 0:  # Every 5 minutes
                logger.info(f"dbt execution still running ({elapsed:.0f}s elapsed)")

            # Wait before next check
            await asyncio.sleep(self.check_interval)
