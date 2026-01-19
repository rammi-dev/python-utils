# DLH Airflow Common Library

A Python library providing common Airflow operators and utilities for building robust data pipelines.

## Features

- **DBT Operator**: Execute dbt commands (run, test, snapshot, seed, compile, deps) in isolated virtual environments with tag-based filtering
- **DBT Hook**: Advanced dbt integration with profile management and Airflow connection support
- **DAG Factory Integration**: Full compatibility with Astronomer dag-factory for YAML-based DAG generation
- **Base Operators**: Standardized base classes for creating custom Airflow operators
- **Common Utilities**: Logging, error handling, and other shared functionality
- **Virtual Environment Support**: Execute commands in pre-existing virtual environments
- **Type Safety**: Full type hints and mypy support
- **Well Tested**: Comprehensive test suite with 99.65% coverage (unit + integration tests)
- **Quality Assured**: Automated linting (ruff), formatting (black), and type checking (mypy)
- **Multi-Python Support**: Tested on Python 3.11 and 3.12
- **Airflow 3.1+**: Compatible with Apache Airflow 3.1 and later (ready for 3.2)

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
      artefact_target_root="/tmp/dbt-artifacts",  # Optional: custom artifact root
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
      artefact_target_root="/tmp/dbt-artifacts",
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
      artefact_target_root="/tmp/dbt-artifacts",
    )

    dbt_run_daily >> dbt_test_daily
```

#### DBT Operator Parameters

- **venv_path**: Path to pre-existing virtual environment with dbt installed
- **dbt_project_dir**: Path to your dbt project directory
- **dbt_command**: Command to execute (`run`, `test`, `snapshot`, `seed`, `compile`, `deps`)
- **conn_id**: Airflow connection ID for dbt profile (recommended)
- **dbt_tags**: List of tags to filter models (e.g., `["daily", "core"]`)
- **dbt_models**: List of specific models to run (e.g., `["model1", "model2"]`)
- **exclude_tags**: List of tags to exclude from execution
- **target**: DBT target environment (e.g., `prod`, `dev`)
- **full_refresh**: Perform full refresh for incremental models (default: False)
- **fail_fast**: Stop on first test failure (default: False)
- **dbt_vars**: Dictionary of variables to pass to dbt
- **profiles_dir**: Custom path to dbt profiles directory (fallback if no conn_id)
- **env_vars**: Additional environment variables
- **push_artifacts**: Push manifest and run_results to XCom (default: True)
- **artefact_target_root**: Root directory for dbt execution artifacts (default: `/tmp`). Use to isolate or redirect dbt output folders for each run.

### DAG Factory Integration

This library is fully compatible with [Astronomer dag-factory](https://github.com/astronomer/dag-factory) for YAML-based DAG generation.

Example YAML configuration:

```yaml
# dags/dbt_pipeline.yml
dbt_daily_run:
  default_args:
    owner: "data-team"
    retries: 2
    retry_delay_sec: 300
  schedule_interval: "0 2 * * *"
  catchup: false
  default_view: "graph"
  description: "Daily DBT pipeline with tag-based model selection"
  tasks:
    dbt_run_core:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: "/opt/airflow/venvs/dbt-venv"
      dbt_project_dir: "/opt/airflow/dbt/my_project"
      dbt_command: "run"
      dbt_tags:
        - "daily"
        - "core"
      target: "{{ var.value.get('dbt_target', 'prod') }}"

    dbt_test_core:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: "/opt/airflow/venvs/dbt-venv"
      dbt_project_dir: "/opt/airflow/dbt/my_project"
      dbt_command: "test"
      dbt_tags:
        - "daily"
      fail_fast: true
      target: "{{ var.value.get('dbt_target', 'prod') }}"
      dependencies:
        - dbt_run_core
```

Create a loader script at `dags/load_dags.py`:

```python
from dagfactory import load_yaml_dags
from pathlib import Path

# Load all YAML configs from dags directory
dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
```

For complete dag-factory integration guide, see `tests/integration/fixtures/dag_factory/README.md`.

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

# Install git hooks for automatic cleanup and quality checks
bash .githooks/install.sh
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

# Install git hooks for automatic cleanup and quality checks
bash .githooks/install.sh
```

### Git Hooks

The project includes pre-commit hooks that automatically clean build artifacts and run quality checks before each commit:

```bash
# Install the hooks (do this once after cloning)
bash .githooks/install.sh
```

**What the pre-commit hook does:**
- Cleans all build artifacts (`__pycache__`, `.pyc`, coverage files, etc.)
- Runs `black` and `ruff` formatters
- Runs linting with `ruff`
- Runs type checking with `mypy`
- Runs unit tests (integration tests skipped for speed)

**Bypass the hook when needed:**
```bash
# For quick commits
git commit --no-verify -m "Quick fix"

# Or skip only quality checks (still cleans)
SKIP_PRE_COMMIT=1 git commit -m "WIP"
```

For more details, see [.githooks/README.md](.githooks/README.md)

### Running Tests

#### Quick Start

```bash
# Run unit tests only (fast - integration tests skipped)
make test

# Run with coverage report
make test-cov

# Run integration tests (requires dbt-duckdb, dag-factory)
make install-integration
make test-integration

# Run ALL tests (unit + integration)
make test-all
```

#### Detailed Test Commands

```bash
# Using pytest directly
pytest                              # Unit tests only
pytest --cov=dlh_airflow_common    # With coverage
pytest -m integration               # Integration tests only
pytest -m ""                        # All tests

# Run specific test file
pytest tests/operators/test_base.py

# With coverage and HTML report
pytest --cov=dlh_airflow_common --cov-report=html
open htmlcov/index.html  # View coverage report
```

#### Multi-Version Testing with Tox

Test across Python 3.11 and 3.12 with Airflow 3.1:

```bash
# Run tests on both Python versions (verbose output)
make tox

# Run all quality checks + tests sequentially (shows full output)
make tox-parallel-verbose

# Run in parallel mode (fast, minimal output)
make tox-parallel

# Run specific environment
tox -e py311-airflow31              # Python 3.11 + Airflow 3.1
tox -e py312-airflow31              # Python 3.12 + Airflow 3.1

# Run integration tests via tox
make tox-integration
```

#### Integration Tests

Integration tests execute:
- **Real dbt execution** using dbt-duckdb (in-memory database)
- **DAG Factory rendering** using Airflow DagBag to verify YAML configs

```bash
# Install integration dependencies
make install-integration
# Or manually
uv pip install -e ".[integration]"

# Run integration tests
make test-integration

# Or with pytest
pytest -m integration
```

**Note**: Integration tests are skipped by default to keep unit tests fast. They run actual dbt commands and DAG rendering, taking ~10-15 seconds.

For more details:
- DAG Factory integration: See `tests/integration/fixtures/dag_factory/README.md`
- Testing DAGs without Airflow: See [docs/TESTING_DAGS.md](docs/TESTING_DAGS.md)

### Code Quality

#### Using Make (Recommended)

```bash
# Linting
make lint           # Check code with ruff
make lint-fix       # Auto-fix linting issues

# Formatting
make format         # Check formatting with black
make format-fix     # Auto-fix formatting

# Type checking
make type-check     # Run mypy

# All checks at once
make all            # Run lint, format, type-check, and tests
```

#### Using Tools Directly

```bash
# Linting with ruff
ruff check src/ tests/
ruff check --fix src/ tests/  # Auto-fix

# Formatting with black
black --check src/ tests/
black src/ tests/              # Auto-format

# Type checking with mypy
mypy src/
```

#### Using Tox

Test across Python versions and environments:

```bash
# Test on Python 3.11 and 3.12 with Airflow 3.1
tox -e py311-airflow31,py312-airflow31

# Quality checks
tox -e lint         # Linting
tox -e format       # Format checking
tox -e format-fix   # Auto-fix formatting
tox -e type-check   # Type checking

# Special environments
tox -e coverage     # Tests with 100% coverage requirement
tox -e integration  # Integration tests only
tox -e build        # Build package

# Run all environments
tox
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
│       ├── _version.py              # Auto-generated by setuptools-scm
│       ├── hooks/
│       │   ├── __init__.py
│       │   ├── dbt.py               # DbtHook for dbt integration
│       │   └── dbt_profiles.py      # Profile management
│       ├── operators/
│       │   ├── __init__.py
│       │   ├── base.py              # BaseOperator
│       │   └── dbt.py               # DbtOperator
│       ├── utils/
│       │   ├── __init__.py
│       │   └── logging.py           # Logging utilities
│       └── validation/
│           ├── __init__.py
│           ├── cli.py               # DAG validation CLI
│           └── yaml_validator.py    # YAML validation
├── tests/
│   ├── conftest.py
│   ├── hooks/
│   │   ├── test_dbt.py
│   │   └── test_dbt_profiles.py
│   ├── integration/                 # Integration tests
│   │   ├── conftest.py
│   │   ├── fixtures/
│   │   │   ├── dag_factory/         # DAG Factory YAML configs
│   │   │   ├── dbt_project/         # dbt project fixtures
│   │   │   └── profiles/            # dbt profiles
│   │   ├── test_dag_factory_integration.py
│   │   └── test_dbt_real_execution.py
│   ├── operators/
│   │   ├── test_base.py
│   │   └── test_dbt.py
│   ├── utils/
│   │   └── test_logging.py
│   └── validation/
│       └── test_yaml_validator.py
├── docs/                            # Documentation
│   ├── DAG_FACTORY_USAGE.md
│   ├── DBT_SETUP.md
│   ├── DEPLOYMENT.md
│   ├── GITLAB_CI_SETUP.md
│   ├── TESTING_DAGS.md
│   ├── UV_SETUP.md
│   └── ...
├── .gitlab-ci.yml                   # CI/CD pipeline
├── Makefile                         # Development commands
├── pyproject.toml                   # Project configuration
├── tox.ini                          # Multi-version testing
├── uv.lock                          # uv lockfile
└── README.md
```

## Configuration

### pyproject.toml

The project uses modern Python packaging with `pyproject.toml`. Key configurations:

- **Build System**: setuptools with setuptools-scm for versioning
- **Python Version**: 3.11-3.12 (both fully tested)
- **Dependencies**: apache-airflow>=3.1.0, dbt-core>=1.8.0, PyYAML>=6.0
- **Development Tools**: pytest, ruff, black, mypy, tox, uv

### Tool Configurations

- **Black**: Line length 100, Python 3.11+ target
- **Ruff**: Comprehensive linting rules (pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade)
- **Mypy**: Strict type checking, Python 3.11 target
- **Pytest**: Coverage reporting (90% required), custom markers (unit, integration)
- **Tox**: Multi-version testing (Python 3.11/3.12 × Airflow 3.1/3.2)

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and quality checks: `tox`
4. Submit a pull request

## Requirements

### Core Requirements
- Python 3.11 or 3.12 (both fully tested)
- Apache Airflow >= 3.1.0 (3.2-ready)
- For DBT Operator: dbt-core in a virtual environment

### Optional Dependencies
- **Integration Testing**: `dbt-duckdb>=1.8.0`, `dag-factory>=0.18.0`
- **Dremio Support**: `dbt-dremio>=1.8.0`
- **Spark Support**: `dbt-spark>=1.8.0`

### Recommended Setup

- Use [uv](https://github.com/astral-sh/uv) for fast package management (10-100x faster than pip)
- Python 3.11 or 3.12 for optimal performance
- See [docs/UV_SETUP.md](docs/UV_SETUP.md) for uv installation and Python management

## License

MIT

## Support

For issues and questions, please open an issue on the repository.
