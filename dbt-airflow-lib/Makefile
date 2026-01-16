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
#   make test-cov           # Run tests with coverage (100% required)
#   make test-cov-report    # Run tests and open HTML coverage report
#   make tox                # Run tests on Python 3.11 and 3.12
#   make tox-parallel       # Run tox in parallel (faster)
#
# Code Quality:
#   make lint               # Run linting (ruff)
#   make format             # Check formatting (black)
#   make format-fix         # Auto-fix formatting
#   make type-check         # Run type checking (mypy)
#   make all                # Run all checks
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

.PHONY: help install install-pip clean test test-cov test-cov-report \
        coverage lint format format-fix type-check build publish-dev publish-prod \
        publish-test version tox tox-parallel all

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
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test               Run tests"
	@echo "  make test-cov           Run tests with coverage (fails if <100%)"
	@echo "  make test-cov-report    Run tests with coverage and open HTML report"
	@echo "  make tox                Run tests on Python 3.11 and 3.12"
	@echo "  make tox-parallel       Run tox environments in parallel"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint               Run linting (ruff)"
	@echo "  make format             Check code formatting (black)"
	@echo "  make format-fix         Auto-fix code formatting"
	@echo "  make type-check         Run type checking (mypy)"
	@echo "  make all                Run all checks (lint, format, type-check, test)"
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

# =============================================================================
# Testing
# =============================================================================

test:
	uv run pytest

test-cov:
	uv run pytest --cov=dlh_airflow_common --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=100

test-cov-report: test-cov
	@echo "Opening coverage report in browser..."
	@command -v xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	 command -v open > /dev/null && open htmlcov/index.html || \
	 echo "Coverage report generated in htmlcov/index.html"

coverage: test-cov-report

# Multi-version testing with tox
tox:
	uv run tox -e py311,py312

tox-parallel:
	uv run tox -e py311,py312 -p auto

tox-all:
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
	@uv run python -c "from setuptools_scm import get_version; print(get_version())"

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

all: lint format type-check test
	@echo ""
	@echo "$(GREEN)All checks passed!$(NC)"

# CI simulation - run what GitLab CI runs
ci: lint format type-check test-cov
	@echo ""
	@echo "$(GREEN)CI checks passed!$(NC)"
