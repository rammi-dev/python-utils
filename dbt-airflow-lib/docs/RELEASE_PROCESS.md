# Release Process

This document describes the versioning and release workflow for dlh-airflow-common.

## Overview

- **Versioning**: Managed automatically by `setuptools-scm` based on git tags
- **Dev builds**: Published to Dev Nexus (mutable, can overwrite)
- **Prod releases**: Published to Prod Nexus (immutable, no overwrites)

## Branch Strategy

```
main                    → Active development for latest major version (e.g., v2.x)
release/1.x             → Maintenance branch for v1.x (bug fixes only)
release/2.x             → Created when v3.x development starts
feature/*               → Feature branches (merged to main or release/*)
```

## Version Naming

| Git State | Version Generated | Destination |
|-----------|-------------------|-------------|
| On tag `v1.0.0` | `1.0.0` | Prod repo |
| 3 commits after `v1.0.0` | `1.0.1.dev3` | Dev repo |
| On tag `v1.0.1` | `1.0.1` | Prod repo |

The `.devN` suffix is automatic - you never create dev tags manually.

## Initial Setup (First Release)

### Step 1: Create initial tag

```bash
# On main branch, create your first release
git tag v0.1.0
git push origin v0.1.0
```

This triggers:
- CI builds version `0.1.0`
- Deploys to **Prod Nexus**

### Step 2: Continue development

```bash
# Make changes
git commit -m "Add new feature"
git push origin main
```

This triggers:
- CI builds version `0.1.1.dev1`
- Deploys to **Dev Nexus**

## Regular Development Workflow

### Feature Development

```bash
# 1. Create feature branch
git checkout main
git pull
git checkout -b feature/add-snapshot-support

# 2. Make changes and commit
git commit -m "Add DbtSnapshotOperator"
git push origin feature/add-snapshot-support

# 3. Create Merge Request in GitLab
#    CI runs tests (no deployment)

# 4. After approval, merge to main
#    CI builds X.Y.Z.devN → deploys to Dev Nexus
```

### Testing Dev Version

```bash
# Install from Dev Nexus
pip install dlh-airflow-common==0.1.1.dev3 --index-url $NEXUS_DEV_URL/simple/

# Or install latest dev version
pip install dlh-airflow-common --index-url $NEXUS_DEV_URL/simple/ --pre
```

### Creating a Release

When ready to release:

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull

# 2. Create release tag
git tag v0.2.0
git push origin v0.2.0

# This triggers:
#   - CI builds version 0.2.0
#   - Deploys to Prod Nexus (immutable)
```

## Maintaining Multiple Major Versions

When you need to support both v1.x and v2.x:

### Creating a Release Branch

```bash
# When starting v2.0.0 development, create release branch for v1.x
git checkout v1.5.0  # Last v1.x tag
git checkout -b release/1.x
git push origin release/1.x
```

### Fixing Bugs in Old Version

```bash
# 1. Checkout release branch
git checkout release/1.x
git pull

# 2. Create fix branch
git checkout -b fix/critical-bug

# 3. Make fix and push
git commit -m "Fix critical bug in validation"
git push origin fix/critical-bug

# 4. Create MR targeting release/1.x (not main!)
#    After merge, CI deploys 1.5.1.dev1 to Dev Nexus

# 5. Test and release
git checkout release/1.x
git pull
git tag v1.5.1
git push origin v1.5.1
#    CI deploys 1.5.1 to Prod Nexus
```

### Cherry-picking to Main (if applicable)

```bash
# If the fix also applies to v2.x
git checkout main
git cherry-pick <commit-hash>
git push origin main
```

## Version Flow Diagram

```
Timeline →

main (v2.x development)
├── v2.0.0.dev1
├── v2.0.0.dev2
├── tag v2.0.0 ────────────────────► Prod: 2.0.0
├── v2.0.1.dev1
├── v2.0.1.dev2
├── tag v2.0.1 ────────────────────► Prod: 2.0.1
│
│   release/1.x (created from v1.5.0)
│   ├── v1.5.1.dev1 (bug fix)
│   ├── tag v1.5.1 ────────────────► Prod: 1.5.1
│   ├── v1.5.2.dev1 (another fix)
│   └── tag v1.5.2 ────────────────► Prod: 1.5.2
│
├── v2.1.0.dev1
└── tag v2.1.0 ────────────────────► Prod: 2.1.0
```

## CI/CD Pipeline Behavior

| Branch/Tag | Tests | Build | Dev Deploy | Prod Deploy |
|------------|-------|-------|------------|-------------|
| `feature/*` (MR) | Auto | Auto | Manual | - |
| `main` | Auto | Auto | Auto | Manual |
| `release/*` | Auto | Auto | Auto | Manual |
| `v*.*.*` tag | Auto | Auto | - | Auto |

## Best Practices

### DO

- Always create tags on `main` or `release/*` branches
- Use semantic versioning: `vMAJOR.MINOR.PATCH`
- Test dev versions before creating release tags
- Create release branches before starting new major versions

### DON'T

- Never delete or move tags
- Never tag feature branches
- Never deploy dev versions (`.devN`) to production manually
- Don't forget to push tags: `git push origin v1.0.0`

## Quick Reference

### Check Current Version Locally

```bash
# With setuptools-scm installed
python -c "from setuptools_scm import get_version; print(get_version())"
```

### List All Tags

```bash
git tag -l "v*" --sort=-version:refname
```

### Create Release

```bash
git tag v1.2.3 && git push origin v1.2.3
```

### Create Release Branch

```bash
git checkout v1.5.0 && git checkout -b release/1.x && git push origin release/1.x
```

## Troubleshooting

### "Version already exists in Prod"

Prod Nexus is immutable. You cannot overwrite versions. Create a new patch version:

```bash
git tag v1.0.1  # instead of trying to re-upload v1.0.0
git push origin v1.0.1
```

### "Cannot deploy dev version to production"

You're trying to deploy from a branch without a tag. Create a tag first:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### Version shows `0.0.0` or fails

No git tags exist. Create your first tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```
