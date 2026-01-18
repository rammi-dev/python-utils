# DBT Operator Setup Guide

This guide explains how to set up and use the DBT operator with virtual environments.

## Prerequisites

- Apache Airflow 3.1+
- Python 3.11 (recommended)
- dbt-core installed in a virtual environment
- Access to Airflow worker filesystem

## Python 3.11 Installation with uv

[uv](https://github.com/astral-sh/uv) can install and manage Python versions for you.

### Install uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if not already done)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

### Install Python 3.11 with uv

```bash
# Install Python 3.11 using uv
uv python install 3.11

# Verify installation
uv python list

# Check which Python 3.11 is available
uv python find 3.11
```

## Virtual Environment Setup

The DBT operator requires a pre-existing virtual environment with dbt installed on the Airflow worker.

### Option 1: Using uv with Python 3.11 (Recommended)

#### Create DBT Virtual Environment with Python 3.11

```bash
# Create a dedicated directory for virtual environments
sudo mkdir -p /opt/airflow/venvs
sudo chown airflow:airflow /opt/airflow/venvs

# Switch to airflow user
sudo -u airflow bash

# Create virtual environment with uv using Python 3.11
cd /opt/airflow/venvs
uv venv dbt-venv --python 3.11

# Activate the virtual environment
source dbt-venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.11.x

# Install dbt-core and adapters using uv
uv pip install dbt-core dbt-postgres dbt-snowflake dbt-bigquery

# Verify installation
dbt --version

# Deactivate
deactivate
```

#### Alternative: Specify Exact Python Path

```bash
# If you have Python 3.11 installed elsewhere
uv venv dbt-venv --python /usr/bin/python3.11

# Or use the python found by uv
uv venv dbt-venv --python $(uv python find 3.11)
```

### Option 2: Using Standard Python venv

```bash
# Create virtual environment
python -m venv /opt/airflow/venvs/dbt-venv

# Activate
source /opt/airflow/venvs/dbt-venv/bin/activate

# Install dbt
pip install dbt-core dbt-postgres

# Verify
dbt --version

# Deactivate
deactivate
```

## DBT Project Setup

### 1. Create DBT Project Structure

```bash
# Create project directory
sudo mkdir -p /opt/airflow/dbt/my_project
sudo chown -R airflow:airflow /opt/airflow/dbt

# Initialize dbt project
cd /opt/airflow/dbt
source /opt/airflow/venvs/dbt-venv/bin/activate
dbt init my_project
```

### 2. Configure profiles.yml

Create or update `~/.dbt/profiles.yml`:

```yaml
my_project:
  target: prod
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: dev_user
      pass: "{{ env_var('DBT_DEV_PASSWORD') }}"
      dbname: dev_db
      schema: dev_schema
      threads: 4

    prod:
      type: postgres
      host: prod-db.example.com
      port: 5432
      user: prod_user
      pass: "{{ env_var('DBT_PROD_PASSWORD') }}"
      dbname: prod_db
      schema: prod_schema
      threads: 8
```

### 3. Tag Your DBT Models

In your dbt models, add tags:

```sql
-- models/staging/stg_customers.sql
{{ config(
    tags=['daily', 'staging', 'core']
) }}

select * from {{ source('raw', 'customers') }}
```

```sql
-- models/marts/fct_orders.sql
{{ config(
    tags=['daily', 'core', 'incremental'],
    materialized='incremental',
    unique_key='order_id'
) }}

select * from {{ ref('stg_orders') }}
{% if is_incremental() %}
  where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

## Using DBT Operator in Airflow

### Basic Example

```python
from airflow import DAG
from dlh_airflow_common.operators.dbt import DbtOperator
from datetime import datetime

with DAG(
    dag_id="dbt_daily_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",  # Run at 2 AM daily
    catchup=False,
    tags=["dbt", "daily"],
) as dag:

    dbt_run = DbtOperator(
        task_id="dbt_run_daily_models",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["daily"],
        target="prod",
    )

    dbt_test = DbtOperator(
        task_id="dbt_test_daily_models",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="test",
        dbt_tags=["daily"],
        fail_fast=True,
        target="prod",
    )

    dbt_run >> dbt_test
```

### Advanced Example with Multiple Tags

```python
from airflow import DAG
from dlh_airflow_common.operators.dbt import DbtOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime

with DAG(
    dag_id="dbt_advanced_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:

    start = EmptyOperator(task_id="start")

    # Run staging models first
    dbt_run_staging = DbtOperator(
        task_id="dbt_run_staging",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["staging"],
        target="prod",
    )

    # Run core models
    dbt_run_core = DbtOperator(
        task_id="dbt_run_core",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["core"],
        exclude_tags=["heavy"],  # Exclude heavy models
        target="prod",
    )

    # Run incremental models with full refresh on Sundays
    dbt_run_incremental = DbtOperator(
        task_id="dbt_run_incremental",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="run",
        dbt_tags=["incremental"],
        full_refresh="{{ dag_run.logical_date.weekday() == 6 }}",  # Sunday
        target="prod",
    )

    # Test all models
    dbt_test_all = DbtOperator(
        task_id="dbt_test_all",
        venv_path="/opt/airflow/venvs/dbt-venv",
        dbt_project_dir="/opt/airflow/dbt/my_project",
        dbt_command="test",
        fail_fast=False,  # Run all tests
        target="prod",
    )

    end = EmptyOperator(task_id="end")

    start >> dbt_run_staging >> [dbt_run_core, dbt_run_incremental]
    [dbt_run_core, dbt_run_incremental] >> dbt_test_all >> end
```

### Using DBT Variables

```python
dbt_run_with_vars = DbtOperator(
    task_id="dbt_run_with_vars",
    venv_path="/opt/airflow/venvs/dbt-venv",
    dbt_project_dir="/opt/airflow/dbt/my_project",
    dbt_command="run",
    dbt_tags=["daily"],
    dbt_vars={
        "start_date": "{{ ds }}",
        "end_date": "{{ tomorrow_ds }}",
        "is_full_refresh": False,
    },
    target="prod",
)
```

### Using Custom Profiles Directory

```python
dbt_run_custom_profile = DbtOperator(
    task_id="dbt_run_custom",
    venv_path="/opt/airflow/venvs/dbt-venv",
    dbt_project_dir="/opt/airflow/dbt/my_project",
    dbt_command="run",
    dbt_tags=["daily"],
    profiles_dir="/opt/airflow/config/dbt/profiles",
    target="prod",
)
```

## Environment Variables

You can pass environment variables to the dbt process:

```python
dbt_run = DbtOperator(
    task_id="dbt_run",
    venv_path="/opt/airflow/venvs/dbt-venv",
    dbt_project_dir="/opt/airflow/dbt/my_project",
    dbt_command="run",
    env_vars={
        "DBT_PROD_PASSWORD": "{{ var.value.dbt_prod_password }}",
        "DBT_LOG_LEVEL": "info",
        "DBT_NO_PARTIAL_PARSE": "true",
    },
)
```

## Troubleshooting

### Virtual Environment Not Found

**Error:** `Virtual environment not found: /path/to/venv`

**Solution:**
1. Verify the path exists on the Airflow worker
2. Ensure the Airflow user has read/execute permissions
3. Check that the path is absolute, not relative

### DBT Executable Not Found

**Error:** `dbt executable not found in venv`

**Solution:**
```bash
source /opt/airflow/venvs/dbt-venv/bin/activate
which dbt
pip install dbt-core
```

### DBT Project Not Found

**Error:** `dbt_project.yml not found`

**Solution:**
1. Verify the dbt project directory path
2. Ensure `dbt_project.yml` exists in the directory
3. Check file permissions

### Connection Issues

**Error:** `Unable to connect to database`

**Solution:**
1. Verify `profiles.yml` configuration
2. Check environment variables for credentials
3. Test connection manually:
```bash
source /opt/airflow/venvs/dbt-venv/bin/activate
cd /opt/airflow/dbt/my_project
dbt debug
```

### Permission Denied

**Error:** `Permission denied: /opt/airflow/dbt/my_project`

**Solution:**
```bash
sudo chown -R airflow:airflow /opt/airflow/dbt
sudo chmod -R 755 /opt/airflow/dbt
```

## Performance Tips

### 1. Use Specific Model Selection

Instead of running all models, use tags or specific models:

```python
# Good - runs only necessary models
dbt_tags=["daily", "core"]

# Less efficient - runs all models
dbt_tags=[]
```

### 2. Enable Partial Parsing

In `dbt_project.yml`:
```yaml
flags:
  partial_parse: true
```

### 3. Adjust Thread Count

In `profiles.yml`:
```yaml
outputs:
  prod:
    threads: 8  # Adjust based on worker resources
```

### 4. Use Incremental Models

For large tables, use incremental materialization:
```sql
{{ config(
    materialized='incremental',
    unique_key='id'
) }}
```

## Best Practices

### 1. Organize Models with Tags

```sql
-- Staging models
{{ config(tags=['staging', 'hourly']) }}

-- Core business logic
{{ config(tags=['core', 'daily']) }}

-- Reports and aggregations
{{ config(tags=['reporting', 'weekly']) }}
```

### 2. Separate Run and Test Tasks

Always run tests after models:
```python
dbt_run >> dbt_test
```

### 3. Use Templating

Leverage Airflow's Jinja templating:
```python
dbt_vars={
    "execution_date": "{{ ds }}",
    "run_id": "{{ run_id }}",
}
```

### 4. Monitor Execution

Add logging and monitoring:
```python
from airflow.providers.slack.operators.slack import SlackAPIPostOperator

dbt_test = DbtOperator(...)

slack_alert = SlackAPIPostOperator(
    task_id="slack_alert",
    text="DBT tests completed successfully!",
    trigger_rule="all_success",
)

dbt_test >> slack_alert
```

### 5. Version Control

Store dbt projects in git and deploy via CI/CD:
```bash
# In your deployment script
cd /opt/airflow/dbt
git pull origin main
```

## Additional Resources

- [DAG Factory Usage](DAG_FACTORY_USAGE.md) - YAML-based DAG configuration
- [UV Setup Guide](UV_SETUP.md) - Fast Python package management
- [dbt Documentation](https://docs.getdbt.com/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [DBT Best Practices](https://docs.getdbt.com/guides/best-practices)
