"""Tests for YAML DAG validation CLI."""

import tempfile
from pathlib import Path

import pytest

from dlh_airflow_common.validation.cli import main


class TestValidationCLI:
    """Tests for validation CLI."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_validate_single_valid_file(self, temp_dir: Path) -> None:
        """Test CLI with a single valid file."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        yaml_file = temp_dir / "dag.yaml"
        yaml_file.write_text(yaml_content)

        exit_code = main([str(yaml_file)])
        assert exit_code == 0

    def test_validate_single_invalid_file(self, temp_dir: Path) -> None:
        """Test CLI with a single invalid file."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
  # Missing schedule and start_date
"""
        yaml_file = temp_dir / "dag.yaml"
        yaml_file.write_text(yaml_content)

        exit_code = main([str(yaml_file)])
        assert exit_code == 1

    def test_validate_directory(self, temp_dir: Path) -> None:
        """Test CLI with a directory."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        (temp_dir / "dag1.yaml").write_text(yaml_content)
        (temp_dir / "dag2.yaml").write_text(yaml_content)

        exit_code = main([str(temp_dir)])
        assert exit_code == 0

    def test_validate_directory_with_invalid_file(self, temp_dir: Path) -> None:
        """Test CLI with directory containing invalid file."""
        valid_content = """
dag_1:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        invalid_content = """
dag_2:
  default_args:
    owner: airflow
"""
        (temp_dir / "valid.yaml").write_text(valid_content)
        (temp_dir / "invalid.yaml").write_text(invalid_content)

        exit_code = main([str(temp_dir)])
        assert exit_code == 1

    def test_verbose_flag(self, temp_dir: Path, capsys: pytest.CaptureFixture) -> None:
        """Test CLI with verbose flag."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
"""
        yaml_file = temp_dir / "dag.yaml"
        yaml_file.write_text(yaml_content)

        exit_code = main(["-v", str(yaml_file)])
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "WARNING" in captured.out  # Should show "No tasks defined" warning

    def test_no_recursive_flag(self, temp_dir: Path) -> None:
        """Test CLI with --no-recursive flag."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        (temp_dir / "root.yaml").write_text(yaml_content)
        (subdir / "nested.yaml").write_text("invalid: yaml: syntax:")

        # Without --no-recursive, it would find the invalid file
        exit_code = main(["--no-recursive", str(temp_dir)])
        assert exit_code == 0

    def test_custom_pattern(self, temp_dir: Path) -> None:
        """Test CLI with custom pattern."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        (temp_dir / "dag.yaml").write_text(yaml_content)
        (temp_dir / "dag.custom").write_text(yaml_content)

        # Default pattern should only find .yaml
        exit_code = main(["--pattern", "*.custom", str(temp_dir)])
        assert exit_code == 0

    def test_strict_mode(self, temp_dir: Path) -> None:
        """Test CLI with --strict flag."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  # No tasks - will generate warning
"""
        yaml_file = temp_dir / "dag.yaml"
        yaml_file.write_text(yaml_content)

        # Without strict, should pass (warnings don't fail)
        exit_code = main([str(yaml_file)])
        assert exit_code == 0

        # With strict, warnings should fail
        exit_code = main(["--strict", str(yaml_file)])
        assert exit_code == 1

    def test_nonexistent_path(self) -> None:
        """Test CLI with non-existent path."""
        exit_code = main(["/nonexistent/path"])
        assert exit_code == 1

    def test_summary_output(self, temp_dir: Path, capsys: pytest.CaptureFixture) -> None:
        """Test CLI shows summary output."""
        yaml_content = """
my_dag:
  default_args:
    owner: airflow
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    task_1:
      operator: BashOperator
"""
        (temp_dir / "dag.yaml").write_text(yaml_content)

        main([str(temp_dir)])

        captured = capsys.readouterr()
        assert "Validation Summary" in captured.out
        assert "Total files:" in captured.out
        assert "Valid:" in captured.out
        assert "Invalid:" in captured.out
