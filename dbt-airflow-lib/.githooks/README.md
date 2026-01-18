# Git Hooks for dbt-airflow-lib

This directory contains git hooks to maintain code quality and cleanliness.

## Installation

Run the installation script to set up the hooks:

```bash
bash .githooks/install.sh
```

## Available Hooks

### pre-commit

Runs automatically before each commit to ensure code quality. This hook:

1. **Cleans build artifacts**:
   - Removes `__pycache__` directories
   - Deletes `.pyc`, `.pyo` files
   - Removes `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
   - Cleans `htmlcov/`, `build/`, `dist/`, `*.egg-info`
   - Removes coverage reports

2. **Runs code formatters**:
   - `black` for code formatting
   - `ruff --fix` for auto-fixable issues

3. **Runs linters**:
   - `ruff check` for code quality

4. **Runs type checking**:
   - `mypy` for type safety

5. **Runs unit tests**:
   - `pytest` (integration tests skipped for speed)

6. **Validates YAML fixtures**:
   - `validate-dags` for dag-factory configs

## Bypassing the Hook

For quick commits when you're confident in your changes:

```bash
# Option 1: Environment variable
SKIP_PRE_COMMIT=1 git commit -m "Quick fix"

# Option 2: Git flag
git commit --no-verify -m "Quick fix"
```

## Manual Cleanup

To manually clean the project without committing:

```bash
# Run the cleanup portion only
bash .githooks/pre-commit
```

Or use the Makefile:

```bash
make clean
```

## What Gets Cleaned

The pre-commit hook removes:

- **Python cache**: `__pycache__/`, `*.pyc`, `*.pyo`, `*.py~`
- **Test cache**: `.pytest_cache/`, `htmlcov/`, `.coverage`, `coverage.xml`
- **Build artifacts**: `build/`, `dist/`, `*.egg-info`
- **Tool cache**: `.mypy_cache/`, `.ruff_cache/`, `.tox/`

## Troubleshooting

### Hook fails with "No virtual environment found"

Make sure you have a virtual environment set up:

```bash
# Using uv (recommended)
uv venv

# Or using venv
python -m venv .venv
```

### Hook is too slow

The pre-commit hook runs all quality checks and tests. For faster commits during development:

```bash
# Skip the hook temporarily
git commit --no-verify -m "WIP: work in progress"

# Or only clean without running checks
SKIP_PRE_COMMIT=1 git commit -m "Quick commit"
```

### Tests fail during commit

Fix the failing tests before committing, or:

1. Run tests manually: `pytest`
2. Check specific failures: `pytest -v`
3. Fix issues, then commit again

## Integration with Makefile

The Makefile includes a `clean` target that performs the same cleanup:

```bash
# Clean project artifacts
make clean

# Clean and run all checks
make all

# Clean before building
make clean build
```

## Uninstalling

To remove the hook:

```bash
rm $(git rev-parse --git-dir)/hooks/pre-commit
```

## Best Practices

1. **Commit often**: The hook is designed to be fast for normal development
2. **Fix issues early**: Don't let formatting/linting issues accumulate
3. **Use --no-verify sparingly**: Only bypass for truly urgent commits
4. **Run tests manually**: For comprehensive testing, use `make test-all` or `tox`
