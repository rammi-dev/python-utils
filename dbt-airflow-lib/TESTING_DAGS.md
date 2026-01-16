# Testing DAGs Without Airflow

This guide explains how to test your DAGs and operators without running a full Airflow environment.

## Testing Approaches

### 1. Unit Testing Operators (Isolated)

Test operators without Airflow by mocking the context:

```python
import pytest
from unittest.mock import Mock, patch
from dlh_airflow_common.operators.dbt import DbtOperator

def test_dbt_operator_execution():
    """Test DbtOperator without Airflow."""

    # Create operator
    operator = DbtOperator(
        task_id="test_dbt",
        venv_path="/path/to/venv",
        dbt_project_dir="/path/to/project",
        dbt_command="run",
        dbt_tags=["daily"],
    )

    # Mock context (minimal Airflow context)
    context = {
        "task_instance": Mock(),
        "dag_run": Mock(),
        "execution_date": "2024-01-01",
    }

    # Mock subprocess execution
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        # Execute operator
        result = operator.execute(context)

        # Verify
        assert mock_run.called
        assert "dbt" in str(mock_run.call_args)
```

### 2. Testing DAG Structure

Test that your DAG is correctly defined:

```python
import pytest
from airflow.models import DagBag

def test_dag_loaded():
    """Test that DAG loads without errors."""
    dagbag = DagBag(dag_folder="dags/", include_examples=False)

    # Check no import errors
    assert len(dagbag.import_errors) == 0, f"DAG import errors: {dagbag.import_errors}"

    # Check DAG exists
    assert "my_dag_id" in dagbag.dags
    dag = dagbag.get_dag("my_dag_id")
    assert dag is not None

def test_dag_structure():
    """Test DAG has correct tasks and dependencies."""
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    dag = dagbag.get_dag("my_dag_id")

    # Check tasks exist
    assert "dbt_run" in dag.task_ids
    assert "dbt_test" in dag.task_ids

    # Check dependencies
    dbt_run_task = dag.get_task("dbt_run")
    dbt_test_task = dag.get_task("dbt_test")

    assert dbt_test_task in dbt_run_task.downstream_list

def test_dag_tags():
    """Test DAG has required tags."""
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    dag = dagbag.get_dag("my_dag_id")

    assert "production" in dag.tags
    assert "dbt" in dag.tags
```

### 3. Testing DAG Execution (Without Airflow)

Execute DAG tasks without Airflow scheduler:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

def test_dag_task_execution():
    """Test DAG task execution without Airflow."""
    from airflow import DAG
    from dlh_airflow_common.operators.dbt import DbtOperator

    # Create DAG
    dag = DAG(
        "test_dag",
        start_date=datetime(2024, 1, 1),
        schedule=None,
    )

    # Create task
    with dag:
        dbt_task = DbtOperator(
            task_id="dbt_run",
            venv_path="/path/to/venv",
            dbt_project_dir="/path/to/project",
            dbt_command="run",
        )

    # Mock context
    mock_ti = Mock()
    mock_ti.xcom_push = Mock()
    mock_ti.xcom_pull = Mock(return_value=None)

    context = {
        "task_instance": mock_ti,
        "dag_run": Mock(execution_date=datetime(2024, 1, 1)),
        "execution_date": datetime(2024, 1, 1),
        "ds": "2024-01-01",
        "task": dbt_task,
    }

    # Mock subprocess
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        # Execute task
        result = dbt_task.execute(context)

        # Verify
        assert mock_run.called
```

## Testing Strategies

### Strategy 1: Minimal Airflow (DagBag Only)

Install minimal Airflow for structure testing:

```bash
# Install only Airflow (no extras)
pip install apache-airflow==3.1.0

# Or with uv
uv pip install apache-airflow==3.1.0
```

```python
# tests/test_dag_integrity.py
import pytest
from airflow.models import DagBag

@pytest.fixture(scope="session")
def dagbag():
    """Load all DAGs once for testing."""
    return DagBag(dag_folder="dags/", include_examples=False)

def test_no_import_errors(dagbag):
    """Ensure all DAGs load without errors."""
    assert not dagbag.import_errors

def test_all_dags_have_tags(dagbag):
    """Ensure all DAGs have tags."""
    for dag_id, dag in dagbag.dags.items():
        assert len(dag.tags) > 0, f"DAG {dag_id} has no tags"

def test_all_dags_have_owner(dagbag):
    """Ensure all DAGs have an owner."""
    for dag_id, dag in dagbag.dags.items():
        assert dag.owner != "airflow", f"DAG {dag_id} using default owner"
```

### Strategy 2: Pure Python (No Airflow)

Test operator logic without any Airflow dependency:

```python
# tests/test_operators_standalone.py
import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path

def test_dbt_operator_command_building():
    """Test DBT command construction without Airflow."""
    from dlh_airflow_common.operators.dbt import DbtOperator

    operator = DbtOperator(
        task_id="test",
        venv_path="/opt/venv",
        dbt_project_dir="/opt/project",
        dbt_command="run",
        dbt_tags=["daily", "core"],
        target="prod",
        full_refresh=True,
    )

    # Build command (internal method)
    cmd = operator._build_dbt_command()

    # Verify command parts
    assert "/opt/venv/bin/dbt" in " ".join(cmd)
    assert "run" in cmd
    assert "--select" in cmd
    assert "tag:daily" in cmd
    assert "tag:core" in cmd
    assert "--target" in cmd
    assert "prod" in cmd
    assert "--full-refresh" in cmd

def test_dbt_operator_validation():
    """Test operator input validation."""
    from dlh_airflow_common.operators.dbt import DbtOperator

    # Invalid command
    with pytest.raises(ValueError, match="dbt_command must be"):
        DbtOperator(
            task_id="test",
            venv_path="/opt/venv",
            dbt_project_dir="/opt/project",
            dbt_command="invalid",
        )

    # Missing venv
    with pytest.raises(ValueError, match="venv_path"):
        DbtOperator(
            task_id="test",
            venv_path="/nonexistent",
            dbt_project_dir="/opt/project",
        )
```

### Strategy 3: Integration Testing (with mocked subprocess)

Test full execution flow with mocked external calls:

```python
# tests/test_integration.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for all tests."""
    with patch("subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="Success", stderr="")
        yield mock

@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    venv_path = tmp_path / "venv"
    venv_path.mkdir()
    (venv_path / "bin").mkdir()
    (venv_path / "bin" / "dbt").touch()
    (venv_path / "bin" / "dbt").chmod(0o755)

    project_path = tmp_path / "project"
    project_path.mkdir()
    (project_path / "dbt_project.yml").touch()

    return {
        "venv": str(venv_path),
        "project": str(project_path),
    }

def test_dbt_dag_execution(mock_subprocess, mock_paths):
    """Test complete DAG execution flow."""
    from airflow import DAG
    from dlh_airflow_common.operators.dbt import DbtOperator

    dag = DAG("test_dag", start_date=datetime(2024, 1, 1))

    with dag:
        dbt_run = DbtOperator(
            task_id="dbt_run",
            venv_path=mock_paths["venv"],
            dbt_project_dir=mock_paths["project"],
            dbt_command="run",
            dbt_tags=["daily"],
        )

        dbt_test = DbtOperator(
            task_id="dbt_test",
            venv_path=mock_paths["venv"],
            dbt_project_dir=mock_paths["project"],
            dbt_command="test",
            dbt_tags=["daily"],
        )

    # Set dependencies
    dbt_run >> dbt_test

    # Create mock context
    context = {
        "task_instance": Mock(),
        "dag_run": Mock(execution_date=datetime(2024, 1, 1)),
        "execution_date": datetime(2024, 1, 1),
        "ds": "2024-01-01",
    }

    # Execute tasks in order
    dbt_run.execute(context)
    assert mock_subprocess.call_count == 1

    dbt_test.execute(context)
    assert mock_subprocess.call_count == 2

    # Verify commands
    calls = mock_subprocess.call_args_list
    assert "run" in str(calls[0])
    assert "test" in str(calls[1])
```

## Testing Best Practices

### 1. Use pytest fixtures

```python
# conftest.py
import pytest
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture
def airflow_context():
    """Standard Airflow context for testing."""
    return {
        "task_instance": Mock(),
        "dag_run": Mock(),
        "execution_date": "2024-01-01",
        "ds": "2024-01-01",
        "ts": "2024-01-01T00:00:00+00:00",
    }

@pytest.fixture
def mock_venv(tmp_path):
    """Create a mock virtual environment."""
    venv = tmp_path / "venv"
    venv.mkdir()
    bin_dir = venv / "bin"
    bin_dir.mkdir()

    # Create mock dbt executable
    dbt = bin_dir / "dbt"
    dbt.touch()
    dbt.chmod(0o755)

    return str(venv)

@pytest.fixture
def mock_dbt_project(tmp_path):
    """Create a mock dbt project."""
    project = tmp_path / "dbt_project"
    project.mkdir()

    # Create dbt_project.yml
    yml = project / "dbt_project.yml"
    yml.write_text("name: test_project\nversion: 1.0.0\n")

    return str(project)
```

### 2. Mock external dependencies

```python
import pytest
from unittest.mock import patch, Mock

@pytest.fixture(autouse=True)
def mock_external_calls():
    """Automatically mock external calls for all tests."""
    with patch("subprocess.run") as mock_subprocess, \
         patch("os.path.exists", return_value=True), \
         patch("os.access", return_value=True):

        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Success",
            stderr=""
        )
        yield mock_subprocess
```

### 3. Test data builders

```python
# tests/builders.py
from dataclasses import dataclass
from typing import Optional, List
from unittest.mock import Mock

@dataclass
class DbtOperatorBuilder:
    """Builder for creating DbtOperator test instances."""

    task_id: str = "test_dbt"
    venv_path: str = "/opt/venv"
    dbt_project_dir: str = "/opt/project"
    dbt_command: str = "run"
    dbt_tags: Optional[List[str]] = None
    target: Optional[str] = None

    def with_tags(self, *tags: str):
        self.dbt_tags = list(tags)
        return self

    def with_target(self, target: str):
        self.target = target
        return self

    def build(self):
        from dlh_airflow_common.operators.dbt import DbtOperator
        return DbtOperator(
            task_id=self.task_id,
            venv_path=self.venv_path,
            dbt_project_dir=self.dbt_project_dir,
            dbt_command=self.dbt_command,
            dbt_tags=self.dbt_tags,
            target=self.target,
        )

# Usage in tests
def test_with_builder():
    operator = (
        DbtOperatorBuilder()
        .with_tags("daily", "core")
        .with_target("prod")
        .build()
    )
    assert operator.dbt_tags == ["daily", "core"]
```

## Running Tests

### Basic testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_dbt.py

# Run with coverage
pytest --cov=dlh_airflow_common --cov-report=html

# Or use make
make test
make test-cov
make coverage
```

### Testing DAG structure only

```bash
# Run only DAG structure tests
pytest tests/test_dag_integrity.py -v

# Run without external dependencies
pytest -m "not integration" -v
```

### Testing with markers

```python
# Mark tests
@pytest.mark.unit
def test_operator_logic():
    pass

@pytest.mark.integration
def test_with_subprocess():
    pass

@pytest.mark.dag
def test_dag_structure():
    pass
```

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only DAG tests
pytest -m dag
```

## CI/CD Testing

### GitLab CI Testing

Your `.gitlab-ci.yml` already includes comprehensive testing:

```yaml
test:pytest:
  script:
    - uv pip install -e ".[dev]"
    - pytest --cov=dlh_airflow_common --cov-report=xml
```

### Testing without Airflow in CI

For faster tests without full Airflow:

```yaml
test:quick:
  stage: test
  script:
    - uv pip install pytest pytest-cov pytest-mock
    - pytest -m "not dag" --cov=dlh_airflow_common
```

## Example: Complete Test Suite

```python
# tests/test_dbt_operator_complete.py
import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path
from datetime import datetime

class TestDbtOperator:
    """Complete test suite for DbtOperator."""

    @pytest.fixture
    def operator(self, mock_venv, mock_dbt_project):
        """Create operator instance."""
        from dlh_airflow_common.operators.dbt import DbtOperator
        return DbtOperator(
            task_id="test_dbt",
            venv_path=mock_venv,
            dbt_project_dir=mock_dbt_project,
            dbt_command="run",
        )

    def test_initialization(self, operator):
        """Test operator initializes correctly."""
        assert operator.task_id == "test_dbt"
        assert operator.dbt_command == "run"

    def test_command_building(self, operator):
        """Test DBT command is built correctly."""
        cmd = operator._build_dbt_command()
        assert "dbt" in cmd[0]
        assert "run" in cmd

    @patch("subprocess.run")
    def test_execution(self, mock_run, operator, airflow_context):
        """Test operator executes successfully."""
        mock_run.return_value = Mock(returncode=0, stdout="OK", stderr="")

        result = operator.execute(airflow_context)

        assert mock_run.called
        assert mock_run.call_args[0][0][1] == "run"

    @patch("subprocess.run")
    def test_execution_failure(self, mock_run, operator, airflow_context):
        """Test operator handles execution failure."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")

        with pytest.raises(Exception):
            operator.execute(airflow_context)
```

## Summary

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| Unit Testing | Fast, isolated | Limited scope | Operator logic |
| DAG Structure | Validates config | Needs Airflow | DAG integrity |
| Integration | Full flow | Complex mocking | End-to-end validation |
| Pure Python | No dependencies | Limited DAG testing | CI/CD speed |

Choose the approach based on:
- **Development**: Unit tests for quick feedback
- **Pre-commit**: Structure tests for DAG validation
- **CI/CD**: Full suite with coverage
- **Production**: Integration tests with mocks
