# YAML DAG Validation

This module provides validation utilities for [DAG Factory](https://github.com/ajbosco/dag-factory) YAML configurations. Use it during deployment to catch configuration errors before they reach your Airflow environment.

## Installation

The validation module is included with `dlh-airflow-common`:

```bash
pip install dlh-airflow-common
```

## Quick Start

### Command Line (Recommended for CI/CD)

After installation, use the `validate-dags` command:

```bash
# Validate all YAML files in a directory (recursive)
validate-dags /path/to/dags/

# Validate a single file
validate-dags /path/to/dag.yaml

# Verbose output (show warnings)
validate-dags -v /path/to/dags/

# Strict mode (treat warnings as errors)
validate-dags --strict /path/to/dags/

# Non-recursive validation
validate-dags --no-recursive /path/to/dags/
```

### Python API

```python
from dlh_airflow_common.validation import (
    validate_yaml_file,
    validate_yaml_directory,
    YamlDagValidator,
)

# Validate a single file
result = validate_yaml_file("/path/to/dag.yaml")
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")

# Validate a directory
results = validate_yaml_directory("/path/to/dags/")
for result in results:
    if not result.is_valid:
        print(f"{result.file_path}: FAILED")
        for error in result.errors:
            print(f"  - {error}")
```

## Integration with CI/CD

### GitLab CI

Add a validation stage to your `.gitlab-ci.yml`:

```yaml
stages:
  - validate
  - deploy

validate:dags:
  stage: validate
  image: python:3.11
  script:
    - pip install dlh-airflow-common
    - validate-dags --strict dags/
  rules:
    - changes:
        - dags/**/*.yaml
        - dags/**/*.yml
```

### GitHub Actions

```yaml
name: Validate DAGs

on:
  push:
    paths:
      - 'dags/**/*.yaml'
      - 'dags/**/*.yml'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install dlh-airflow-common

      - name: Validate DAG configurations
        run: validate-dags --strict dags/
```

### Pre-commit Hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-dags
        name: Validate DAG YAML files
        entry: validate-dags --strict
        language: python
        additional_dependencies: ['dlh-airflow-common']
        files: ^dags/.*\.(yaml|yml)$
        pass_filenames: false
        args: ['dags/']
```

## What Gets Validated

### YAML Syntax
- Valid YAML structure
- Proper indentation
- Correct data types

### DAG Structure
- At least one DAG definition exists
- Required fields are present:
  - `default_args`
  - `schedule`

### Default Args
- Required fields:
  - `owner`
  - `start_date`

### Tasks
- Each task has an `operator` field
- Task dependencies reference existing tasks

## Example Valid Configuration

```yaml
my_etl_dag:
  default_args:
    owner: data-team
    start_date: "2024-01-01"
    retries: 3
    retry_delay_sec: 300

  schedule: "0 6 * * *"
  catchup: false
  tags:
    - etl
    - daily

  tasks:
    extract:
      operator: airflow.operators.python.PythonOperator
      python_callable_file: /opt/airflow/dags/scripts/extract.py
      python_callable_name: run_extract

    transform:
      operator: airflow.operators.python.PythonOperator
      python_callable_file: /opt/airflow/dags/scripts/transform.py
      python_callable_name: run_transform
      dependencies:
        - extract

    load:
      operator: airflow.operators.python.PythonOperator
      python_callable_file: /opt/airflow/dags/scripts/load.py
      python_callable_name: run_load
      dependencies:
        - transform
```

## Custom Validation

You can customize which fields are required:

```python
from dlh_airflow_common.validation import YamlDagValidator

# Create validator with custom requirements
validator = YamlDagValidator(
    required_dag_fields={"schedule", "tags"},  # Custom DAG fields
    required_default_args={"owner", "start_date", "retries"},  # Custom default_args
    required_task_fields={"operator", "python_callable_file"},  # Custom task fields
)

result = validator.validate_file("/path/to/dag.yaml")
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All validations passed |
| 1 | One or more validations failed |

In `--strict` mode, warnings also cause exit code 1.

## Troubleshooting

### Common Errors

**"No DAG configurations found"**
- Your YAML file might only contain a `default` key or be empty
- Ensure you have at least one DAG definition (any key other than `default`)

**"Missing required field 'schedule'"**
- Add `schedule` to your DAG configuration
- Example: `schedule: "@daily"` or `schedule: "0 0 * * *"`

**"Dependency 'task_x' references non-existent task"**
- Check spelling of task names in `dependencies` list
- Ensure the referenced task is defined in the same DAG

**"YAML syntax error"**
- Check indentation (use spaces, not tabs)
- Ensure quotes are balanced
- Validate using an online YAML validator if needed
