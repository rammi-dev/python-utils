# UV Setup Guide - Fast Python Package Management

This guide covers using [uv](https://github.com/astral-sh/uv) for fast Python package and version management.

## What is uv?

uv is an extremely fast Python package installer and resolver, written in Rust. It's 10-100x faster than pip and can also manage Python versions.

**Key Benefits:**
- 🚀 10-100x faster than pip
- 🐍 Manages Python versions (install Python 3.11 with one command)
- 🔒 Reliable dependency resolution
- 💾 Smart caching
- 🎯 Drop-in replacement for pip

## Installation

### Linux/macOS

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (usually done automatically)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

### Windows

```powershell
# Using PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### Alternative: Using pip

```bash
pip install uv
```

## Python Version Management with uv

One of uv's killer features is built-in Python version management.

### Install Python 3.11

```bash
# Install Python 3.11 (latest patch version)
uv python install 3.11

# Install specific version
uv python install 3.11.7

# Install multiple versions
uv python install 3.11 3.12
```

### List Available Python Versions

```bash
# Show installed Python versions
uv python list

# Find specific Python version
uv python find 3.11

# Show all available Python versions for installation
uv python list --all-versions
```

### Pin Python Version for Project

The `.python-version` file is a standard way to specify which Python version a project should use.

#### What Uses .python-version?

Multiple tools read this file:

- **uv** - Automatically uses this Python version
- **pyenv** - Python version manager
- **asdf** - Multi-language version manager
- **poetry** - Python dependency manager
- **pipenv** - Python packaging tool
- **VS Code** - Can detect Python version
- **PyCharm** - IDE integration

#### Create .python-version File

```bash
# Create .python-version file
echo "3.11" > .python-version

# Now uv will automatically use Python 3.11
uv venv  # Creates venv with Python 3.11 (no --python flag needed!)

# Other tools respect it too
pyenv install $(cat .python-version)
```

#### How It Works

When you run `uv venv` without specifying `--python`, uv looks for `.python-version`:

```bash
# Without .python-version
uv venv --python 3.11  # Must specify explicitly

# With .python-version containing "3.11"
uv venv  # Automatically uses 3.11!
```

#### Project Benefits

```
dlh-airflow-common/
├── .python-version       ← "3.11"
└── ...

✅ Team consistency - Everyone uses same Python version
✅ Tool compatibility - Works with uv, pyenv, poetry, etc.
✅ Less typing - No need for --python flag
✅ CI/CD friendly - Automated builds use correct version
```

## Virtual Environment Management

### Create Virtual Environment

```bash
# Create venv with default Python
uv venv

# Create venv with specific Python version
uv venv --python 3.11

# Create venv with custom name and location
uv venv /opt/airflow/venvs/dbt-venv --python 3.11

# Create venv with specific Python executable
uv venv --python /usr/bin/python3.11
```

### Activate Virtual Environment

```bash
# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

## Package Installation with uv

Once in a virtual environment (or using uv directly):

### Basic Package Installation

```bash
# Install single package
uv pip install dbt-core

# Install multiple packages
uv pip install dbt-core dbt-postgres dbt-snowflake

# Install from requirements.txt
uv pip install -r requirements.txt

# Install in editable mode
uv pip install -e .
uv pip install -e ".[dev]"
```

### Speed Comparison

```bash
# Traditional pip (slow)
time pip install dbt-core dbt-postgres
# Takes: 20-60 seconds

# With uv (fast!)
time uv pip install dbt-core dbt-postgres
# Takes: 2-5 seconds
```

## Complete Workflow: Setting Up Development Environment

### For dlh-airflow-common Development

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Python 3.11
uv python install 3.11

# 3. Clone repository
git clone <repository-url>
cd dlh-airflow-common

# 4. Create virtual environment with Python 3.11
uv venv --python 3.11

# 5. Activate virtual environment
source .venv/bin/activate

# 6. Install development dependencies
uv pip install -e ".[dev]"

# 7. Verify installation
python --version  # Should show Python 3.11.x
pytest --version
ruff --version
```

### For Airflow Worker DBT Setup

```bash
# 1. Install uv on Airflow worker
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Python 3.11
uv python install 3.11

# 3. Create DBT virtual environment
sudo mkdir -p /opt/airflow/venvs
sudo chown airflow:airflow /opt/airflow/venvs

# Switch to airflow user
sudo -u airflow bash

# 4. Create venv with Python 3.11
cd /opt/airflow/venvs
uv venv dbt-venv --python 3.11

# 5. Install dbt
source dbt-venv/bin/activate
uv pip install dbt-core dbt-postgres

# 6. Verify
python --version
dbt --version
```

## Configuration

### uv Configuration File

Create `.config/uv/uv.toml` (or `~/.config/uv/uv.toml`):

```toml
# Cache directory
cache-dir = "~/.cache/uv"

# Default Python version
python-version = "3.11"

# Index URLs
index-url = "https://pypi.org/simple"

# Extra index URLs (e.g., private PyPI)
extra-index-url = [
    "https://your-nexus-server/repository/pypi-private/simple"
]
```

### Project-Specific Configuration

In your project root, create `.python-version`:

```
3.11
```

This tells uv (and other tools) to use Python 3.11 for this project.

## Advanced Usage

### Working with Multiple Python Versions

```bash
# Create venvs for different Python versions
uv venv venv-py38 --python 3.8
uv venv venv-py39 --python 3.9
uv venv venv-py311 --python 3.11

# Activate different versions
source venv-py311/bin/activate
python --version  # 3.11.x

deactivate
source venv-py38/bin/activate
python --version  # 3.8.x
```

### Syncing Dependencies

```bash
# Install exact versions from lock file
uv pip sync requirements.txt

# Compile dependencies
uv pip compile pyproject.toml -o requirements.txt
```

### Using with CI/CD

```yaml
# .gitlab-ci.yml example
test:
  image: ubuntu:22.04
  before_script:
    # Install uv
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

    # Install Python 3.11
    - uv python install 3.11

    # Create venv and install dependencies
    - uv venv --python 3.11
    - source .venv/bin/activate
    - uv pip install -e ".[dev]"

  script:
    - pytest
    - ruff check src/
    - mypy src/
```

## Troubleshooting

### uv not found after installation

```bash
# Add to PATH manually
export PATH="$HOME/.cargo/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Python version not found

```bash
# Install the Python version first
uv python install 3.11

# Then create venv
uv venv --python 3.11
```

### Permission denied on /opt/airflow

```bash
# Create directory with correct permissions
sudo mkdir -p /opt/airflow/venvs
sudo chown -R $USER:$USER /opt/airflow/venvs

# Or use sudo
sudo uv venv /opt/airflow/venvs/dbt-venv --python 3.11
```

### SSL certificate errors

```bash
# Trust host (for private PyPI)
uv pip install --trusted-host your-nexus-server.com package-name
```

## Comparison: pip vs uv

| Feature | pip | uv |
|---------|-----|-----|
| Speed | Baseline | 10-100x faster |
| Python version management | ❌ | ✅ |
| Dependency resolution | Slow | Fast |
| Cache | Limited | Smart caching |
| Parallel downloads | ❌ | ✅ |
| Cross-platform | ✅ | ✅ |
| Pip compatibility | ✅ | ✅ (drop-in) |

## Best Practices

### 1. Use Python 3.11 for New Projects

```bash
# Always specify Python version
uv venv --python 3.11
```

### 2. Pin Dependencies

```bash
# Create requirements.txt with pinned versions
uv pip freeze > requirements.txt
```

### 3. Use Virtual Environments

```bash
# Always work in venvs
uv venv
source .venv/bin/activate
```

### 4. Cache Management

```bash
# Clean cache if needed
uv cache clean

# Show cache info
uv cache info
```

### 5. Use .python-version

```bash
# Pin Python version for project
echo "3.11" > .python-version
```

## Migration from pip to uv

### Step 1: Install uv

```bash
pip install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Replace pip commands

```bash
# Old way
pip install package

# New way
uv pip install package
```

### Step 3: Recreate virtual environments

```bash
# Old way
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# New way
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [uv Python Docs](https://docs.astral.sh/uv/concepts/python-versions/)
- [uv GitHub](https://github.com/astral-sh/uv)
- [Astral (creators of ruff and uv)](https://astral.sh/)

## Quick Reference

```bash
# Installation
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python management
uv python install 3.11              # Install Python 3.11
uv python list                      # List installed versions
uv python find 3.11                 # Find Python 3.11 path

# Virtual environments
uv venv --python 3.11               # Create venv with Python 3.11
source .venv/bin/activate           # Activate (Linux/macOS)

# Package management
uv pip install package              # Install package
uv pip install -r requirements.txt  # Install from requirements
uv pip install -e ".[dev]"          # Editable install with extras
uv pip list                         # List packages
uv pip freeze                       # Show installed versions

# Cache
uv cache clean                      # Clean cache
uv cache info                       # Show cache info
```
