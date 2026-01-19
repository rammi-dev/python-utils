"""Tests for dbt exception hierarchy and classification."""

from dlh_airflow_common.exceptions import (
    DbtArtifactException,
    DbtCompilationException,
    DbtConnectionException,
    DbtException,
    DbtExecutionTimeoutException,
    DbtProfileException,
    DbtRuntimeException,
    classify_dbt_error,
)


class TestDbtExceptionHierarchy:
    """Test the dbt exception class hierarchy."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """All dbt exceptions should inherit from DbtException."""
        exceptions = [
            DbtCompilationException("test"),
            DbtRuntimeException("test"),
            DbtConnectionException("test"),
            DbtProfileException("test"),
            DbtArtifactException("test"),
            DbtExecutionTimeoutException("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, DbtException)

    def test_runtime_exception_retryable_flag(self) -> None:
        """DbtRuntimeException should support is_retryable flag."""
        retryable = DbtRuntimeException("test", is_retryable=True)
        not_retryable = DbtRuntimeException("test", is_retryable=False)

        assert retryable.is_retryable is True
        assert not_retryable.is_retryable is False

    def test_runtime_exception_node_id(self) -> None:
        """DbtRuntimeException should store node_id."""
        exc = DbtRuntimeException("test", node_id="model.my_project.my_model", is_retryable=False)

        assert exc.node_id == "model.my_project.my_model"

    def test_connection_exception_metadata(self) -> None:
        """DbtConnectionException should store connection metadata."""
        exc = DbtConnectionException("test", conn_id="my_conn", database_type="postgres")

        assert exc.conn_id == "my_conn"
        assert exc.database_type == "postgres"

    def test_profile_exception_metadata(self) -> None:
        """DbtProfileException should store profile metadata."""
        exc = DbtProfileException("test", conn_id="my_conn", profile_name="my_profile")

        assert exc.conn_id == "my_conn"
        assert exc.profile_name == "my_profile"

    def test_artifact_exception_metadata(self) -> None:
        """DbtArtifactException should store artifact metadata."""
        exc = DbtArtifactException(
            "test", artifact_path="/path/to/manifest.json", artifact_type="manifest"
        )

        assert exc.artifact_path == "/path/to/manifest.json"
        assert exc.artifact_type == "manifest"

    def test_timeout_exception_metadata(self) -> None:
        """DbtExecutionTimeoutException should store timeout metadata."""
        exc = DbtExecutionTimeoutException("test", timeout_seconds=3600, elapsed_seconds=3700.5)

        assert exc.timeout_seconds == 3600
        assert exc.elapsed_seconds == 3700.5


class TestClassifyDbtError:
    """Test the classify_dbt_error function."""

    def test_classify_connection_errors(self) -> None:
        """Connection-related errors should be classified as retryable."""
        test_cases = [
            RuntimeError("Connection timeout to database"),
            Exception("Network connection refused"),
            RuntimeError("Connection closed by server"),
            Exception("Broken pipe during connect"),
            RuntimeError("Connection reset by peer"),
        ]

        for exc in test_cases:
            exc_class, is_retryable = classify_dbt_error(exc)
            assert exc_class == DbtConnectionException
            assert is_retryable is True

    def test_classify_compilation_errors(self) -> None:
        """Compilation errors should be classified as non-retryable."""
        test_cases = [
            RuntimeError("Compilation error in model"),
            Exception("Syntax error in SQL"),
            RuntimeError("Jinja template error"),
            Exception("Could not find model in ref()"),
            RuntimeError("depends on a node named 'missing_model'"),
        ]

        for exc in test_cases:
            exc_class, is_retryable = classify_dbt_error(exc)
            assert exc_class == DbtCompilationException
            assert is_retryable is False

    def test_classify_profile_errors(self) -> None:
        """Profile errors should be classified as non-retryable."""
        test_cases = [
            RuntimeError("Invalid profile configuration"),
            Exception("profiles.yml not found"),
            RuntimeError("Target not found in profile"),
            Exception("Missing credentials in profile"),
        ]

        for exc in test_cases:
            exc_class, is_retryable = classify_dbt_error(exc)
            assert exc_class == DbtProfileException
            assert is_retryable is False

    def test_classify_timeout_errors(self) -> None:
        """Timeout errors should be classified as retryable."""
        test_cases = [
            RuntimeError("Query execution timeout"),
            Exception("Operation timed out after 60 seconds"),
            RuntimeError("Connection timed out"),
        ]

        for exc in test_cases:
            exc_class, is_retryable = classify_dbt_error(exc)
            assert exc_class in [DbtExecutionTimeoutException, DbtConnectionException]
            assert is_retryable is True

    def test_classify_generic_runtime_error(self) -> None:
        """Generic errors should default to non-retryable runtime exception."""
        exc = RuntimeError("Some random error")

        exc_class, is_retryable = classify_dbt_error(exc)

        assert exc_class == DbtRuntimeException
        assert is_retryable is False

    def test_classify_case_insensitive(self) -> None:
        """Error classification should be case-insensitive."""
        test_cases = [
            RuntimeError("CONNECTION TIMEOUT"),
            Exception("Compilation Error"),
            RuntimeError("PROFILE NOT FOUND"),
        ]

        expected_classes = [
            DbtConnectionException,
            DbtCompilationException,
            DbtProfileException,
        ]

        for exc, expected_class in zip(test_cases, expected_classes, strict=True):
            exc_class, _ = classify_dbt_error(exc)
            assert exc_class == expected_class
