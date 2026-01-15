# .python-version File Explained

## What is .python-version?

The `.python-version` file is a simple text file that specifies which Python version a project should use. It's a **de facto standard** used by multiple Python tools.

```bash
# Content of .python-version
3.11
```

## Who Uses It?

### Tools That Read .python-version

| Tool | Description | Auto-Detection |
|------|-------------|----------------|
| **uv** | Fast Python package installer | ✅ Yes |
| **pyenv** | Python version manager | ✅ Yes |
| **asdf** | Multi-language version manager | ✅ Yes |
| **poetry** | Dependency management | ✅ Yes |
| **pipenv** | Package and venv management | ✅ Yes |
| **VS Code** | IDE with Python extension | ✅ Yes (with settings) |
| **PyCharm** | JetBrains Python IDE | ✅ Yes |
| **rtx** | Polyglot tool manager | ✅ Yes |

### How Each Tool Uses It

#### uv
```bash
# uv automatically reads .python-version
uv venv  # Uses Python 3.11 from .python-version
```

#### pyenv
```bash
# pyenv switches to specified version when entering directory
cd my-project/  # Automatically activates Python 3.11
python --version  # Python 3.11.x
```

#### poetry
```bash
# poetry respects .python-version for new projects
poetry install  # Uses Python 3.11
```

#### VS Code
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
// VS Code can detect .python-version automatically
```

## Why Use .python-version?

### 1. Team Consistency

**Without .python-version:**
```bash
# Developer 1
uv venv --python 3.10  # Uses Python 3.10

# Developer 2
uv venv --python 3.12  # Uses Python 3.12

# Result: Different Python versions, potential bugs!
```

**With .python-version:**
```bash
# Both developers
uv venv  # Both use Python 3.11 automatically

# Result: Consistent environment!
```

### 2. Simplified Commands

**Without .python-version:**
```bash
# Must specify version every time
uv venv --python 3.11
uv venv my-env --python 3.11
poetry install --python 3.11
```

**With .python-version:**
```bash
# Version specified once in file
uv venv            # Uses 3.11
uv venv my-env     # Uses 3.11
poetry install     # Uses 3.11
```

### 3. CI/CD Integration

**GitLab CI without .python-version:**
```yaml
script:
  - uv venv --python 3.11  # Hardcoded
  - source .venv/bin/activate
```

**GitLab CI with .python-version:**
```yaml
script:
  - uv venv  # Reads from .python-version
  - source .venv/bin/activate
```

### 4. Tool Compatibility

Works with multiple tools without configuration duplication:

```
One file (.python-version)
    ↓
    ├─→ uv uses it
    ├─→ pyenv uses it
    ├─→ poetry uses it
    ├─→ pipenv uses it
    └─→ VS Code uses it
```

## File Format

### Basic Format
```
3.11
```

### Specific Version
```
3.11.7
```

### Version Range (some tools)
```
3.11.*
```

### Multiple Versions (pyenv only)
```
3.11.7
3.10.12
```

## For This Project (dlh-airflow-common)

### Current Configuration

```bash
# .python-version content
3.11
```

This means:
- Project requires Python 3.11
- All developers should use Python 3.11
- CI/CD uses Python 3.11
- Compatible with Airflow 3.1+

### Usage Examples

#### Setup Development Environment

```bash
# Clone project
git clone <repo>
cd dlh-airflow-common

# Install Python 3.11 (if needed)
uv python install 3.11

# Create venv (automatically uses 3.11)
uv venv

# Activate
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

#### Verify Python Version

```bash
# Check what .python-version specifies
cat .python-version
# Output: 3.11

# Check actual Python version in venv
python --version
# Output: Python 3.11.x
```

## Comparison with Other Methods

### Method 1: .python-version (Recommended)

```
✅ Pros:
- Standardized across tools
- Automatic detection
- Team consistency
- No command-line flags needed

❌ Cons:
- Additional file in repo
```

### Method 2: pyproject.toml requires-python

```toml
[project]
requires-python = ">=3.11"
```

```
✅ Pros:
- Part of standard Python packaging
- Enforces minimum version

❌ Cons:
- Not auto-detected by all tools
- Only specifies minimum, not exact version
```

### Method 3: Manual specification

```bash
uv venv --python 3.11
```

```
✅ Pros:
- Explicit control

❌ Cons:
- Must remember to specify
- Inconsistency across team
- More typing
```

### Best Practice: Use Both

```
.python-version        → Exact version for development (3.11)
pyproject.toml         → Minimum version for distribution (>=3.8)
```

## Integration Examples

### With uv

```bash
# .python-version: 3.11

# Create venv (auto-detects)
uv venv
source .venv/bin/activate

# Install with uv
uv pip install -e ".[dev]"
```

### With pyenv

```bash
# Install version from .python-version
pyenv install $(cat .python-version)

# Set local version (uses .python-version)
pyenv local 3.11

# Verify
python --version
```

### With VS Code

```json
// .vscode/settings.json
{
  "python.pythonPath": ".venv/bin/python",
  "python.venvPath": ".",
  "python.terminal.activateEnvironment": true
}
```

VS Code will detect `.python-version` and suggest using Python 3.11.

### With Poetry

```bash
# Poetry respects .python-version
poetry install  # Uses Python 3.11

# Or explicitly
poetry env use $(cat .python-version)
```

## Troubleshooting

### Tool Not Detecting .python-version

**Problem:** Tool ignores `.python-version`

**Solutions:**

1. **Check file location**
   ```bash
   # Must be in project root
   ls -la .python-version
   ```

2. **Check file content**
   ```bash
   cat .python-version
   # Should show: 3.11
   ```

3. **Update tool**
   ```bash
   # Update uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Wrong Python Version Used

**Problem:** Different version than specified

**Solutions:**

1. **Check if Python version is installed**
   ```bash
   uv python list  # Should show 3.11
   ```

2. **Install if missing**
   ```bash
   uv python install 3.11
   ```

3. **Recreate venv**
   ```bash
   rm -rf .venv
   uv venv
   ```

### Multiple .python-version Files

**Problem:** Different versions in different directories

**Solution:** Keep only one in project root:
```
dlh-airflow-common/
├── .python-version    ← Keep this
└── subdirectory/
    └── .python-version ← Remove this
```

## Best Practices

### 1. Commit to Version Control

```bash
# Always commit .python-version
git add .python-version
git commit -m "Set Python version to 3.11"
```

### 2. Document in README

```markdown
## Requirements

- Python 3.11 (specified in .python-version)
```

### 3. Use Exact Version for Stability

```
✅ Good: 3.11      (specific major.minor)
✅ Good: 3.11.7    (exact version)
❌ Avoid: 3        (too vague)
```

### 4. Update When Upgrading Python

```bash
# Update to Python 3.12
echo "3.12" > .python-version

# Install new version
uv python install 3.12

# Recreate venv
rm -rf .venv
uv venv
```

### 5. Align with CI/CD

Ensure CI/CD uses same version:

```yaml
# .gitlab-ci.yml
variables:
  PYTHON_VERSION: "3.11"  # Match .python-version

script:
  - uv python install $PYTHON_VERSION
  - uv venv  # Or explicit: uv venv --python $PYTHON_VERSION
```

## Quick Reference

```bash
# Create .python-version
echo "3.11" > .python-version

# Use with uv (auto-detects)
uv venv
uv python install $(cat .python-version)

# Use with pyenv
pyenv install $(cat .python-version)
pyenv local $(cat .python-version)

# Use with poetry
poetry env use $(cat .python-version)

# Verify version
cat .python-version
python --version
```

## Additional Resources

- [pyenv .python-version](https://github.com/pyenv/pyenv#choosing-the-python-version)
- [uv Python version management](https://docs.astral.sh/uv/concepts/python-versions/)
- [PEP 582 - Python local packages directory](https://peps.python.org/pep-0582/)
