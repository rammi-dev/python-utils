"""
DBT profile adapters for converting Airflow Connections to dbt profile configurations.

This module provides adapters that convert Airflow Connection objects into dbt profile
target configurations, enabling centralized credential management through Airflow's
connection system.
"""

from abc import ABC, abstractmethod
from typing import Any

from airflow.sdk.definitions.connection import Connection


class DbtProfileAdapter(ABC):
    """
    Abstract base class for converting Airflow Connections to dbt profile targets.

    Subclasses should implement the `to_dbt_target` method to handle database-specific
    connection parameter mapping.
    """

    @abstractmethod
    def to_dbt_target(self, conn: Connection) -> dict[str, Any]:
        """
        Convert an Airflow Connection to a dbt target configuration dictionary.

        Args:
            conn: Airflow Connection object containing database credentials and config

        Returns:
            Dictionary representing a dbt profile target configuration

        Raises:
            ValueError: If required connection fields are missing
        """
        pass


class DremioProfileAdapter(DbtProfileAdapter):
    """
    Adapter for Dremio on-premises connections.

    Converts Airflow Dremio connections to dbt Dremio profile targets.
    Only supports Dremio Software (on-premises) deployments.

    Example Airflow Connection:
        conn_id: dbt_dremio
        conn_type: dremio
        host: dremio.example.com
        schema: my_catalog
        login: dbt_user
        password: ****
        port: 9047
        extra: {
            "use_ssl": true,
            "threads": 4
        }

    Resulting dbt target:
        {
            "type": "dremio",
            "software_host": "dremio.example.com",
            "port": 9047,
            "user": "dbt_user",
            "password": "****",
            "database": "my_catalog",
            "dremio_space": "my_catalog",
            "dremio_space_folder": null,
            "use_ssl": true,
            "threads": 4,
        }
    """

    def to_dbt_target(self, conn: Connection) -> dict[str, Any]:
        """Convert Dremio on-premises connection to dbt target."""
        if not conn.login:
            raise ValueError(f"Connection '{conn.conn_id}' missing required field: login (user)")

        # Parse extra fields
        extra = conn.extra_dejson if conn.extra_dejson else {}

        # Get software host (on-premises only)
        software_host = extra.get("software_host") or conn.host
        if not software_host:
            raise ValueError(
                f"Connection '{conn.conn_id}' missing required field: "
                "host or extra.software_host for Dremio on-premises"
            )

        # Build dbt target config for Dremio Software (on-premises)
        target: dict[str, Any] = {
            "type": "dremio",
            "user": conn.login,
            "password": conn.password or "",
            "threads": extra.get("threads", 4),
            "software_host": software_host,
            "port": conn.port or 9047,
        }

        # Add database/catalog configuration
        if conn.schema:
            target["database"] = conn.schema
            target["dremio_space"] = conn.schema

        # Add optional parameters
        if "dremio_space_folder" in extra:
            target["dremio_space_folder"] = extra["dremio_space_folder"]
        if "use_ssl" in extra:
            target["use_ssl"] = extra["use_ssl"]
        if "object_storage_source" in extra:
            target["object_storage_source"] = extra["object_storage_source"]
        if "object_storage_path" in extra:
            target["object_storage_path"] = extra["object_storage_path"]

        return target


class SparkProfileAdapter(DbtProfileAdapter):
    """
    Adapter for Spark connections.

    Converts Airflow Spark connections to dbt Spark profile targets.
    Supports Thrift and ODBC connection methods.

    Example Airflow Connection (Thrift):
        conn_id: dbt_spark
        conn_type: spark
        host: spark-cluster.example.com
        schema: my_database
        login: spark_user
        password: ****
        port: 10000
        extra: {
            "method": "thrift",
            "threads": 4
        }

    Resulting dbt target:
        {
            "type": "spark",
            "method": "thrift",
            "host": "spark-cluster.example.com",
            "port": 10000,
            "user": "spark_user",
            "password": "****",
            "schema": "my_database",
            "threads": 4,
        }
    """

    def to_dbt_target(self, conn: Connection) -> dict[str, Any]:
        """Convert Spark connection to dbt target."""
        # Parse extra fields
        extra = conn.extra_dejson if conn.extra_dejson else {}

        # Determine connection method
        method = extra.get("method", "thrift")

        # Build base target config
        target: dict[str, Any] = {
            "type": "spark",
            "method": method,
            "threads": extra.get("threads", 4),
        }

        # Add schema if provided
        if conn.schema:
            target["schema"] = conn.schema

        # Method-specific configuration
        if method == "thrift":
            if not conn.host:
                raise ValueError(
                    f"Connection '{conn.conn_id}' missing required field: host "
                    "(for thrift method)"
                )
            target["host"] = conn.host
            target["port"] = conn.port or 10000

            # Add authentication if provided
            if conn.login:
                target["user"] = conn.login
            if conn.password:
                target["password"] = conn.password

        elif method == "odbc":
            # ODBC configuration
            if "driver" in extra:
                target["driver"] = extra["driver"]
            if "dsn" in extra:
                target["dsn"] = extra["dsn"]
            if conn.host:
                target["host"] = conn.host
            if conn.port:
                target["port"] = conn.port
        else:
            raise ValueError(
                f"Connection '{conn.conn_id}' has unsupported method '{method}'. "
                "Supported methods: thrift, odbc"
            )

        # Add optional parameters
        if "connect_retries" in extra:
            target["connect_retries"] = extra["connect_retries"]
        if "connect_timeout" in extra:
            target["connect_timeout"] = extra["connect_timeout"]
        if "retry_all" in extra:
            target["retry_all"] = extra["retry_all"]

        return target


def get_profile_adapter(conn_type: str) -> DbtProfileAdapter:
    """
    Factory function to get the appropriate profile adapter for a connection type.

    Args:
        conn_type: Airflow connection type (e.g., 'postgres', 'snowflake')

    Returns:
        DbtProfileAdapter instance for the connection type

    Raises:
        ValueError: If the connection type is not supported

    Example:
        >>> adapter = get_profile_adapter("postgres")
        >>> conn = BaseHook.get_connection("my_postgres_conn")
        >>> target = adapter.to_dbt_target(conn)
    """
    adapters: dict[str, type[DbtProfileAdapter]] = {
        "dremio": DremioProfileAdapter,
        "spark": SparkProfileAdapter,
    }

    adapter_class = adapters.get(conn_type)
    if not adapter_class:
        supported = ", ".join(adapters.keys())
        raise ValueError(
            f"Unsupported connection type '{conn_type}'. " f"Supported types: {supported}"
        )

    return adapter_class()
