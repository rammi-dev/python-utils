# Quick Start Guide

Get started with `dlh-airflow-common` in minutes!

## Installation

### Using uv with Python 3.11 (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11 (if not already installed)
uv python install 3.11

# Clone the repository
git clone <your-repo-url>
cd dlh-airflow-common

# Create virtual environment with Python 3.11
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x

# Install with dev dependencies
uv pip install -e ".[dev]"
```

For detailed uv setup and Python management, see [UV_SETUP.md](UV_SETUP.md).

### Using pip

```bash
# Clone the repository
git clone <your-repo-url>
cd dlh-airflow-common

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Quick Commands

### Development

```bash
# Run tests
pytest

# Run all quality checks
make all

# Format code
make format-fix

# Run tests with coverage
pytest --cov
```

### Building and Publishing

```bash
# Build package
make build

# Publish to Nexus
make publish-nexus
```

### Using Tox

```bash
# Run all checks
tox

# Run tests on Python 3.11
tox -e py311

# Run linting
tox -e lint

# Format code
tox -e format-fix
```

## Quick DBT Example

```python
from airflow import DAG
from dlh_airflow_common.operators.dbt import DbtOperator
from datetime import datetime

with DAG("dbt_pipeline", start_date=datetime(2024, 1, 1), schedule_interval="@daily") as dag:

    dbt_run = DbtOperator(
        task_id="dbt_run_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["daily"],
        target="prod",
    )

    dbt_test = DbtOperator(
        task_id="dbt_test_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="test",
        dbt_tags=["daily"],
        fail_fast=True,
        target="prod",
    )

    dbt_run >> dbt_test
```

For detailed DBT setup, see [DBT_SETUP.md](DBT_SETUP.md).

## Project Structure

```
dlh-airflow-common/
├── src/dlh_airflow_common/     # Source code
│   ├── operators/              # Custom operators (base, dbt)
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── pyproject.toml              # Project configuration
├── tox.ini                     # Tox configuration
├── Makefile                    # Convenience commands
├── README.md                   # Full documentation
├── DBT_SETUP.md                # DBT operator guide
└── DEPLOYMENT.md               # Deployment guide
```

## Creating Your First Operator

1. Create a new file in `src/dlh_airflow_common/operators/`:

```python
from typing import Any, Dict
from dlh_airflow_common.operators.base import BaseOperator


class MyOperator(BaseOperator):
    def __init__(self, task_id: str, my_param: str, **kwargs: Any) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.my_param = my_param

    def execute(self, context: Dict[str, Any]) -> Any:
        self.logger.info(f"Running with: {self.my_param}")
        return "success"
```

2. Add to `src/dlh_airflow_common/operators/__init__.py`:

```python
from dlh_airflow_common.operators.my_operator import MyOperator

__all__ = ["BaseOperator", "MyOperator"]
```

3. Write tests in `tests/operators/test_my_operator.py`

4. Run quality checks:

```bash
make all
```

## Common Tasks

### Add a new utility function

1. Add to `src/dlh_airflow_common/utils/`
2. Write tests in `tests/utils/`
3. Export in `src/dlh_airflow_common/utils/__init__.py`

### Update version

1. Edit `pyproject.toml` - change version
2. Edit `src/dlh_airflow_common/__init__.py` - update `__version__`
3. Commit and tag:
   ```bash
   git commit -am "Bump version to X.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

### Run specific tests

```bash
# Single test file
pytest tests/operators/test_base.py

# Single test function
pytest tests/operators/test_base.py::TestBaseOperator::test_initialization

# Tests matching pattern
pytest -k "test_logger"
```

## Environment Variables for Nexus

```bash
export TWINE_USERNAME=your-username
export TWINE_PASSWORD=your-password
export TWINE_REPOSITORY_URL=https://nexus.example.com/repository/pypi-private/
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions
- Review example operators in `src/dlh_airflow_common/operators/`
- Customize configuration in `pyproject.toml`

## Getting Help

- Run `make help` for available commands
- Check test examples for usage patterns
- Review inline documentation in source files
