# DLH Airflow Common Library

A Python library providing common Airflow operators and utilities for building robust data pipelines.

## Features

- **DBT Operator**: Execute dbt run and test commands in isolated virtual environments with tag-based filtering
- **Base Operators**: Standardized base classes for creating custom Airflow operators
- **Common Utilities**: Logging, error handling, and other shared functionality
- **Virtual Environment Support**: Execute commands in pre-existing virtual environments
- **Type Safety**: Full type hints and mypy support
- **Well Tested**: Comprehensive test suite with pytest
- **Quality Assured**: Automated linting (ruff), formatting (black), and type checking (mypy)
- **Airflow 3.1+**: Compatible with Apache Airflow 3.1 and later

## Installation

### From Private PyPI (Nexus)

#### Using uv (Recommended - 10x faster)
```bash
# Install from Nexus with uv
uv pip install dlh-airflow-common --index-url https://your-nexus-server/repository/pypi-private/simple
```

#### Using pip
```bash
# Install from Nexus with pip
pip install dlh-airflow-common --index-url https://your-nexus-server/repository/pypi-private/simple
```

### From Source

#### Option 1: Using uv with Python 3.11 (Recommended)
[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver (10-100x faster than pip) that can also manage Python versions.

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11 (uv will download and manage it)
uv python install 3.11

# Clone and install
git clone <repository-url>
cd dlh-airflow-common

# Create virtual environment with Python 3.11
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x

# Install with dev dependencies
uv pip install -e ".[dev]"
```

For complete uv setup guide, see [UV_SETUP.md](UV_SETUP.md).

#### Option 2: Using pip
```bash
git clone <repository-url>
cd dlh-airflow-common
pip install -e ".[dev]"
```

## Usage

### Basic Operator Example

```python
from dlh_airflow_common.operators.base import BaseOperator
from typing import Any, Dict


class MyCustomOperator(BaseOperator):
    """Custom operator implementation."""

    def __init__(self, task_id: str, my_param: str, **kwargs: Any) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.my_param = my_param

    def execute(self, context: Dict[str, Any]) -> Any:
        self.logger.info(f"Executing with param: {self.my_param}")
        # Your custom logic here
        return "success"


# Use in DAG
from airflow import DAG
from datetime import datetime

with DAG(
    "my_dag",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
) as dag:
    task = MyCustomOperator(
        task_id="my_task",
        my_param="value",
    )
```

### DBT Operator Example

```python
from dlh_airflow_common.operators.dbt import DbtOperator
from airflow import DAG
from datetime import datetime

with DAG(
    "dbt_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:

    # Run dbt models with specific tags
    dbt_run_daily = DbtOperator(
        task_id="dbt_run_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["daily", "core"],
        target="prod",
    )

    # Run dbt tests for daily models
    dbt_test_daily = DbtOperator(
        task_id="dbt_test_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="test",
        dbt_tags=["daily"],
        fail_fast=True,
        target="prod",
    )

    # Full refresh for incremental models
    dbt_run_incremental = DbtOperator(
        task_id="dbt_run_incremental",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["incremental"],
        full_refresh=True,
        target="prod",
    )

    dbt_run_daily >> dbt_test_daily
```

#### DBT Operator Parameters

- **venv_path**: Path to pre-existing virtual environment with dbt installed
- **dbt_project_dir**: Path to your dbt project directory
- **dbt_command**: Command to execute (`run` or `test`)
- **dbt_tags**: List of tags to filter models (e.g., `["daily", "core"]`)
- **dbt_models**: List of specific models to run (e.g., `["model1", "model2"]`)
- **exclude_tags**: List of tags to exclude from execution
- **target**: DBT target environment (e.g., `prod`, `dev`)
- **full_refresh**: Perform full refresh for incremental models (default: False)
- **fail_fast**: Stop on first test failure (default: False)
- **dbt_vars**: Dictionary of variables to pass to dbt
- **profiles_dir**: Custom path to dbt profiles directory
- **additional_args**: Additional command-line arguments
- **env_vars**: Additional environment variables

### Using Utilities

```python
from dlh_airflow_common.utils.logging import get_logger, log_execution_time

# Get a configured logger
logger = get_logger(__name__, level="DEBUG")
logger.info("Processing data")

# Decorate functions to log execution time
@log_execution_time(logger)
def process_data():
    # Your processing logic
    pass
```

## Development

### Setup Development Environment

#### Option 1: Using uv with Python 3.11 (Recommended - Fastest)
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11
uv python install 3.11

# Clone the repository
git clone <repository-url>
cd dlh-airflow-common

# Create virtual environment with Python 3.11
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x

# Install development dependencies (10x faster than pip)
uv pip install -e ".[dev]"
```

#### Option 2: Using pip
```bash
# Clone the repository
git clone <repository-url>
cd dlh-airflow-common

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run unit tests (integration tests skipped by default)
pytest

# Run with coverage
pytest --cov=dlh_airflow_common --cov-report=html

# Run specific test file
pytest tests/operators/test_base.py

# Run with specific marker
pytest -m unit

# Using Make (recommended)
make test           # Quick test run
make test-cov       # Test with coverage reports
make coverage       # Test with coverage + open HTML report
```

#### Integration Tests

Integration tests execute real dbt commands using DuckDB (in-memory database):

```bash
# Install integration test dependencies
pip install -e ".[integration]"
# Or with uv
uv pip install -e ".[integration]"

# Run integration tests only
pytest -m integration

# Run all tests (unit + integration)
pytest -m ""

# Using tox
tox -e integration
```

**Note**: Integration tests are skipped by default to keep unit tests fast. They run actual dbt execution and take longer (~10-15 seconds).

For testing DAGs without running Airflow, see [TESTING_DAGS.md](TESTING_DAGS.md).

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/

# Run all checks with tox
tox
```

### Using Tox

Tox allows testing across multiple Python versions and running various quality checks:

```bash
# Run tests on all Python versions
tox

# Run specific environment
tox -e py311

# Run linting only
tox -e lint

# Run formatting check
tox -e format

# Auto-fix formatting
tox -e format-fix

# Run type checking
tox -e type-check

# Run all checks at once
tox -e all

# Build the package
tox -e build
```

## CI/CD and Versioning

### Automated GitLab CI/CD

The project includes a comprehensive GitLab CI/CD pipeline with **automatic semantic versioning**:

- 📦 **Automatic versioning** based on merge request descriptions
- ✅ **Quality checks** (lint, format, type-check, tests, security)
- 🏗️ **Automated builds** with uv and Python 3.11
- 🏷️ **Git tagging** on successful merges
- 🚀 **Nexus deployment** for distribution

#### Version Bumping

Add version keywords to your merge request description:

```
Add snapshot support [MINOR]     → 0.1.0 → 0.2.0
Fix validation bug [PATCH]       → 0.1.0 → 0.1.1
Refactor API [MAJOR]             → 0.1.0 → 1.0.0
Update docs                      → 0.1.0 → 0.1.1 (default: PATCH)
```

See [GITLAB_CI_SETUP.md](GITLAB_CI_SETUP.md) for complete CI/CD documentation.

## Building and Publishing

### Build Package

#### Option 1: Using uv (Recommended - Fastest)
```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install build
python -m build
```

#### Option 2: Using tox
```bash
tox -e build
```

#### Option 3: Using pip
```bash
python -m venv venv
source venv/bin/activate
pip install build
python -m build
```

This creates distribution files in the `dist/` directory:
- `dlh_airflow_common-0.1.0.tar.gz` (source distribution)
- `dlh_airflow_common-0.1.0-py3-none-any.whl` (wheel)

### Publish to Nexus

#### Setup Nexus Repository

1. Configure your `.pypirc` file:

```ini
[distutils]
index-servers =
    nexus

[nexus]
repository = https://your-nexus-server/repository/pypi-private/
username = your-username
password = your-password
```

Or use environment variables for CI/CD:

```bash
export TWINE_USERNAME=your-username
export TWINE_PASSWORD=your-password
export TWINE_REPOSITORY_URL=https://your-nexus-server/repository/pypi-private/
```

#### Upload to Nexus

##### Using uv (Recommended)
```bash
# Install twine
uv pip install twine

# Upload to Nexus
twine upload --repository nexus dist/*

# Or with environment variables
twine upload dist/*
```

##### Using pip
```bash
# Install twine
pip install twine

# Upload to Nexus
twine upload --repository nexus dist/*
```

#### CI/CD Pipeline Example

```yaml
# .gitlab-ci.yml or similar
build_and_publish:
  stage: deploy
  script:
    - python -m build
    - twine upload --repository-url $NEXUS_URL dist/*
  only:
    - tags
```

## Project Structure

```
dlh-airflow-common/
├── src/
│   └── dlh_airflow_common/
│       ├── __init__.py
│       ├── operators/
│       │   ├── __init__.py
│       │   └── base.py
│       └── utils/
│           ├── __init__.py
│           └── logging.py
├── tests/
│   ├── __init__.py
│   ├── operators/
│   │   ├── __init__.py
│   │   └── test_base.py
│   └── utils/
│       ├── __init__.py
│       └── test_logging.py
├── pyproject.toml
├── tox.ini
├── .gitignore
└── README.md
```

## Configuration

### pyproject.toml

The project uses modern Python packaging with `pyproject.toml`. Key configurations:

- **Build System**: setuptools
- **Python Version**: >=3.8
- **Dependencies**: apache-airflow>=2.5.0
- **Development Tools**: pytest, ruff, black, mypy, tox

### Tool Configurations

- **Black**: Line length 100, Python 3.8+ target
- **Ruff**: Comprehensive linting rules (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade)
- **Mypy**: Strict type checking enabled
- **Pytest**: Coverage reporting, custom markers

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and quality checks: `tox`
4. Submit a pull request

## Requirements

- Python >= 3.8 (Python 3.11 recommended)
- Apache Airflow >= 3.1.0
- For DBT Operator: dbt-core in a virtual environment

### Recommended Setup

- Use [uv](https://github.com/astral-sh/uv) for fast package management
- Python 3.11 for optimal performance and compatibility
- See [UV_SETUP.md](UV_SETUP.md) for uv installation and Python management

## License

MIT

## Support

For issues and questions, please open an issue on the repository.
