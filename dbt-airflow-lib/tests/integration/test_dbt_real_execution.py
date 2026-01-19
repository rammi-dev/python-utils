"""Integration tests for real dbt execution."""

from pathlib import Path

import pytest

from dlh_airflow_common.operators.dbt import DbtOperator


@pytest.mark.integration
@pytest.mark.slow
class TestDbtRealExecution:
    """Integration tests with actual dbt execution using DuckDB."""

    def test_real_dbt_run_success(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        airflow_context: dict,
    ):
        """Test actual dbt run with DuckDB adapter."""
        # Create operator
        operator = DbtOperator(
            task_id="integration_test_run",
            venv_path=str(integration_venv_path),
            dbt_project_dir=str(dbt_test_project),
            dbt_command="run",
            profiles_dir=str(dbt_profiles_dir),
        )

        # Use proper Airflow context
        context = airflow_context

        # Execute - this will actually run dbt
        result = operator.execute(context)

        # Verify results
        assert result["success"] is True
        assert result["command"] == "run"
        assert result["manifest"] is not None
        assert result["run_results"] is not None
        assert len(result["run_results"].get("results", [])) > 0

        # Verify artifacts were pushed
        assert context["ti"].xcom_push.call_count == 2

    def test_real_dbt_test_success(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        airflow_context: dict,
    ):
        """Test actual dbt test command."""
        # First run models to have something to test
        run_operator = DbtOperator(
            task_id="integration_test_run",
            venv_path=str(integration_venv_path),
            dbt_project_dir=str(dbt_test_project),
            dbt_command="run",
            profiles_dir=str(dbt_profiles_dir),
        )

        run_operator.execute(airflow_context)

        # Now run tests
        test_operator = DbtOperator(
            task_id="integration_test_test",
            venv_path=str(integration_venv_path),
            dbt_project_dir=str(dbt_test_project),
            dbt_command="test",
            profiles_dir=str(dbt_profiles_dir),
        )

        result = test_operator.execute(airflow_context)
        assert result["success"] is True
        assert result["command"] == "test"

    def test_real_dbt_seed_success(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        airflow_context: dict,
    ):
        """Test actual dbt seed command."""
        operator = DbtOperator(
            task_id="integration_test_seed",
            venv_path=str(integration_venv_path),
            dbt_project_dir=str(dbt_test_project),
            dbt_command="seed",
            profiles_dir=str(dbt_profiles_dir),
        )

        result = operator.execute(airflow_context)
        assert result["success"] is True
        assert result["command"] == "seed"
        assert result["run_results"] is not None
