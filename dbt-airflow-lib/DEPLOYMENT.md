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

Create or update your ` ` file with Nexus credentials:

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

## Version Management (setuptools-scm)

This project uses **setuptools-scm** for automatic version management. The version is derived directly from git tags - no manual version updates required.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     VERSION DERIVATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Git Tag          →    Package Version                          │
│  ─────────────────────────────────────────────                  │
│  v1.0.0           →    1.0.0                                    │
│  v1.2.3           →    1.2.3                                    │
│  v2.0.0-rc1       →    2.0.0rc1                                 │
│                                                                  │
│  After tag (3 commits after v1.2.0):                            │
│  No tag yet       →    1.2.1.dev3                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Release Process

#### Step 1: Prepare Your Release

```bash
# Ensure you're on main with latest changes
git checkout main
git pull origin main

# Verify all tests pass
pytest
ruff check src/
mypy src/
```

#### Step 2: Create Git Tag

```bash
# Create annotated tag (recommended)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Or lightweight tag
git tag v1.0.0

# Push tag to remote
git push origin v1.0.0
```

#### Step 3: CI Builds and Publishes Automatically

Once the tag is pushed:
1. CI detects the new tag
2. `setuptools-scm` reads the tag → version becomes `1.0.0`
3. Package is built with that version
4. Package is uploaded to Nexus

#### Step 4: Verify the Release

```bash
# Check available versions in Nexus
pip index versions dlh-airflow-common \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple

# Install and verify
pip install dlh-airflow-common==1.0.0 \
  --index-url https://your-nexus-server.com/repository/pypi-private/simple

python -c "import dlh_airflow_common; print(dlh_airflow_common.__version__)"
# Output: 1.0.0
```

### Version Formats

| Git State | Package Version | Use Case |
|-----------|-----------------|----------|
| Exactly on `v1.2.0` tag | `1.2.0` | Production release |
| 3 commits after `v1.2.0` | `1.2.1.dev3` | Development build |
| No tags exist | `0.0.0.dev1` | Initial development |

### Tagging Best Practices

```bash
# List existing tags
git tag -l

# View tag details
git show v1.0.0

# Delete local tag (if mistake)
git tag -d v1.0.0

# Delete remote tag (if mistake - use carefully!)
git push origin --delete v1.0.0

# Create tag from specific commit
git tag -a v1.0.0 abc1234 -m "Release 1.0.0"
```

### Semantic Versioning

Follow semantic versioning (SemVer):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

### Pre-release Versions

```bash
# Alpha release
git tag v1.0.0a1

# Beta release
git tag v1.0.0b1

# Release candidate
git tag v1.0.0rc1
```

### Local Development Version Check

```bash
# See what version would be generated from current git state
python -c "from setuptools_scm import get_version; print(get_version())"
```

## CI/CD Integration

### GitLab CI - Dev/Prod Pipeline

The project uses a two-stage deployment model with separate Dev and Prod Nexus repositories.

#### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────┐   ┌────────┐   ┌────────────┐   ┌────────────┐      │
│  │  TEST  │ → │ BUILD  │ → │ DEPLOY-DEV │ → │ DEPLOY-PROD│      │
│  └────────┘   └────────┘   └────────────┘   └────────────┘      │
│                                                                  │
│  Stages run on:                                                  │
│  • MR opened     → Test, Build, Deploy-Dev (manual)             │
│  • Push to main  → Test, Build, Deploy-Dev (auto)               │
│  • Git tag       → Test, Build, Deploy-Prod (auto)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Trigger Rules

| Trigger | Test | Build | Deploy Dev | Deploy Prod |
|---------|------|-------|------------|-------------|
| MR opened | ✓ Auto | ✓ Auto | Manual | - |
| Push to main | ✓ Auto | ✓ Auto | ✓ Auto | Manual |
| Git tag `v1.0.0` | ✓ Auto | ✓ Auto | - | ✓ Auto |

#### Required GitLab Variables

Set these in **GitLab → Settings → CI/CD → Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXUS_USERNAME` | Nexus authentication username | `deployer` |
| `NEXUS_PASSWORD` | Nexus password (masked) | `***` |
| `NEXUS_DEV_URL` | Dev repository upload URL | `http://nexus:8081/repository/pypi-dev/` |
| `NEXUS_PROD_URL` | Prod repository upload URL | `http://nexus:8081/repository/pypi-prod/` |

#### Development Workflow

```bash
# 1. Work on feature branch, create MR
git checkout -b feature/new-operator
# ... make changes ...
git push origin feature/new-operator
# → CI runs tests, build available
# → Can manually deploy to DEV for testing

# 2. Merge to main
# → CI auto-deploys to DEV Nexus
# → Version: 1.0.1.dev3 (dev version)

# 3. Ready for production release
git checkout main
git pull
git tag -a v1.1.0 -m "Release 1.1.0"
git push origin v1.1.0
# → CI auto-deploys to PROD Nexus
# → Version: 1.1.0 (stable version)
```

#### Version Flow

```
Development (main branch)     Production (git tags)
─────────────────────────     ────────────────────
     │                              │
     ▼                              ▼
  1.0.1.dev1  ─────────────→   v1.1.0 tag
  1.0.1.dev2                       │
  1.0.1.dev3                       ▼
     │                          1.1.0
     ▼                              │
  pypi-dev                     pypi-prod
```

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

### Repository URLs

| Repository | Purpose | Mutable | URL |
|------------|---------|---------|-----|
| `pypi-dev` | Development/testing | ✓ Yes | `http://nexus:8081/repository/pypi-dev/simple/` |
| `pypi-prod` | Production releases | ✗ No | `http://nexus:8081/repository/pypi-prod/simple/` |
| `pypi-group` | Combined (prod + pypi.org) | - | `http://nexus:8081/repository/pypi-group/simple/` |

### Repository Policies

```
┌─────────────────────────────────────────────────────────────────┐
│                    REPOSITORY POLICIES                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  pypi-dev (MUTABLE)                                              │
│  ├── Allow redeploy: YES                                         │
│  ├── Same version can be overwritten                             │
│  ├── Use for: testing, iteration, CI builds                      │
│  └── Versions: 1.0.1.dev1, 1.0.1.dev2, ...                      │
│                                                                  │
│  pypi-prod (IMMUTABLE)                                           │
│  ├── Allow redeploy: NO                                          │
│  ├── Once published, version is permanent                        │
│  ├── Use for: stable releases only                               │
│  └── Versions: 1.0.0, 1.1.0, 2.0.0, ...                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why immutable prod?**
- Reproducible builds - same version always means same code
- Audit trail - can trace exactly what was deployed
- Security - prevents accidental or malicious overwrites
- Compliance - many regulations require immutable artifacts

### Install from DEV (Testing)

```bash
# Install dev version for testing
pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-dev/simple/

# Install specific dev version
pip install dlh-airflow-common==1.0.1.dev3 \
  --index-url http://nexus:8081/repository/pypi-dev/simple/
```

### Install from PROD (Production)

```bash
# Install stable version
pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-prod/simple/

# Or use group (includes public PyPI packages too)
pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-group/simple/
```

### Direct Installation with uv (Recommended)

```bash
# From prod
uv pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-prod/simple/

# From dev (for testing)
uv pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-dev/simple/
```

### In requirements.txt

```txt
# For production
--index-url http://nexus:8081/repository/pypi-group/simple/
dlh-airflow-common==1.0.0

# For development/testing
# --index-url http://nexus:8081/repository/pypi-dev/simple/
# dlh-airflow-common==1.0.1.dev3
```

### Using pip.conf

Create `~/.pip/pip.conf` (Linux/Mac) or `%APPDATA%\pip\pip.ini` (Windows):

```ini
[global]
# Use group repo (combines prod + public pypi)
index-url = http://nexus:8081/repository/pypi-group/simple/
trusted-host = nexus

# For dev environments, use:
# index-url = http://nexus:8081/repository/pypi-dev/simple/
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

Here's a complete end-to-end workflow using uv, setuptools-scm, and the dev/prod pipeline:

```bash
# 1. Install uv and Python 3.11
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.11

# 2. Clone and setup project
git clone <repository-url>
cd dlh-airflow-common
uv venv --python 3.11
source .venv/bin/activate

# 3. Make your changes (no version editing needed!)
# ... edit source files ...

# 4. Run tests and quality checks
uv pip install -e ".[dev]"
pytest
ruff check src/
black --check src/
mypy src/

# 5. Commit and push to main
git add .
git commit -m "Add new feature XYZ"
git push origin main
# → CI auto-deploys to DEV Nexus (version: 1.0.1.dev4)

# 6. Test from DEV repository
uv pip install dlh-airflow-common \
  --index-url http://nexus:8081/repository/pypi-dev/simple/ \
  --upgrade
python -c "import dlh_airflow_common; print(dlh_airflow_common.__version__)"
# Output: 1.0.1.dev4

# 7. Ready for production? Create and push tag
git tag -a v1.1.0 -m "Release 1.1.0 - Add feature XYZ"
git push origin v1.1.0
# → CI auto-deploys to PROD Nexus (version: 1.1.0)

# 8. Verify production deployment
uv pip install dlh-airflow-common==1.1.0 \
  --index-url http://nexus:8081/repository/pypi-prod/simple/
python -c "import dlh_airflow_common; print(dlh_airflow_common.__version__)"
# Output: 1.1.0
```

### Manual Deployment (if needed)

```bash
# Build package
python -m build

# Deploy to DEV
twine upload --repository nexus-dev dist/*

# Deploy to PROD (after testing)
twine upload --repository nexus-prod dist/*
```

Requires `~/.pypirc`:
```ini
[distutils]
index-servers = nexus-dev nexus-prod

[nexus-dev]
repository = http://nexus:8081/repository/pypi-dev/
username = your-user
password = your-pass

[nexus-prod]
repository = http://nexus:8081/repository/pypi-prod/
username = your-user
password = your-pass
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
