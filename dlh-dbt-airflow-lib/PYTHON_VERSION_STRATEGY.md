# Python Version Strategy for Multi-Version Libraries

## The Question

For a library that supports **multiple Python versions** (3.8-3.12), should we keep `.python-version`?

## Answer: Yes, Keep It! Here's Why

### Understanding the Two Concepts

#### 1. `.python-version` - **Development** Python Version
```
Purpose: What Python version developers use to work on the library
File: .python-version
Content: 3.11
```

#### 2. `requires-python` - **Supported** Python Versions
```
Purpose: What Python versions the library works with
File: pyproject.toml
Content: requires-python = ">=3.8"
```

### They Serve Different Purposes

```
┌─────────────────────────────────────────────┐
│ Library Development (dlh-airflow-common)    │
├─────────────────────────────────────────────┤
│ .python-version: 3.11                       │
│ → Developers use Python 3.11                │
│ → CI/CD tests with Python 3.11 first        │
│ → Consistent dev environment                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Built Package Distribution                   │
├─────────────────────────────────────────────┤
│ requires-python: >=3.8                      │
│ → Works on Python 3.8, 3.9, 3.10, 3.11, 3.12│
│ → Users can install on any supported version│
└─────────────────────────────────────────────┘
```

## Current Configuration (Recommended)

### `.python-version` - Development Standard
```
3.11
```

**Why Python 3.11 for development:**
- ✅ Modern Python features
- ✅ Better performance (10-60% faster than 3.10)
- ✅ Improved error messages
- ✅ Long-term support (until 2027)
- ✅ Compatible with Airflow 3.1+
- ✅ Good balance (not too old, not bleeding edge)

### `pyproject.toml` - Library Requirements
```toml
[project]
requires-python = ">=3.8"
```

**Why >=3.8:**
- ✅ Broad compatibility
- ✅ Supports older environments
- ✅ Many companies still on 3.8-3.10
- ✅ Airflow 3.1+ supports 3.8+

## Real-World Analogy

Think of it like car manufacturing:

```
Factory uses latest equipment (Python 3.11)
  ↓
Builds cars that work on regular roads (Python >=3.8)
  ↓
Customers can drive on any compatible road
```

## Workflow Example

### Developer Workflow
```bash
# Clone repo
git clone <repo>
cd dlh-airflow-common

# .python-version ensures all devs use 3.11
uv venv  # Creates Python 3.11 venv
source .venv/bin/activate

# Develop using Python 3.11 features (if needed)
# But code must work on >=3.8
```

### CI/CD Testing (Multiple Versions)
```yaml
# .gitlab-ci.yml
test:pytest:
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.8", "3.9", "3.10", "3.11", "3.12"]
  script:
    - uv python install $PYTHON_VERSION
    - uv venv --python $PYTHON_VERSION
    - source .venv/bin/activate
    - uv pip install -e ".[dev]"
    - pytest
```

### User Installation (Any Supported Version)
```bash
# User with Python 3.8
python3.8 -m pip install dlh-airflow-common  # ✓ Works

# User with Python 3.11
python3.11 -m pip install dlh-airflow-common  # ✓ Works

# User with Python 3.12
python3.12 -m pip install dlh-airflow-common  # ✓ Works
```

## Benefits of Keeping .python-version

### 1. Team Consistency
```bash
# Developer A
cd dlh-airflow-common
uv venv  # Uses Python 3.11

# Developer B
cd dlh-airflow-common
uv venv  # Uses Python 3.11

# Result: Same development environment!
```

### 2. Modern Development Experience
```python
# Can use modern Python 3.11 features in dev tools
# But library code uses only >=3.8 compatible features

# Development script (not in library)
def debug_info() -> None:  # Python 3.10+ syntax
    match status:  # Python 3.10+ feature
        case "success": ...

# Library code (compatible with 3.8+)
def execute(self, context: Dict[str, Any]) -> Any:  # Python 3.8+ syntax
    if status == "success":  # Python 3.8+ compatible
        ...
```

### 3. CI/CD Primary Testing
```yaml
# Test on 3.11 first (fastest feedback)
test:quick:
  script:
    - uv venv  # Uses .python-version (3.11)
    - pytest

# Then test on all versions
test:matrix:
  parallel:
    matrix:
      - PYTHON: [3.8, 3.9, 3.10, 3.11, 3.12]
```

### 4. IDE Integration
```
VS Code / PyCharm automatically detect .python-version
  ↓
Developer gets Python 3.11 features:
  - Better autocomplete
  - Modern type hints
  - Faster performance
```

## What NOT to Do

### ❌ Don't: Use Python 3.11-only features in library code

```python
# ❌ BAD - Breaks on Python 3.8
match status:  # match only in 3.10+
    case "success": ...

# ✅ GOOD - Works on Python 3.8+
if status == "success":
    ...
```

### ❌ Don't: Set .python-version to minimum supported version

```
# ❌ BAD
echo "3.8" > .python-version
# Why: Devs miss out on modern Python features

# ✅ GOOD
echo "3.11" > .python-version
# Why: Devs get best experience, library still supports 3.8+
```

### ❌ Don't: Remove .python-version to "support all versions"

```
# ❌ BAD: No .python-version
# Result: Each dev might use different Python version
# Developer A: Python 3.8
# Developer B: Python 3.12
# Inconsistent development!

# ✅ GOOD: Keep .python-version
# Result: All devs use Python 3.11
# Consistent development, faster debugging
```

## Best Practices for Multi-Version Libraries

### 1. Use .python-version for Development
```bash
# Set to modern, stable version
echo "3.11" > .python-version
```

### 2. Set requires-python for Compatibility
```toml
# pyproject.toml
[project]
requires-python = ">=3.8"
```

### 3. Test on All Supported Versions
```yaml
# tox.ini
[tox]
envlist = py{38,39,310,311,312}

# .gitlab-ci.yml
test:matrix:
  parallel:
    matrix:
      - PYTHON: [3.8, 3.9, 3.10, 3.11, 3.12]
```

### 4. Use Compatible Code Syntax
```python
# Use type hints compatible with 3.8+
from typing import Dict, List, Optional  # 3.8+
# Not: dict, list (lowercase) - requires 3.9+

# Use traditional patterns
if condition:  # 3.8+
    ...
# Not: match condition: - requires 3.10+
```

### 5. Document Both Versions
```markdown
# README.md

## Requirements

- **Development**: Python 3.11 (see .python-version)
- **Runtime**: Python >= 3.8 (see pyproject.toml)

## Setup

Development environment:
```bash
uv venv  # Uses Python 3.11 from .python-version
```

## For This Project: dlh-airflow-common

### Current Setup ✅

```
Development: Python 3.11 (.python-version)
Support: Python >=3.8 (pyproject.toml)
Testing: Python 3.8, 3.9, 3.10, 3.11, 3.12 (tox.ini, .gitlab-ci.yml)
```

### Why This Works

1. **Developers** use Python 3.11 for best experience
2. **Code** is written to work on Python >=3.8
3. **CI/CD** tests on all supported versions
4. **Users** can install on any Python 3.8-3.12

### Verification Strategy

```bash
# Development (Python 3.11)
uv venv
source .venv/bin/activate
pytest  # Quick test with 3.11

# Pre-release testing (all versions)
tox  # Tests on 3.8, 3.9, 3.10, 3.11, 3.12

# CI/CD (all versions)
git push  # GitLab runs matrix tests
```

## Conclusion

### Keep .python-version = "3.11" ✅

**Reasons:**
1. Consistent development environment
2. Modern Python features for dev tools
3. Best performance during development
4. IDE integration
5. Simplified commands (`uv venv` vs `uv venv --python 3.11`)

### Keep requires-python = ">=3.8" ✅

**Reasons:**
1. Broad compatibility
2. Users can install on older Python
3. Production environments often use older versions
4. Gradual migration path for users

### Test on All Supported Versions ✅

**Reasons:**
1. Ensure compatibility claims are true
2. Catch version-specific bugs
3. Build confidence
4. Users trust the library

## Summary Table

| Aspect | Configuration | Purpose |
|--------|--------------|---------|
| **Development** | `.python-version: 3.11` | Dev environment consistency |
| **Library Support** | `requires-python: >=3.8` | User compatibility |
| **Testing** | `tox: py38-py312` | Verify multi-version support |
| **CI/CD Primary** | Uses `.python-version` (3.11) | Fast feedback |
| **CI/CD Full** | Matrix tests all versions | Complete validation |
| **Recommendation** | **Keep .python-version** | Best of both worlds |
