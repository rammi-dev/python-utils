"""Integration test fixtures."""

import shutil
from pathlib import Path
from unittest.mock import Mock

import pytest


def pytest_configure(config):
    """Register integration marker."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (deselect with '-m \"not integration\"')",
    )


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to integration test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def dbt_test_project(tmp_path_factory, fixtures_dir: Path) -> Path:
    """Copy static dbt project fixtures to temporary directory for testing.

    This uses real fixture files from tests/integration/fixtures/dbt_project/
    instead of creating them dynamically, making them reviewable.
    """
    # Create temporary directory for this test module
    temp_dir = tmp_path_factory.mktemp("dbt_integration")

    # Copy entire dbt_project directory from fixtures
    source_project = fixtures_dir / "dbt_project"
    dest_project = temp_dir / "dbt_project"

    shutil.copytree(source_project, dest_project)

    return dest_project


@pytest.fixture(scope="module")
def dbt_profiles_dir(tmp_path_factory, fixtures_dir: Path) -> Path:
    """Copy static profiles.yml to temporary directory for testing.

    This uses the real profiles.yml from tests/integration/fixtures/profiles/
    instead of creating it dynamically.
    """
    # Create temporary profiles directory
    temp_dir = tmp_path_factory.mktemp("dbt_profiles")

    # Copy profiles directory from fixtures
    source_profiles = fixtures_dir / "profiles"
    dest_profiles = temp_dir / "profiles"

    shutil.copytree(source_profiles, dest_profiles)

    return dest_profiles


@pytest.fixture(scope="module")
def dag_factory_fixtures_dir(fixtures_dir: Path) -> Path:
    """Path to DAG Factory YAML fixtures."""
    return fixtures_dir / "dag_factory"


@pytest.fixture
def airflow_context():
    """Create a real Airflow context for integration testing.

    Uses actual Airflow objects (DAG, Task, TaskInstance) instead of mocks.
    """
    from datetime import datetime

    import pendulum
    from airflow import DAG
    from airflow.models import DagRun, TaskInstance
    from airflow.operators.python import PythonOperator
    from airflow.utils.state import DagRunState
    from airflow.utils.types import DagRunType

    # Create a real DAG
    dag = DAG(
        dag_id="integration_test_dag",
        start_date=datetime(2024, 1, 1),
        schedule=None,
    )

    # Create a real task
    task = PythonOperator(
        task_id="integration_test_task",
        python_callable=lambda: None,
        dag=dag,
    )

    # Create a real DAG run using DagRun constructor (Airflow 3.x)
    dag_run = DagRun(
        dag_id=dag.dag_id,
        run_id="test_run_1",
        run_type=DagRunType.MANUAL,
        start_date=pendulum.now(),
        state=DagRunState.RUNNING,
    )

    # Create a real task instance (Airflow 3.x requires dag_version_id)
    ti = TaskInstance(task=task, dag_version_id=1, run_id=dag_run.run_id)
    ti.dag_id = dag.dag_id
    ti.task_id = task.task_id
    ti.try_number = 1

    # Mock xcom_push to avoid database interaction in tests
    ti.xcom_push = Mock()

    # Return the context dictionary that Airflow operators expect
    return {
        "dag": dag,
        "task": task,
        "dag_run": dag_run,
        "task_instance": ti,
        "ti": ti,
    }
