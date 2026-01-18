"""Shared pytest fixtures for all tests."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def integration_venv_path() -> Path:
    """Path to venv with dbt-duckdb installed for integration tests."""
    # Use current venv for integration tests
    return Path(__file__).parent.parent / ".venv"


@pytest.fixture(scope="session")
def integration_dbt_project_root() -> Path:
    """Path to integration test fixtures directory."""
    return Path(__file__).parent / "integration" / "fixtures"
