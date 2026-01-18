# DAG Factory Test Fixtures

YAML configuration files for testing `DbtOperator` integration with [dag-factory](https://www.astronomer.io/docs/learn/dag-factory).

## Files

### `dbt_simple_dag.yml`
Single-task DAG demonstrating basic `dbt run` execution with Airflow Variables.

### `dbt_full_workflow.yml`
Complete dbt workflow: `seed → run → test` with task dependencies and selective artifact pushing.

### `dbt_with_connection.yml`
Connection-based configuration using Airflow Connections instead of `profiles_dir`.

## Production Usage

### 1. Copy YAML to DAGs directory
```bash
cp dbt_simple_dag.yml /opt/airflow/dags/
```

### 2. Set Airflow Variables
```bash
airflow variables set venv_path /opt/airflow/venvs/dbt-venv
airflow variables set dbt_project_dir /opt/airflow/dbt/my_project
airflow variables set profiles_dir /opt/airflow/dbt/profiles
```

### 3. Create dag-factory loader
`/opt/airflow/dags/load_dags.py`:
```python
from dagfactory import load_yaml_dags
from pathlib import Path

dag_dir = Path(__file__).parent.resolve()
for yaml_file in dag_dir.glob("*.yml"):
    load_yaml_dags(globals(), config_filepath=str(yaml_file.resolve()))
```

**Important**: Use absolute paths (`.resolve()`) for `config_filepath`.

## Testing

```bash
make test-integration
# or
pytest -m integration tests/integration/test_dag_factory_integration.py
```

## References

- [dag-factory Documentation](https://www.astronomer.io/docs/learn/dag-factory)
- [dag-factory GitHub](https://github.com/astronomer/dag-factory)
