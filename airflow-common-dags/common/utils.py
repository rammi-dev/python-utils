"""Common utilities for DAGs."""

from datetime import timedelta
from typing import Any


def get_default_args(
    owner: str = "data-team",
    retries: int = 2,
    retry_delay_minutes: int = 5,
    email_on_failure: bool = False,
) -> dict[str, Any]:
    """
    Return standardized default_args for DAGs.

    Args:
        owner: DAG owner name
        retries: Number of retries on task failure
        retry_delay_minutes: Minutes between retries
        email_on_failure: Send email on task failure

    Returns:
        Dictionary of default arguments for DAG tasks
    """
    return {
        "owner": owner,
        "retries": retries,
        "retry_delay": timedelta(minutes=retry_delay_minutes),
        "email_on_failure": email_on_failure,
        "depends_on_past": False,
    }


def generate_dag_id(domain: str, name: str, environment: str = "prod") -> str:
    """
    Generate a standardized DAG ID.

    Args:
        domain: Business domain (e.g., "sales", "finance")
        name: DAG name
        environment: Environment name (default: "prod")

    Returns:
        Formatted DAG ID: "{domain}_{name}_{environment}"
    """
    # Sanitize inputs
    domain = domain.lower().strip().replace(" ", "_")
    name = name.lower().strip().replace(" ", "_")
    environment = environment.lower().strip()

    return f"{domain}_{name}_{environment}"
