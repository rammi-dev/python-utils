# GitLab CI/CD Setup Guide

This guide explains the automated CI/CD pipeline with semantic versioning for the dlh-airflow-common project.

## Overview

The GitLab CI/CD pipeline provides:
- ✅ **Automatic semantic versioning** based on merge request descriptions
- ✅ **Quality checks** (linting, formatting, type checking, tests)
- ✅ **Automated builds** with uv and Python 3.11
- ✅ **Git tagging** on successful merges
- ✅ **Nexus deployment** for distribution
- ✅ **Security scanning** with bandit and safety

## Pipeline Stages

```
version → test → build → deploy
   ↓       ↓       ↓       ↓
Calculate  Lint   Build   Tag
Version    Format Package Version
          Types           Deploy
          Tests           Nexus
          Security        Release
```

## Semantic Versioning

### How It Works

The pipeline automatically calculates the next version based on **keywords in your merge request description**:

| Keyword | Version Bump | Example |
|---------|-------------|---------|
| `[MAJOR]` | Breaking changes | 1.2.3 → 2.0.0 |
| `[MINOR]` | New features | 1.2.3 → 1.3.0 |
| `[PATCH]` | Bug fixes (default) | 1.2.3 → 1.2.4 |

### Version Source

The pipeline gets the **last tag from the target branch** (e.g., `main`) as the base version:

```bash
# If last tag on main is v1.2.3
# And MR description contains [MINOR]
# New version will be v1.3.0
```

### Example Merge Request Descriptions

#### Major Version Bump (Breaking Changes)

```
Refactor DBT operator API [MAJOR]

Breaking changes:
- Renamed `dbt_project_path` to `dbt_project_dir`
- Changed `tags` parameter to `dbt_tags`
- Removed deprecated `legacy_mode` option

This requires users to update their DAGs.
```

Result: `1.2.3` → `2.0.0`

#### Minor Version Bump (New Features)

```
Add support for dbt snapshot command [MINOR]

New features:
- Added DbtSnapshotOperator
- Support for snapshot-specific options
- Added examples in documentation

Backward compatible with existing code.
```

Result: `1.2.3` → `1.3.0`

#### Patch Version Bump (Bug Fixes)

```
Fix validation error for custom profiles directory [PATCH]

Bug fixes:
- Fixed path validation in DbtOperator
- Corrected error message formatting
- Added test case for edge case

No API changes.
```

Result: `1.2.3` → `1.2.4`

#### Default (No Keyword = Patch)

```
Update documentation for DBT setup

- Clarified Python 3.11 installation steps
- Added troubleshooting section
- Fixed typos
```

Result: `1.2.3` → `1.2.4` (defaults to PATCH)

## GitLab Configuration

### Required Variables

Set these in **Settings → CI/CD → Variables**:

| Variable | Description | Protected | Masked |
|----------|-------------|-----------|--------|
| `NEXUS_REPOSITORY_URL` | Nexus PyPI URL | ✅ | ❌ |
| `NEXUS_USERNAME` | Nexus username | ✅ | ❌ |
| `NEXUS_PASSWORD` | Nexus password | ✅ | ✅ |
| `CI_PUSH_TOKEN` | Personal/Project access token | ✅ | ✅ |

### Creating CI_PUSH_TOKEN

The `CI_PUSH_TOKEN` is needed to push tags and commits back to the repository.

#### Option 1: Project Access Token (Recommended)

1. Go to **Settings → Access Tokens**
2. Click **Add new token**
3. Name: `ci-push-token`
4. Role: **Maintainer**
5. Scopes: ☑️ `write_repository`
6. Click **Create project access token**
7. Copy the token and add as CI/CD variable `CI_PUSH_TOKEN`

#### Option 2: Personal Access Token

1. Go to **User Settings → Access Tokens**
2. Name: `gitlab-ci-push`
3. Scopes: ☑️ `write_repository`
4. Create and copy token
5. Add as CI/CD variable `CI_PUSH_TOKEN`

### Repository Settings

Enable these settings in **Settings → Repository**:

1. **Protected Branches**
   - Branch: `main` (or `master`)
   - Allowed to push: **Maintainers**
   - Allowed to merge: **Developers + Maintainers**

2. **Protected Tags**
   - Tag: `v*`
   - Allowed to create: **Maintainers** + CI/CD

## Workflow

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/add-dbt-snapshot

# 2. Make changes
# ... code changes ...

# 3. Commit changes
git add .
git commit -m "Add DbtSnapshotOperator"
git push origin feature/add-dbt-snapshot

# 4. Create Merge Request
# Description: "Add support for dbt snapshot [MINOR]"

# 5. Pipeline runs automatically:
#    - Calculates version: 0.1.0 → 0.2.0
#    - Runs tests
#    - Creates build (manual trigger)

# 6. After approval, merge to main

# 7. On merge to main, pipeline:
#    - Runs tests again
#    - Builds package with version 0.2.0
#    - Creates git tag v0.2.0
#    - Deploys to Nexus
```

### Pipeline Execution

#### On Merge Request

```
┌─────────────────────┐
│ calculate_version   │ ← Determines next version
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ test:lint           │ ← Ruff linting
│ test:format         │ ← Black formatting
│ test:type-check     │ ← Mypy type checking
│ test:pytest         │ ← Unit tests with coverage
│ test:security       │ ← Security scanning
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ build:package       │ ← Manual trigger
└─────────────────────┘
```

#### On Merge to Main

```
┌─────────────────────┐
│ calculate_version   │ ← Re-calculates version
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ All Tests           │ ← Same as MR
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ build:package       │ ← Auto builds
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ deploy:tag-version  │ ← Creates git tag
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ deploy:nexus        │ ← Deploys to Nexus
│ create:release-notes│ ← Generates changelog
└─────────────────────┘
```

## Pipeline Jobs Explained

### Version Stage

#### `calculate_version`
- Reads last tag from target branch
- Parses MR description for version keywords
- Calculates new semantic version
- Saves to `version.txt` for later jobs

### Test Stage

#### `test:lint`
- Runs `ruff check` on source and tests
- Ensures code quality standards

#### `test:format`
- Runs `black --check` on source and tests
- Ensures consistent code formatting

#### `test:type-check`
- Runs `mypy` on source code
- Validates type hints

#### `test:pytest`
- Runs unit tests with pytest
- Generates coverage reports (XML, HTML)
- Coverage badge in README

#### `test:security`
- Runs `bandit` for security vulnerabilities
- Runs `safety` for known CVEs in dependencies
- Allows failure (won't block pipeline)

### Build Stage

#### `build:package`
- Updates version in `pyproject.toml` and `__init__.py`
- Builds wheel and source distribution with `python -m build`
- Saves artifacts for deployment

**Trigger:**
- MR: Manual trigger only
- Main: Automatic after tests pass

### Deploy Stage

#### `deploy:tag-version`
- Commits version changes
- Creates annotated git tag (e.g., `v0.2.0`)
- Pushes tag to repository
- Only runs on `main` branch

#### `deploy:nexus`
- Uploads package to Nexus PyPI
- Only runs after successful tagging
- Requires `NEXUS_*` variables

#### `deploy:nexus-manual`
- Manual deployment option for MRs
- Useful for testing Nexus upload

#### `create:release-notes`
- Generates changelog from commits
- Creates `RELEASE_NOTES.md`
- Optional (can fail without blocking)

## Troubleshooting

### Version Not Incrementing

**Problem:** Version stays the same

**Solution:**
- Check MR description contains `[MAJOR]`, `[MINOR]`, or `[PATCH]`
- Verify tags exist on target branch: `git tag -l`
- Check pipeline logs for version calculation

### Tag Push Failed

**Problem:** `deploy:tag-version` fails with permission error

**Solution:**
- Verify `CI_PUSH_TOKEN` is set in CI/CD variables
- Ensure token has `write_repository` scope
- Check protected tags settings allow CI/CD to create tags

### Nexus Upload Failed

**Problem:** `deploy:nexus` fails with 401/403 error

**Solution:**
- Verify `NEXUS_USERNAME` and `NEXUS_PASSWORD` are correct
- Check `NEXUS_REPOSITORY_URL` format
- Ensure Nexus repository exists and accepts uploads
- Verify user has deployment permissions in Nexus

### Tests Failing

**Problem:** Pipeline fails at test stage

**Solution:**
- Run tests locally: `pytest`
- Check specific failing test in pipeline logs
- Fix code and push again

### Build Fails on Version Update

**Problem:** `sed` command fails to update version

**Solution:**
- Verify `pyproject.toml` has `version = "X.Y.Z"` format
- Check `__init__.py` has `__version__ = "X.Y.Z"` format
- Review pipeline logs for sed errors

## Best Practices

### 1. Always Use Version Keywords

```
✅ Good: "Add new feature [MINOR]"
✅ Good: "Fix bug in validation [PATCH]"
✅ Good: "Breaking API change [MAJOR]"
❌ Bad: "Add new feature" (defaults to PATCH)
```

### 2. Meaningful Commit Messages

```
✅ Good: "feat: add DbtSnapshotOperator with tests"
❌ Bad: "updates"
```

### 3. Test Before Merging

- Create MR and wait for tests to pass
- Review coverage report
- Manually trigger build to verify

### 4. Protect Main Branch

- Require approvals before merge
- Require pipeline to pass
- Don't push directly to main

### 5. Tag Naming Convention

- Always use `v` prefix: `v1.2.3`
- Follow semantic versioning: `MAJOR.MINOR.PATCH`
- Never delete or modify tags

## Example Pipeline Run

### Merge Request Example

```
MR: "Add snapshot support [MINOR]"
Current version on main: v0.1.0

Pipeline execution:
├── calculate_version
│   └── Result: 0.2.0
├── test:lint ✓
├── test:format ✓
├── test:type-check ✓
├── test:pytest ✓
└── build:package (manual) ✓
```

### After Merge to Main

```
Merge to main completed

Pipeline execution:
├── calculate_version
│   └── Result: 0.2.0
├── All tests ✓
├── build:package ✓
├── deploy:tag-version ✓
│   └── Created tag: v0.2.0
├── deploy:nexus ✓
│   └── Uploaded to Nexus
└── create:release-notes ✓
    └── Generated RELEASE_NOTES.md
```

## Quick Reference

### Version Keywords

```
[MAJOR] → Breaking changes   → X.0.0
[MINOR] → New features       → 0.X.0
[PATCH] → Bug fixes          → 0.0.X
(none)  → Defaults to PATCH  → 0.0.X
```

### Required Variables

```bash
NEXUS_REPOSITORY_URL=https://nexus.example.com/repository/pypi-private/
NEXUS_USERNAME=deployment-user
NEXUS_PASSWORD=********
CI_PUSH_TOKEN=glpat-****************
```

### Common Commands

```bash
# View last tag
git describe --tags --abbrev=0

# View all tags
git tag -l

# Manually trigger version bump
git tag v0.2.0
git push origin v0.2.0

# Check pipeline status
# Go to CI/CD → Pipelines in GitLab
```

## Additional Resources

- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Semantic Versioning](https://semver.org/)
- [DEPLOYMENT.md](DEPLOYMENT.md) - Manual deployment guide
- [UV_SETUP.md](UV_SETUP.md) - uv installation and usage
