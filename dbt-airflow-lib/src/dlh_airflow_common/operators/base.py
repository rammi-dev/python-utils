"""Base operator re-export from Airflow SDK.

This module re-exports Airflow's BaseOperator for backwards compatibility.
Use self.log for logging (provided by Airflow's BaseOperator).
"""

from airflow.models import BaseOperator

__all__ = ["BaseOperator"]
