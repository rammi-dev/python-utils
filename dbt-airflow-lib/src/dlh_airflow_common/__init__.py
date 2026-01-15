"""DLH Airflow Common Library.

This library provides common Airflow operators and utilities for data pipelines.
"""

try:
    from dlh_airflow_common._version import version as __version__
except ImportError:
    __version__ = "0.0.0.dev0"  # Fallback for editable installs without build

from dlh_airflow_common.operators.base import BaseOperator
from dlh_airflow_common.operators.dbt import DbtOperator

__all__ = ["BaseOperator", "DbtOperator", "__version__"]
