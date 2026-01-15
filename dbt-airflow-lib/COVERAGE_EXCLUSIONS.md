# Coverage Exclusions Guide

This guide explains how to exclude code from coverage analysis when testing doesn't make sense or isn't practical.

## Why Exclude Code?

Some code should be excluded from coverage requirements:
- **Defensive programming**: Checks that should never happen in practice
- **Debug code**: Logging or debugging helpers
- **Type checking blocks**: Code only executed by type checkers
- **Abstract methods**: Methods meant to be overridden
- **Platform-specific code**: OS-specific branches that can't be tested in CI
- **Unreachable code**: Safety checks for impossible states

## How to Exclude Code

### 1. Inline Exclusion with `# pragma: no cover`

Add `# pragma: no cover` comment to exclude specific lines or blocks:

#### Exclude Single Line
```python
def process_data(data: str) -> str:
    if not data:  # pragma: no cover
        return ""  # Defensive check, tested elsewhere
    return data.upper()
```

#### Exclude Entire Function
```python
def debug_helper() -> None:  # pragma: no cover
    """Debug utility, only used during development."""
    print("Debug info")
```

#### Exclude Block
```python
def process(value: int) -> int:
    if value < 0:  # pragma: no cover
        # This should never happen due to validation
        raise ValueError("Negative value")
    return value * 2
```

### 2. Configuration-Based Exclusions

The project already has several patterns excluded in [pyproject.toml](pyproject.toml):

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

These patterns are automatically excluded:
- `pragma: no cover` - Explicit exclusion marker
- `def __repr__` - String representations (usually not critical)
- `raise AssertionError` - Should-never-happen assertions
- `raise NotImplementedError` - Abstract method placeholders
- `if __name__ == .__main__.:` - Script entry points
- `if TYPE_CHECKING:` - Type-only imports
- `@abstractmethod` - Abstract method declarations

## Common Use Cases

### 1. Defensive Assertions

```python
def divide(a: int, b: int) -> float:
    """Divide two numbers."""
    assert b != 0, "Divisor cannot be zero"  # pragma: no cover
    return a / b
```

**Why exclude**: The assertion is defensive; validation happens upstream.

### 2. Platform-Specific Code

```python
import sys

def get_config_dir() -> str:
    """Get platform-specific config directory."""
    if sys.platform == "win32":
        return "C:\\Config"
    elif sys.platform == "darwin":  # pragma: no cover
        return "/Users/Config"
    else:  # pragma: no cover
        return "/etc/config"
```

**Why exclude**: CI only runs on Linux; can't test all platforms.

### 3. Debug/Development Code

```python
def process_batch(items: list) -> None:
    """Process items in batch."""
    if DEBUG_MODE:  # pragma: no cover
        print(f"Processing {len(items)} items")

    for item in items:
        process_item(item)
```

**Why exclude**: Debug code not executed in tests.

### 4. Type Checking Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from airflow.models import DAG
    from .custom_types import CustomConfig
```

**Why exclude**: These imports only run during static type checking, not at runtime.

### 5. Abstract Methods

```python
from abc import ABC, abstractmethod

class BaseOperator(ABC):
    @abstractmethod
    def execute(self, context: dict) -> Any:  # pragma: no cover
        """Execute operator logic."""
        raise NotImplementedError("Subclasses must implement execute()")
```

**Why exclude**: Abstract methods are never called directly; subclasses implement them.

### 6. Impossible Conditions

```python
def get_status(code: int) -> str:
    """Get status from code."""
    if code == 200:
        return "OK"
    elif code == 404:
        return "Not Found"
    elif code == 500:
        return "Error"
    else:  # pragma: no cover
        # Should never happen, all codes handled above
        raise ValueError(f"Unknown code: {code}")
```

**Why exclude**: The else branch is unreachable by design.

### 7. Error Logging Details

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    if hasattr(e, "details"):  # pragma: no cover
        # Only some exceptions have details
        logger.error(f"Details: {e.details}")
    raise
```

**Why exclude**: Testing all exception types with/without attributes is excessive.

## Best Practices

### DO Use Exclusions For:
✅ Defensive checks that should never trigger
✅ Platform-specific code you can't test
✅ Debug/development utilities
✅ Type-checking-only imports
✅ Abstract method stubs
✅ `__repr__` and `__str__` methods

### DON'T Use Exclusions For:
❌ Code you're too lazy to test
❌ Complex business logic
❌ Error handling you should test
❌ Edge cases you don't want to handle
❌ Most of your codebase

### Guidelines:
1. **Be judicious**: Only exclude when testing truly doesn't make sense
2. **Document why**: Add comments explaining the exclusion
3. **Review regularly**: Periodically review exclusions during code review
4. **Test the main path**: Ensure the normal execution path is fully tested

## Adding Custom Exclusion Patterns

Edit `pyproject.toml` to add project-specific exclusion patterns:

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    # Add your custom patterns below:
    "if DEBUG:",                    # Debug-only code
    "if TESTING:",                  # Test-only code
    "raise NotImplementedError",    # Placeholder methods
    "pass  # pragma: no cover",     # Explicit pass statements
]
```

## Example: Real-World Scenario

```python
class DbtOperator(BaseOperator):
    """Operator to run dbt commands."""

    def execute(self, context: dict) -> dict:
        """Execute dbt command."""
        # Validate inputs (tested)
        self._validate()

        # Build command (tested)
        cmd = self._build_dbt_command()

        # Execute (tested)
        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"DBT failed: {e}")

            # Log stdout if available (good to exclude - hard to test reliably)
            if e.stdout:  # pragma: no cover
                self.logger.error(f"stdout: {e.stdout}")

            # Log stderr if available (good to exclude - hard to test reliably)
            if e.stderr:  # pragma: no cover
                self.logger.error(f"stderr: {e.stderr}")

            raise AirflowException(f"DBT failed: {e}")

        return {"return_code": result.returncode}

    def on_kill(self) -> None:  # pragma: no cover
        """Handle task kill (hard to test in unit tests)."""
        self.logger.warning("Task killed by user")
```

## Viewing Excluded Code

### Check what's excluded in HTML report:

```bash
# Generate coverage report
make test-cov

# Open HTML report
open htmlcov/index.html
```

Excluded lines appear grayed out in the HTML report.

### Check coverage with details:

```bash
# Show line-by-line coverage
pytest --cov=dlh_airflow_common --cov-report=term-missing

# Output shows which lines are missing or excluded
```

## Temporary Exclusions During Development

Sometimes you want to exclude new code temporarily while developing:

```python
def new_feature_in_progress():  # pragma: no cover
    """Still implementing this."""
    # TODO: Add tests once feature is complete
    pass
```

**Remember to remove** `# pragma: no cover` once you add tests!

## CI/CD Considerations

The coverage threshold is enforced in CI/CD:

```yaml
# .gitlab-ci.yml
test:pytest:
  script:
    - pytest --cov-fail-under=100
```

Exclusions are respected, so:
- Excluded code doesn't count toward the 100% requirement
- But exclusions are visible in coverage reports
- Code reviewers can verify exclusions are appropriate

## Code Review Checklist

When reviewing code with coverage exclusions:

- [ ] Is the exclusion justified?
- [ ] Is there a comment explaining why?
- [ ] Could this code be tested with reasonable effort?
- [ ] Is the main execution path fully tested?
- [ ] Are we excluding too much?

## Summary

| Scenario | Use Exclusion? | Method |
|----------|---------------|--------|
| Defensive assertion | ✅ Yes | `# pragma: no cover` |
| Platform-specific code | ✅ Yes | `# pragma: no cover` |
| Type checking imports | ✅ Yes | Auto-excluded |
| Abstract methods | ✅ Yes | Auto-excluded |
| Debug logging | ✅ Yes | `# pragma: no cover` |
| Business logic | ❌ No | Write tests |
| Error handling | ❌ No | Write tests |
| Edge cases | ❌ No | Write tests |
| Complex calculations | ❌ No | Write tests |

**Key principle**: Exclude only when testing is impractical or doesn't add value, not when you're avoiding writing tests.
