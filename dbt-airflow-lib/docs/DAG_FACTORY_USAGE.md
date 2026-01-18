# Using DbtOperator with dag-factory

This guide shows how to use `DbtOperator` with [dag-factory](https://github.com/astronomer/dag-factory) (Astronomer) for YAML-based DAG generation.

**Note**: For production deployment examples, see `tests/integration/fixtures/dag_factory/README.md`.

## Overview

The `DbtOperator` integrates seamlessly with dag-factory, allowing you to:
- Define dbt DAGs in YAML files
- Use Airflow Connections for centralized credential management
- Leverage Jinja2 templating for dynamic configurations
- Maintain environment-specific configurations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       dag-factory YAML                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ tasks:                                                     │  │
│  │   dbt_run:                                                 │  │
│  │     operator: DbtOperator                                  │  │
│  │     conn_id: "dbt_dremio_prod"  ← References connection   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Airflow Connections                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Connection ID: dbt_dremio_prod                            │  │
│  │ Type: generic (for Dremio)                                 │  │
│  │ Host: dremio.example.com                                   │  │
│  │ Credentials: (stored securely in Airflow)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DbtOperator                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Creates DbtHook with conn_id                              │  │
│  │         │                                                  │  │
│  │         ▼                                                  │  │
│  │   ┌──────────────────────────────────────────┐            │  │
│  │   │           DbtHook                         │            │  │
│  │   │  1. Load connection from Airflow         │            │  │
│  │   │  2. Convert to dbt profile (adapter)     │            │  │
│  │   │  3. Generate temp profiles.yml           │            │  │
│  │   │  4. Setup venv (sys.path)                │            │  │
│  │   │  5. Execute dbtRunner Python API         │            │  │
│  │   │  6. Return artifacts (manifest, results) │            │  │
│  │   └──────────────────────────────────────────┘            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      dbt-core (Python API)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ dbtRunner().invoke(["run", "--select", "tag:daily"])      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install the Library

```bash
pip install dlh-airflow-common[dremio,spark]  # Include your dbt adapters
```

### 2. Create Airflow Connections

#### Via Airflow CLI

```bash
# Dremio connection (on-premises)
airflow connections add dbt_dremio_prod \
    --conn-type generic \
    --conn-host dremio.example.com \
    --conn-schema my_catalog \
    --conn-login dbt_user \
    --conn-password <password> \
    --conn-port 9047 \
    --conn-extra '{"use_ssl": true, "threads": 4, "dremio_space_folder": "analytics"}'

# Spark/Databricks connection
airflow connections add dbt_databricks_prod \
    --conn-type spark \
    --conn-host dbc-abc123.cloud.databricks.com \
    --conn-schema default \
    --conn-login token \
    --conn-password <databricks-token> \
    --conn-port 443 \
    --conn-extra '{"method": "http", "organization": "my_org", "cluster": "my_cluster"}'
```

#### Via Airflow UI

1. Navigate to **Admin** → **Connections**
2. Click **+** to add a new connection
3. Fill in the details based on your database type (see examples below)

### 3. Create dag-factory YAML

```yaml
# dags/dbt_analytics.yml
dbt_analytics_pipeline:
  default_args:
    owner: 'data_team'
    start_date: '2024-01-01'
    retries: 2
    retry_delay_sec: 300

  schedule_interval: '0 2 * * *'  # 2 AM daily
  catchup: false

  tasks:
    dbt_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      dbt_command: 'run'
      conn_id: 'dbt_dremio_prod'  # Reference to Airflow Connection
      dbt_tags:
        - 'daily'
      target: 'prod'
      push_artifacts: true
```

### 4. Load DAGs with dag-factory

Create a loader script at `dags/load_dags.py`:

```python
# dags/load_dags.py
from dagfactory import load_yaml_dags
from pathlib import Path

# Load all YAML configs from dags directory
dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
```

**Important**:
- Use absolute paths (`.resolve()`) for `config_filepath`
- This is required by dag-factory for proper file resolution

## Connection Examples

### Dremio (On-premises)

**Airflow Connection**:
```yaml
Connection ID: dbt_dremio_prod
Connection Type: Generic
Host: dremio.example.com
Schema: my_catalog
Login: dbt_user
Password: ****
Port: 9047
Extra: {
  "use_ssl": true,
  "threads": 4,
  "dremio_space_folder": "analytics"
}
```

**How DbtHook Converts It**:
```python
# DbtHook uses DremioProfileAdapter to convert to:
{
    "type": "dremio",
    "software_host": "dremio.example.com",  # From conn.host
    "port": 9047,
    "user": "dbt_user",
    "password": "****",
    "database": "my_catalog",
    "dremio_space": "my_catalog",
    "dremio_space_folder": "analytics",
    "use_ssl": true,
    "threads": 4
}
```

**Generated profiles.yml** (temporary, created by DbtHook):
```yaml
analytics:  # From dbt_project.yml
  target: prod
  outputs:
    prod:
      type: dremio
      software_host: dremio.example.com
      port: 9047
      user: dbt_user
      password: ****
      database: my_catalog
      dremio_space: my_catalog
      dremio_space_folder: analytics
      use_ssl: true
      threads: 4
```

**Note**: Only Dremio on-premises (software) is currently supported. Dremio Cloud support has been removed.

### Spark (Thrift)

**Airflow Connection**:
```yaml
Connection ID: dbt_spark_prod
Connection Type: Spark
Host: spark-cluster.example.com
Schema: default
Login: spark_user
Password: ****
Port: 10000
Extra: {
  "method": "thrift",
  "threads": 4
}
```

**How DbtHook Converts It**:
```python
# DbtHook uses SparkProfileAdapter to convert to:
{
    "type": "spark",
    "method": "thrift",
    "host": "spark-cluster.example.com",
    "port": 10000,
    "user": "spark_user",
    "password": "****",
    "schema": "default",
    "threads": 4
}
```

### Spark (Databricks HTTP)

**Airflow Connection**:
```yaml
Connection ID: dbt_databricks_prod
Connection Type: Spark
Host: dbc-abc123.cloud.databricks.com
Schema: default
Login: token
Password: dapi1234567890abcdef  # Databricks token
Port: 443
Extra: {
  "method": "http",
  "organization": "my_org",
  "cluster": "my_cluster",
  "endpoint": "/sql/1.0/endpoints/abc123",
  "threads": 8
}
```

**How DbtHook Converts It**:
```python
# DbtHook uses SparkProfileAdapter to convert to:
{
    "type": "spark",
    "method": "http",
    "host": "dbc-abc123.cloud.databricks.com",
    "port": 443,
    "user": "token",
    "token": "dapi1234567890abcdef",  # password → token
    "schema": "default",
    "organization": "my_org",
    "cluster": "my_cluster",
    "endpoint": "/sql/1.0/endpoints/abc123",
    "threads": 8
}
```

## DbtHook Execution Flow

When `DbtOperator` executes, it creates a `DbtHook` which performs the following steps:

### Step 1: Environment Setup
```python
# DbtHook._setup_dbt_environment()
# Modifies sys.path to import dbt from the venv
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"  # e.g., "3.11" or "3.12"
sys.path.insert(0, f"{venv_path}/lib/python{python_version}/site-packages")
```

### Step 2: Load Connection & Generate Profile
```python
# DbtHook._load_profile_from_connection()
conn = BaseHook.get_connection(conn_id)  # Get from Airflow

# Get the appropriate adapter for the connection type
adapter = get_profile_adapter(conn.conn_type)  # e.g., PostgresProfileAdapter

# Convert to dbt target config
target_config = adapter.to_dbt_target(conn)
# Returns: {"type": "postgres", "host": "...", "user": "...", ...}
```

### Step 3: Create Temporary profiles.yml
```python
# DbtHook._get_or_create_profiles_yml()
# Read dbt_project.yml to get project name
with open(f"{dbt_project_dir}/dbt_project.yml") as f:
    project_name = yaml.safe_load(f)["name"]

# Create profiles.yml content
profiles_yml = {
    project_name: {
        "target": target_name,  # e.g., "prod"
        "outputs": {
            target_name: target_config  # From step 2
        }
    }
}

# Write to temporary directory
temp_dir = tempfile.TemporaryDirectory()
with open(f"{temp_dir.name}/profiles.yml", "w") as f:
    yaml.dump(profiles_yml, f)
```

### Step 4: Execute dbt via Python API
```python
# DbtHook.run_dbt_task()
from dbt.cli.main import dbtRunner

# Build command arguments
args = [
    "run",
    "--select", "tag:daily",
    "--target", "prod",
    "--profiles-dir", temp_profiles_dir,
    "--project-dir", dbt_project_dir,
]

# Execute
runner = dbtRunner()
result = runner.invoke(args)
```

### Step 5: Load Artifacts
```python
# DbtHook.get_manifest() and get_run_results()
manifest = json.load(open(f"{dbt_project_dir}/target/manifest.json"))
run_results = json.load(open(f"{dbt_project_dir}/target/run_results.json"))

return DbtTaskResult(
    success=result.success,
    command="run",
    manifest=manifest,
    run_results=run_results
)
```

### Step 6: Cleanup
```python
# DbtHook.__del__() or finally block
temp_profiles_dir.cleanup()  # Delete temporary profiles.yml
```

## Complete dag-factory Examples

### Example 1: Multi-Stage Pipeline

```yaml
# dags/dbt_multi_stage.yml
dbt_multi_stage_pipeline:
  default_args:
    owner: 'data_engineering'
    start_date: '2024-01-01'
    retries: 2

  schedule_interval: '0 2 * * *'
  catchup: false

  tasks:
    # Stage 1: Staging models
    dbt_staging:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'
      dbt_command: 'run'
      dbt_tags: ['staging']
      target: 'prod'

    # Stage 2: Intermediate models
    dbt_intermediate:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'
      dbt_command: 'run'
      dbt_tags: ['intermediate']
      target: 'prod'
      dependencies:
        - dbt_staging

    # Stage 3: Mart models
    dbt_marts:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'
      dbt_command: 'run'
      dbt_tags: ['marts']
      target: 'prod'
      full_refresh: false
      dependencies:
        - dbt_intermediate

    # Stage 4: Tests
    dbt_test:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'
      dbt_command: 'test'
      target: 'prod'
      fail_fast: false
      dependencies:
        - dbt_marts
```

### Example 2: Environment-Specific DAGs

```yaml
# dags/dbt_dev.yml
dbt_dev_pipeline:
  default_args:
    owner: 'data_team'
    start_date: '2024-01-01'

  schedule_interval: '@hourly'

  tasks:
    dbt_dev_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_dev'  # Dev connection
      dbt_command: 'run'
      target: 'dev'
      dbt_tags: ['daily']

# dags/dbt_prod.yml
dbt_prod_pipeline:
  default_args:
    owner: 'data_team'
    start_date: '2024-01-01'

  schedule_interval: '@daily'

  tasks:
    dbt_prod_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      conn_id: 'dbt_dremio_prod'  # Prod connection
      dbt_command: 'run'
      target: 'prod'
      dbt_tags: ['daily']
      full_refresh: false
```

### Example 3: With Jinja2 Templates

```yaml
# dags/dbt_templated.yml
dbt_templated_pipeline:
  default_args:
    owner: 'data_team'
    start_date: '2024-01-01'

  schedule_interval: '@daily'

  tasks:
    dbt_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: "{{ var.value.dbt_venv_path }}"
      dbt_project_dir: "{{ var.value.dbt_project_dir }}"
      conn_id: "{{ var.value.dbt_conn_id }}"
      target: "{{ var.value.env }}"
      dbt_vars:
        run_date: "{{ ds }}"
        env: "{{ var.value.env }}"
        year: "{{ execution_date.year }}"
        month: "{{ execution_date.month }}"
```

Set variables:
```bash
airflow variables set dbt_conn_id "dbt_dremio_prod"
airflow variables set env "prod"
airflow variables set dbt_venv_path "/opt/airflow/venvs/dbt-venv"
airflow variables set dbt_project_dir "/opt/airflow/dbt/analytics"
```

## Backward Compatibility (profiles_dir)

You can still use `profiles_dir` instead of `conn_id`:

```yaml
# dags/dbt_old_way.yml
dbt_legacy_pipeline:
  tasks:
    dbt_run:
      operator: dlh_airflow_common.operators.dbt.DbtOperator
      venv_path: '/opt/airflow/venvs/dbt-venv'
      dbt_project_dir: '/opt/airflow/dbt/analytics'
      profiles_dir: '/opt/airflow/dbt/profiles'  # Old way - still works!
      target: 'dev'
      dbt_command: 'run'
```

## Supported Connection Types

| Connection Type | Adapter Class | Notes |
|----------------|---------------|-------|
| `postgres` | `PostgresProfileAdapter` | Postgres databases |
| `redshift` | `PostgresProfileAdapter` | Uses Postgres adapter |
| `dremio` | `DremioProfileAdapter` | Dremio on-premises only |
| `generic` | `DremioProfileAdapter` | Fallback for Dremio |
| `spark` | `SparkProfileAdapter` | Spark/Databricks |

## Benefits

1. **No Hardcoded Credentials**: Secrets stored in Airflow, not in YAML files
2. **Environment Separation**: One YAML, different `conn_id` per environment
3. **Version Control Safe**: YAML files can be committed without secrets
4. **Centralized Management**: Manage connections via Airflow UI
5. **Reusability**: One connection used by multiple DAGs
6. **Templating**: Use Airflow Variables for dynamic configuration

## Troubleshooting

### Connection not found
```
Error: Connection 'dbt_dremio_prod' not found
```
**Solution**: Create the connection in Airflow:
```bash
airflow connections list  # Check existing connections
airflow connections add dbt_dremio_prod ...
```

### Missing venv
```
Error: Virtual environment not found at: /opt/airflow/venvs/dbt-venv
```
**Solution**: Create the venv and install dbt:
```bash
python -m venv /opt/airflow/venvs/dbt-venv
source /opt/airflow/venvs/dbt-venv/bin/activate
pip install dbt-core dbt-dremio  # or dbt-spark for Databricks
```

### Missing dbt_project.yml
```
Error: dbt_project.yml not found at: /opt/airflow/dbt/analytics/dbt_project.yml
```
**Solution**: Ensure your dbt project is in the correct location and initialized.

## Testing

For integration tests showing dag-factory + DbtOperator in action:
```bash
# Install integration dependencies
uv pip install -e ".[integration]"

# Run dag-factory integration tests
pytest -m integration tests/integration/test_dag_factory_integration.py -v
```

These tests use Airflow's DagBag to verify DAGs load correctly from YAML configs.

## Additional Resources

- [dag-factory Documentation](https://github.com/astronomer/dag-factory) (Astronomer)
- [Airflow 3.1 Connections](https://airflow.apache.org/docs/apache-airflow/3.1.0/howto/connection.html)
- [dbt Documentation](https://docs.getdbt.com/)
- [Production Deployment Guide](tests/integration/fixtures/dag_factory/README.md)
