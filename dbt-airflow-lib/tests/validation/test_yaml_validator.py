"""Tests for YAML DAG validation module."""

import tempfile
from pathlib import Path

import pytest

from dlh_airflow_common.validation import (
    ValidationResult,
    YamlDagValidator,
    validate_yaml_directory,
    validate_yaml_file,
)

# Path to test resources
RESOURCES_DIR = Path(__file__).parent / "resources"
VALID_DIR = RESOURCES_DIR / "valid"
INVALID_DIR = RESOURCES_DIR / "invalid"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test valid result string representation."""
        result = ValidationResult(is_valid=True, file_path="dag.yaml")
        assert "VALID" in str(result)
        assert "dag.yaml" in str(result)

    def test_invalid_result_with_errors(self) -> None:
        """Test invalid result with errors."""
        result = ValidationResult(
            is_valid=False,
            file_path="dag.yaml",
            errors=["Missing field 'owner'", "Invalid syntax"],
        )
        output = str(result)
        assert "INVALID" in output
        assert "ERROR: Missing field 'owner'" in output
        assert "ERROR: Invalid syntax" in output

    def test_result_with_warnings(self) -> None:
        """Test result with warnings."""
        result = ValidationResult(
            is_valid=True,
            file_path="dag.yaml",
            warnings=["No tasks defined"],
        )
        output = str(result)
        assert "WARNING: No tasks defined" in output


class TestYamlDagValidator:
    """Tests for YamlDagValidator class."""

    @pytest.fixture
    def validator(self) -> YamlDagValidator:
        """Create a validator instance."""
        return YamlDagValidator()

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    # --- Syntax validation tests ---

    def test_validate_yaml_syntax_valid(self, validator: YamlDagValidator) -> None:
        """Test validation of valid YAML syntax."""
        result = validator.validate_yaml_syntax(VALID_DIR / "simple_dag.yaml")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_yaml_syntax_invalid(self, validator: YamlDagValidator) -> None:
        """Test validation of invalid YAML syntax."""
        result = validator.validate_yaml_syntax(INVALID_DIR / "syntax_error.yaml")
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "YAML syntax error" in result.errors[0]

    def test_validate_yaml_syntax_file_not_found(self, validator: YamlDagValidator) -> None:
        """Test validation when file doesn't exist."""
        result = validator.validate_yaml_syntax("/nonexistent/path.yaml")
        assert not result.is_valid
        assert "File not found" in result.errors[0]

    def test_validate_yaml_syntax_permission_denied(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test validation when file permission is denied."""
        yaml_file = temp_dir / "noperm.yaml"
        yaml_file.write_text("key: value")
        yaml_file.chmod(0o000)

        try:
            result = validator.validate_yaml_syntax(yaml_file)
            assert not result.is_valid
            assert "Permission denied" in result.errors[0]
        finally:
            yaml_file.chmod(0o644)  # Restore permissions for cleanup

    # --- DAG structure validation tests ---

    def test_validate_dag_structure_valid(self, validator: YamlDagValidator) -> None:
        """Test validation of valid DAG structure."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "operator": "airflow.operators.bash.BashOperator",
                        "bash_command": "echo hello",
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_dag_structure_missing_required_fields(
        self, validator: YamlDagValidator
    ) -> None:
        """Test validation fails when required fields are missing."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    # Missing start_date
                },
                # Missing schedule
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("schedule" in e for e in result.errors)
        assert any("start_date" in e for e in result.errors)

    def test_validate_dag_structure_no_dags(self, validator: YamlDagValidator) -> None:
        """Test validation fails when no DAGs are defined."""
        config = {"default": {"some": "value"}}

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("No DAG configurations found" in e for e in result.errors)

    def test_validate_dag_structure_not_dict(self, validator: YamlDagValidator) -> None:
        """Test validation fails when config is not a dict."""
        result = validator.validate_dag_structure("not a dict", "test.yaml")  # type: ignore[arg-type]
        assert not result.is_valid
        assert any("must be a dictionary" in e for e in result.errors)

    def test_validate_task_missing_operator(self, validator: YamlDagValidator) -> None:
        """Test validation fails when task is missing operator."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "bash_command": "echo hello",
                        # Missing operator
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("Missing required field 'operator'" in e for e in result.errors)

    def test_validate_task_invalid_dependency(self, validator: YamlDagValidator) -> None:
        """Test validation fails when dependency references non-existent task."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "operator": "BashOperator",
                        "dependencies": ["nonexistent_task"],
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("references non-existent task" in e for e in result.errors)

    def test_validate_task_string_dependency(self, validator: YamlDagValidator) -> None:
        """Test validation handles string dependency."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "operator": "BashOperator",
                    },
                    "task_2": {
                        "operator": "BashOperator",
                        "dependencies": "task_1",  # String instead of list
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert result.is_valid

    def test_validate_task_string_dependency_invalid(self, validator: YamlDagValidator) -> None:
        """Test validation fails for invalid string dependency."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "operator": "BashOperator",
                        "dependencies": "nonexistent",
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid

    def test_validate_dag_no_tasks_warning(self, validator: YamlDagValidator) -> None:
        """Test validation warns when DAG has no tasks."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert result.is_valid
        assert any("No tasks defined" in w for w in result.warnings)

    # --- File validation tests using resources ---

    def test_validate_file_valid(self, validator: YamlDagValidator) -> None:
        """Test full file validation for valid file."""
        result = validator.validate_file(VALID_DIR / "simple_dag.yaml")
        assert result.is_valid

    def test_validate_file_with_dependencies(self, validator: YamlDagValidator) -> None:
        """Test validation of file with task dependencies."""
        result = validator.validate_file(VALID_DIR / "dag_with_dependencies.yaml")
        assert result.is_valid

    def test_validate_file_multiple_dags(self, validator: YamlDagValidator) -> None:
        """Test validation of file with multiple DAGs."""
        result = validator.validate_file(VALID_DIR / "multiple_dags.yaml")
        assert result.is_valid

    def test_validate_file_depends_on(self, validator: YamlDagValidator) -> None:
        """Test validation handles depends_on key."""
        result = validator.validate_file(VALID_DIR / "dag_with_depends_on.yaml")
        assert result.is_valid

    def test_validate_file_no_tasks_warning(self, validator: YamlDagValidator) -> None:
        """Test validation of file with no tasks generates warning."""
        result = validator.validate_file(VALID_DIR / "dag_no_tasks.yaml")
        assert result.is_valid
        assert any("No tasks defined" in w for w in result.warnings)

    def test_validate_file_empty(self, validator: YamlDagValidator) -> None:
        """Test validation of empty file."""
        result = validator.validate_file(INVALID_DIR / "empty.yaml")
        assert not result.is_valid
        assert any("Empty YAML file" in e for e in result.errors)

    def test_validate_file_invalid_syntax(self, validator: YamlDagValidator) -> None:
        """Test validate_file returns early on syntax error."""
        result = validator.validate_file(INVALID_DIR / "syntax_error.yaml")
        assert not result.is_valid
        assert any("YAML syntax error" in e for e in result.errors)

    def test_validate_file_missing_schedule(self, validator: YamlDagValidator) -> None:
        """Test validation fails for missing schedule."""
        result = validator.validate_file(INVALID_DIR / "missing_schedule.yaml")
        assert not result.is_valid
        assert any("schedule" in e for e in result.errors)

    def test_validate_file_missing_start_date(self, validator: YamlDagValidator) -> None:
        """Test validation fails for missing start_date."""
        result = validator.validate_file(INVALID_DIR / "missing_start_date.yaml")
        assert not result.is_valid
        assert any("start_date" in e for e in result.errors)

    def test_validate_file_missing_operator(self, validator: YamlDagValidator) -> None:
        """Test validation fails for missing operator."""
        result = validator.validate_file(INVALID_DIR / "missing_operator.yaml")
        assert not result.is_valid
        assert any("operator" in e for e in result.errors)

    def test_validate_file_invalid_dependency(self, validator: YamlDagValidator) -> None:
        """Test validation fails for invalid dependency."""
        result = validator.validate_file(INVALID_DIR / "invalid_dependency.yaml")
        assert not result.is_valid
        assert any("non-existent task" in e for e in result.errors)

    def test_validate_file_no_dags(self, validator: YamlDagValidator) -> None:
        """Test validation fails when no DAGs defined."""
        result = validator.validate_file(INVALID_DIR / "no_dags.yaml")
        assert not result.is_valid
        assert any("No DAG configurations found" in e for e in result.errors)

    def test_validate_file_permission_denied(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test validation when file permission is denied during structure load."""
        yaml_file = temp_dir / "noperm.yaml"
        yaml_file.write_text("key: value")

        # Use mock to simulate read failure during structure validation
        import unittest.mock

        with unittest.mock.patch(
            "builtins.open",
            side_effect=[
                unittest.mock.mock_open(read_data="key: value")(),  # First call for syntax
                PermissionError("Permission denied"),  # Second call fails
            ],
        ):
            result = validator.validate_file(yaml_file)
            assert not result.is_valid
            assert any("Failed to load YAML" in e for e in result.errors)

    # --- Directory validation tests ---

    def test_validate_directory_valid(self, validator: YamlDagValidator) -> None:
        """Test validation of directory with valid files."""
        results = validator.validate_directory(VALID_DIR)
        assert len(results) > 0
        # All valid files should pass (though some may have warnings)
        assert all(r.is_valid for r in results)

    def test_validate_directory_invalid(self, validator: YamlDagValidator) -> None:
        """Test validation of directory with invalid files."""
        results = validator.validate_directory(INVALID_DIR)
        assert len(results) > 0
        # All invalid files should fail
        assert all(not r.is_valid for r in results)

    def test_validate_directory_mixed(self, validator: YamlDagValidator, temp_dir: Path) -> None:
        """Test validation of directory with mixed valid/invalid files."""
        # Copy one valid and one invalid file
        import shutil

        shutil.copy(VALID_DIR / "simple_dag.yaml", temp_dir / "valid.yaml")
        shutil.copy(INVALID_DIR / "missing_schedule.yaml", temp_dir / "invalid.yaml")

        results = validator.validate_directory(temp_dir)
        assert len(results) == 2
        valid_count = sum(1 for r in results if r.is_valid)
        assert valid_count == 1

    def test_validate_directory_recursive(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test recursive directory validation."""
        import shutil

        subdir = temp_dir / "subdir"
        subdir.mkdir()

        shutil.copy(VALID_DIR / "simple_dag.yaml", temp_dir / "root.yaml")
        shutil.copy(VALID_DIR / "simple_dag.yaml", subdir / "nested.yaml")

        results = validator.validate_directory(temp_dir, recursive=True)
        assert len(results) == 2

    def test_validate_directory_non_recursive(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test non-recursive directory validation."""
        import shutil

        subdir = temp_dir / "subdir"
        subdir.mkdir()

        shutil.copy(VALID_DIR / "simple_dag.yaml", temp_dir / "root.yaml")
        shutil.copy(VALID_DIR / "simple_dag.yaml", subdir / "nested.yaml")

        results = validator.validate_directory(temp_dir, recursive=False)
        assert len(results) == 1

    def test_validate_directory_not_found(self, validator: YamlDagValidator) -> None:
        """Test validation of non-existent directory."""
        results = validator.validate_directory("/nonexistent/dir")
        assert len(results) == 1
        assert not results[0].is_valid
        assert any("Directory not found" in e for e in results[0].errors)

    def test_validate_directory_not_a_dir(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test validation when path is a file not directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        results = validator.validate_directory(file_path)
        assert len(results) == 1
        assert not results[0].is_valid
        assert any("Not a directory" in e for e in results[0].errors)

    def test_validate_directory_no_yaml_files(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test validation of directory with no YAML files."""
        (temp_dir / "file.txt").write_text("not yaml")

        results = validator.validate_directory(temp_dir)
        assert len(results) == 1
        assert results[0].is_valid
        assert any("No YAML files found" in w for w in results[0].warnings)

    def test_validate_directory_yml_extension(
        self, validator: YamlDagValidator, temp_dir: Path
    ) -> None:
        """Test validation includes .yml files."""
        import shutil

        # Copy valid file with .yml extension
        shutil.copy(VALID_DIR / "simple_dag.yaml", temp_dir / "dag.yml")

        results = validator.validate_directory(temp_dir)
        assert len(results) == 1
        assert results[0].is_valid

    # --- Custom validator tests ---

    def test_custom_required_fields(self) -> None:
        """Test validator with custom required fields."""
        validator = YamlDagValidator(
            required_dag_fields={"custom_field"},
            required_default_args=set(),
            required_task_fields=set(),
        )

        config = {
            "my_dag": {
                "default_args": {},
                "custom_field": "value",
                "tasks": {
                    "task_1": {"operator": "BashOperator"},
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert result.is_valid

    def test_dag_config_not_dict(self, validator: YamlDagValidator) -> None:
        """Test validation when DAG config is not a dict (filtered out as non-DAG)."""
        config = {"my_dag": "not a dict"}

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        # Non-dict values are filtered out, resulting in "No DAG configurations found"
        assert any("No DAG configurations found" in e for e in result.errors)

    def test_validate_single_dag_not_dict(self, validator: YamlDagValidator) -> None:
        """Test _validate_single_dag when config is not a dict."""
        # Directly call internal method to test this edge case
        errors, warnings = validator._validate_single_dag("test_dag", "not a dict")
        assert len(errors) == 1
        assert "Configuration must be a dictionary" in errors[0]
        assert len(warnings) == 0

    def test_default_args_not_dict(self, validator: YamlDagValidator) -> None:
        """Test validation when default_args is not a dict."""
        config = {
            "my_dag": {
                "default_args": "not a dict",
                "schedule": "@daily",
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("default_args must be a dictionary" in e for e in result.errors)

    def test_tasks_not_dict(self, validator: YamlDagValidator) -> None:
        """Test validation when tasks is not a dict."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": "not a dict",
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("'tasks' must be a dictionary" in e for e in result.errors)

    def test_task_config_not_dict(self, validator: YamlDagValidator) -> None:
        """Test validation when task config is not a dict."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": "not a dict",
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert not result.is_valid
        assert any("Configuration must be a dictionary" in e for e in result.errors)

    def test_depends_on_key(self, validator: YamlDagValidator) -> None:
        """Test validation handles depends_on key for dependencies."""
        config = {
            "my_dag": {
                "default_args": {
                    "owner": "airflow",
                    "start_date": "2024-01-01",
                },
                "schedule": "@daily",
                "tasks": {
                    "task_1": {
                        "operator": "BashOperator",
                    },
                    "task_2": {
                        "operator": "BashOperator",
                        "depends_on": ["task_1"],
                    },
                },
            }
        }

        result = validator.validate_dag_structure(config, "test.yaml")
        assert result.is_valid


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_yaml_file_function(self) -> None:
        """Test validate_yaml_file convenience function."""
        result = validate_yaml_file(VALID_DIR / "simple_dag.yaml")
        assert result.is_valid

    def test_validate_yaml_directory_function(self) -> None:
        """Test validate_yaml_directory convenience function."""
        results = validate_yaml_directory(VALID_DIR)
        assert len(results) > 0
        assert all(r.is_valid for r in results)
