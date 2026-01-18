#!/usr/bin/env bash
# Install git hooks for dbt-airflow-lib project

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Installing git hooks for dbt-airflow-lib...${NC}"

# Get the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Find the git hooks directory (could be in parent monorepo)
GIT_DIR=$(git rev-parse --git-dir)
HOOKS_DIR="$GIT_DIR/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "Error: Git hooks directory not found at $HOOKS_DIR"
    exit 1
fi

# Install pre-commit hook
echo "Installing pre-commit hook..."
cp .githooks/pre-commit "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo -e "${GREEN}✓ Git hooks installed successfully!${NC}"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: Runs formatting, linting, type checking, and tests"
echo ""
echo "To bypass the hook for a quick commit, use:"
echo "  SKIP_PRE_COMMIT=1 git commit -m 'message'"
echo "  or"
echo "  git commit --no-verify -m 'message'"
