---
name: excalidraw-diagram
description: Create Excalidraw diagram JSON files that make visual arguments. Use when the user wants to visualize workflows, architectures, or concepts.
---

# Excalidraw Diagram Creator

Generate `.excalidraw` files by following the steps below **in order**. Each step produces a concrete output. Do NOT skip steps or jump to generation early.

**Key rule:** NEVER hand-write Excalidraw JSON. Use `references/primitives.py` to generate all elements deterministically. The generator handles all Excalidraw boilerplate, sizing, grouping, arrow binding, and layout.

**Setup:** If first time, see `README.md` for instructions. Requires Graphviz (`dot`) for auto-layout.

---

## STEP 1: Load the Color Palette

**Action:** Read `references/color-palette.md` using the Read tool. This is the single source of truth for ALL colors.

**Output:** Confirm you've loaded it. You will reference it in Step 3.

Do NOT proceed until you have read the palette file.

---

## STEP 2: Inventory All Elements

**Action:** List every element the diagram needs. For each element, assign:
- A descriptive ID (e.g., `http_server`, `ingress`, `ihs`)
- Its element kind: `person`, `node`, `arrow`, `group`
- Its text content mapped to primitive fields: **title**, **subtitle**, **detail**, **tag**
- For arrows: source → target, label (keep labels SHORT)
- For groups: which nodes belong inside

### Text fields (for nodes and persons)

| Field | Required | Purpose | Example |
|---|---|---|---|
| **title** | yes | What it's called | `HTTP Server` |
| **subtitle** | no | Secondary identifier (tech, version, port) | `[Go :8080]` |
| **detail** | no | What it does (use `\n` for multiple lines) | `Handlers + middleware\n+ in-mem caches` |
| **tag** | no | Classification label (guillemets added automatically) | `external system` |

**Output:** A markdown table:

| ID | Kind | Title | Subtitle | Detail | Tag | Notes |
|---|---|---|---|---|---|---|
| `user` | person | Browser User | — | CDN-delivered\ninsurance site | — | Actor |
| `http` | node | HTTP Server | [Go :8080] | Handlers + middleware\n+ in-mem caches | — | group: service |
| `ihs` | node | IHS Markit API | [SOAP] | Vehicle data\n(S&P Global) | external system | — |
| `service` | group | — | — | — | — | label: "VINtelligence Service" |
| — | arrow | — | — | — | — | user → ingress, label: "HTTPS" |

---

## STEP 3: Assign Colors from Palette

**Action:** For each node/person, assign fill and stroke colors from the palette:

| Element Type | Palette Category |
|---|---|
| Person icon | Secondary or Tertiary |
| Internal containers (main request path) | Primary/Neutral |
| Background processes (goroutines, workers) | End/Success (green) |
| External systems | Start/Trigger (orange) |
| Observability (metrics, monitoring) | AI/LLM (purple) |
| Boundary group | Primary/Neutral (auto-rendered as dashed, opacity 15) |
| Arrows | Auto-colored to match source node's stroke |

**Output:** Updated table with fill/stroke columns.

Every element MUST have colors assigned before proceeding. Do NOT use one color for everything.

---

## STEP 4: Write the Generator Script

**Action:** Write a Python script using the `Graph` API from `references/primitives.py`. The Graph handles all layout automatically via Graphviz — you do NOT need to assign coordinates.

### Graph API reference

```python
import sys
sys.path.insert(0, "{skill_dir}/references")
from primitives import Graph

g = Graph(
    "Diagram Title",
    subtitle="Optional subtitle",
    rankdir="LR",  # LR (left-right), TB (top-bottom), RL, BT
)
```

**`g.group(id, label, *, fill, stroke)`**
- Declares a boundary group. Nodes assigned to this group are visually enclosed in a dashed rectangle.
- The boundary rect, its label, and all child nodes share a `groupIds` entry — they move together in the editor.

**`g.person(id, title, *, detail, fill, stroke)`**
- Declares a person/actor (head ellipse + body rect + label).
- Arrows connect via a hidden bounding rect.

**`g.node(id, title, *, subtitle, detail, tag, width, fill, stroke, group)`**
- Declares a rectangular node with up to 4 text elements (tag, title, subtitle, detail).
- `width` and `height` auto-computed from text content.
- `tag` gets guillemets (`«»`) added automatically.
- `group="service"` places the node inside the named boundary group.

**`g.edge(from_id, to_id, *, label, color, dashed)`**
- Declares a directed arrow between two nodes/persons.
- Endpoints, connection sides, and bindings are computed automatically.
- Labels are bound to the arrow (move with it in the editor).
- `color` defaults to source node's stroke color.

**`g.build(output_path)`**
- Runs Graphviz `dot` to compute layout positions.
- Generates all Excalidraw elements (nodes, persons, boundaries, arrows, title).
- Writes the `.excalidraw` JSON file.

### Example: full C2 container diagram

```python
import sys
sys.path.insert(0, "/home/user/.claude/skills/excalidraw-diagram/references")
from primitives import Graph

g = Graph(
    "Container Diagram — VINtelligence Service",
    subtitle="C4 Level 2 — Runtime processes within EKS pod",
    rankdir="LR",
)

g.group("service", label="VINtelligence Service — EKS ps-production")

g.person("user", title="Browser User",
         detail="CDN-delivered\ninsurance site")

g.node("ingress", title="nginx-ps Ingress", subtitle="[nginx]",
       detail="TLS, host routing,\nrate limiting",
       fill="#3b82f6", stroke="#1e3a5f", group="service")
g.node("http", title="HTTP Server", subtitle="[Go :8080]",
       detail="Handlers + middleware\n+ in-mem caches",
       fill="#3b82f6", stroke="#1e3a5f", group="service")
g.node("ihs", title="IHS Markit API", subtitle="[SOAP]",
       detail="Vehicle data\n(S&P Global)", tag="external system",
       fill="#fed7aa", stroke="#c2410c")

g.edge("user", "ingress", label="HTTPS")
g.edge("ingress", "http", label=":8080")
g.edge("http", "ihs", label="SOAP")

g.build("/path/to/output.excalidraw")
```

### Low-level API (manual placement)

For cases where you need manual control over coordinates, the low-level functions are still available:

```python
from primitives import node, person, arrow, diagram_title, diagram

elements = []
elements += node("http", title="HTTP Server", x=100, y=100, ...)
elements += person("user", title="Browser User", x=0, y=100, ...)
elements += arrow("user", "http", elements, label="HTTPS")
elements += diagram_title("My Diagram", x=0, y=0, subtitle="Level 2")
diagram(elements, "output.excalidraw")
```

---

## STEP 5: Run and Render

**Action:** Run the generator script, then render the output.

```bash
# Generate
python3 /path/to/generate_diagram.py

# Render
cd ~/.claude/skills/excalidraw-diagram/references && uv run python render_excalidraw.py --dark <path-to-file.excalidraw>
```

Always use `--dark`. Share the PNG path with the user as a clickable `file://` URI (percent-encode spaces as `%20`):
```
Latest render: `file:///home/user/My%20Project/diagram.png`
```

### Validation loop
1. **Render** → share PNG path → Read the PNG yourself
2. **Check composition**: Balanced layout? Empty voids or cramped areas?
3. **Check colors**: Distinct for each element type?
4. **Check text**: Visible, not clipped, not overlapping?
5. **Check arrows**: Connected to right shapes? Labels readable?
6. **Fix the generator script** → re-run → re-render → repeat until clean

**Important:** Always fix issues in the generator script, never in the `.excalidraw` output. The output is disposable — the script is the source of truth.

### First-time setup
```bash
# Renderer dependencies
cd ~/.claude/skills/excalidraw-diagram/references
uv sync
uv run playwright install chromium

# Verify Graphviz
which dot
```

---

## Reference: Visual Patterns → rankdir

| If the diagram shows... | Use this rankdir |
|---|---|
| Left-to-right request flow | `rankdir="LR"` |
| Top-down hierarchy | `rankdir="TB"` |
| Right-to-left (reverse flow) | `rankdir="RL"` |
| Bottom-up (data flowing up) | `rankdir="BT"` |

Graphviz handles the layout pattern automatically based on the graph structure and `rankdir`. Complex patterns (hub-and-spoke, fan-out) emerge naturally from the edge topology.
