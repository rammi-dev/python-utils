# Documentation Build Tools

Tools for generating DOCX documents and diagram images from Dremio architecture documentation.

## Quick Start

```bash
cd docs-build
./build-docs.sh
```

## Prerequisites

### Python (for DOCX generation)
```bash
uv venv ../.venv
source ../.venv/bin/activate
uv pip install python-docx pillow
```

### Node.js (for diagram generation)
```bash
cd ..
npm install @mermaid-js/mermaid-cli puppeteer --save-dev
```

## Tools

| File | Description |
|------|-------------|
| `build-docs.sh` | Full build script (diagrams + DOCX) |
| `md_to_docx.py` | Python script to convert markdown to DOCX |

## Manual Commands

### Generate Diagram Images

Convert Mermaid `.mermaid` files to PNG:

```bash
cd /path/to/dremio-helm

# Overview diagram (high-level architecture, LR layout with ELK renderer)
npx mmdc -i docs/k8s-overview-diagram.mermaid \
         -o docs/k8s-overview-diagram.png \
         -b white -w 1800 -H 1600

# Detailed diagram (K8s resources, LR layout with ELK renderer)
npx mmdc -i docs/k8s-detailed-diagram.mermaid \
         -o docs/k8s-detailed-diagram.png \
         -b white -w 3600 -H 2000

# Storage diagram (LR layout with ELK renderer)
npx mmdc -i docs/storage-diagram.mermaid \
         -o docs/storage-diagram.png \
         -b white -w 2000 -H 1200
```

### Mermaid CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `-i` | Input file | `-i diagram.mermaid` |
| `-o` | Output file | `-o diagram.png` |
| `-b` | Background | `-b white` or `-b transparent` |
| `-w` | Width (px) | `-w 2400` |
| `-H` | Height (px) | `-H 1200` |
| `-t` | Theme | `-t default`, `dark`, `forest`, `neutral` |

### Mermaid Diagram Configuration

The diagrams use in-file configuration directives for layout control:

```mermaid
%%{init: {"flowchart": {"defaultRenderer": "elk"}} }%%
graph LR
    %% diagram content
```

| Directive | Description |
|-----------|-------------|
| `defaultRenderer: "elk"` | Uses ELK (Eclipse Layout Kernel) for better edge routing and node placement |
| `graph LR` | Left-to-right layout (vs `TB` for top-to-bottom) |
| `graph TB` | Top-to-bottom layout (default) |

**ELK Renderer Benefits:**
- Better handling of complex diagrams with many connections
- Improved edge routing (fewer crossings)
- More consistent node spacing
- Requires no additional installation (bundled with mermaid-cli)

### Color Scheme

All diagrams use a consistent professional color palette:

| Category | Node Fill | Stroke | Usage |
|----------|-----------|--------|-------|
| Coordinator | `#457b9d` | `#1d3557` | Dremio master, coordinators |
| Executor | `#2a9d8f` | `#264653` | Executor pods |
| Catalog | `#9c89b8` | `#6c567b` | Catalog components |
| Infrastructure | `#f4a261` | `#e76f51` | ZK, NATS, MongoDB |
| Storage | `#e63946` | `#9d0208` | S3, distributed storage |
| Service | `#e9c46a` | `#e76f51` | K8s services, PVCs |
| Config | `#a8dadc` | `#457b9d` | ConfigMaps |

Subgraph backgrounds use lighter tints of the same palette for visual hierarchy.

### Generate DOCX

```bash
source ../.venv/bin/activate
python md_to_docx.py
```

## Output Files

Generated files are placed in the `docs/` folder:

```
docs/
├── dremio-architecture.docx        # Generated DOCX with embedded diagrams
├── k8s-overview-diagram.png        # High-level architecture
├── k8s-detailed-diagram.png        # Detailed K8s resources
└── storage-diagram.png             # Storage architecture
```

## Source Files

| File | Description |
|------|-------------|
| `docs/dremio-architecture.md` | Main architecture documentation (English) |
| `docs/dremio-architecture-pl.md` | Polish translation |
| `docs/ha-architecture.md` | High availability details |
| `docs/k8s-overview-diagram.mermaid` | Overview diagram source |
| `docs/k8s-detailed-diagram.mermaid` | Detailed diagram source |
| `docs/storage-diagram.mermaid` | Storage diagram source |

## Workflow

1. **Edit** - Modify `.md` or `.mermaid` source files
2. **Build** - Run `./build-docs.sh`
3. **Review** - Check generated `.png` and `.docx` files

## Troubleshooting

### Chrome not found
```bash
npx puppeteer browsers install chrome-headless-shell
```

### Python dependencies missing
```bash
uv venv ../.venv
source ../.venv/bin/activate
uv pip install python-docx pillow
```

### Permission denied on build script
```bash
chmod +x build-docs.sh
```
