.PHONY: help install install-dev install-uv clean test test-cov test-cov-report coverage lint format format-fix type-check build publish-nexus publish-test all

help:
	@echo "Available commands:"
	@echo "  make install          - Install package"
	@echo "  make install-dev      - Install package with dev dependencies"
	@echo "  make install-uv       - Install package with dev dependencies using uv (recommended)"
	@echo "  make clean            - Clean build artifacts"
	@echo "  make test             - Run tests"
	@echo "  make test-cov         - Run tests with coverage (fails if <100%)"
	@echo "  make test-cov-report  - Run tests with coverage and open HTML report"
	@echo "  make coverage         - Alias for test-cov-report"
	@echo "  make lint             - Run linting"
	@echo "  make format           - Check code formatting"
	@echo "  make format-fix       - Fix code formatting"
	@echo "  make type-check       - Run type checking"
	@echo "  make build            - Build package"
	@echo "  make publish-nexus    - Publish to Nexus"
	@echo "  make all              - Run all checks"

install:
	pip install .

install-dev:
	pip install -e ".[dev]"

install-uv:
	uv pip install -e ".[dev]"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .tox
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest

test-cov:
	pytest --cov=dlh_airflow_common --cov-report=term --cov-report=html --cov-report=xml --cov-fail-under=100

test-cov-report: test-cov
	@echo "Opening coverage report in browser..."
	@command -v xdg-open > /dev/null && xdg-open htmlcov/index.html || \
	 command -v open > /dev/null && open htmlcov/index.html || \
	 echo "Coverage report generated in htmlcov/index.html"

coverage: test-cov-report

lint:
	ruff check src/ tests/

format:
	black --check src/ tests/

format-fix:
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/

build: clean
	python -m build

publish-nexus: build
	twine upload --repository nexus dist/*

publish-test:
	twine check dist/*

all: lint format type-check test
	@echo "All checks passed!"
