"""Tests for DBT operator."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from airflow.exceptions import AirflowException

from dlh_airflow_common.operators.dbt import DbtOperator


@pytest.fixture
def mock_venv_path(tmp_path: Path) -> Path:
    """Create a mock virtual environment path."""
    venv_path = tmp_path / "venv"
    venv_path.mkdir()
    bin_dir = venv_path / "bin"
    bin_dir.mkdir()
    dbt_bin = bin_dir / "dbt"
    dbt_bin.touch()
    dbt_bin.chmod(0o755)
    return venv_path


@pytest.fixture
def mock_dbt_project(tmp_path: Path) -> Path:
    """Create a mock dbt project directory."""
    project_path = tmp_path / "dbt_project"
    project_path.mkdir()
    dbt_project_yml = project_path / "dbt_project.yml"
    dbt_project_yml.write_text("name: test_project\nversion: 1.0.0\n")
    return project_path


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
            dbt_tags=["daily", "core"],
            dbt_models=["model1", "model2"],
            exclude_tags=["exclude_me"],
            dbt_vars={"key": "value"},
            full_refresh=True,
            fail_fast=True,
            target="prod",
            profiles_dir="/path/to/profiles",
            additional_args=["--debug"],
            env_vars={"ENV_VAR": "value"},
        )

        assert operator.dbt_command == "test"
        assert operator.dbt_tags == ["daily", "core"]
        assert operator.dbt_models == ["model1", "model2"]
        assert operator.exclude_tags == ["exclude_me"]
        assert operator.dbt_vars == {"key": "value"}
        assert operator.full_refresh is True
        assert operator.fail_fast is True
        assert operator.target == "prod"
        assert operator.profiles_dir == "/path/to/profiles"
        assert operator.additional_args == ["--debug"]
        assert operator.env_vars == {"ENV_VAR": "value"}

    def test_template_fields(self) -> None:
        """Test that template fields are properly defined."""
        assert "venv_path" in DbtOperator.template_fields
        assert "dbt_project_dir" in DbtOperator.template_fields
        assert "dbt_tags" in DbtOperator.template_fields
        assert "dbt_models" in DbtOperator.template_fields
        assert "dbt_vars" in DbtOperator.template_fields
        assert "target" in DbtOperator.template_fields


class TestDbtOperatorValidation:
    """Test suite for DbtOperator validation."""

    def test_validate_nonexistent_venv(self, mock_dbt_project: Path) -> None:
        """Test validation fails for non-existent virtual environment."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path="/nonexistent/venv",
            dbt_project_dir=str(mock_dbt_project),
        )

        with pytest.raises(AirflowException, match="Virtual environment not found"):
            operator._validate_inputs()

    def test_validate_missing_dbt_executable(
        self, tmp_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test validation fails when dbt executable is missing."""
        venv_path = tmp_path / "venv"
        venv_path.mkdir()
        (venv_path / "bin").mkdir()

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )

        with pytest.raises(AirflowException, match="dbt executable not found"):
            operator._validate_inputs()

    def test_validate_nonexistent_project_dir(self, mock_venv_path: Path) -> None:
        """Test validation fails for non-existent dbt project directory."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir="/nonexistent/project",
        )

        with pytest.raises(AirflowException, match="DBT project directory not found"):
            operator._validate_inputs()

    def test_validate_missing_dbt_project_yml(
        self, mock_venv_path: Path, tmp_path: Path
    ) -> None:
        """Test validation fails when dbt_project.yml is missing."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(project_path),
        )

        with pytest.raises(AirflowException, match="dbt_project.yml not found"):
            operator._validate_inputs()

    def test_validate_invalid_command(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test validation fails for invalid dbt command."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="invalid_command",
        )

        with pytest.raises(AirflowException, match="Invalid dbt command"):
            operator._validate_inputs()

    def test_validate_success(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test successful validation."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )

        # Should not raise any exception
        operator._validate_inputs()


class TestDbtOperatorCommandBuilding:
    """Test suite for DBT command building."""

    def test_build_basic_run_command(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building basic dbt run command."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
        )

        cmd = operator._build_dbt_command()

        assert cmd[0] == str(mock_venv_path / "bin" / "dbt")
        assert cmd[1] == "run"

    def test_build_command_with_tags(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with tags."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_tags=["daily", "core"],
        )

        cmd = operator._build_dbt_command()

        assert "--select" in cmd
        assert "tag:daily" in cmd
        assert "tag:core" in cmd

    def test_build_command_with_models(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with specific models."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_models=["model1", "model2"],
        )

        cmd = operator._build_dbt_command()

        assert "--select" in cmd
        idx = cmd.index("--select")
        assert "model1 model2" == cmd[idx + 1]

    def test_build_command_with_exclude_tags(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with exclude tags."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            exclude_tags=["exclude_me"],
        )

        cmd = operator._build_dbt_command()

        assert "--exclude" in cmd
        assert "tag:exclude_me" in cmd

    def test_build_command_with_target(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with target."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            target="prod",
        )

        cmd = operator._build_dbt_command()

        assert "--target" in cmd
        assert "prod" in cmd

    def test_build_command_with_profiles_dir(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with profiles directory."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir="/path/to/profiles",
        )

        cmd = operator._build_dbt_command()

        assert "--profiles-dir" in cmd
        assert "/path/to/profiles" in cmd

    def test_build_command_with_full_refresh(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building run command with full refresh."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
            full_refresh=True,
        )

        cmd = operator._build_dbt_command()

        assert "--full-refresh" in cmd

    def test_build_command_with_fail_fast(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building test command with fail fast."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="test",
            fail_fast=True,
        )

        cmd = operator._build_dbt_command()

        assert "--fail-fast" in cmd

    def test_build_command_with_vars(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with variables."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_vars={"key1": "value1", "key2": 42},
        )

        cmd = operator._build_dbt_command()

        assert "--vars" in cmd
        idx = cmd.index("--vars")
        vars_json = cmd[idx + 1]
        parsed_vars = json.loads(vars_json)
        assert parsed_vars == {"key1": "value1", "key2": 42}

    def test_build_command_with_additional_args(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test building command with additional arguments."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            additional_args=["--debug", "--log-format", "json"],
        )

        cmd = operator._build_dbt_command()

        assert "--debug" in cmd
        assert "--log-format" in cmd
        assert "json" in cmd


class TestDbtOperatorEnvironment:
    """Test suite for environment preparation."""

    @patch.dict("os.environ", {"EXISTING_VAR": "existing"}, clear=True)
    def test_prepare_environment_basic(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test basic environment preparation."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )

        env = operator._prepare_environment()

        assert "DBT_PROJECT_DIR" in env
        assert env["DBT_PROJECT_DIR"] == str(mock_dbt_project)
        assert env["EXISTING_VAR"] == "existing"

    @patch.dict("os.environ", {}, clear=True)
    def test_prepare_environment_with_custom_vars(
        self, mock_venv_path: Path, mock_dbt_project: Path
    ) -> None:
        """Test environment preparation with custom variables."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            env_vars={"CUSTOM_VAR": "custom_value", "ANOTHER_VAR": "another"},
        )

        env = operator._prepare_environment()

        assert env["CUSTOM_VAR"] == "custom_value"
        assert env["ANOTHER_VAR"] == "another"
        assert env["DBT_PROJECT_DIR"] == str(mock_dbt_project)


class TestDbtOperatorExecution:
    """Test suite for DBT operator execution."""

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_run_success(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test successful dbt run execution."""
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="Success!", stderr=""
        )

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        result = operator.execute(context)

        assert result["command"] == "run"
        assert result["return_code"] == 0
        assert result["stdout"] == "Success!"
        mock_subprocess.assert_called_once()

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_test_success(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test successful dbt test execution."""
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="All tests passed!", stderr=""
        )

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="test",
            dbt_tags=["daily"],
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        result = operator.execute(context)

        assert result["command"] == "test"
        assert result["return_code"] == 0
        mock_subprocess.assert_called_once()

        # Verify command includes tags
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "test" in cmd
        assert "--select" in cmd

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_failure(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt execution failure."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["dbt", "run"], stderr="Error occurred"
        )

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}

        with pytest.raises(AirflowException, match="DBT run failed"):
            operator.execute(context)

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_with_output_logging(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test that output is properly logged."""
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Line 1\nLine 2\nLine 3",
            stderr="Warning: Something",
        )

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        operator.execute(context)

        # Verify logging calls
        assert operator.logger.info.call_count > 0
        assert operator.logger.warning.call_count > 0

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_validates_before_running(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
    ) -> None:
        """Test that validation runs before execution."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir="/nonexistent",
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}

        with pytest.raises(AirflowException, match="DBT project directory not found"):
            operator.execute(context)

        # subprocess.run should not be called
        mock_subprocess.assert_not_called()

    def test_on_kill(self, mock_venv_path: Path, mock_dbt_project: Path) -> None:
        """Test on_kill handler."""
        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )
        operator.logger = MagicMock()

        # Should not raise exception
        operator.on_kill()
        operator.logger.warning.assert_called_once()


class TestDbtOperatorIntegration:
    """Integration tests for complete workflows."""

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_run_with_multiple_tags(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test run command with multiple tags."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
            dbt_tags=["daily", "core", "incremental"],
            target="prod",
            full_refresh=True,
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        result = operator.execute(context)

        assert result["return_code"] == 0

        # Verify command structure
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "run" in cmd
        assert "--target" in cmd
        assert "prod" in cmd
        assert "--full-refresh" in cmd

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_test_with_fail_fast(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test test command with fail fast."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="test",
            dbt_tags=["daily"],
            fail_fast=True,
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        result = operator.execute(context)

        assert result["return_code"] == 0

        # Verify command structure
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert "test" in cmd
        assert "--fail-fast" in cmd

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_with_models_and_exclude_tags(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test execution with dbt_models and exclude_tags to cover logging."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success", stderr="")

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
            dbt_command="run",
            dbt_models=["model1", "model2"],
            exclude_tags=["skip", "deprecated"],
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}
        operator.execute(context)

        # Verify models logging (line 220)
        models_logged = any(
            "Models:" in str(call) for call in operator.logger.info.call_args_list
        )
        assert models_logged, "dbt_models should be logged"

        # Verify exclude_tags logging (line 222)
        exclude_logged = any(
            "Exclude tags:" in str(call) for call in operator.logger.info.call_args_list
        )
        assert exclude_logged, "exclude_tags should be logged"

    @patch("dlh_airflow_common.operators.dbt.subprocess.run")
    def test_execute_failure_with_stdout(
        self,
        mock_subprocess: Mock,
        mock_venv_path: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test execution failure with stdout to cover error logging (lines 266-269)."""
        # Simulate dbt failure with stdout output
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["dbt", "run"],
            output=None,
        )
        error.stdout = "Error line 1\nError line 2\n\nError line 3\n"
        error.stderr = "Warning"
        mock_subprocess.side_effect = error

        operator = DbtOperator(
            task_id="test_dbt",
            venv_path=str(mock_venv_path),
            dbt_project_dir=str(mock_dbt_project),
        )
        operator.logger = MagicMock()

        context: Dict[str, Any] = {}

        with pytest.raises(AirflowException, match="DBT run failed"):
            operator.execute(context)

        # Verify stdout was logged (lines 266-269)
        stdout_logged = any(
            "DBT stdout:" in str(call) for call in operator.logger.error.call_args_list
        )
        assert stdout_logged, "DBT stdout should be logged on failure"

        # Verify error lines were logged
        error_lines_logged = any(
            "Error line" in str(call) for call in operator.logger.error.call_args_list
        )
        assert error_lines_logged, "Error lines from stdout should be logged"
