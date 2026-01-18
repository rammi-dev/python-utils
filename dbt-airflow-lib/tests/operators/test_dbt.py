"""Tests for DBT operator."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from airflow import DAG

from dlh_airflow_common.hooks.dbt import DbtTaskResult
from dlh_airflow_common.operators.dbt import DbtOperator


@pytest.fixture
def mock_venv_path(tmp_path: Path) -> Path:
    """Create a mock virtual environment path."""
    venv_path = tmp_path / "venv"
    venv_path.mkdir()
    site_packages = venv_path / "lib" / "python3.11" / "site-packages"
    site_packages.mkdir(parents=True)
    return venv_path


@pytest.fixture
def mock_dbt_project(tmp_path: Path) -> Path:
    """Create a mock dbt project directory."""
    project_path = tmp_path / "dbt_project"
    project_path.mkdir()

    # Create dbt_project.yml
    dbt_project_yml = project_path / "dbt_project.yml"
    dbt_project_yml.write_text("name: test_project\nversion: 1.0.0\n")

    # Create target directory
    target_dir = project_path / "target"
    target_dir.mkdir()

    return project_path


@pytest.fixture
def mock_profiles_dir(tmp_path: Path) -> Path:
    """Create a mock profiles directory."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # Create profiles.yml
    profiles_yml = profiles_dir / "profiles.yml"
    profiles_yml.write_text(
        """
test_project:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: test
      password: test
      database: test
      schema: public
"""
    )

    return profiles_dir


class TestDbtOperatorInitialization:
    """Test suite for DbtOperator initialization."""

    def test_initialization_with_minimal_params(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test operator initialization with minimal parameters."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir="/tmp/profiles",  # Required: either conn_id or profiles_dir
        )

        assert operator.task_id == "test_dbt"
        assert operator.venv_path == str(mock_venv_path)
        assert operator.dbt_project_dir == str(mock_dbt_project)
        assert operator.dbt_command == "run"
        assert operator.dbt_tags == []
        assert operator.dbt_models == []
        assert operator.exclude_tags == []
        assert operator.dbt_vars == {}
        assert operator.full_refresh is False
        assert operator.fail_fast is False
        assert operator.target is None
        assert operator.conn_id is None
        assert operator.push_artifacts is True

    def test_initialization_with_conn_id(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test operator initialization with Airflow connection."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres_conn",
        )

        assert operator.conn_id == "dbt_postgres_conn"
        assert operator.profiles_dir is None

    def test_initialization_with_all_params(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test operator initialization with all parameters."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="test",
            conn_id="dbt_postgres",
            dbt_tags=["daily", "core"],
            dbt_models=["model1", "model2"],
            exclude_tags=["exclude_me"],
            dbt_vars={"key": "value"},
            full_refresh=True,
            fail_fast=True,
            target="prod",
            env_vars={"ENV_VAR": "value"},
            push_artifacts=False,
        )

        assert operator.dbt_command == "test"
        assert operator.conn_id == "dbt_postgres"
        assert operator.dbt_tags == ["daily", "core"]
        assert operator.dbt_models == ["model1", "model2"]
        assert operator.exclude_tags == ["exclude_me"]
        assert operator.dbt_vars == {"key": "value"}
        assert operator.full_refresh is True
        assert operator.fail_fast is True
        assert operator.target == "prod"
        assert operator.env_vars == {"ENV_VAR": "value"}
        assert operator.push_artifacts is False

    def test_template_fields(self) -> None:
        """Test that template fields are properly defined."""
        assert "venv_path" in DbtOperator.template_fields
        assert "dbt_project_dir" in DbtOperator.template_fields
        assert "conn_id" in DbtOperator.template_fields
        assert "dbt_tags" in DbtOperator.template_fields
        assert "dbt_models" in DbtOperator.template_fields
        assert "dbt_vars" in DbtOperator.template_fields
        assert "target" in DbtOperator.template_fields


class TestDbtOperatorExecution:
    """Tests for DbtOperator execution."""

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_run_success_with_conn_id(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test successful dbt run execution with Airflow connection."""
        # Mock DbtHook
        mock_hook = Mock()
        mock_result = DbtTaskResult(
            success=True,
            command="run",
            run_results={"results": []},
            manifest={"nodes": {}},
        )
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
            conn_id="dbt_postgres",
            dbt_tags=["daily"],
        )

        # Mock context
        context = {
            "ti": Mock(xcom_push=Mock()),
        }

        result = operator.execute(context)

        # Verify hook was created correctly
        mock_hook_class.assert_called_once_with(
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            target=None,
            profiles_dir=None,
            env_vars={},
        )

        # Verify run_dbt_task was called with correct parameters
        mock_hook.run_dbt_task.assert_called_once_with(
            command="run",
            select=["tag:daily"],
            exclude=None,
            vars={},
            full_refresh=False,
            fail_fast=False,
        )

        # Verify XCom push
        assert context["ti"].xcom_push.call_count == 2
        context["ti"].xcom_push.assert_any_call(key="manifest", value={"nodes": {}})
        context["ti"].xcom_push.assert_any_call(key="run_results", value={"results": []})

        # Verify result
        assert result["success"] is True
        assert result["command"] == "run"

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_with_profiles_dir(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
        mock_profiles_dir: Path,
    ) -> None:
        """Test execution with profiles_dir (backward compatibility)."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(
            success=True,
            command="run",
            run_results={},
            manifest={},
        )
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir=str(mock_profiles_dir),
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify hook was created with profiles_dir
        mock_hook_class.assert_called_once_with(
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id=None,
            target=None,
            profiles_dir=str(mock_profiles_dir),
            env_vars={},
        )

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_test_with_fail_fast(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt test command with fail_fast."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(
            success=True,
            command="test",
        )
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt_test",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="test",
            conn_id="dbt_postgres",
            fail_fast=True,
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify fail_fast was passed
        mock_hook.run_dbt_task.assert_called_once_with(
            command="test",
            select=None,
            exclude=None,
            vars={},
            full_refresh=False,
            fail_fast=True,
        )

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_with_models_and_exclude_tags(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test execution with models and exclude tags."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(success=True, command="run")
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            dbt_models=["model1", "model2"],
            dbt_tags=["daily"],
            exclude_tags=["deprecated", "slow"],
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify select includes both models and tags
        call_args = mock_hook.run_dbt_task.call_args
        assert call_args[1]["select"] == ["model1", "model2", "tag:daily"]
        assert call_args[1]["exclude"] == ["tag:deprecated", "tag:slow"]

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_with_full_refresh_and_vars(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test execution with full_refresh and variables."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(success=True, command="run")
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            full_refresh=True,
            dbt_vars={"start_date": "2024-01-01", "env": "prod"},
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify parameters
        call_args = mock_hook.run_dbt_task.call_args
        assert call_args[1]["full_refresh"] is True
        assert call_args[1]["vars"] == {"start_date": "2024-01-01", "env": "prod"}

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_execute_without_artifact_push(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test execution without artifact push."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(
            success=True,
            command="run",
            manifest={"nodes": {}},
            run_results={"results": []},
        )
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            push_artifacts=False,
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify XCom push was NOT called
        context["ti"].xcom_push.assert_not_called()

    def test_on_kill(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test on_kill method logs warning."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
        )

        # Should not raise an error
        operator.on_kill()


class TestDbtOperatorAirflow31DAGRendering:
    """Tests for Airflow 3.1 DAG rendering compatibility."""

    def test_dag_rendering_with_conn_id(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test that operator can be added to a DAG and rendered (Airflow 3.1)."""
        with DAG(
            dag_id="test_parse_dag",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ) as dag:
            dbt_task = DbtOperator(
                task_id="dbt_run",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="dbt_postgres",
            )

        # Airflow parser should be able to read task properties
        assert dbt_task.task_id == "dbt_run"
        assert dbt_task in dbt_task.dag.tasks
        assert dag.task_dict["dbt_run"] == dbt_task
        assert dbt_task.dag == dag

        # Verify task can be serialized (important for Airflow 3.1)
        task_dict = dbt_task.__dict__
        assert "venv_path" in task_dict
        assert "dbt_project_dir" in task_dict
        assert "conn_id" in task_dict

    def test_dag_rendering_with_profiles_dir(
        self, mock_venv_path: Path, mock_dbt_project: Path, mock_profiles_dir: Path
    ) -> None:
        """Test DAG rendering with profiles_dir (backward compatibility)."""
        with DAG(
            dag_id="test_dbt_dag_profiles",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ) as dag:
            dbt_task = DbtOperator(
                task_id="dbt_test",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="test",
                profiles_dir=str(mock_profiles_dir),
                target="dev",
            )

        assert "dbt_test" in dag.task_dict
        assert dbt_task.profiles_dir == str(mock_profiles_dir)
        assert dbt_task.conn_id is None

    def test_multiple_dbt_tasks_in_dag(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test multiple DBT tasks in a single DAG."""
        with DAG(
            dag_id="test_dbt_multiple_tasks",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ) as dag:
            dbt_run = DbtOperator(
                task_id="dbt_run",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="run",
                conn_id="dbt_postgres",
            )

            dbt_test = DbtOperator(
                task_id="dbt_test",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="test",
                conn_id="dbt_postgres",
            )

            # Set dependencies
            dbt_run >> dbt_test

            # Verify both tasks are in DAG
            assert len(dag.tasks) == 2
            assert "dbt_run" in dag.task_dict
            assert "dbt_test" in dag.task_dict

            # Verify dependencies
            assert dbt_test in dbt_run.downstream_list
            assert dbt_run in dbt_test.upstream_list

    def test_templated_fields_rendering(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test that templated fields work in DAG context."""
        with DAG(
            dag_id="test_dbt_templated",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ):
            dbt_task = DbtOperator(
                task_id="dbt_run",
                venv_path="{{ params.venv_path }}",
                dbt_project_dir="{{ params.project_dir }}",
                conn_id="{{ params.conn_id }}",
                target="{{ params.target }}",
                dbt_tags=["{{ params.env }}"],
                dbt_vars={"date": "{{ ds }}"},
            )

        # Verify templated fields are set as strings (not rendered yet)
        assert dbt_task.venv_path == "{{ params.venv_path }}"
        assert dbt_task.conn_id == "{{ params.conn_id }}"
        assert dbt_task.target == "{{ params.target }}"
        assert "{{ params.env }}" in dbt_task.dbt_tags
        assert dbt_task.dbt_vars["date"] == "{{ ds }}"


class TestDbtOperatorIntegration:
    """Integration tests for DbtOperator."""

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_complete_workflow_with_artifacts(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test complete workflow with artifact handling."""
        # Setup mock hook with realistic results
        mock_hook = Mock()
        manifest = {
            "nodes": {
                "model.test.my_model": {
                    "name": "my_model",
                    "resource_type": "model",
                }
            }
        }
        run_results = {
            "results": [
                {
                    "unique_id": "model.test.my_model",
                    "status": "success",
                    "execution_time": 1.5,
                }
            ]
        }
        mock_result = DbtTaskResult(
            success=True,
            command="run",
            manifest=manifest,
            run_results=run_results,
        )
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        operator = DbtOperator(
            task_id="dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            dbt_models=["my_model"],
            target="prod",
        )

        context = {"ti": Mock(xcom_push=Mock())}
        result = operator.execute(context)

        # Verify result structure
        assert result["success"] is True
        assert result["command"] == "run"
        assert result["manifest"] == manifest
        assert result["run_results"] == run_results

        # Verify XCom pushes
        assert context["ti"].xcom_push.call_count == 2

    @patch("dlh_airflow_common.operators.dbt.DbtHook")
    def test_env_vars_passed_to_hook(
        self,
        mock_hook_class: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test that environment variables are passed to hook."""
        mock_hook = Mock()
        mock_result = DbtTaskResult(success=True, command="run")
        mock_hook.run_dbt_task.return_value = mock_result
        mock_hook_class.return_value = mock_hook

        env_vars = {"DBT_ENV": "production", "CUSTOM_VAR": "value"}
        operator = DbtOperator(
            task_id="dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            env_vars=env_vars,
        )

        context = {"ti": Mock(xcom_push=Mock())}
        operator.execute(context)

        # Verify env_vars were passed to hook
        mock_hook_class.assert_called_once_with(
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            target=None,
            profiles_dir=None,
            env_vars=env_vars,
        )


class TestDbtOperatorAirflowSerialization:
    """Tests for Airflow serialization and rendering compatibility."""

    def test_operator_can_be_pickled(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test that operator can be pickled for Airflow serialization."""
        import pickle

        operator = DbtOperator(
            task_id="dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            dbt_tags=["daily"],
        )

        # Pickle and unpickle
        pickled = pickle.dumps(operator)
        unpickled = pickle.loads(pickled)

        assert unpickled.task_id == "dbt_run"
        assert unpickled.venv_path == str(mock_venv_path)
        assert unpickled.conn_id == "dbt_postgres"
        assert unpickled.dbt_tags == ["daily"]

    def test_operator_serializable_to_json(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test that operator attributes are JSON serializable."""
        operator = DbtOperator(
            task_id="dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            dbt_tags=["daily", "core"],
            dbt_models=["model1", "model2"],
            dbt_vars={"key": "value", "number": 42},
            full_refresh=True,
        )

        # Verify all attributes are JSON serializable

        serializable_attrs = {
            "task_id": operator.task_id,
            "venv_path": operator.venv_path,
            "dbt_project_dir": operator.dbt_project_dir,
            "conn_id": operator.conn_id,
            "dbt_tags": operator.dbt_tags,
            "dbt_models": operator.dbt_models,
            "dbt_vars": operator.dbt_vars,
            "full_refresh": operator.full_refresh,
        }

        # Should not raise
        json_str = json.dumps(serializable_attrs)
        assert json_str is not None

    def test_dag_can_be_parsed_without_execution(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test that DAG can be parsed without executing tasks (Airflow requirement)."""
        with DAG(
            dag_id="test_parse_dag",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ):
            dbt_task = DbtOperator(
                task_id="dbt_run",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="dbt_postgres",
            )

        # Airflow parser should be able to read task properties
        assert dbt_task.task_id == "dbt_run"
        assert dbt_task in dbt_task.dag.tasks

    def test_operator_with_all_template_fields(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test operator with all template fields for Airflow rendering."""
        operator = DbtOperator(
            task_id="dbt_run",
            venv_path="{{ var.value.venv_path }}",
            dbt_project_dir="{{ var.value.project_dir }}",
            conn_id="{{ var.value.conn_id }}",
            target="{{ var.value.target }}",
            dbt_tags=["{{ var.value.env }}", "daily"],
            dbt_vars={"date": "{{ ds }}", "env": "{{ var.value.env }}"},
        )

        # Verify template fields are preserved as strings
        assert "{{" in operator.venv_path
        assert "{{" in operator.conn_id
        assert "{{" in operator.target
        assert any("{{" in tag for tag in operator.dbt_tags)
        assert "{{" in operator.dbt_vars["date"]

    def test_dag_import_without_airflow_webserver(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test that DAG file can be imported without Airflow webserver running."""
        # This simulates what happens during airflow dags list or dag testing
        dag = DAG(
            dag_id="test_import_dag",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        )

        dbt_task = DbtOperator(
            task_id="dbt_run",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="dbt_postgres",
            dag=dag,
        )

        # Should not raise any errors
        assert dbt_task.dag == dag
        assert dbt_task.task_id == "dbt_run"

    def test_operator_with_complex_dependencies(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test operator in DAG with complex dependencies."""
        with DAG(
            dag_id="test_complex_dag",
            start_date=datetime(2024, 1, 1),
            catchup=False,
        ):
            dbt_seed = DbtOperator(
                task_id="dbt_seed",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="run",
                conn_id="dbt_postgres",
            )

            dbt_run = DbtOperator(
                task_id="dbt_run",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="run",
                conn_id="dbt_postgres",
                dbt_tags=["daily"],
            )

            dbt_test = DbtOperator(
                task_id="dbt_test",
                venv_path=str(mock_venv_path),
                dbt_project_dir=str(mock_dbt_project),
                dbt_command="test",
                conn_id="dbt_postgres",
            )

            # Complex dependency chain
            dbt_seed >> dbt_run >> dbt_test
            dbt_seed >> dbt_test  # Also direct dependency

        # Verify dependency graph
        assert dbt_run in dbt_seed.downstream_list
        assert dbt_test in dbt_run.downstream_list
        assert dbt_test in dbt_seed.downstream_list
        assert len(dbt_test.upstream_list) == 2
