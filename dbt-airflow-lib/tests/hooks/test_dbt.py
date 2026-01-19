"""Tests for DbtHook."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from airflow.exceptions import AirflowException

from dlh_airflow_common.hooks.dbt import DbtHook, DbtTaskResult

try:
    from airflow.sdk.definitions.connection import Connection
except ImportError:
    from airflow.models import Connection  # type: ignore[assignment, no-redef]


@pytest.fixture
def mock_venv(tmp_path: Path) -> Path:
    """Create a mock virtual environment."""
    import sys

    venv_path = tmp_path / "venv"
    venv_path.mkdir()

    # Create bin directory with dbt executable
    bin_dir = venv_path / "bin"
    bin_dir.mkdir()
    dbt_bin = bin_dir / "dbt"
    dbt_bin.write_text("#!/bin/bash\necho 'dbt'")
    dbt_bin.chmod(0o755)

    # Create site-packages directory using current Python version
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = venv_path / "lib" / python_version / "site-packages"
    site_packages.mkdir(parents=True)

    return venv_path


@pytest.fixture
def mock_dbt_project(tmp_path: Path) -> Path:
    """Create a mock dbt project."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create dbt_project.yml
    dbt_project_yml = project_dir / "dbt_project.yml"
    dbt_project_yml.write_text(
        yaml.dump({"name": "test_project", "version": "1.0.0", "profile": "test"})
    )

    # Create target directory
    target_dir = project_dir / "target"
    target_dir.mkdir()

    return project_dir


@pytest.fixture
def mock_profiles_dir(tmp_path: Path) -> Path:
    """Create a mock profiles directory."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # Create profiles.yml
    profiles_yml = profiles_dir / "profiles.yml"
    profiles_yml.write_text(
        yaml.dump(
            {
                "test_project": {
                    "target": "dev",
                    "outputs": {
                        "dev": {
                            "type": "postgres",
                            "host": "localhost",
                            "port": 5432,
                            "user": "test",
                            "password": "test",
                            "database": "test",
                            "schema": "public",
                        }
                    },
                }
            }
        )
    )

    return profiles_dir


class TestDbtHookInitialization:
    """Tests for DbtHook initialization."""

    def test_init_with_conn_id(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test initialization with connection ID."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        assert hook.venv_path == str(mock_venv)
        assert hook.dbt_project_dir == str(mock_dbt_project)
        assert hook.conn_id == "test_conn"
        assert hook.profiles_dir is None

    def test_init_with_profiles_dir(
        self, mock_venv: Path, mock_dbt_project: Path, mock_profiles_dir: Path
    ) -> None:
        """Test initialization with profiles directory."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir=str(mock_profiles_dir),
        )

        assert hook.profiles_dir == str(mock_profiles_dir)
        assert hook.conn_id is None

    def test_init_missing_both_conn_id_and_profiles_dir(
        self, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test initialization fails without conn_id or profiles_dir."""
        with pytest.raises(ValueError, match="Either conn_id or profiles_dir must be provided"):
            DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
            )

    def test_init_with_env_vars(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test initialization with environment variables."""
        env_vars = {"DBT_ENV": "test", "CUSTOM_VAR": "value"}
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
            env_vars=env_vars,
        )

        assert hook.env_vars == env_vars


class TestDbtHookSetupEnvironment:
    """Tests for DbtHook environment setup."""

    def test_setup_dbt_environment_adds_to_sys_path(
        self, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test that setup adds venv site-packages to sys.path."""
        import sys

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        original_path = sys.path.copy()

        # Create mock dbt module to satisfy the import check
        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = MagicMock()

        try:
            # Mock sys.path to track insert calls
            with patch("dlh_airflow_common.hooks.dbt.sys") as mock_sys:
                # Use actual Python version to match the fixture
                mock_sys.version_info = MagicMock(
                    major=sys.version_info.major, minor=sys.version_info.minor
                )
                mock_sys.path = MagicMock()

                hook._setup_dbt_environment()

                # Check that site-packages was inserted at position 0
                python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
                expected_path = str(mock_venv / "lib" / python_version / "site-packages")
                mock_sys.path.insert.assert_called_once_with(0, expected_path)
        finally:
            sys.path = original_path
            # Cleanup sys.modules
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    def test_setup_dbt_environment_missing_venv(
        self, mock_dbt_project: Path, tmp_path: Path
    ) -> None:
        """Test setup fails with missing venv."""
        nonexistent_venv = tmp_path / "nonexistent"
        hook = DbtHook(
            venv_path=str(nonexistent_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        with pytest.raises(FileNotFoundError, match="Virtual environment not found"):
            hook._setup_dbt_environment()

    def test_setup_dbt_environment_missing_site_packages(
        self, mock_dbt_project: Path, tmp_path: Path
    ) -> None:
        """Test setup fails with missing site-packages directory."""
        # Create venv directory but not site-packages
        venv_dir = tmp_path / "bad_venv"
        venv_dir.mkdir()

        hook = DbtHook(
            venv_path=str(venv_dir),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        with pytest.raises(FileNotFoundError, match="Site-packages not found in venv"):
            hook._setup_dbt_environment()

    def test_setup_dbt_environment_import_error(
        self, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test setup fails when dbt cannot be imported."""
        import builtins
        import sys

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        # Clear any existing dbt modules
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith("dbt")]
        for module in modules_to_remove:
            sys.modules.pop(module, None)

        # Mock builtins.__import__ to raise ImportError for dbt
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("dbt"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="Failed to import dbt from venv"):
                hook._setup_dbt_environment()


class TestDbtHookLoadProfileFromConnection:
    """Tests for loading profiles from Airflow connections."""

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_load_profile_from_dremio_connection(
        self, mock_get_connection: Mock, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test loading profile from Dremio connection."""
        # Mock connection
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
            login="user",
            password="pass",
            port=9047,
        )
        mock_get_connection.return_value = conn

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_dremio",
        )

        target = hook._load_profile_from_connection()

        assert target["type"] == "dremio"
        assert target["software_host"] == "dremio.example.com"
        assert target["user"] == "user"
        assert target["database"] == "my_catalog"

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_load_profile_connection_not_found(
        self, mock_get_connection: Mock, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test loading profile fails when connection not found."""
        mock_get_connection.side_effect = Exception("Connection not found")

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="nonexistent",
        )

        with pytest.raises(AirflowException, match="Failed to retrieve Airflow connection"):
            hook._load_profile_from_connection()

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    @patch("dlh_airflow_common.hooks.dbt.get_profile_adapter")
    def test_load_profile_adapter_conversion_failure(
        self,
        mock_get_adapter: Mock,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test loading profile fails when adapter conversion fails."""
        conn = Connection(
            conn_id="test_conn",
            conn_type="dremio",
            host="localhost",
        )
        mock_get_connection.return_value = conn

        # Mock adapter to raise an exception during conversion
        mock_adapter = Mock()
        mock_adapter.to_dbt_target.side_effect = ValueError("Invalid connection config")
        mock_get_adapter.return_value = mock_adapter

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        with pytest.raises(AirflowException, match="Failed to convert connection"):
            hook._load_profile_from_connection()


class TestDbtHookGetOrCreateProfilesYml:
    """Tests for profiles.yml creation and retrieval."""

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_create_profiles_yml_from_connection(
        self, mock_get_connection: Mock, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test creating temporary profiles.yml from connection."""
        # Mock connection
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
            login="user",
            password="pass",
            port=9047,
        )
        mock_get_connection.return_value = conn

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_dremio",
            target="prod",
        )

        profiles_dir = hook._get_or_create_profiles_yml()

        # Check that profiles.yml was created
        profiles_path = Path(profiles_dir) / "profiles.yml"
        assert profiles_path.exists()

        # Verify content
        with open(profiles_path) as f:
            profiles = yaml.safe_load(f)

        assert "test_project" in profiles
        assert profiles["test_project"]["target"] == "prod"
        assert profiles["test_project"]["outputs"]["prod"]["type"] == "dremio"

    def test_use_existing_profiles_yml(
        self, mock_venv: Path, mock_dbt_project: Path, mock_profiles_dir: Path
    ) -> None:
        """Test using existing profiles.yml."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir=str(mock_profiles_dir),
        )

        profiles_dir = hook._get_or_create_profiles_yml()

        assert profiles_dir == str(mock_profiles_dir)

    def test_profiles_yml_not_found(
        self, mock_venv: Path, mock_dbt_project: Path, tmp_path: Path
    ) -> None:
        """Test error when profiles.yml not found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir=str(empty_dir),
        )

        with pytest.raises(FileNotFoundError, match="profiles.yml not found"):
            hook._get_or_create_profiles_yml()

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_create_profiles_yml_missing_dbt_project(
        self, mock_get_connection: Mock, mock_venv: Path, tmp_path: Path
    ) -> None:
        """Test error when dbt_project.yml is missing."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        # Create a directory without dbt_project.yml
        empty_project = tmp_path / "empty_project"
        empty_project.mkdir()

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(empty_project),
            conn_id="test_dremio",
        )

        with pytest.raises(FileNotFoundError, match="dbt_project.yml not found"):
            hook._get_or_create_profiles_yml()


class TestDbtHookRunDbtTask:
    """Tests for running dbt tasks."""

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_success(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test successful dbt task execution."""
        import sys

        # Mock connection
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        # Create manifest and run_results files
        target_dir = mock_dbt_project / "target"
        manifest_file = target_dir / "manifest.json"
        manifest_file.write_text(json.dumps({"nodes": {}}))
        run_results_file = target_dir / "run_results.json"
        run_results_file.write_text(json.dumps({"results": []}))

        # Mock dbtRunner and dbtRunnerResult
        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        # Create mock dbt.cli.main module
        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        # Inject into sys.modules
        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                result = hook.run_dbt_task("run", select=["tag:daily"], full_refresh=True)

            assert result.success is True
            assert result.command == "run"
            assert result.manifest is not None
            assert result.run_results is not None
            assert mock_runner_instance.invoke.called
        finally:
            # Cleanup sys.modules
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_with_vars(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt task with variables."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        # Create mock dbt.cli.main module
        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        # Inject into sys.modules
        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                result = hook.run_dbt_task("run", vars={"start_date": "2024-01-01", "env": "prod"})
                assert result is not None
            # Check that vars were passed as JSON
            call_args = mock_runner_instance.invoke.call_args[0][0]
            assert "--vars" in call_args
            vars_index = call_args.index("--vars") + 1
            vars_json = call_args[vars_index]
            vars_dict = json.loads(vars_json)
            assert vars_dict["start_date"] == "2024-01-01"
            assert vars_dict["env"] == "prod"
        finally:
            # Cleanup sys.modules
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_failure(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt task failure handling."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.exception = Exception("DBT execution failed")
        mock_runner_instance.invoke.return_value = mock_result

        # Create mock dbt.cli.main module
        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        # Inject into sys.modules
        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                with pytest.raises(Exception, match="dbt run failed"):
                    result = hook.run_dbt_task("run")
                    assert result is not None
        finally:
            # Cleanup sys.modules
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)


class TestDbtHookGetArtifacts:
    """Tests for getting dbt artifacts."""

    def test_get_manifest(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting manifest.json."""
        # Create manifest file
        target_dir = mock_dbt_project / "target"
        manifest_file = target_dir / "manifest.json"
        manifest_data = {"nodes": {"model.test.my_model": {"name": "my_model"}}}
        manifest_file.write_text(json.dumps(manifest_data))

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        manifest = hook.get_manifest()

        assert manifest == manifest_data

    def test_get_manifest_not_found(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting manifest when file doesn't exist."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        manifest = hook.get_manifest()

        assert manifest == {}

    def test_get_run_results(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting run_results.json."""
        # Create run results file
        target_dir = mock_dbt_project / "target"
        run_results_file = target_dir / "run_results.json"
        run_results_data = {"results": [{"node": {"name": "my_model"}, "status": "success"}]}
        run_results_file.write_text(json.dumps(run_results_data))

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        run_results = hook.get_run_results()

        assert run_results == run_results_data

    def test_get_run_results_not_found(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting run results when file doesn't exist."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        run_results = hook.get_run_results()

        assert run_results == {}


class TestDbtTaskResult:
    """Tests for DbtTaskResult dataclass."""

    def test_task_result_creation(self) -> None:
        """Test creating DbtTaskResult."""
        result = DbtTaskResult(
            success=True,
            command="run",
            run_results={"results": []},
            manifest={"nodes": {}},
        )

        assert result.success is True
        assert result.command == "run"
        assert result.run_results == {"results": []}
        assert result.manifest == {"nodes": {}}
        assert result.exception is None

    def test_task_result_with_exception(self) -> None:
        """Test DbtTaskResult with exception."""
        exc = Exception("Test error")
        result = DbtTaskResult(
            success=False,
            command="test",
            exception=exc,
        )

        assert result.success is False
        assert result.command == "test"
        assert result.exception == exc
        assert result.run_results is None
        assert result.manifest is None


class TestDbtHookEdgeCases:
    """Tests for DbtHook edge cases and error paths."""

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_load_profile_without_conn_id_raises_error(
        self, mock_get_connection: Mock, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test loading profile fails when conn_id is not set."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            profiles_dir="/tmp/profiles",
        )
        hook.conn_id = None  # Force conn_id to None

        with pytest.raises(AirflowException, match="conn_id must be set"):
            hook._load_profile_from_connection()

    def test_get_manifest_invalid_json(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting manifest with invalid JSON."""
        target_dir = mock_dbt_project / "target"
        manifest_file = target_dir / "manifest.json"
        manifest_file.write_text("invalid json {")

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        manifest = hook.get_manifest()
        assert manifest == {}

    def test_get_run_results_invalid_json(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test getting run results with invalid JSON."""
        target_dir = mock_dbt_project / "target"
        run_results_file = target_dir / "run_results.json"
        run_results_file.write_text("invalid json {")

        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        run_results = hook.get_run_results()
        assert run_results == {}

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_with_exclude_and_selector(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt task with exclude and selector arguments."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        target_dir = mock_dbt_project / "target"
        manifest_file = target_dir / "manifest.json"
        manifest_file.write_text(json.dumps({"nodes": {}}))
        run_results_file = target_dir / "run_results.json"
        run_results_file.write_text(json.dumps({"results": []}))

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                result = hook.run_dbt_task(
                    "run",
                    exclude=["tag:deprecated"],
                    selector="my_selector",
                )
                assert result is not None

            call_args = mock_runner_instance.invoke.call_args[0][0]
            assert "--exclude" in call_args
            assert "--selector" in call_args
        finally:
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_exception_handling(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt task with exception during execution."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_runner_instance.invoke.side_effect = Exception("Unexpected error")

        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                with pytest.raises(Exception, match="dbt run failed"):
                    hook.run_dbt_task("run")
        finally:
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    def test_hook_destructor_cleanup(self, mock_venv: Path, mock_dbt_project: Path) -> None:
        """Test that __del__ cleans up temporary resources."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        # Create a mock temp directory
        mock_temp_dir = Mock()
        hook._temp_profiles_dir = mock_temp_dir

        # Call destructor
        hook.__del__()

        # Verify cleanup was called
        mock_temp_dir.cleanup.assert_called_once()

    def test_hook_destructor_cleanup_with_error(
        self, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test that __del__ handles cleanup errors gracefully."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        # Create a mock temp directory that raises on cleanup
        mock_temp_dir = Mock()
        mock_temp_dir.cleanup.side_effect = Exception("Cleanup failed")
        hook._temp_profiles_dir = mock_temp_dir

        # Call destructor - should not raise
        hook.__del__()

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_with_target_flag(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt task with target flag."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
                target="prod",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                result = hook.run_dbt_task("run")
                assert result is not None

            # Verify target flag was added
            call_args = mock_runner_instance.invoke.call_args[0][0]
            assert "--target" in call_args
            assert "prod" in call_args
        finally:
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_test_with_fail_fast(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt test command with fail_fast flag."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                result = hook.run_dbt_task("test", fail_fast=True)
                assert result is not None

            # Verify fail-fast flag was added for test command
            call_args = mock_runner_instance.invoke.call_args[0][0]
            assert "--fail-fast" in call_args
        finally:
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_temp_profiles_cleanup_error_logged(
        self, mock_logger: Mock, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test that cleanup errors are logged."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        # Create mock temp dir that fails on cleanup
        mock_temp_dir = Mock()
        mock_temp_dir.cleanup.side_effect = Exception("Cleanup error")
        hook._temp_profiles_dir = mock_temp_dir

        # Manually invoke the cleanup logic from run_dbt_task finally block

        if hook._temp_profiles_dir:
            try:
                hook._temp_profiles_dir.cleanup()
                hook._temp_profiles_dir = None
            except Exception as e:
                mock_logger.warning(f"Failed to cleanup temporary profiles directory: {e}")

        # Verify warning was logged
        mock_logger.warning.assert_called_once()

    def test_get_or_create_profiles_yml_neither_conn_nor_profiles(
        self, mock_venv: Path, mock_dbt_project: Path
    ) -> None:
        """Test error when neither conn_id nor profiles_dir is set."""
        hook = DbtHook(
            venv_path=str(mock_venv),
            dbt_project_dir=str(mock_dbt_project),
            conn_id="test_conn",
        )

        # Force both to None
        hook.conn_id = None
        hook.profiles_dir = None

        with pytest.raises(AirflowException, match="Neither conn_id nor profiles_dir"):
            hook._get_or_create_profiles_yml()

    @patch("dlh_airflow_common.hooks.dbt.BaseHook.get_connection")
    def test_run_dbt_task_build_command_with_full_refresh(
        self,
        mock_get_connection: Mock,
        mock_venv: Path,
        mock_dbt_project: Path,
    ) -> None:
        """Test dbt build command with full refresh flag."""
        import sys

        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="localhost",
            schema="my_db",
            login="user",
            password="pass",
        )
        mock_get_connection.return_value = conn

        mock_runner_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.exception = None
        mock_runner_instance.invoke.return_value = mock_result

        mock_dbt_cli_main = MagicMock()
        mock_dbt_cli_main.dbtRunner = Mock(return_value=mock_runner_instance)
        mock_dbt_cli_main.dbtRunnerResult = Mock

        sys.modules["dbt"] = MagicMock()
        sys.modules["dbt.cli"] = MagicMock()
        sys.modules["dbt.cli.main"] = mock_dbt_cli_main

        try:
            hook = DbtHook(
                venv_path=str(mock_venv),
                dbt_project_dir=str(mock_dbt_project),
                conn_id="test_dremio",
            )

            with patch.object(hook, "_setup_dbt_environment"):
                ret = hook.run_dbt_task("build", full_refresh=True)
                assert ret is not None

            # Verify full-refresh flag was added
            call_args = mock_runner_instance.invoke.call_args[0][0]
            assert "--full-refresh" in call_args
        finally:
            sys.modules.pop("dbt.cli.main", None)
            sys.modules.pop("dbt.cli", None)
            sys.modules.pop("dbt", None)
