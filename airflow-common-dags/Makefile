.PHONY: help install-test test test-cov lint lint-fix format format-fix type-check all clean hooks-install

.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# SETUP
# =============================================================================

install-test: ## Install test dependencies using uv
	@echo "$(BLUE)Installing test dependencies with uv...$(NC)"
	uv venv --python 3.11 --clear
	uv pip install -e ".[dev]"
	@echo "$(GREEN)Test dependencies installed! Activate venv with: source .venv/bin/activate$(NC)"

hooks-install: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	uv run pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"

# =============================================================================
# TESTING
# =============================================================================

test: ## Run tests with pytest
	@echo "$(BLUE)Running tests...$(NC)"
	PYTHONPATH=. uv run pytest -v
	@echo "$(GREEN)Tests complete!$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	PYTHONPATH=. uv run pytest --cov=dags --cov=common --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: ## Run linting with ruff
	@echo "$(BLUE)Running linter...$(NC)"
	uv run ruff check dags/ common/ tests/
	@echo "$(GREEN)Linting complete!$(NC)"

lint-fix: ## Auto-fix linting issues
	@echo "$(BLUE)Fixing lint issues...$(NC)"
	uv run ruff check --fix dags/ common/ tests/
	@echo "$(GREEN)Lint fixes applied!$(NC)"

format: ## Check code formatting with black
	@echo "$(BLUE)Checking formatting...$(NC)"
	uv run black --check dags/ common/ tests/
	@echo "$(GREEN)Formatting check complete!$(NC)"

format-fix: ## Auto-fix formatting with black and ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	uv run black dags/ common/ tests/
	uv run ruff check --fix dags/ common/ tests/
	@echo "$(GREEN)Formatting complete!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checker...$(NC)"
	uv run mypy dags/ common/
	@echo "$(GREEN)Type checking complete!$(NC)"

# =============================================================================
# COMBINED COMMANDS
# =============================================================================

all: lint format type-check test ## Run all checks (lint, format, type-check, test)
	@echo "$(GREEN)All checks passed!$(NC)"

ci: format-fix lint-fix type-check test ## Run CI pipeline (format, lint, type-check, test)
	@echo "$(GREEN)CI pipeline complete!$(NC)"

# =============================================================================
# CLEANUP
# =============================================================================

clean: ## Remove build artifacts and cache files
	@echo "$(BLUE)Cleaning up...$(NC)"
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"
