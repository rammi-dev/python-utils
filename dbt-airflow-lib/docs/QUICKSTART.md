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

with DAG("dbt_pipeline", start_date=datetime(2024, 1, 1), schedule="@daily") as dag:

    dbt_run = DbtOperator(
        task_id="dbt_run_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        conn_id="dbt_dremio_prod",  # Use Airflow connection
        dbt_command="run",
        dbt_tags=["daily"],
        target="prod",
    )

    dbt_test = DbtOperator(
        task_id="dbt_test_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        conn_id="dbt_dremio_prod",
        dbt_command="test",
        dbt_tags=["daily"],
        fail_fast=True,
        target="prod",
    )

    dbt_run >> dbt_test
```

For detailed DBT setup, see [DBT_SETUP.md](DBT_SETUP.md) and [DAG_FACTORY_USAGE.md](DAG_FACTORY_USAGE.md).

## Project Structure

```
dlh-airflow-common/
├── src/dlh_airflow_common/     # Source code
│   ├── operators/              # Custom operators (base, dbt)
│   ├── hooks/                  # Airflow hooks
│   ├── utils/                  # Utilities
│   └── validation/             # YAML validation
├── tests/                      # Test suite (99.65% coverage)
├── docs/                       # Documentation
├── pyproject.toml              # Project configuration
├── Makefile                    # Convenience commands
└── .python-version             # Python 3.11
```

## Using with dag-factory

Create YAML configuration for your DAGs:

```yaml
# dags/dbt_pipeline.yml
dbt_daily_pipeline:
  default_args:
    owner: 'data_team'
    start_date: '2024-01-01'
    retries: 2

  schedule: '@daily'
  catchup: false

  tasks:
    dbt_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'
      dbt_command: 'run'
      dbt_tags: ['daily']
      target: 'prod'
```

Validate your YAML:

```bash
validate-dags dags/
```

See [DAG_FACTORY_USAGE.md](DAG_FACTORY_USAGE.md) for complete guide.

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

- Read [README.md](../README.md) for detailed documentation
- Check [DBT_SETUP.md](DBT_SETUP.md) for DBT operator setup
- Review [DAG_FACTORY_USAGE.md](DAG_FACTORY_USAGE.md) for YAML-based DAGs
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions

## Getting Help

- Run `make help` for available commands
- Check test examples for usage patterns
- Review inline documentation in source files
