"""Tests for dbt execution trigger."""

import time

import pytest

from dlh_airflow_common.triggers.dbt import DbtExecutionTrigger


class TestDbtExecutionTrigger:
    """Test the DbtExecutionTrigger."""

    @pytest.fixture
    def trigger(self) -> DbtExecutionTrigger:
        """Create a trigger instance for testing."""
        return DbtExecutionTrigger(
            dbt_project_dir="/fake/project",
            pid=12345,
            check_interval=1,
            timeout=10,
            start_time=time.time(),
        )

    def test_serialize(self, trigger: DbtExecutionTrigger) -> None:
        """Trigger should serialize correctly."""
        module_path, params = trigger.serialize()

        assert module_path == "dlh_airflow_common.triggers.dbt.DbtExecutionTrigger"
        assert params["dbt_project_dir"] == "/fake/project"
        assert params["pid"] == 12345
        assert params["check_interval"] == 1
        assert params["timeout"] == 10
        assert "start_time" in params

    def test_init_with_defaults(self) -> None:
        """Trigger should initialize with default values."""
        trigger = DbtExecutionTrigger(dbt_project_dir="/fake/project")

        assert trigger.dbt_project_dir == "/fake/project"
        assert trigger.pid is None
        assert trigger.check_interval == 60
        assert trigger.timeout == 86400
        assert trigger.start_time is not None

    def test_init_with_custom_values(self) -> None:
        """Trigger should accept custom configuration."""
        custom_start = time.time() - 100
        trigger = DbtExecutionTrigger(
            dbt_project_dir="/custom/project",
            pid=99999,
            check_interval=30,
            timeout=7200,
            start_time=custom_start,
        )

        assert trigger.dbt_project_dir == "/custom/project"
        assert trigger.pid == 99999
        assert trigger.check_interval == 30
        assert trigger.timeout == 7200
        assert trigger.start_time == custom_start
