# =============================================================================
# Makefile for dlh-airflow-common
# =============================================================================
#
# Quick reference for development tasks. Uses uv by default for speed.
#
# Setup:
#   make install            # Install with dev dependencies (uv)
#   make install-pip        # Install with dev dependencies (pip fallback)
#
# Testing:
#   make test               # Run tests
#   make test-cov           # Run tests with coverage (90% required)
#   make test-cov-report    # Run tests and open HTML coverage report
#   make tox                # Run tests on Python 3.11/3.12 × dbt 1.8/1.10
#   make tox-parallel       # Run tox in parallel (faster)
#
# Code Quality:
#   make lint               # Run linting (ruff)
#   make format             # Check formatting (black)
#   make format-fix         # Auto-fix formatting
#   make type-check         # Run type checking (mypy)
#   make quality-all        # Run all quality checks (lint, format, type-check, test)
#
# Build & Deploy:
#   make build              # Build package
#   make publish-dev        # Publish to Dev Nexus
#   make publish-prod       # Publish to Prod Nexus (requires tag)
#   make version            # Show current version
#
# Cleanup:
#   make clean              # Remove build artifacts
#
# =============================================================================

.PHONY: help install install-pip install-integration clean test test-cov test-cov-report \
        test-integration test-all coverage lint format format-fix type-check build publish-dev publish-prod \
        publish-test version tox tox-parallel tox-parallel-verbose tox-integration tox-all tox-all-verbose \
        quality-all check check-python ci

.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help:
	@echo ""
	@echo "$(BLUE)dlh-airflow-common Development Commands$(NC)"
	@echo "========================================"
	@echo ""
	@echo "$(GREEN)Setup:$(NC)"
	@echo "  make install            Install with dev dependencies (uv)"
	@echo "  make install-pip        Install with dev dependencies (pip fallback)"
	@echo "  make install-integration Install integration test dependencies"
	@echo "  make check              Check/install required Python versions for tox"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test               Run unit tests only (fast)"
	@echo "  make test-integration   Run integration tests with real dbt execution"
	@echo "  make test-all           Run all tests (unit + integration)"
	@echo "  make test-cov           Run unit tests with coverage (fails if <90%)"
	@echo "  make test-cov-report    Run tests with coverage and open HTML report"
	@echo "  make tox                Run tests on Python 3.11/3.12 × dbt 1.8/1.10"
	@echo "  make tox-parallel       Run tox in parallel (fast, minimal output)"
	@echo "  make tox-parallel-verbose Run all checks sequentially (shows full output)"
	@echo "  make tox-integration    Run integration tests via tox"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint               Run linting (ruff)"
	@echo "  make format             Check code formatting (black)"
	@echo "  make format-fix         Auto-fix code formatting"
	@echo "  make type-check         Run type checking (mypy)"
	@echo "  make quality-all        Run all checks (lint, format, type-check, test)"
	@echo ""
	@echo "$(GREEN)Build & Deploy:$(NC)"
	@echo "  make build              Build package (wheel and sdist)"
	@echo "  make publish-dev        Publish to Dev Nexus repository"
	@echo "  make publish-prod       Publish to Prod Nexus repository"
	@echo "  make publish-test       Verify package before publishing"
	@echo "  make version            Show current version (from setuptools-scm)"
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@echo "  make clean              Remove all build artifacts"
	@echo ""

# =============================================================================
# Setup
# =============================================================================

install:
	uv pip install -e ".[dev]"

install-pip:
	pip install -e ".[dev]"

install-integration:
	uv pip install -e ".[integration]"
	@echo "$(GREEN)Integration test dependencies installed$(NC)"
	@echo "Run 'make test-integration' to execute integration tests"

# Check that required Python versions are installed for tox
check-python:
	@echo "$(BLUE)Checking Python versions for tox...$(NC)"
	@PY311_PATH=$$(uv python find 3.11 2>/dev/null); \
	if [ -z "$$PY311_PATH" ] || [ ! -x "$$PY311_PATH" ]; then \
		echo "$(YELLOW)Python 3.11 not found or invalid. Installing...$(NC)"; \
		uv python install 3.11; \
		rm -rf .tox/py311*; \
	else \
		echo "$(GREEN)Python 3.11: OK ($$PY311_PATH)$(NC)"; \
	fi
	@PY312_PATH=$$(uv python find 3.12 2>/dev/null); \
	if [ -z "$$PY312_PATH" ] || [ ! -x "$$PY312_PATH" ]; then \
		echo "$(YELLOW)Python 3.12 not found or invalid. Installing...$(NC)"; \
		uv python install 3.12; \
		rm -rf .tox/py312*; \
	else \
		echo "$(GREEN)Python 3.12: OK ($$PY312_PATH)$(NC)"; \
	fi

check: check-python
	@echo "$(GREEN)All checks passed!$(NC)"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache
	rm -rf .tox
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.py~" -delete 2>/dev/null || true

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "$(BLUE)Running unit tests (integration tests skipped)...$(NC)"
	uv run pytest

test-integration:
	@echo "$(BLUE)Running integration tests with real dbt execution...$(NC)"
	uv run pytest -m integration --no-cov

test-all:
	@echo "$(BLUE)Running all tests (unit + integration)...$(NC)"
	uv run pytest -m ""

test-cov:
	uv run pytest --cov=dlh_airflow_common --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=90

test-cov-report: test-cov
	@echo "Opening coverage report in browser..."
	@command -v xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	 command -v open > /dev/null && open htmlcov/index.html || \
	 echo "Coverage report generated in htmlcov/index.html"

coverage: test-cov-report

# Multi-version testing with tox
# Tests against Python 3.11/3.12 × Airflow 3.1 × dbt-core 1.8/1.10 (shows full output)
# Note: py312-dbt18 excluded due to importlib-metadata conflict
tox: check-python
	@echo "$(BLUE)Running tests on Python 3.11/3.12 with dbt-core 1.8 and 1.10...$(NC)"
	uv run tox -e py311-airflow31-dbt18,py311-airflow31-dbt110,py312-airflow31-dbt110

tox-integration:
	@echo "$(BLUE)Running integration tests via tox...$(NC)"
	uv run tox -e integration

# Run quality checks and tests in parallel (faster but hides output)
tox-parallel: check-python
	@echo "$(BLUE)Running parallel tox tests (use 'make tox-parallel-verbose' to see output)...$(NC)"
	uv run tox -e py311-airflow31-dbt18,py311-airflow31-dbt110,py312-airflow31-dbt110,lint,format,type-check -p auto

# Run quality checks and tests sequentially (shows full output)
tox-parallel-verbose: check-python
	@echo "$(BLUE)Running all quality checks with verbose output...$(NC)"
	uv run tox -e lint,format,type-check,py311-airflow31-dbt18,py311-airflow31-dbt110,py312-airflow31-dbt110

# Run all quality checks sequentially (alias for tox-parallel-verbose)
tox-all-verbose: check-python
	@echo "$(BLUE)Running all quality checks with verbose output...$(NC)"
	uv run tox -e lint,format,type-check,py311-airflow31-dbt18,py311-airflow31-dbt110,py312-airflow31-dbt110

tox-all: check-python
	@echo "$(BLUE)Running all tox environments...$(NC)"
	uv run tox

# =============================================================================
# Code Quality
# =============================================================================

lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

format:
	uv run black --check src/ tests/

format-fix:
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

type-check:
	uv run mypy src/

# =============================================================================
# Build & Deploy
# =============================================================================

build: clean
	uv run python -m build
	@echo ""
	@echo "$(GREEN)Built packages:$(NC)"
	@ls -lh dist/

version:
	@uv run python -c "from setuptools_scm import get_version; print(get_version(root='..'))"

publish-test:
	uv run twine check dist/*

# Deploy to Dev Nexus (mutable - can overwrite versions)
publish-dev: build publish-test
	@echo "$(YELLOW)Publishing to DEV Nexus...$(NC)"
	uv run twine upload --repository nexus-dev dist/*
	@echo "$(GREEN)Published to Dev Nexus$(NC)"

# Deploy to Prod Nexus (immutable - cannot overwrite)
publish-prod: build publish-test
	@echo "$(YELLOW)Publishing to PROD Nexus (immutable)...$(NC)"
	@VERSION=$$(uv run python -c "from setuptools_scm import get_version; print(get_version())"); \
	if echo "$$VERSION" | grep -q "\.dev"; then \
		echo "$(YELLOW)ERROR: Cannot publish dev version ($$VERSION) to production!$(NC)"; \
		echo "Create a git tag first: git tag vX.Y.Z && git push origin vX.Y.Z"; \
		exit 1; \
	fi
	uv run twine upload --repository nexus-prod dist/*
	@echo "$(GREEN)Published to Prod Nexus$(NC)"

# Legacy alias
publish-nexus: publish-dev

# =============================================================================
# Combined Commands
# =============================================================================

quality-all: lint format type-check test
	@echo ""
	@echo "$(GREEN)All quality checks passed!$(NC)"

# CI simulation - run what GitLab CI runs
ci: lint format type-check test-cov
	@echo ""
	@echo "$(GREEN)CI checks passed!$(NC)"
