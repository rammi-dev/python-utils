#!/bin/bash
# Verification script to check project setup

set -e

echo "========================================="
echo "DLH Airflow Common - Setup Verification"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        return 1
    fi
}

echo "1. Checking Python installation..."
check_command python3
python3 --version
echo ""

echo "2. Checking project structure..."
required_files=(
    "pyproject.toml"
    "tox.ini"
    "README.md"
    "Makefile"
    "src/dlh_airflow_common/__init__.py"
    "tests/__init__.py"
)

all_exist=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file is missing"
        all_exist=false
    fi
done
echo ""

echo "3. Checking if virtual environment is activated..."
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment is active: $VIRTUAL_ENV"
else
    echo -e "${RED}✗${NC} Virtual environment is NOT active"
    echo "   Run: python -m venv venv && source venv/bin/activate"
fi
echo ""

echo "4. Checking dependencies (if venv is active)..."
if [ -n "$VIRTUAL_ENV" ]; then
    if pip show pytest > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} pytest is installed"
    else
        echo -e "${RED}✗${NC} pytest is NOT installed"
        echo "   Run: pip install -e '.[dev]'"
    fi

    if pip show ruff > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ruff is installed"
    else
        echo -e "${RED}✗${NC} ruff is NOT installed"
        echo "   Run: pip install -e '.[dev]'"
    fi

    if pip show black > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} black is installed"
    else
        echo -e "${RED}✗${NC} black is NOT installed"
        echo "   Run: pip install -e '.[dev]'"
    fi
else
    echo "Skipped - activate virtual environment first"
fi
echo ""

echo "5. Project structure overview..."
echo "src/dlh_airflow_common/"
ls -la src/dlh_airflow_common/ | tail -n +4 | awk '{print "  " $9}'
echo ""

echo "tests/"
ls -la tests/ | tail -n +4 | awk '{print "  " $9}'
echo ""

echo "========================================="
echo "Verification complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Create virtual environment: python -m venv venv"
echo "  2. Activate it: source venv/bin/activate"
echo "  3. Install dependencies: pip install -e '.[dev]'"
echo "  4. Run tests: pytest"
echo "  5. Check code quality: make all"
echo ""
echo "For deployment to Nexus, see DEPLOYMENT.md"
