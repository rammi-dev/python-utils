"""Unit tests for common utilities."""

from datetime import timedelta

from common.utils import generate_dag_id, get_default_args


class TestGetDefaultArgs:
    """Tests for get_default_args function."""

    def test_default_values(self) -> None:
        """Should return expected default values."""
        args = get_default_args()

        assert args["owner"] == "data-team"
        assert args["retries"] == 2
        assert args["retry_delay"] == timedelta(minutes=5)
        assert args["email_on_failure"] is False
        assert args["depends_on_past"] is False

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        args = get_default_args(
            owner="analytics",
            retries=5,
            retry_delay_minutes=10,
            email_on_failure=True,
        )

        assert args["owner"] == "analytics"
        assert args["retries"] == 5
        assert args["retry_delay"] == timedelta(minutes=10)
        assert args["email_on_failure"] is True


class TestGenerateDagId:
    """Tests for generate_dag_id function."""

    def test_basic_format(self) -> None:
        """Should format DAG ID correctly."""
        dag_id = generate_dag_id("sales", "daily_report")
        assert dag_id == "sales_daily_report_prod"

    def test_custom_environment(self) -> None:
        """Should include custom environment."""
        dag_id = generate_dag_id("finance", "etl", environment="dev")
        assert dag_id == "finance_etl_dev"

    def test_sanitizes_input(self) -> None:
        """Should sanitize spaces and case."""
        dag_id = generate_dag_id("  Sales  ", "Daily Report", "DEV")
        assert dag_id == "sales_daily_report_dev"
