# Python 3.11 + uv Quick Reference

Quick reference for using Python 3.11 with uv for the dlh-airflow-common project.

## One-Time Setup

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install Python 3.11
uv python install 3.11

# 3. Verify
uv python list
```

## Project Setup (Development)

```bash
# Clone and setup project
git clone <repository-url>
cd dlh-airflow-common

# Create venv with Python 3.11
uv venv --python 3.11

# Activate
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e ".[dev]"

# Verify
python --version           # Should show 3.11.x
pytest --version
```

## Airflow Worker Setup (DBT)

```bash
# On Airflow worker
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11

# Create DBT venv
sudo mkdir -p /opt/airflow/venvs
sudo chown airflow:airflow /opt/airflow/venvs

# As airflow user
sudo -u airflow bash
cd /opt/airflow/venvs
uv venv dbt-venv --python 3.11
source dbt-venv/bin/activate

# Install dbt
uv pip install dbt-core dbt-dremio

# Verify
python --version  # 3.11.x
dbt --version
```

## Daily Commands

```bash
# Install new package
uv pip install package-name

# Update package
uv pip install --upgrade package-name

# Install from requirements
uv pip install -r requirements.txt

# Freeze dependencies
uv pip freeze > requirements.txt

# Run tests
pytest

# Code quality
ruff check src/
black src/
mypy src/
```

## Common Operations

### Create New Virtual Environment

```bash
# Default (uses .python-version file = 3.11)
uv venv

# Explicit Python 3.11
uv venv --python 3.11

# Custom location
uv venv /path/to/venv --python 3.11
```

### List Python Versions

```bash
# Installed versions
uv python list

# Find specific version
uv python find 3.11

# All available versions
uv python list --all-versions
```

### Switch Python Versions

```bash
# Create venvs with different versions
uv venv venv-38 --python 3.8
uv venv venv-311 --python 3.11

# Activate desired version
source venv-311/bin/activate
```

## Troubleshooting

### uv not found

```bash
export PATH="$HOME/.cargo/bin:$PATH"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
```

### Python 3.11 not found

```bash
# Install it first
uv python install 3.11

# Verify
uv python list
```

### Wrong Python version in venv

```bash
# Remove old venv
rm -rf .venv

# Create new with explicit version
uv venv --python 3.11

# Verify
source .venv/bin/activate
python --version
```

## Speed Comparison

| Operation | pip | uv | Speedup |
|-----------|-----|-----|---------|
| Install dbt-core | ~30s | ~3s | 10x |
| Install all dev deps | ~60s | ~6s | 10x |
| Create venv | ~5s | ~1s | 5x |

## Why Python 3.11?

- **Performance**: 10-60% faster than Python 3.10
- **Better error messages**: Enhanced traceback
- **Type hints**: Improved type system
- **Airflow 3.1**: Fully compatible
- **dbt**: Officially supported
- **Long-term support**: Active until 2027

## File Structure

```
dlh-airflow-common/
├── .python-version          # Pin to 3.11
├── pyproject.toml           # Requires Python >= 3.8
├── .venv/                   # Virtual environment (Python 3.11)
└── src/
```

## Integration with CI/CD

### GitLab CI

```yaml
test:
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
    - uv python install 3.11
    - uv venv --python 3.11
    - source .venv/bin/activate
    - uv pip install -e ".[dev]"
  script:
    - pytest
```

### GitHub Actions

```yaml
- uses: actions/checkout@v4
- name: Setup uv
  run: curl -LsSf https://astral.sh/uv/install.sh | sh
- name: Setup Python 3.11
  run: |
    uv python install 3.11
    uv venv --python 3.11
    source .venv/bin/activate
    uv pip install -e ".[dev]"
- name: Run tests
  run: pytest
```

## Additional Resources

- [UV Setup Guide](UV_SETUP.md) - Complete uv setup guide
- [DBT Setup Guide](DBT_SETUP.md) - DBT operator setup with Python 3.11
- [Python Version File](PYTHON_VERSION_FILE.md) - Understanding `.python-version`
- [uv documentation](https://github.com/astral-sh/uv)
- [Python 3.11 docs](https://docs.python.org/3.11/)

## Quick Tips

1. **Always pin Python version**: Use `.python-version` file
2. **Use uv for speed**: 10-100x faster than pip
3. **Verify version**: Check with `python --version` after activating venv
4. **Clean cache**: `uv cache clean` if issues occur
5. **Update uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
