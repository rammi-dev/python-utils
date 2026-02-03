"""Dummy DAG for testing and demonstration."""

from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator

from common.utils import generate_dag_id, get_default_args

# Use common utilities
dag_id = generate_dag_id("example", "dummy")
default_args = get_default_args(owner="test-team")

with DAG(
    dag_id=dag_id,
    default_args=default_args,
    description="A dummy DAG for testing",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["example", "test"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    start >> end
