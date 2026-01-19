"""
Structured exception hierarchy for dbt operations.

This module provides a hierarchy of exceptions for dbt-related errors, enabling
targeted error handling and retry strategies based on error type.
"""

from airflow.exceptions import AirflowException


class DbtException(AirflowException):
    """
    Base exception for all dbt operations.

    All dbt-specific exceptions inherit from this class, allowing catch-all
    error handling when needed.
    """

    pass


class DbtCompilationException(DbtException):
    """
    Raised when dbt compilation fails.

    Compilation failures are typically caused by:
    - Syntax errors in SQL or YAML
    - Missing model references (ref() to non-existent model)
    - Invalid Jinja templating
    - Schema validation failures

    These errors are NOT retryable and require user intervention to fix.
    """

    pass


class DbtRuntimeException(DbtException):
    """
    Raised when dbt model execution fails.

    Runtime failures can be caused by:
    - Query execution errors (syntax, permissions, resources)
    - Data quality issues (constraints, type mismatches)
    - Timeout errors during query execution

    Some runtime errors may be retryable (timeouts, temp resource exhaustion),
    while others are permanent (syntax errors, permission issues).
    """

    def __init__(
        self,
        message: str,
        node_id: str | None = None,
        is_retryable: bool = False,
    ):
        """
        Initialize runtime exception.

        Args:
            message: Error message describing the failure
            node_id: dbt node unique_id that failed (e.g., "model.my_project.my_model")
            is_retryable: Whether this error should trigger retry logic
        """
        super().__init__(message)
        self.node_id = node_id
        self.is_retryable = is_retryable


class DbtConnectionException(DbtException):
    """
    Raised when database connection fails.

    Connection failures are typically retryable and can be caused by:
    - Network timeouts or interruptions
    - Temporary database unavailability
    - Connection pool exhaustion
    - Authentication token expiration (if token refresh is supported)

    This exception is ALWAYS considered retryable.
    """

    def __init__(
        self,
        message: str,
        conn_id: str | None = None,
        database_type: str | None = None,
    ):
        """
        Initialize connection exception.

        Args:
            message: Error message describing the connection failure
            conn_id: Airflow connection ID that failed
            database_type: Database adapter type (postgres, dremio, spark, etc.)
        """
        super().__init__(message)
        self.conn_id = conn_id
        self.database_type = database_type


class DbtProfileException(DbtException):
    """
    Raised when profile configuration is invalid.

    Profile errors are typically caused by:
    - Missing required profile fields
    - Invalid profile structure
    - Unsupported database adapter type
    - Failed profile rendering

    These errors are NOT retryable and require configuration fixes.
    """

    def __init__(
        self,
        message: str,
        conn_id: str | None = None,
        profile_name: str | None = None,
    ):
        """
        Initialize profile exception.

        Args:
            message: Error message describing the profile issue
            conn_id: Airflow connection ID with invalid configuration
            profile_name: dbt profile name being used
        """
        super().__init__(message)
        self.conn_id = conn_id
        self.profile_name = profile_name


class DbtArtifactException(DbtException):
    """
    Raised when artifact loading or parsing fails.

    Artifact errors can be caused by:
    - Missing artifact files (manifest.json, run_results.json)
    - Corrupted JSON content
    - Incompatible dbt version (artifact schema changes)

    These errors may be retryable if the artifact is still being written.
    """

    def __init__(
        self,
        message: str,
        artifact_path: str | None = None,
        artifact_type: str | None = None,
    ):
        """
        Initialize artifact exception.

        Args:
            message: Error message describing the artifact issue
            artifact_path: Path to the artifact file
            artifact_type: Type of artifact (manifest, run_results, catalog, etc.)
        """
        super().__init__(message)
        self.artifact_path = artifact_path
        self.artifact_type = artifact_type


class DbtExecutionTimeoutException(DbtException):
    """
    Raised when dbt execution exceeds configured timeout.

    Timeout errors can be caused by:
    - Long-running queries exceeding limits
    - Hung database connections
    - Resource contention

    These errors may be retryable depending on the root cause.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: int | None = None,
        elapsed_seconds: float | None = None,
    ):
        """
        Initialize timeout exception.

        Args:
            message: Error message describing the timeout
            timeout_seconds: Configured timeout value
            elapsed_seconds: Actual elapsed time before timeout
        """
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


def classify_dbt_error(exception: Exception) -> tuple[type[DbtException], bool]:
    """
    Classify a generic exception into a specific dbt exception type.

    This helper function analyzes exception messages and types to determine:
    1. The most appropriate DbtException subclass
    2. Whether the error should trigger retry logic

    Args:
        exception: The exception to classify

    Returns:
        Tuple of (DbtException subclass, is_retryable)

    Example:
        >>> exc = RuntimeError("Connection timeout to database")
        >>> exc_class, retryable = classify_dbt_error(exc)
        >>> exc_class
        <class 'DbtConnectionException'>
        >>> retryable
        True
    """
    error_message = str(exception).lower()

    # Connection-related errors (always retryable)
    connection_keywords = [
        "connection",
        "network",
        "timeout",
        "timed out",
        "connection refused",
        "connection reset",
        "broken pipe",
        "connection closed",
        "connect",
    ]
    if any(keyword in error_message for keyword in connection_keywords):
        return DbtConnectionException, True

    # Compilation errors (never retryable)
    compilation_keywords = [
        "compilation",
        "compile error",
        "syntax error",
        "parsing error",
        "jinja",
        "undefined variable",
        "could not find model",
        "depends on a node named",
    ]
    if any(keyword in error_message for keyword in compilation_keywords):
        return DbtCompilationException, False

    # Profile errors (never retryable)
    profile_keywords = [
        "profile",
        "profiles.yml",
        "target not found",
        "invalid profile",
        "credentials",
    ]
    if any(keyword in error_message for keyword in profile_keywords):
        return DbtProfileException, False

    # Timeout errors (sometimes retryable)
    if "timeout" in error_message or "timed out" in error_message:
        return DbtExecutionTimeoutException, True

    # Default to runtime exception (not retryable by default)
    return DbtRuntimeException, False
