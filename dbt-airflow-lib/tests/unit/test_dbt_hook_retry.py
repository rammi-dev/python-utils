"""Tests for dbt hook retry logic and structured logging."""

from unittest.mock import Mock, patch

import pytest

from dlh_airflow_common.exceptions import (
    DbtCompilationException,
    DbtConnectionException,
    DbtRuntimeException,
)
from dlh_airflow_common.hooks.dbt import DbtHook


class TestDbtHookRetryLogic:
    """Test retry logic in DbtHook."""

    @pytest.fixture
    def mock_hook(self) -> DbtHook:
        """Create a DbtHook instance for testing."""
        return DbtHook(
            venv_path="/fake/venv",
            dbt_project_dir="/fake/project",
            conn_id="fake_conn",
            retry_limit=3,
            retry_delay=1,
        )

    def test_is_retryable_error_connection_exception(self, mock_hook: DbtHook) -> None:
        """Connection exceptions should be retryable."""
        exc = DbtConnectionException("Connection timeout")

        assert mock_hook._is_retryable_error(exc) is True

    def test_is_retryable_error_compilation_exception(self, mock_hook: DbtHook) -> None:
        """Compilation exceptions should not be retryable."""
        exc = DbtCompilationException("Syntax error")

        assert mock_hook._is_retryable_error(exc) is False

    def test_is_retryable_error_runtime_exception_retryable(self, mock_hook: DbtHook) -> None:
        """Runtime exceptions with is_retryable=True should be retryable."""
        exc = DbtRuntimeException("Timeout error", is_retryable=True)

        assert mock_hook._is_retryable_error(exc) is True

    def test_is_retryable_error_runtime_exception_not_retryable(self, mock_hook: DbtHook) -> None:
        """Runtime exceptions with is_retryable=False should not be retryable."""
        exc = DbtRuntimeException("Permission denied", is_retryable=False)

        assert mock_hook._is_retryable_error(exc) is False

    def test_is_retryable_error_generic_exception(self, mock_hook: DbtHook) -> None:
        """Generic exceptions should be classified using classify_dbt_error."""
        # Connection-like error should be retryable
        connection_exc = RuntimeError("Connection timeout")
        assert mock_hook._is_retryable_error(connection_exc) is True

        # Generic error should not be retryable
        generic_exc = RuntimeError("Some error")
        assert mock_hook._is_retryable_error(generic_exc) is False

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_retry_attempt(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Retry attempts should be logged with details."""
        # Create a mock retry state
        mock_state = Mock()
        mock_state.attempt_number = 2
        mock_outcome = Mock()
        mock_outcome.exception.return_value = RuntimeError("Connection timeout")
        mock_state.outcome = mock_outcome
        mock_state.next_action = Mock(sleep=2.0)

        mock_hook._log_retry_attempt(mock_state)

        # Verify logging calls
        assert mock_logger.warning.called
        assert mock_logger.info.called
        assert "attempt 2" in str(mock_logger.warning.call_args)


class TestDbtHookStructuredLogging:
    """Test structured node-level logging."""

    @pytest.fixture
    def mock_hook(self) -> DbtHook:
        """Create a DbtHook instance for testing."""
        return DbtHook(
            venv_path="/fake/venv",
            dbt_project_dir="/fake/project",
            conn_id="fake_conn",
        )

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_node_results_success(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Successful runs should log summary statistics."""
        run_results = {
            "results": [
                {
                    "unique_id": "model.project.model1",
                    "status": "success",
                    "execution_time": 1.5,
                },
                {
                    "unique_id": "model.project.model2",
                    "status": "success",
                    "execution_time": 2.3,
                },
            ]
        }

        mock_hook._log_node_results(run_results)

        # Verify summary logging
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Total nodes: 2" in call for call in info_calls)
        assert any("Total time:" in call for call in info_calls)
        assert any("success: 2" in call for call in info_calls)

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_node_results_with_failures(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Failed nodes should be logged with error details."""
        run_results = {
            "results": [
                {
                    "unique_id": "model.project.model1",
                    "status": "success",
                    "execution_time": 1.5,
                },
                {
                    "unique_id": "model.project.model2",
                    "status": "error",
                    "execution_time": 0.5,
                    "message": "Database connection failed",
                },
            ]
        }

        mock_hook._log_node_results(run_results)

        # Verify error logging
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("1 node(s) failed" in call for call in error_calls)
        assert any("model.project.model2" in call for call in error_calls)
        assert any("Database connection failed" in call for call in error_calls)

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_node_results_with_warnings(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Warned nodes should be logged."""
        run_results = {
            "results": [
                {
                    "unique_id": "model.project.model1",
                    "status": "success",
                    "execution_time": 1.5,
                },
                {
                    "unique_id": "model.project.model2",
                    "status": "warn",
                    "execution_time": 2.0,
                    "message": "Query returned no rows",
                },
            ]
        }

        mock_hook._log_node_results(run_results)

        # Verify warning logging
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("1 node(s) with warnings" in call for call in warning_calls)
        assert any("model.project.model2" in call for call in warning_calls)

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_node_results_slowest_nodes(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Slowest nodes should be highlighted."""
        run_results = {
            "results": [
                {
                    "unique_id": "model.project.fast",
                    "status": "success",
                    "execution_time": 0.5,
                },
                {
                    "unique_id": "model.project.slow",
                    "status": "success",
                    "execution_time": 10.0,
                },
                {
                    "unique_id": "model.project.medium",
                    "status": "success",
                    "execution_time": 5.0,
                },
            ]
        }

        mock_hook._log_node_results(run_results)

        # Verify slowest nodes are logged
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Slowest nodes" in call for call in info_calls)
        assert any("slow" in call for call in info_calls)

    @patch("dlh_airflow_common.hooks.dbt.logger")
    def test_log_node_results_empty(self, mock_logger: Mock, mock_hook: DbtHook) -> None:
        """Empty results should log appropriate message."""
        run_results = {"results": []}

        mock_hook._log_node_results(run_results)

        # Verify empty results message
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("No node results to log" in call for call in info_calls)


class TestDbtHookRetryIntegration:
    """Integration tests for retry logic with actual execution."""

    @pytest.fixture
    def mock_hook(self) -> DbtHook:
        """Create a DbtHook instance for testing."""
        return DbtHook(
            venv_path="/fake/venv",
            dbt_project_dir="/fake/project",
            conn_id="fake_conn",
            retry_limit=3,
            retry_delay=0.1,  # Short delay for tests
        )

    @patch("dlh_airflow_common.hooks.dbt.DbtHook._setup_dbt_environment")
    @patch("dlh_airflow_common.hooks.dbt.DbtHook._get_or_create_profiles_yml")
    def test_retry_on_connection_error(
        self,
        mock_profiles: Mock,
        mock_setup: Mock,
        mock_hook: DbtHook,
    ) -> None:
        """Connection errors should trigger retry logic."""
        mock_profiles.return_value = "/fake/profiles"

        # Mock dbtRunner to fail twice then succeed
        call_count = 0

        def mock_invoke(args: list[str]) -> Mock:
            nonlocal call_count
            call_count += 1

            result = Mock()
            if call_count < 3:
                # First two attempts fail with connection error
                result.success = False
                result.exception = RuntimeError("Connection timeout to database")
            else:
                # Third attempt succeeds
                result.success = True
                result.exception = None

            return result

        # Patch dbtRunner in the function where it's imported
        with patch("dbt.cli.main.dbtRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.invoke = mock_invoke
            mock_runner_class.return_value = mock_runner

            with patch("dlh_airflow_common.hooks.dbt.DbtHook.get_run_results"):
                with patch("dlh_airflow_common.hooks.dbt.DbtHook.get_manifest"):
                    # Should succeed after retries
                    result = mock_hook.run_dbt_task("run")

                    assert result.success is True
                    assert call_count == 3  # Failed twice, succeeded on third

    @patch("dlh_airflow_common.hooks.dbt.DbtHook._setup_dbt_environment")
    @patch("dlh_airflow_common.hooks.dbt.DbtHook._get_or_create_profiles_yml")
    def test_no_retry_on_compilation_error(
        self,
        mock_profiles: Mock,
        mock_setup: Mock,
        mock_hook: DbtHook,
    ) -> None:
        """Compilation errors should fail immediately without retry."""
        mock_profiles.return_value = "/fake/profiles"

        call_count = 0

        def mock_invoke(args: list[str]) -> Mock:
            nonlocal call_count
            call_count += 1

            result = Mock()
            result.success = False
            result.exception = RuntimeError("Compilation error in model")
            return result

        # Patch dbtRunner in the function where it's imported
        with patch("dbt.cli.main.dbtRunner") as mock_runner_class:
            mock_runner = Mock()
            mock_runner.invoke = mock_invoke
            mock_runner_class.return_value = mock_runner

            # Should raise DbtCompilationException without retrying
            with pytest.raises(DbtCompilationException):
                mock_hook.run_dbt_task("run")

            assert call_count == 1  # No retries
