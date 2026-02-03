"""DAG loading tests - validates all DAGs can be loaded without errors."""

from airflow.models import DagBag


def test_no_import_errors(dagbag: DagBag) -> None:
    """All DAGs should load without import errors."""
    assert dagbag.import_errors == {}, f"Import errors: {dagbag.import_errors}"


def test_dags_have_tasks(dagbag: DagBag) -> None:
    """All DAGs should have at least one task."""
    for dag_id, dag in dagbag.dags.items():
        assert len(dag.tasks) > 0, f"DAG {dag_id} has no tasks"


def test_dummy_dag_exists(dagbag: DagBag) -> None:
    """Dummy DAG should exist and be valid."""
    # Use dagbag.dags dict instead of get_dag() which requires database
    assert "example_dummy_prod" in dagbag.dags, "Dummy DAG not found"
    dag = dagbag.dags["example_dummy_prod"]
    assert len(dag.tasks) == 2, f"Expected 2 tasks, got {len(dag.tasks)}"


def test_dummy_dag_task_dependencies(dagbag: DagBag) -> None:
    """Dummy DAG tasks should have correct dependencies."""
    dag = dagbag.dags["example_dummy_prod"]

    start_task = dag.get_task("start")
    end_task = dag.get_task("end")

    assert start_task is not None, "start task not found"
    assert end_task is not None, "end task not found"

    # Verify start -> end dependency
    assert end_task in start_task.downstream_list, "start should be upstream of end"
