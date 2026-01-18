"""Integration test fixtures."""

import shutil
from pathlib import Path

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
