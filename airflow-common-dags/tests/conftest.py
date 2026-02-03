"""pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest
from airflow.models import DagBag

# Add project root to Python path so imports work (dags/, common/)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def dagbag() -> DagBag:
    """Load all DAGs from dags/ folder."""
    dag_folder = PROJECT_ROOT / "dags"
    return DagBag(dag_folder=str(dag_folder), include_examples=False)
