"""Integration tests for DAG Factory with DbtOperator.

These tests verify that DbtOperator works correctly with Astronomer's dag-factory
by testing actual DAG rendering using Airflow's DagBag.

References:
- https://www.astronomer.io/docs/learn/dag-factory
- https://github.com/astronomer/dag-factory
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Check if dag-factory is installed
try:
    import yaml
    from airflow.models import DagBag

    DAG_FACTORY_AVAILABLE = True
except ImportError:
    DAG_FACTORY_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not DAG_FACTORY_AVAILABLE, reason="dag-factory not installed")
class TestDagFactoryIntegration:
    """Integration tests for DbtOperator with dag-factory using DagBag."""

    def test_dag_factory_yaml_validation(
        self,
        dag_factory_fixtures_dir: Path,
    ):
        """Test that DAG Factory YAML files are valid and parseable."""
        yaml_files = [
            "dbt_simple_dag.yml",
            "dbt_full_workflow.yml",
            "dbt_with_connection.yml",
        ]

        for yaml_file in yaml_files:
            file_path = dag_factory_fixtures_dir / yaml_file

            # Verify file exists
            assert file_path.exists(), f"Fixture {yaml_file} not found"

            # Verify YAML is valid
            with open(file_path) as f:
                config = yaml.safe_load(f)

            # Verify it has required DAG structure
            assert isinstance(config, dict)
            # Each YAML should have at least one DAG definition
            assert len(config) > 0

            # Verify each DAG has required fields
            for _dag_id, dag_config in config.items():
                # start_date can be at top level or in default_args
                has_start_date = "start_date" in dag_config or (
                    "default_args" in dag_config and "start_date" in dag_config["default_args"]
                )
                assert has_start_date, f"start_date not found in {yaml_file}"
                assert "schedule" in dag_config
                assert "tasks" in dag_config
                assert isinstance(dag_config["tasks"], dict)

                # Verify tasks have operator specified
                for _task_id, task_config in dag_config["tasks"].items():
                    assert "operator" in task_config
                    # Should be using DbtOperator
                    assert "DbtOperator" in task_config["operator"]

    def test_dagbag_loads_simple_dbt_dag(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        dag_factory_fixtures_dir: Path,
    ):
        """Test that Airflow DagBag can load a simple DBT DAG from YAML."""
        with tempfile.TemporaryDirectory() as temp_dag_dir:
            # Copy YAML to temporary DAGs directory
            yaml_file = dag_factory_fixtures_dir / "dbt_simple_dag.yml"
            temp_yaml = Path(temp_dag_dir) / "dbt_simple_dag.yml"
            shutil.copy(yaml_file, temp_yaml)

            # Create a loader script that dag-factory expects
            loader_script = Path(temp_dag_dir) / "load_dags.py"
            loader_script.write_text(
                """
from dagfactory import load_yaml_dags
from pathlib import Path

# Load DAGs from YAML files in this directory
dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
"""
            )

            # Mock Airflow variables
            mock_vars = {
                "venv_path": str(integration_venv_path),
                "dbt_project_dir": str(dbt_test_project),
                "profiles_dir": str(dbt_profiles_dir),
            }

            with patch("airflow.models.Variable.get") as mock_var_get:
                mock_var_get.side_effect = lambda key, default=None: mock_vars.get(key, default)

                # Load DAGs using DagBag (how Airflow actually loads DAGs)
                dagbag = DagBag(dag_folder=temp_dag_dir, include_examples=False, safe_mode=False)

                # Verify no import errors
                assert len(dagbag.import_errors) == 0, f"Import errors: {dagbag.import_errors}"

                # Verify DAG was loaded
                assert "dbt_simple_test" in dagbag.dags

                # Get the DAG
                dag = dagbag.dags["dbt_simple_test"]

                # Verify DAG properties
                assert dag.dag_id == "dbt_simple_test"
                assert dag.catchup is False

                # Verify task exists and is correct type
                assert "dbt_run" in dag.task_dict
                task = dag.task_dict["dbt_run"]

                from dlh_airflow_common.operators.dbt import DbtOperator

                assert isinstance(task, DbtOperator)
                assert task.dbt_command == "run"
                assert task.task_id == "dbt_run"

    def test_dagbag_loads_full_workflow(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        dag_factory_fixtures_dir: Path,
    ):
        """Test that Airflow DagBag can load full DBT workflow with dependencies."""
        with tempfile.TemporaryDirectory() as temp_dag_dir:
            # Copy YAML to temporary DAGs directory
            yaml_file = dag_factory_fixtures_dir / "dbt_full_workflow.yml"
            temp_yaml = Path(temp_dag_dir) / "dbt_full_workflow.yml"
            shutil.copy(yaml_file, temp_yaml)

            # Create loader script
            loader_script = Path(temp_dag_dir) / "load_dags.py"
            loader_script.write_text(
                """
from dagfactory import load_yaml_dags
from pathlib import Path

dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
"""
            )

            # Mock Airflow variables
            mock_vars = {
                "venv_path": str(integration_venv_path),
                "dbt_project_dir": str(dbt_test_project),
                "profiles_dir": str(dbt_profiles_dir),
            }

            with patch("airflow.models.Variable.get") as mock_var_get:
                mock_var_get.side_effect = lambda key, default=None: mock_vars.get(key, default)

                # Load DAGs using DagBag
                dagbag = DagBag(dag_folder=temp_dag_dir, include_examples=False, safe_mode=False)

                # Verify no import errors
                assert len(dagbag.import_errors) == 0, f"Import errors: {dagbag.import_errors}"

                # Verify DAG was loaded
                assert "dbt_full_workflow_test" in dagbag.dags
                dag = dagbag.dags["dbt_full_workflow_test"]

                # Verify all tasks exist
                assert "dbt_seed" in dag.task_dict
                assert "dbt_run" in dag.task_dict
                assert "dbt_test" in dag.task_dict

                # Verify task types
                from dlh_airflow_common.operators.dbt import DbtOperator

                dbt_seed = dag.task_dict["dbt_seed"]
                dbt_run = dag.task_dict["dbt_run"]
                dbt_test = dag.task_dict["dbt_test"]

                assert isinstance(dbt_seed, DbtOperator)
                assert isinstance(dbt_run, DbtOperator)
                assert isinstance(dbt_test, DbtOperator)

                # Verify task dependencies (seed -> run -> test)
                assert dbt_run in dbt_seed.downstream_list
                assert dbt_test in dbt_run.downstream_list

                # Verify task properties
                assert dbt_seed.dbt_command == "seed"
                assert dbt_seed.push_artifacts is False

                assert dbt_run.dbt_command == "run"
                assert dbt_run.push_artifacts is True

                assert dbt_test.dbt_command == "test"
                assert dbt_test.push_artifacts is False

    def test_dagbag_dag_serialization(
        self,
        integration_venv_path: Path,
        dbt_test_project: Path,
        dbt_profiles_dir: Path,
        dag_factory_fixtures_dir: Path,
    ):
        """Test that DAGs loaded via dag-factory can be serialized (Airflow requirement)."""
        with tempfile.TemporaryDirectory() as temp_dag_dir:
            yaml_file = dag_factory_fixtures_dir / "dbt_simple_dag.yml"
            temp_yaml = Path(temp_dag_dir) / "dbt_simple_dag.yml"
            shutil.copy(yaml_file, temp_yaml)

            loader_script = Path(temp_dag_dir) / "load_dags.py"
            loader_script.write_text(
                """
from dagfactory import load_yaml_dags
from pathlib import Path

dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
"""
            )

            mock_vars = {
                "venv_path": str(integration_venv_path),
                "dbt_project_dir": str(dbt_test_project),
                "profiles_dir": str(dbt_profiles_dir),
            }

            with patch("airflow.models.Variable.get") as mock_var_get:
                mock_var_get.side_effect = lambda key, default=None: mock_vars.get(key, default)

                dagbag = DagBag(dag_folder=temp_dag_dir, include_examples=False, safe_mode=False)
                assert len(dagbag.import_errors) == 0

                dag = dagbag.dags["dbt_simple_test"]
                task = dag.task_dict["dbt_run"]

                # Test pickle serialization (Airflow requirement)
                import pickle

                pickled_task = pickle.dumps(task)
                unpickled_task = pickle.loads(pickled_task)

                assert unpickled_task.task_id == task.task_id
                assert unpickled_task.dbt_command == "run"

                # Test pickle serialization of entire DAG
                pickled_dag = pickle.dumps(dag)
                unpickled_dag = pickle.loads(pickled_dag)

                assert unpickled_dag.dag_id == dag.dag_id


# NOTE: Real execution tests with dag-factory are covered in test_dbt_real_execution.py
# The dag-factory YAML configs use Jinja templates ({{ var.value.get(...) }}) which
# require Airflow's template rendering during task execution. This makes direct
# task.execute() testing complex. The tests above verify that:
# 1. DAGs can be loaded from YAML by DagBag
# 2. Tasks are correctly configured with proper types and dependencies
# 3. DAGs can be serialized (Airflow requirement)
#
# Real dbt execution is thoroughly tested in test_dbt_real_execution.py
