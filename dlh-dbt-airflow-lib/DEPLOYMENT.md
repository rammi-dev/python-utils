# Deployment Guide to Nexus PyPI

This guide explains how to deploy the `dlh-airflow-common` package to a private Nexus PyPI repository.

## Prerequisites

1. Python 3.11 (recommended) or 3.8+
2. [uv](https://github.com/astral-sh/uv) installed (recommended) or pip
3. Access to your Nexus repository
4. Nexus credentials (username and password)
5. `twine` for publishing

### Installing uv and Python 3.11

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.11
uv python install 3.11

# Install twine
uv pip install twine
```

## Setup

### 1. Configure Nexus Repository

Create or update your `~/.pypirc` file with Nexus credentials:

```ini
[distutils]
index-servers =
    nexus

[nexus]
repository = https://your-nexus-server.com/repository/pypi-private/
username = your-username
password = your-password
```

Alternatively, use environment variables (recommended for CI/CD):

```bash
export TWINE_USERNAME=your-username
export TWINE_PASSWORD=your-password
export TWINE_REPOSITORY_URL=https://your-nexus-server.com/repository/pypi-private/
```

### 2. Verify Nexus Repository Setup

Ensure your Nexus repository is configured to accept PyPI packages:

1. Log in to Nexus web interface
2. Navigate to Repositories
3. Verify you have a `pypi-private` (hosted) repository
4. Check that your user has deployment permissions

## Building the Package

### Option 1: Using uv (Recommended - Fastest)

```bash
# Ensure you're in the project directory with Python 3.11 venv
uv venv --python 3.11
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install build dependencies
uv pip install build

# Build the package
python -m build

# Or combine with uv run
uv run python -m build
```

### Option 2: Using Make

```bash
make build
```

### Option 3: Using Tox

```bash
tox -e build
```

### Option 4: Traditional pip

```bash
pip install build
python -m build
```

This creates two files in `dist/`:
- `dlh_airflow_common-X.Y.Z.tar.gz` (source distribution)
- `dlh_airflow_common-X.Y.Z-py3-none-any.whl` (wheel distribution)

### Build Speed Comparison

| Method | Typical Time | Notes |
|--------|-------------|-------|
| uv + build | ~2-5s | **Fastest**, recommended |
| pip + build | ~10-20s | Traditional method |
| make build | ~10-20s | Uses pip internally |
| tox -e build | ~15-30s | Full environment setup |

## Publishing to Nexus

### Option 1: Using uv with twine (Recommended)

```bash
# Ensure twine is installed
uv pip install twine

# Method A: Using .pypirc configuration
uv run twine upload --repository nexus dist/*

# Method B: Using environment variables (better for CI/CD)
export TWINE_USERNAME=your-username
export TWINE_PASSWORD=your-password
export TWINE_REPOSITORY_URL=https://your-nexus-server.com/repository/pypi-private/
uv run twine upload dist/*

# Or if venv is activated
source .venv/bin/activate
twine upload --repository nexus dist/*
```

### Option 2: Using Make

```bash
make publish-nexus
```

### Option 3: Direct twine with .pypirc

```bash
twine upload --repository nexus dist/*
```

### Option 4: Direct twine with environment variables

```bash
twine upload \
  --repository-url https://your-nexus-server.com/repository/pypi-private/ \
  --username your-username \
  --password your-password \
  dist/*
```

## Verify Upload

After uploading, verify the package is available:

### Using uv (Recommended)

```bash
# Create a clean test environment
uv venv test-env --python 3.11
source test-env/bin/activate

# Install from Nexus
uv pip install dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple

# Verify version
python -c "import dlh_airflow_common; print(dlh_airflow_common.__version__)"

# Test imports
python -c "from dlh_airflow_common.operators import DbtOperator; print('Success!')"

# Cleanup
deactivate
rm -rf test-env
```

### Using pip

```bash
pip install dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple \
  --trusted-host your-nexus-server.com
```

## Version Management

### Updating Version

1. Update version in [pyproject.toml](pyproject.toml):
   ```toml
   [project]
   version = "0.2.0"
   ```

2. Update version in [src/dlh_airflow_common/__init__.py](src/dlh_airflow_common/__init__.py):
   ```python
   __version__ = "0.2.0"
   ```

3. Commit changes:
   ```bash
   git add pyproject.toml src/dlh_airflow_common/__init__.py
   git commit -m "Bump version to 0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```

4. Build and publish new version

### Semantic Versioning

Follow semantic versioning (SemVer):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

## CI/CD Integration

### GitLab CI

The project includes a [.gitlab-ci.yml](.gitlab-ci.yml) file with:

1. **Test Stage**: Runs linting, formatting, type checking, and tests
2. **Build Stage**: Builds the package
3. **Deploy Stage**: Publishes to Nexus on tags

#### Required GitLab Variables

Set these in GitLab CI/CD Settings > Variables:

- `NEXUS_REPOSITORY_URL`: Your Nexus PyPI repository URL
- `NEXUS_USERNAME`: Nexus username
- `NEXUS_PASSWORD`: Nexus password (mark as protected and masked)

#### Triggering Deployment

```bash
# Create and push a tag
git tag v0.1.0
git push origin v0.1.0
```

This automatically triggers the CI/CD pipeline and deploys to Nexus.

### GitHub Actions (with uv)

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to Nexus

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Add uv to PATH
        run: echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install Python 3.11
        run: uv python install 3.11

      - name: Create virtual environment
        run: uv venv --python 3.11

      - name: Install dependencies
        run: |
          source .venv/bin/activate
          uv pip install build twine

      - name: Build package
        run: |
          source .venv/bin/activate
          python -m build

      - name: Publish to Nexus
        env:
          TWINE_USERNAME: ${{ secrets.NEXUS_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.NEXUS_PASSWORD }}
          TWINE_REPOSITORY_URL: ${{ secrets.NEXUS_REPOSITORY_URL }}
        run: |
          source .venv/bin/activate
          twine upload dist/*
```

## Installing from Nexus

### Direct Installation with uv (Recommended)

```bash
# Install in current environment
uv pip install dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple

# Or create new project with it
uv venv --python 3.11
source .venv/bin/activate
uv pip install dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple
```

### Direct Installation with pip

```bash
pip install dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple
```

### In requirements.txt

```txt
--index-url https://your-nexus-server.com/repository/pypi-private/simple
dlh-airflow-common==0.1.0
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "dlh-airflow-common==0.1.0",
]

[[tool.pip.index-urls]]
url = "https://your-nexus-server.com/repository/pypi-private/simple"
```

### Using pip.conf

Create `~/.pip/pip.conf` (Linux/Mac) or `%APPDATA%\pip\pip.ini` (Windows):

```ini
[global]
index-url = https://your-nexus-server.com/repository/pypi-private/simple
trusted-host = your-nexus-server.com
```

## Troubleshooting

### Authentication Issues

If you get 401/403 errors:
1. Verify credentials in `.pypirc` or environment variables
2. Check user permissions in Nexus
3. Ensure the repository allows deployments

### Upload Conflicts

If package version already exists:
1. Nexus hosted repositories typically don't allow redeployment
2. Bump the version number
3. Or delete the old version from Nexus (if permissions allow)

### SSL Certificate Issues

For self-signed certificates:

```bash
# Add to pip command
pip install --trusted-host your-nexus-server.com ...

# Or configure globally in pip.conf
[global]
trusted-host = your-nexus-server.com
```

### Connection Issues

Check network connectivity:

```bash
curl -v https://your-nexus-server.com/repository/pypi-private/
```

## Security Best Practices

1. **Never commit credentials** to version control
2. Use environment variables or secret management tools
3. Mark CI/CD secrets as protected and masked
4. Rotate credentials regularly
5. Use token-based authentication when available
6. Restrict deployment permissions to necessary users/services

## Rollback

To rollback to a previous version:

1. Install specific version:
   ```bash
   pip install dlh-airflow-common==0.1.0 --index-url ...
   ```

2. Or delete problematic version from Nexus and redeploy

## Complete Deployment Workflow with uv

Here's a complete end-to-end workflow using uv:

```bash
# 1. Install uv and Python 3.11
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11

# 2. Clone and setup project
git clone <repository-url>
cd dlh-airflow-common
uv venv --python 3.11
source .venv/bin/activate

# 3. Make changes and update version
vim src/dlh_airflow_common/__init__.py  # Update __version__
vim pyproject.toml  # Update version

# 4. Run tests and quality checks
uv pip install -e ".[dev]"
pytest
ruff check src/
black --check src/
mypy src/

# 5. Commit and tag
git add .
git commit -m "Bump version to 0.2.0"
git tag v0.2.0
git push origin main --tags

# 6. Build package
uv pip install build
python -m build

# 7. Publish to Nexus
uv pip install twine
export TWINE_USERNAME=your-username
export TWINE_PASSWORD=your-password
export TWINE_REPOSITORY_URL=https://your-nexus-server.com/repository/pypi-private/
twine upload dist/*

# 8. Verify deployment
uv venv test-env --python 3.11
source test-env/bin/activate
uv pip install dlh-airflow-common==0.2.0 \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple
python -c "import dlh_airflow_common; print(dlh_airflow_common.__version__)"
deactivate
rm -rf test-env
```

## Quick Reference

### Build and Deploy (uv)

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build
uv venv --python 3.11
source .venv/bin/activate
uv pip install build
python -m build

# Deploy
uv pip install twine
twine upload --repository nexus dist/*
```

### Speed Benefits

| Operation | pip | uv | Improvement |
|-----------|-----|-----|-------------|
| Install deps | ~30s | ~3s | **10x faster** |
| Build package | ~15s | ~5s | **3x faster** |
| Create venv | ~8s | ~1s | **8x faster** |
| Total workflow | ~53s | ~9s | **6x faster** |

## Support

For issues with:
- Package functionality: Open issue on repository
- Nexus access: Contact your Nexus administrator
- CI/CD pipeline: Check GitLab/GitHub logs and configuration
- uv usage: See [UV_SETUP.md](UV_SETUP.md)
