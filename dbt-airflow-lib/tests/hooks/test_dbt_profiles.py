"""Tests for dbt profile adapters."""

import pytest
from airflow.sdk.definitions.connection import Connection

from dlh_airflow_common.hooks.dbt_profiles import (
    DremioProfileAdapter,
    SparkProfileAdapter,
    get_profile_adapter,
)


class TestDremioProfileAdapter:
    """Tests for DremioProfileAdapter."""

    def test_basic_dremio_software_conversion(self) -> None:
        """Test basic Dremio software connection conversion."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
            login="dbt_user",
            password="secret",
            port=9047,
            extra='{"use_ssl": true, "threads": 4}',
        )

        adapter = DremioProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["type"] == "dremio"
        assert target["software_host"] == "dremio.example.com"
        assert target["port"] == 9047
        assert target["user"] == "dbt_user"
        assert target["password"] == "secret"
        assert target["database"] == "my_catalog"
        assert target["dremio_space"] == "my_catalog"
        assert target["use_ssl"] is True
        assert target["threads"] == 4

    def test_dremio_with_space_folder(self) -> None:
        """Test Dremio connection with space folder."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
            login="dbt_user",
            password="secret",
            extra='{"dremio_space_folder": "my_folder"}',
        )

        adapter = DremioProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["dremio_space_folder"] == "my_folder"

    def test_dremio_missing_user(self) -> None:
        """Test Dremio connection missing required user."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
        )

        adapter = DremioProfileAdapter()
        with pytest.raises(ValueError, match="missing required field: login"):
            adapter.to_dbt_target(conn)

    def test_dremio_missing_host(self) -> None:
        """Test Dremio software connection missing required host."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            login="dbt_user",
            password="secret",
        )

        adapter = DremioProfileAdapter()
        with pytest.raises(ValueError, match="missing required field"):
            adapter.to_dbt_target(conn)

    def test_dremio_with_object_storage(self) -> None:
        """Test Dremio connection with object storage configuration."""
        conn = Connection(
            conn_id="test_dremio",
            conn_type="dremio",
            host="dremio.example.com",
            schema="my_catalog",
            login="dbt_user",
            password="secret",
            extra='{"object_storage_source": "s3", "object_storage_path": "s3://bucket/path"}',
        )

        adapter = DremioProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["object_storage_source"] == "s3"
        assert target["object_storage_path"] == "s3://bucket/path"


class TestSparkProfileAdapter:
    """Tests for SparkProfileAdapter."""

    def test_spark_thrift_conversion(self) -> None:
        """Test Spark thrift connection conversion."""
        conn = Connection(
            conn_id="test_spark",
            conn_type="spark",
            host="spark-master.example.com",
            schema="my_database",
            login="spark_user",
            password="secret",
            port=10000,
            extra='{"method": "thrift", "threads": 4}',
        )

        adapter = SparkProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["type"] == "spark"
        assert target["method"] == "thrift"
        assert target["host"] == "spark-master.example.com"
        assert target["port"] == 10000
        assert target["user"] == "spark_user"
        assert target["password"] == "secret"
        assert target["schema"] == "my_database"
        assert target["threads"] == 4

    def test_spark_odbc_conversion(self) -> None:
        """Test Spark ODBC connection conversion."""
        conn = Connection(
            conn_id="test_spark_odbc",
            conn_type="spark",
            schema="my_database",
            extra='{"method": "odbc", "driver": "/path/to/driver.so", ' '"dsn": "my_dsn"}',
        )

        adapter = SparkProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["type"] == "spark"
        assert target["method"] == "odbc"
        assert target["driver"] == "/path/to/driver.so"
        assert target["dsn"] == "my_dsn"

    def test_spark_odbc_with_host_port(self) -> None:
        """Test Spark ODBC connection with host and port."""
        conn = Connection(
            conn_id="test_spark_odbc",
            conn_type="spark",
            host="spark-odbc.example.com",
            port=10001,
            schema="my_database",
            extra='{"method": "odbc", "driver": "/path/to/driver.so", ' '"dsn": "my_dsn"}',
        )

        adapter = SparkProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["type"] == "spark"
        assert target["method"] == "odbc"
        assert target["host"] == "spark-odbc.example.com"
        assert target["port"] == 10001
        assert target["driver"] == "/path/to/driver.so"
        assert target["dsn"] == "my_dsn"

    def test_spark_default_method(self) -> None:
        """Test Spark connection with default method."""
        conn = Connection(
            conn_id="test_spark",
            conn_type="spark",
            host="spark-master.example.com",
            schema="my_database",
        )

        adapter = SparkProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["method"] == "thrift"

    def test_spark_thrift_missing_host(self) -> None:
        """Test Spark thrift connection missing required host."""
        conn = Connection(
            conn_id="test_spark",
            conn_type="spark",
            schema="my_database",
            extra='{"method": "thrift"}',
        )

        adapter = SparkProfileAdapter()
        with pytest.raises(ValueError, match="missing required field: host"):
            adapter.to_dbt_target(conn)

    def test_spark_with_retry_config(self) -> None:
        """Test Spark connection with retry configuration."""
        conn = Connection(
            conn_id="test_spark",
            conn_type="spark",
            host="spark-master.example.com",
            schema="my_database",
            extra='{"connect_retries": 3, "connect_timeout": 30, "retry_all": true}',
        )

        adapter = SparkProfileAdapter()
        target = adapter.to_dbt_target(conn)

        assert target["connect_retries"] == 3
        assert target["connect_timeout"] == 30
        assert target["retry_all"] is True

    def test_spark_unsupported_method(self) -> None:
        """Test Spark connection with unsupported method."""
        conn = Connection(
            conn_id="test_spark",
            conn_type="spark",
            host="spark-master.example.com",
            schema="my_database",
            extra='{"method": "http"}',
        )

        adapter = SparkProfileAdapter()
        with pytest.raises(ValueError, match="unsupported method 'http'"):
            adapter.to_dbt_target(conn)


class TestGetProfileAdapter:
    """Tests for get_profile_adapter factory function."""

    def test_get_dremio_adapter(self) -> None:
        """Test getting Dremio adapter."""
        adapter = get_profile_adapter("dremio")
        assert isinstance(adapter, DremioProfileAdapter)

    def test_get_spark_adapter(self) -> None:
        """Test getting Spark adapter."""
        adapter = get_profile_adapter("spark")
        assert isinstance(adapter, SparkProfileAdapter)

    def test_unsupported_connection_type(self) -> None:
        """Test getting adapter for unsupported connection type."""
        with pytest.raises(ValueError, match="Unsupported connection type"):
            get_profile_adapter("mysql")

    def test_error_message_lists_supported_types(self) -> None:
        """Test error message includes supported types."""
        with pytest.raises(ValueError, match="dremio, spark"):
            get_profile_adapter("unsupported")
