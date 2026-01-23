#!/bin/bash
# Build documentation: Generate diagrams and DOCX from source files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"

echo "=== Documentation Build Script ==="
echo "Project root: $PROJECT_ROOT"

# Step 1: Install mermaid-cli if needed
if ! command -v npx &> /dev/null || ! npx mmdc --version &> /dev/null 2>&1; then
    echo ""
    echo "[1/3] Installing mermaid-cli..."
    cd "$PROJECT_ROOT"
    npm install @mermaid-js/mermaid-cli puppeteer --save-dev --silent
else
    echo ""
    echo "[1/3] mermaid-cli already available"
fi

# Step 2: Generate diagram images
echo ""
echo "[2/3] Generating diagram images..."

cd "$PROJECT_ROOT"

echo "  - k8s-overview-diagram.png"
npx mmdc -i "$DOCS_DIR/k8s-overview-diagram.mermaid" \
         -o "$DOCS_DIR/k8s-overview-diagram.png" \
         -b white -w 1800 -H 1400 2>/dev/null

echo "  - k8s-detailed-diagram.png"
npx mmdc -i "$DOCS_DIR/k8s-detailed-diagram.mermaid" \
         -o "$DOCS_DIR/k8s-detailed-diagram.png" \
         -b white -w 2400 -H 3200 2>/dev/null

echo "  - storage-diagram.png"
npx mmdc -i "$DOCS_DIR/storage-diagram.mermaid" \
         -o "$DOCS_DIR/storage-diagram.png" \
         -b white -w 1600 -H 1000 2>/dev/null

# Step 3: Generate DOCX
echo ""
echo "[3/3] Generating DOCX document..."

# Setup Python venv if needed
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "  Creating Python virtual environment..."
    uv venv "$PROJECT_ROOT/.venv"
fi

source "$PROJECT_ROOT/.venv/bin/activate"

# Install dependencies if needed
if ! python -c "import docx" 2>/dev/null; then
    echo "  Installing Python dependencies..."
    uv pip install python-docx pillow --quiet
fi

python "$SCRIPT_DIR/md_to_docx.py"

# Cleanup npm artifacts
echo ""
echo "Cleaning up..."
rm -rf "$PROJECT_ROOT/node_modules" "$PROJECT_ROOT/package.json" "$PROJECT_ROOT/package-lock.json" 2>/dev/null || true

echo ""
echo "=== Build Complete ==="
echo "Generated files:"
ls -lh "$DOCS_DIR"/*.png "$DOCS_DIR"/*.docx 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
