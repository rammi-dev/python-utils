"""Dummy DAG for testing and demonstration."""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for common module access
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from airflow.sdk import dag, task

from common.utils import generate_dag_id, get_default_args

# Use common utilities
dag_id = generate_dag_id("example", "dummy", "devcontainer")
default_args = get_default_args(owner="test-team")


@dag(
    dag_id=dag_id,
    default_args=default_args,
    description="A dummy DAG for testing",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["example", "test"],
)
def dummy_dag() -> None:
    @task
    def start() -> None:
        pass

    @task
    def end() -> None:
        pass

    start() >> end()


dummy_dag()
