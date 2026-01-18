# DLH Airflow Common - Project Summary

## Overview

**Project Name:** dlh-airflow-common
**Type:** Python Library
**Purpose:** Common Airflow operators and utilities for data pipelines
**Version:** 0.1.0

## Project Structure

```
dlh-airflow-common/
├── src/dlh_airflow_common/           # Main package source code
│   ├── __init__.py                   # Package initialization
│   ├── py.typed                      # PEP 561 type marker
│   ├── operators/                    # Custom Airflow operators
│   │   ├── base.py                   # Base operator
│   │   └── dbt.py                    # DBT operator
│   ├── hooks/                        # Airflow hooks
│   │   ├── dbt.py                    # DBT hook
│   │   └── dbt_profiles.py           # Profile adapters
│   ├── utils/                        # Utility functions
│   │   └── logging.py                # Logging utilities
│   └── validation/                   # YAML validation
│       ├── yaml_validator.py         # Validator class
│       └── cli.py                    # CLI tool
│
├── tests/                            # Test suite (154 tests, 99.65% coverage)
│   ├── operators/                    # Operator tests
│   ├── hooks/                        # Hook tests
│   ├── utils/                        # Utility tests
│   └── validation/                   # Validation tests
│
├── docs/                             # Documentation
│   ├── CHANGELOG.md
│   ├── DEPLOYMENT.md
│   ├── DBT_SETUP.md
│   ├── QUICKSTART.md
│   └── ...
│
├── pyproject.toml                    # Project configuration & dependencies
├── tox.ini                           # Tox multi-environment testing config
├── Makefile                          # Convenience commands
├── .gitlab-ci.yml                    # GitLab CI/CD pipeline
└── .python-version                   # Python 3.11
```

## Key Features

### 1. DbtOperator
- **Location:** `src/dlh_airflow_common/operators/dbt.py`
- Execute dbt commands in virtual environments
- Support for run, test, build, compile, seed, snapshot
- Tag-based and model-based filtering
- Airflow connection-based credential management

### 2. DbtHook
- **Location:** `src/dlh_airflow_common/hooks/dbt.py`
- Manages dbt execution environment
- Converts Airflow connections to dbt profiles
- Uses dbt Python API (dbtRunner)
- Supports multiple database adapters

### 3. YAML DAG Validation
- **Location:** `src/dlh_airflow_common/validation/`
- Validates dag-factory YAML configurations
- CLI tool: `validate-dags`
- Integration with CI/CD pipelines

### 4. Testing
- **Framework:** pytest
- **Coverage:** 99.65% (574/576 lines)
- **Tests:** 154 passing
- Comprehensive unit tests for all components

### 4. Code Quality
- **Linting:** ruff (modern, fast linter)
- **Formatting:** black (opinionated code formatter)
- **Type Checking:** mypy (static type checker)
- **Configuration:** All in [pyproject.toml](pyproject.toml)

### 5. Multi-Environment Testing
- **Tool:** tox
- **Environments:** Python 3.8, 3.9, 3.10, 3.11, 3.12
- **Commands:** lint, format, type-check, test, build
- **Configuration:** [tox.ini](tox.ini)

## Configuration Files

### pyproject.toml
Modern Python project configuration including:
- Build system (setuptools)
- Project metadata
- Dependencies (airflow, dev tools)
- Tool configurations (black, ruff, mypy, pytest, coverage)

### tox.ini
Multi-environment testing configuration:
- Python version matrix (3.8-3.12)
- Separate environments for lint, format, type-check, tests
- Build and coverage environments

### Makefile
Convenience commands for common operations:
- `make install` / `make install-dev`
- `make test` / `make lint` / `make format`
- `make build` / `make publish-nexus`
- `make all` - runs all quality checks

## Dependencies

### Core
- `apache-airflow>=3.1.0` - Airflow framework
- `dbt-core>=1.8.0` - dbt Python API
- `pyyaml` - YAML parsing

### Development
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage plugin
- `pytest-mock>=3.10.0` - Mocking plugin
- `ruff>=0.1.0` - Linting
- `black>=23.0.0` - Formatting
- `mypy>=1.0.0` - Type checking
- `tox>=4.0.0` - Multi-environment testing

## Deployment Strategy

### Target: Private Nexus PyPI Repository

**Deployment Methods:**
1. **Manual:** Using `twine` with `.pypirc` configuration
2. **CI/CD:** GitLab CI pipeline (included)
3. **Make:** `make publish-nexus` command

**Version Management:**
- Semantic versioning (SemVer)
- Version in `pyproject.toml` and `__init__.py`
- Git tags for releases

**CI/CD Pipeline:**
- **Test Stage:** lint, format, type-check, pytest
- **Build Stage:** Creates wheel and source distribution
- **Deploy Stage:** Uploads to Nexus on git tags

## Getting Started

### Quick Setup
```bash
# Clone and setup
git clone <repo-url>
cd dlh-airflow-common
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Verify setup
./verify_setup.sh

# Run tests
pytest

# Run all checks
make all
```

### Development Workflow
1. Create feature branch
2. Implement changes
3. Write/update tests
4. Run `make all` to verify quality
5. Commit and push
6. Create merge request

### Deployment Workflow
1. Update version in `pyproject.toml` and `__init__.py`
2. Commit changes
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. CI/CD automatically builds and deploys to Nexus

## Quality Standards

### Code Coverage
- Target: >80% coverage
- Reporting: HTML, XML, terminal
- Command: `pytest --cov`

### Linting Rules
- pycodestyle (E, W)
- pyflakes (F)
- isort (I)
- flake8-bugbear (B)
- flake8-comprehensions (C4)
- pyupgrade (UP)

### Type Checking
- Full type hints required
- Strict mypy configuration
- PEP 561 compliant (py.typed marker)

### Formatting
- Black formatter with 100 char line length
- Consistent code style
- Auto-fixable with `make format-fix`

## CI/CD Variables (GitLab)

Required environment variables:
- `NEXUS_REPOSITORY_URL` - Nexus PyPI repository URL
- `NEXUS_USERNAME` - Deployment username
- `NEXUS_PASSWORD` - Deployment password (protected, masked)

## Usage Example

```python
from dlh_airflow_common.operators.dbt import DbtOperator
from airflow import DAG
from datetime import datetime

with DAG("dbt_pipeline", start_date=datetime(2024, 1, 1), schedule="@daily") as dag:
    dbt_run = DbtOperator(
        task_id="dbt_run_daily",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        conn_id="dbt_postgres_prod",
        dbt_command="run",
        dbt_tags=["daily"],
        target="prod",
    )
```

## Future Enhancements

Potential additions:
- Integration tests with real dbt execution
- Additional database adapters (Snowflake, BigQuery)
- Performance optimization (profiles.yml caching)
- Enhanced monitoring and metrics
- Circuit breaker pattern for failing connections
- Documentation site (MkDocs)

## Documentation

- **[README.md](../README.md)** - Comprehensive project documentation
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed deployment instructions
- **[DBT_SETUP.md](DBT_SETUP.md)** - DBT operator setup guide
- **[DAG_FACTORY_USAGE.md](DAG_FACTORY_USAGE.md)** - dag-factory integration
- **Inline docs** - All code includes docstrings and type hints

## Support & Maintenance

- **Issues:** Report via repository issue tracker
- **Code Review:** Required for all changes
- **Testing:** All changes must include tests
- **Documentation:** Update docs with significant changes

## License

MIT License - See [LICENSE](LICENSE) file

## Contact

For questions or support, contact the DLH team or open an issue on the repository.

---

**Last Updated:** 2026-01-17
**Status:** Production-ready (99.65% test coverage)
**Python Support:** 3.10, 3.11 (recommended), 3.12, 3.13
**Python Development:** 3.11 (see `.python-version`)
**Airflow Support:** >=3.1.0, <4.0.0
**Package Manager:** uv (recommended) or pip
**Test Coverage:** 99.65% (574/576 lines covered)
