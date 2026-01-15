# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-15

### Added
- **DbtOperator**: New operator for executing dbt commands in virtual environments
  - Support for `dbt run` and `dbt test` commands
  - Tag-based model filtering with `dbt_tags` parameter
  - Specific model selection with `dbt_models` parameter
  - Tag exclusion with `exclude_tags` parameter
  - Full refresh support for incremental models
  - Fail-fast option for tests
  - Custom target environment selection
  - DBT variables support via `dbt_vars` parameter
  - Custom profiles directory configuration
  - Environment variable injection
  - Comprehensive input validation
  - Detailed logging and error reporting

- **BaseOperator**: Base class for custom operators
  - Standardized logging with configurable levels
  - Pre and post execution hooks
  - Type-safe implementation

- **Logging Utilities**:
  - `get_logger()`: Factory function for configured loggers
  - `log_execution_time()`: Decorator for execution time tracking

- **Development Tools**:
  - pytest configuration with coverage reporting
  - ruff for fast linting
  - black for code formatting
  - mypy for type checking
  - tox for multi-environment testing (Python 3.8-3.12)

- **Documentation**:
  - Comprehensive README with examples
  - DBT_SETUP.md with detailed setup instructions
  - QUICKSTART.md for fast onboarding
  - DEPLOYMENT.md for Nexus PyPI deployment
  - PROJECT_SUMMARY.md for project overview

- **Testing**:
  - Full test suite for BaseOperator
  - Comprehensive tests for DbtOperator (60+ test cases)
  - Mock-based testing for Airflow dependencies
  - Test coverage reporting

- **Build and Deployment**:
  - GitLab CI/CD pipeline configuration
  - Makefile with convenience commands
  - tox environments for quality checks
  - Nexus PyPI deployment support

- **uv Support**:
  - Documentation for uv-based virtual environments
  - Fast package installation and resolution
  - Recommended setup instructions

### Changed
- Updated to Apache Airflow 3.1+ compatibility
- Modern Python packaging with pyproject.toml
- Source layout with `src/` directory structure

### Technical Details

#### DbtOperator Features
- **Virtual Environment Isolation**: Execute dbt in pre-existing virtual environments
- **Validation**: Comprehensive validation of venv, dbt executable, and project structure
- **Command Building**: Smart command construction based on parameters
- **Error Handling**: Detailed error messages and logging
- **Template Fields**: Airflow templating support for dynamic values
- **Subprocess Management**: Safe subprocess execution with proper error handling

#### Test Coverage
- DbtOperator: 60+ test cases covering:
  - Initialization with various parameter combinations
  - Input validation (venv, project, command)
  - Command building with all parameter types
  - Environment preparation
  - Successful execution scenarios
  - Failure handling and error reporting
  - Integration workflows

#### Code Quality
- Type hints throughout codebase
- Docstrings for all public APIs
- Linting rules: pycodestyle, pyflakes, isort, bugbear, comprehensions, pyupgrade
- Code formatting: Black with 100 char line length
- Type checking: Strict mypy configuration

### Requirements
- Python >= 3.8
- Apache Airflow >= 3.1.0
- dbt-core (in virtual environment)

### Migration Notes
This is the initial release. No migration required.

### Known Issues
None at this time.

### Contributors
- DLH Team

---

## Future Releases

### Planned for 0.2.0
- Support for additional dbt commands (snapshot, seed, docs)
- Retry logic and exponential backoff
- Metrics collection and monitoring hooks
- Connection pooling utilities
- Enhanced error recovery

### Under Consideration
- Cloud provider operators (AWS, GCP, Azure)
- Database operators with connection management
- Data quality validation operators
- Notification and alerting utilities
- Documentation site with Sphinx/MkDocs
