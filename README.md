# Excalidraw Diagram Skill

A coding agent skill that generates Excalidraw diagrams from pure declarations — no coordinates, no hand-written JSON.

Nodes and edges are declared, Graphviz computes the layout, and `primitives.py` generates the Excalidraw JSON with all boilerplate, bindings, sizing, and grouping handled automatically.

## How It Works

```python
from primitives import Graph

g = Graph("Container Diagram", subtitle="C4 Level 2", rankdir="LR")

g.group("service", label="My Service — EKS")
g.person("user", title="Browser User", detail="End user")
g.node("api", title="API Server", subtitle="[Go :8080]", group="service",
       fill="#3b82f6", stroke="#1e3a5f")
g.node("db", title="Database", subtitle="[PostgreSQL]", tag="external system",
       fill="#fed7aa", stroke="#c2410c")

g.edge("user", "api", label="HTTPS")
g.edge("api", "db", label="SQL")

g.build("output.excalidraw")
```

This produces a fully editable `.excalidraw` file with:
- Auto-sized nodes (width/height computed from text content)
- Auto-routed arrows with bound labels
- Boundary groups with dashed rectangles
- Person icons (head + body + label)
- Diagram title and subtitle
- All Excalidraw bindings, seeds, and groupIds wired correctly

## Requirements

- **Python 3.11+**
- **Graphviz** — layout engine (`dot`)
- **uv** — Python package manager (for renderer)

## Setup

```bash
# Graphviz
sudo apt install graphviz    # Debian/Ubuntu
brew install graphviz         # macOS

# Renderer (Playwright + Chromium)
cd .claude/skills/excalidraw-diagram/references
uv sync
uv run playwright install chromium
```

## Rendering

```bash
cd .claude/skills/excalidraw-diagram/references
uv run python render_excalidraw.py --dark <path-to-file.excalidraw>
```

## Customization

Edit `references/color-palette.md` to change the color system. All semantic color assignments in generator scripts reference this palette.

## File Structure

```
excalidraw-diagram/
  SKILL.md                          # Workflow + API reference
  README.md                         # This file
  references/
    primitives.py                   # Node, person, arrow, Graph API + Graphviz layout
    color-palette.md                # Brand colors (edit to customize)
    json-schema.md                  # Excalidraw JSON format reference
    render_excalidraw.py            # Render .excalidraw → PNG (Playwright)
    render_template.html            # Browser template for rendering
    pyproject.toml                  # Python dependencies
```

## Credits

Rendering pipeline (`render_excalidraw.py`, `render_template.html`) adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill). The declarative Graph API, primitives generator, and Graphviz auto-layout are original work.
