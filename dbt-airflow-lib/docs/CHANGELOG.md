# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of dlh-airflow-common library
- **DbtOperator**: Operator for executing dbt commands in virtual environments
  - Support for `run`, `test`, `build`, `compile`, `seed`, `snapshot` commands
  - Tag-based and model-based filtering
  - Full refresh support
  - Custom target environment selection
  - Environment variable injection
- **BaseOperator**: Base class for custom operators with standardized logging
- **Logging Utilities**: `get_logger()` and `log_execution_time()` decorator
- **get_dag_description()**: Helper to embed library version in DAG descriptions
- **YAML DAG Validation**: Validation utilities for DAG Factory YAML configurations
  - `YamlDagValidator` class for customizable validation
  - `validate_yaml_file()` and `validate_yaml_directory()` convenience functions
  - CLI tool `validate-dags` for deployment-time validation
  - Validates YAML syntax, DAG structure, required fields, and task dependencies
- Comprehensive test suite with 100% coverage
- GitLab CI/CD pipeline with Python 3.11/3.12 matrix testing
- setuptools-scm for automatic versioning from git tags

### Requirements
- Python >= 3.10, < 3.14
- Apache Airflow >= 3.1.0, < 4.0.0
