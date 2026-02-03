# UV Setup Guide

This guide explains how to set up a development environment for the DAGs project using [uv](https://github.com/astral-sh/uv).

## What is uv?

uv is a fast Python package installer and resolver (10-100x faster than pip) that can also manage Python versions.

## Installation

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install Python 3.11

```bash
uv python install 3.11
```

## Project Setup

### 1. Create Virtual Environment

```bash
cd airflow-common-dags
uv venv --python 3.11 --clear
```

### 2. Activate Virtual Environment

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Test Dependencies

```bash
make install-test
```

Or manually:

```bash
uv pip install -e ".[dev]"
```

### 4. Install Pre-commit Hooks

```bash
make hooks-install
```

## Common Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Run linting
make lint

# Auto-fix linting issues
make lint-fix

# Check formatting
make format

# Auto-fix formatting
make format-fix

# Run type checking
make type-check

# Run all checks
make all

# Clean up cache files
make clean
```

## Verifying Setup

After installation, verify everything works:

```bash
# Check Python version
python --version  # Should show Python 3.11.x

# Run all checks
make all
```

If all checks pass, your environment is ready for development.
