"""Excalidraw primitive generators.

Deterministically generate Excalidraw JSON elements from simple declarations.

Usage (manual placement):
    from primitives import node, arrow, diagram

    elements = []
    elements += node("http", title="HTTP Server", x=100, y=100, ...)
    elements += node("ihs", title="IHS Markit API", x=500, y=100, ...)
    elements += arrow("http", "ihs", elements, label="SOAP")
    diagram(elements, "output.excalidraw")

Usage (auto-layout via Graphviz):
    from primitives import Graph

    g = Graph("Container Diagram — VINtelligence Service", rankdir="LR")
    g.node("http", title="HTTP Server", subtitle="[Go :8080]",
           fill="#3b82f6", stroke="#1e3a5f")
    g.node("ihs", title="IHS Markit API", tag="external system",
           fill="#fed7aa", stroke="#c2410c")
    g.edge("http", "ihs", label="SOAP")
    g.build("output.excalidraw")
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Deterministic seeds from IDs
# ---------------------------------------------------------------------------

def _seed(id_str: str) -> int:
    return int(hashlib.md5(id_str.encode()).hexdigest()[:8], 16)


def _nonce(id_str: str) -> int:
    return int(hashlib.md5((id_str + "_n").encode()).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# Text element factory
# ---------------------------------------------------------------------------

def _text(
    id: str,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: int,
    color: str,
    group_id: str,
    height: float | None = None,
) -> dict:
    lines = text.count("\n") + 1
    h = height or lines * font_size * 1.25
    return {
        "type": "text",
        "id": id,
        "x": x,
        "y": y,
        "width": width,
        "height": h,
        "text": text,
        "originalText": text,
        "fontSize": font_size,
        "fontFamily": 3,
        "textAlign": "center",
        "verticalAlign": "top",
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": _seed(id),
        "version": 1,
        "versionNonce": _nonce(id),
        "isDeleted": False,
        "groupIds": [group_id],
        "boundElements": None,
        "link": None,
        "locked": False,
        "containerId": None,
        "autoResize": True,
        "lineHeight": 1.25,
    }


# ---------------------------------------------------------------------------
# Node primitive
# ---------------------------------------------------------------------------

# Layout constants (y-offsets relative to box top)
TAG_FONT = 11
TAG_PAD_TOP = 8           # from box top to tag baseline
TAG_GAP = 6               # between tag and title

TITLE_FONT = 16
TITLE_GAP = 10            # between title and subtitle

SUBTITLE_FONT = 12
SUBTITLE_GAP = 10         # between subtitle and detail

DETAIL_FONT = 12
DETAIL_PAD_BOTTOM = 12    # from last detail line to box bottom

# Text colors
COLOR_TAG = None           # defaults to stroke color
COLOR_TITLE = "#1e293b"
COLOR_SUBTITLE = "#475569"
COLOR_DETAIL = "#64748b"

# Width sizing
CHAR_WIDTH = 0.6           # monospace char width as fraction of font size
PAD_HORIZONTAL = 30        # left + right padding inside box


def _auto_width(
    title: str,
    subtitle: str | None,
    detail: str | None,
    tag: str | None,
) -> float:
    """Compute minimum box width to fit all text lines."""
    lines: list[tuple[str, int]] = []  # (text, font_size)
    if tag:
        tag_text = f"\u00ab{tag}\u00bb" if not tag.startswith("\u00ab") else tag
        lines.append((tag_text, TAG_FONT))
    lines.append((title, TITLE_FONT))
    if subtitle:
        lines.append((subtitle, SUBTITLE_FONT))
    if detail:
        for line in detail.split("\n"):
            lines.append((line, DETAIL_FONT))

    max_text_width = max(len(text) * font * CHAR_WIDTH for text, font in lines)
    return max(max_text_width + PAD_HORIZONTAL, 120)  # minimum 120px


def node(
    id: str,
    title: str,
    x: float,
    y: float,
    *,
    subtitle: str | None = None,
    detail: str | None = None,
    tag: str | None = None,
    width: float | None = None,
    fill: str = "#3b82f6",
    stroke: str = "#1e3a5f",
) -> list[dict]:
    """Generate a Node primitive: rect + tag + title + subtitle + detail.

    Args:
        id:       Unique node identifier (e.g., "ihs", "http_server")
        title:    Required. The node's name.
        x, y:     Top-left position of the rectangle.
        subtitle: Optional secondary label (technology, version, etc.)
        detail:   Optional description. Use \\n for multiple lines.
        tag:      Optional classification label. Guillemets added automatically.
        width:    Rectangle width. Auto-computed from text if None.
        fill:     Background color.
        stroke:   Border color.

    Returns:
        List of Excalidraw element dicts.
    """
    if width is None:
        width = _auto_width(title, subtitle, detail, tag)

    group_id = f"grp_{id}"
    elements: list[dict] = []

    # --- Compute height by stacking elements ---
    cursor_y = y + TAG_PAD_TOP

    if tag:
        tag_y = cursor_y
        cursor_y += TAG_FONT * 1.25 + TAG_GAP

    title_y = cursor_y
    cursor_y += TITLE_FONT * 1.25 + TITLE_GAP

    if subtitle:
        subtitle_y = cursor_y
        cursor_y += SUBTITLE_FONT * 1.25 + SUBTITLE_GAP

    if detail:
        detail_y = cursor_y
        detail_lines = detail.count("\n") + 1
        cursor_y += detail_lines * DETAIL_FONT * 1.25

    height = cursor_y - y + DETAIL_PAD_BOTTOM

    # --- Rectangle ---
    rect_id = f"{id}_rect"
    elements.append({
        "type": "rectangle",
        "id": rect_id,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 70,
        "angle": 0,
        "seed": _seed(rect_id),
        "version": 1,
        "versionNonce": _nonce(rect_id),
        "isDeleted": False,
        "groupIds": [group_id],
        "boundElements": None,
        "link": None,
        "locked": False,
        "roundness": {"type": 3},
    })

    # --- Tag ---
    if tag:
        tag_text = f"\u00ab{tag}\u00bb" if not tag.startswith("\u00ab") else tag
        elements.append(_text(
            id=f"{id}_tag", text=tag_text,
            x=x, y=tag_y, width=width,
            font_size=TAG_FONT, color=stroke,
            group_id=group_id,
        ))

    # --- Title ---
    elements.append(_text(
        id=f"{id}_title", text=title,
        x=x, y=title_y, width=width,
        font_size=TITLE_FONT, color=COLOR_TITLE,
        group_id=group_id,
    ))

    # --- Subtitle ---
    if subtitle:
        elements.append(_text(
            id=f"{id}_subtitle", text=subtitle,
            x=x, y=subtitle_y, width=width,
            font_size=SUBTITLE_FONT, color=COLOR_SUBTITLE,
            group_id=group_id,
        ))

    # --- Detail ---
    if detail:
        elements.append(_text(
            id=f"{id}_detail", text=detail,
            x=x, y=detail_y, width=width,
            font_size=DETAIL_FONT, color=COLOR_DETAIL,
            group_id=group_id,
        ))

    return elements


# ---------------------------------------------------------------------------
# Person primitive
# ---------------------------------------------------------------------------

PERSON_HEAD_R = 18        # head radius
PERSON_BODY_W = 50        # body width
PERSON_BODY_H = 40        # body height
PERSON_GAP = 4            # between head and body
PERSON_LABEL_GAP = 6      # between body and label


def person(
    id: str,
    title: str,
    x: float,
    y: float,
    *,
    detail: str | None = None,
    fill: str = "#60a5fa",
    stroke: str = "#1e3a5f",
) -> list[dict]:
    """Generate a Person primitive: head ellipse + body rect + title + detail.

    The (x, y) is the top-left of the bounding box. A hidden rect is also
    generated for arrow binding (same ID pattern as node: {id}_rect).

    Args:
        id:     Unique identifier.
        title:  Person/role name.
        x, y:   Top-left of bounding box.
        detail: Optional description under the name.
        fill:   Shape fill color.
        stroke: Shape stroke color.
    """
    group_id = f"grp_{id}"
    elements: list[dict] = []

    # Compute overall width (widest of: head, body, title text)
    title_w = max(len(title) * TITLE_FONT * CHAR_WIDTH, PERSON_BODY_W)
    detail_w = 0
    if detail:
        for line in detail.split("\n"):
            detail_w = max(detail_w, len(line) * DETAIL_FONT * CHAR_WIDTH)
    total_w = max(title_w, detail_w, PERSON_HEAD_R * 2, PERSON_BODY_W) + 10
    cx = x + total_w / 2  # center x

    cursor_y = y

    # --- Head (ellipse) ---
    head_id = f"{id}_head"
    elements.append({
        "type": "ellipse",
        "id": head_id,
        "x": cx - PERSON_HEAD_R,
        "y": cursor_y,
        "width": PERSON_HEAD_R * 2,
        "height": PERSON_HEAD_R * 2,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 70,
        "angle": 0,
        "seed": _seed(head_id),
        "version": 1,
        "versionNonce": _nonce(head_id),
        "isDeleted": False,
        "groupIds": [group_id],
        "boundElements": None,
        "link": None,
        "locked": False,
    })
    cursor_y += PERSON_HEAD_R * 2 + PERSON_GAP

    # --- Body (rounded rect) ---
    body_id = f"{id}_body"
    body_x = cx - PERSON_BODY_W / 2
    elements.append({
        "type": "rectangle",
        "id": body_id,
        "x": body_x,
        "y": cursor_y,
        "width": PERSON_BODY_W,
        "height": PERSON_BODY_H,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 70,
        "angle": 0,
        "seed": _seed(body_id),
        "version": 1,
        "versionNonce": _nonce(body_id),
        "isDeleted": False,
        "groupIds": [group_id],
        "boundElements": None,
        "link": None,
        "locked": False,
        "roundness": {"type": 3},
    })
    cursor_y += PERSON_BODY_H + PERSON_LABEL_GAP

    # --- Hidden binding rect (for arrows to target) ---
    # Covers the full person figure so arrows connect to the whole shape
    rect_id = f"{id}_rect"
    total_h = cursor_y - y
    elements.append({
        "type": "rectangle",
        "id": rect_id,
        "x": x,
        "y": y,
        "width": total_w,
        "height": total_h,
        "strokeColor": "transparent",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 0,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 0,
        "angle": 0,
        "seed": _seed(rect_id),
        "version": 1,
        "versionNonce": _nonce(rect_id),
        "isDeleted": False,
        "groupIds": [group_id],
        "boundElements": None,
        "link": None,
        "locked": False,
        "roundness": None,
    })

    # --- Title ---
    elements.append(_text(
        id=f"{id}_title", text=title,
        x=x, y=cursor_y, width=total_w,
        font_size=TITLE_FONT, color=COLOR_TITLE,
        group_id=group_id,
    ))
    cursor_y += TITLE_FONT * 1.25

    # --- Detail ---
    if detail:
        elements.append(_text(
            id=f"{id}_detail", text=detail,
            x=x, y=cursor_y + 2, width=total_w,
            font_size=DETAIL_FONT, color=COLOR_DETAIL,
            group_id=group_id,
        ))

    return elements


# ---------------------------------------------------------------------------
# Diagram title primitive
# ---------------------------------------------------------------------------

DIAGRAM_TITLE_FONT = 22
DIAGRAM_SUBTITLE_FONT = 14
COLOR_DIAGRAM_TITLE = "#1e40af"
COLOR_DIAGRAM_SUBTITLE = "#64748b"


def diagram_title(
    title: str,
    x: float,
    y: float,
    *,
    subtitle: str | None = None,
    width: float = 600,
) -> list[dict]:
    """Generate a diagram title + optional subtitle as free-floating text."""
    elements: list[dict] = []

    elements.append({
        "type": "text",
        "id": "diagram_title",
        "x": x,
        "y": y,
        "width": width,
        "height": DIAGRAM_TITLE_FONT * 1.25,
        "text": title,
        "originalText": title,
        "fontSize": DIAGRAM_TITLE_FONT,
        "fontFamily": 3,
        "textAlign": "center",
        "verticalAlign": "top",
        "strokeColor": COLOR_DIAGRAM_TITLE,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": _seed("diagram_title"),
        "version": 1,
        "versionNonce": _nonce("diagram_title"),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": None,
        "link": None,
        "locked": False,
        "containerId": None,
        "autoResize": True,
        "lineHeight": 1.25,
    })

    if subtitle:
        elements.append({
            "type": "text",
            "id": "diagram_subtitle",
            "x": x,
            "y": y + DIAGRAM_TITLE_FONT * 1.25 + 4,
            "width": width,
            "height": DIAGRAM_SUBTITLE_FONT * 1.25,
            "text": subtitle,
            "originalText": subtitle,
            "fontSize": DIAGRAM_SUBTITLE_FONT,
            "fontFamily": 3,
            "textAlign": "center",
            "verticalAlign": "top",
            "strokeColor": COLOR_DIAGRAM_SUBTITLE,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "seed": _seed("diagram_subtitle"),
            "version": 1,
            "versionNonce": _nonce("diagram_subtitle"),
            "isDeleted": False,
            "groupIds": [],
            "boundElements": None,
            "link": None,
            "locked": False,
            "containerId": None,
            "autoResize": True,
            "lineHeight": 1.25,
        })

    return elements


# ---------------------------------------------------------------------------
# Arrow wiring
# ---------------------------------------------------------------------------

def _find_rect(node_id: str, elements: list[dict]) -> dict | None:
    """Find the rectangle element for a given node ID."""
    rect_id = f"{node_id}_rect"
    for el in elements:
        if el["type"] == "rectangle" and el["id"] == rect_id:
            return el
    return None


def _connection_points(
    src: dict, tgt: dict,
) -> tuple[tuple[float, float], tuple[float, float], str]:
    """Compute where to connect an arrow between two rects.

    Returns (start_point, end_point, direction) where direction is
    'right', 'left', 'down', or 'up' — describing the arrow's travel.
    """
    sx, sy, sw, sh = src["x"], src["y"], src["width"], src["height"]
    tx, ty, tw, th = tgt["x"], tgt["y"], tgt["width"], tgt["height"]

    src_cx, src_cy = sx + sw / 2, sy + sh / 2
    tgt_cx, tgt_cy = tx + tw / 2, ty + th / 2

    dx = tgt_cx - src_cx
    dy = tgt_cy - src_cy

    # Choose connection side based on dominant axis
    if abs(dx) >= abs(dy):
        # Horizontal: connect right side of left node → left side of right node
        if dx >= 0:
            return (sx + sw, src_cy), (tx, tgt_cy), "right"
        else:
            return (sx, src_cy), (tx + tw, tgt_cy), "left"
    else:
        # Vertical: connect bottom of top node → top of bottom node
        if dy >= 0:
            return (src_cx, sy + sh), (tgt_cx, ty), "down"
        else:
            return (src_cx, sy), (tgt_cx, ty + th), "up"


ARROW_GAP = 8
LABEL_FONT = 12
COLOR_LABEL = "#475569"


def arrow(
    from_id: str,
    to_id: str,
    elements: list[dict],
    *,
    label: str | None = None,
    color: str | None = None,
    dashed: bool = False,
) -> list[dict]:
    """Generate an arrow connecting two nodes, with automatic endpoint computation.

    Looks up the source and target rects in `elements` by node ID,
    computes connection points, and wires the boundElements handshake.

    Args:
        from_id:  Source node ID (must already exist in elements).
        to_id:    Target node ID (must already exist in elements).
        elements: The current elements list (mutated to add boundElements).
        label:    Optional short label for the arrow.
        color:    Arrow stroke color. Defaults to source node's stroke color.
        dashed:   Use dashed stroke style.

    Returns:
        List of new Excalidraw elements (arrow + optional label text).
    """
    src_rect = _find_rect(from_id, elements)
    tgt_rect = _find_rect(to_id, elements)

    if src_rect is None:
        raise ValueError(f"No rect found for node '{from_id}'. Did you add it with node() first?")
    if tgt_rect is None:
        raise ValueError(f"No rect found for node '{to_id}'. Did you add it with node() first?")

    # Default color: source node's stroke
    if color is None:
        color = src_rect["strokeColor"]

    (x1, y1), (x2, y2), direction = _connection_points(src_rect, tgt_rect)

    arrow_id = f"arrow_{from_id}_{to_id}"
    new_elements: list[dict] = []

    # --- Arrow element ---
    arrow_el = {
        "type": "arrow",
        "id": arrow_id,
        "x": x1,
        "y": y1,
        "width": x2 - x1,
        "height": y2 - y1,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 0,
        "opacity": 85,
        "angle": 0,
        "seed": _seed(arrow_id),
        "version": 1,
        "versionNonce": _nonce(arrow_id),
        "isDeleted": False,
        "groupIds": [],
        "boundElements": [],
        "link": None,
        "locked": False,
        "roundness": {"type": 2},
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "startBinding": {
            "elementId": src_rect["id"],
            "focus": 0,
            "gap": ARROW_GAP,
        },
        "endBinding": {
            "elementId": tgt_rect["id"],
            "focus": 0,
            "gap": ARROW_GAP,
        },
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }
    new_elements.append(arrow_el)

    # --- Wire boundElements on both rects ---
    for rect in (src_rect, tgt_rect):
        if rect["boundElements"] is None:
            rect["boundElements"] = []
        if not any(b["id"] == arrow_id for b in rect["boundElements"]):
            rect["boundElements"].append({"id": arrow_id, "type": "arrow"})

    # --- Label (bound to arrow) ---
    if label:
        label_id = f"label_{from_id}_{to_id}"
        mid_x = x1 + (x2 - x1) / 2
        mid_y = y1 + (y2 - y1) / 2
        label_w = max(len(label) * LABEL_FONT * CHAR_WIDTH, 30)
        label_h = LABEL_FONT * 1.25

        label_el = {
            "type": "text",
            "id": label_id,
            "x": mid_x - label_w / 2,
            "y": mid_y - label_h / 2,
            "width": label_w,
            "height": label_h,
            "text": label,
            "originalText": label,
            "fontSize": LABEL_FONT,
            "fontFamily": 3,
            "textAlign": "center",
            "verticalAlign": "middle",
            "strokeColor": COLOR_LABEL,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 0,
            "opacity": 100,
            "angle": 0,
            "seed": _seed(label_id),
            "version": 1,
            "versionNonce": _nonce(label_id),
            "isDeleted": False,
            "groupIds": [],
            "boundElements": None,
            "link": None,
            "locked": False,
            "containerId": arrow_id,
            "autoResize": True,
            "lineHeight": 1.25,
        }
        new_elements.append(label_el)

        # Wire: arrow must list label in its boundElements
        arrow_el["boundElements"].append({"id": label_id, "type": "text"})

    return new_elements


# ---------------------------------------------------------------------------
# Graph: declarative API with Graphviz auto-layout
# ---------------------------------------------------------------------------

# Graphviz points → pixels conversion (72 DPI → screen pixels)
GV_SCALE = 1.5
# Minimum gap between nodes in pixels
GV_NODESEP = 100
GV_RANKSEP = 160


class Graph:
    """Declarative diagram builder with automatic layout via Graphviz.

    Usage:
        g = Graph("My Diagram", rankdir="LR")
        g.node("a", title="Service A", fill="#3b82f6", stroke="#1e3a5f")
        g.node("b", title="Service B", fill="#fed7aa", stroke="#c2410c")
        g.edge("a", "b", label="gRPC")
        g.build("output.excalidraw")
    """

    def __init__(self, title: str = "", *, subtitle: str | None = None, rankdir: str = "LR"):
        """
        Args:
            title:    Diagram title rendered above the diagram.
            subtitle: Optional subtitle below the title.
            rankdir:  Graphviz rank direction: LR (left-right), TB (top-bottom),
                      RL, BT.
        """
        self.title = title
        self._subtitle = subtitle
        self.rankdir = rankdir
        self._nodes: dict[str, dict] = {}    # id → node kwargs
        self._persons: dict[str, dict] = {} # id → person kwargs
        self._edges: list[dict] = []        # {from, to, label, color, dashed}
        self._groups: dict[str, dict] = {}  # group_id → {label, fill, stroke}

    def group(
        self,
        id: str,
        label: str,
        *,
        fill: str = "#3b82f6",
        stroke: str = "#1e3a5f",
    ) -> None:
        """Declare a boundary group. Nodes assigned to this group will be
        visually enclosed in a dashed rectangle with a label.

        Args:
            id:     Unique group identifier.
            label:  Text label shown at top of the boundary.
            fill:   Background color (rendered at low opacity).
            stroke: Border color (dashed).
        """
        self._groups[id] = dict(label=label, fill=fill, stroke=stroke)

    def node(
        self,
        id: str,
        title: str,
        *,
        subtitle: str | None = None,
        detail: str | None = None,
        tag: str | None = None,
        width: float | None = None,
        fill: str = "#3b82f6",
        stroke: str = "#1e3a5f",
        group: str | None = None,
    ) -> None:
        """Declare a node. Coordinates are computed automatically.

        Args:
            group: Optional group ID. Node will be placed inside
                   the boundary defined by g.group().
        """
        if group and group not in self._groups:
            raise ValueError(f"Group '{group}' not declared. Call g.group() first.")
        self._nodes[id] = dict(
            title=title, subtitle=subtitle, detail=detail, tag=tag,
            width=width, fill=fill, stroke=stroke, group=group,
        )

    def person(
        self,
        id: str,
        title: str,
        *,
        detail: str | None = None,
        fill: str = "#60a5fa",
        stroke: str = "#1e3a5f",
    ) -> None:
        """Declare a person/actor. Rendered as head + body + label."""
        self._persons[id] = dict(
            title=title, detail=detail, fill=fill, stroke=stroke,
        )

    def edge(
        self,
        from_id: str,
        to_id: str,
        *,
        label: str | None = None,
        color: str | None = None,
        dashed: bool = False,
    ) -> None:
        """Declare an edge. Routing is computed automatically."""
        self._edges.append(dict(
            from_id=from_id, to_id=to_id,
            label=label, color=color, dashed=dashed,
        ))

    def _compute_node_sizes(self) -> dict[str, tuple[float, float]]:
        """Pre-compute width and height for each node (needed for Graphviz)."""
        sizes: dict[str, tuple[float, float]] = {}
        for nid, attrs in self._nodes.items():
            # Compute width
            w = attrs.get("width")
            if w is None:
                w = _auto_width(
                    attrs["title"], attrs.get("subtitle"),
                    attrs.get("detail"), attrs.get("tag"),
                )

            # Compute height by simulating the stacking
            cursor = TAG_PAD_TOP
            if attrs.get("tag"):
                cursor += TAG_FONT * 1.25 + TAG_GAP
            cursor += TITLE_FONT * 1.25 + TITLE_GAP
            if attrs.get("subtitle"):
                cursor += SUBTITLE_FONT * 1.25 + SUBTITLE_GAP
            if attrs.get("detail"):
                detail_lines = attrs["detail"].count("\n") + 1
                cursor += detail_lines * DETAIL_FONT * 1.25
            h = cursor + DETAIL_PAD_BOTTOM

            sizes[nid] = (w, h)

        # Person sizes
        for pid, attrs in self._persons.items():
            title_w = max(len(attrs["title"]) * TITLE_FONT * CHAR_WIDTH, PERSON_BODY_W)
            detail_w = 0
            if attrs.get("detail"):
                for line in attrs["detail"].split("\n"):
                    detail_w = max(detail_w, len(line) * DETAIL_FONT * CHAR_WIDTH)
            w = max(title_w, detail_w, PERSON_HEAD_R * 2, PERSON_BODY_W) + 10
            h = (PERSON_HEAD_R * 2 + PERSON_GAP + PERSON_BODY_H +
                 PERSON_LABEL_GAP + TITLE_FONT * 1.25)
            if attrs.get("detail"):
                detail_lines = attrs["detail"].count("\n") + 1
                h += detail_lines * DETAIL_FONT * 1.25 + 2
            sizes[pid] = (w, h)

        return sizes

    def _run_graphviz(
        self, sizes: dict[str, tuple[float, float]],
    ) -> dict[str, tuple[float, float]]:
        """Run Graphviz dot and return {node_id: (x, y)} positions.

        Graphviz outputs center coordinates in points (72/inch).
        We convert to pixels and return top-left corner positions.
        """
        # Build DOT source
        lines = [
            f'digraph G {{',
            f'  rankdir={self.rankdir};',
            f'  nodesep={GV_NODESEP / 72:.2f};',
            f'  ranksep={GV_RANKSEP / 72:.2f};',
            f'  node [shape=box];',
        ]

        # Collect nodes by group (check both _nodes and _persons)
        grouped: dict[str, list[str]] = {gid: [] for gid in self._groups}
        ungrouped: list[str] = []
        for nid in sizes:
            attrs = self._nodes.get(nid) or self._persons.get(nid) or {}
            grp = attrs.get("group")
            if grp and grp in grouped:
                grouped[grp].append(nid)
            else:
                ungrouped.append(nid)

        # Emit subgraph clusters (Graphviz keeps these together)
        for gid, node_ids in grouped.items():
            lines.append(f'  subgraph cluster_{gid} {{')
            lines.append(f'    style=invis;')  # we draw our own boundary
            for nid in node_ids:
                w_in = sizes[nid][0] / 72
                h_in = sizes[nid][1] / 72
                lines.append(f'    "{nid}" [width={w_in:.3f}, height={h_in:.3f}, fixedsize=true];')
            lines.append(f'  }}')

        # Emit ungrouped nodes
        for nid in ungrouped:
            w_in = sizes[nid][0] / 72
            h_in = sizes[nid][1] / 72
            lines.append(f'  "{nid}" [width={w_in:.3f}, height={h_in:.3f}, fixedsize=true];')

        for e in self._edges:
            lines.append(f'  "{e["from_id"]}" -> "{e["to_id"]}";')
        lines.append('}')
        dot_source = "\n".join(lines)

        # Run dot -Tplain
        result = subprocess.run(
            ["dot", "-Tplain"],
            input=dot_source, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Graphviz failed: {result.stderr}")

        # Parse plain output
        # Format: node <name> <center_x> <center_y> <width> <height> ...
        positions: dict[str, tuple[float, float]] = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts[0] == "node":
                nid = parts[1].strip('"')
                cx_pt = float(parts[2]) * 72  # inches → points
                cy_pt = float(parts[3]) * 72
                w = sizes[nid][0]
                h = sizes[nid][1]
                # Convert center → top-left, scale to pixels
                px = cx_pt * GV_SCALE - w / 2
                py = cy_pt * GV_SCALE - h / 2
                positions[nid] = (px, py)

        # Normalize: shift so minimum x,y is at a comfortable origin
        if positions:
            min_x = min(p[0] for p in positions.values())
            min_y = min(p[1] for p in positions.values())
            margin = 60
            for nid in positions:
                x, y = positions[nid]
                positions[nid] = (x - min_x + margin, y - min_y + margin)

        # Graphviz y-axis is bottom-up; flip to top-down
        if positions:
            max_y = max(p[1] + sizes[nid][1] for nid, p in positions.items())
            for nid in positions:
                x, y = positions[nid]
                h = sizes[nid][1]
                positions[nid] = (x, max_y - y - h + margin)

        return positions

    def build(self, output: str | Path) -> Path:
        """Compute layout and generate the .excalidraw file."""
        sizes = self._compute_node_sizes()
        positions = self._run_graphviz(sizes)

        elements: list[dict] = []

        # Generate boundary rectangles FIRST (so they render behind nodes)
        boundary_pad = 25
        boundary_label_h = 22
        for gid, gattrs in self._groups.items():
            member_ids = [
                nid for nid, nattrs in self._nodes.items()
                if nattrs.get("group") == gid and nid in positions
            ]
            if not member_ids:
                continue

            # Compute bounding box from member positions + sizes
            min_x = min(positions[nid][0] for nid in member_ids)
            min_y = min(positions[nid][1] for nid in member_ids)
            max_x = max(positions[nid][0] + sizes[nid][0] for nid in member_ids)
            max_y = max(positions[nid][1] + sizes[nid][1] for nid in member_ids)

            bx = min_x - boundary_pad
            by = min_y - boundary_pad - boundary_label_h
            bw = (max_x - min_x) + boundary_pad * 2
            bh = (max_y - min_y) + boundary_pad * 2 + boundary_label_h

            boundary_grp_id = f"grp_boundary_{gid}"
            rect_id = f"boundary_{gid}"
            elements.append({
                "type": "rectangle",
                "id": rect_id,
                "x": bx,
                "y": by,
                "width": bw,
                "height": bh,
                "strokeColor": gattrs["stroke"],
                "backgroundColor": gattrs["fill"],
                "fillStyle": "solid",
                "strokeWidth": 2,
                "strokeStyle": "dashed",
                "roughness": 0,
                "opacity": 15,
                "angle": 0,
                "seed": _seed(rect_id),
                "version": 1,
                "versionNonce": _nonce(rect_id),
                "isDeleted": False,
                "groupIds": [boundary_grp_id],
                "boundElements": None,
                "link": None,
                "locked": False,
                "roundness": {"type": 3},
            })

            label_id = f"boundary_{gid}_label"
            elements.append({
                "type": "text",
                "id": label_id,
                "x": bx + 10,
                "y": by + 5,
                "width": bw - 20,
                "height": 18,
                "text": gattrs["label"],
                "originalText": gattrs["label"],
                "fontSize": 13,
                "fontFamily": 3,
                "textAlign": "left",
                "verticalAlign": "top",
                "strokeColor": gattrs["stroke"],
                "backgroundColor": "transparent",
                "fillStyle": "solid",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 0,
                "opacity": 100,
                "angle": 0,
                "seed": _seed(label_id),
                "version": 1,
                "versionNonce": _nonce(label_id),
                "isDeleted": False,
                "groupIds": [boundary_grp_id],
                "boundElements": None,
                "link": None,
                "locked": False,
                "containerId": None,
                "autoResize": True,
                "lineHeight": 1.25,
            })

        # Generate nodes at computed positions
        for nid, attrs in self._nodes.items():
            x, y = positions.get(nid, (0, 0))
            node_elements = node(
                nid, attrs["title"], x, y,
                subtitle=attrs.get("subtitle"),
                detail=attrs.get("detail"),
                tag=attrs.get("tag"),
                width=attrs.get("width"),
                fill=attrs["fill"],
                stroke=attrs["stroke"],
            )
            # If node belongs to a group, add the boundary group ID
            # to all of its elements so they move with the boundary
            grp = attrs.get("group")
            if grp:
                boundary_grp_id = f"grp_boundary_{grp}"
                for el in node_elements:
                    el["groupIds"].append(boundary_grp_id)
            elements += node_elements

        # Generate persons at computed positions
        for pid, attrs in self._persons.items():
            x, y = positions.get(pid, (0, 0))
            elements += person(
                pid, attrs["title"], x, y,
                detail=attrs.get("detail"),
                fill=attrs["fill"],
                stroke=attrs["stroke"],
            )

        # Generate arrows
        for e in self._edges:
            elements += arrow(
                e["from_id"], e["to_id"], elements,
                label=e.get("label"),
                color=e.get("color"),
                dashed=e.get("dashed", False),
            )

        # Generate diagram title above everything
        if self.title:
            # Find top-left extent of all elements
            all_x = [el["x"] for el in elements if "x" in el]
            all_y = [el["y"] for el in elements if "y" in el]
            if all_x and all_y:
                min_x = min(all_x)
                min_y = min(all_y)
                max_x = max(
                    el["x"] + el.get("width", 0) for el in elements if "x" in el
                )
                content_w = max_x - min_x
                title_y = min_y - DIAGRAM_TITLE_FONT * 1.25 - 20
                if hasattr(self, '_subtitle'):
                    title_y -= DIAGRAM_SUBTITLE_FONT * 1.25 + 4
                elements = diagram_title(
                    self.title, min_x, title_y,
                    subtitle=getattr(self, '_subtitle', None),
                    width=content_w,
                ) + elements

        return diagram(elements, output)


# ---------------------------------------------------------------------------
# Diagram wrapper
# ---------------------------------------------------------------------------

def diagram(elements: list[dict], output: str | Path) -> Path:
    """Wrap elements in an Excalidraw document and write to file."""
    doc = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": "#ffffff",
            "gridSize": 20,
        },
        "files": {},
    }
    path = Path(output)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI: quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    g = Graph(
        "Container Diagram — VINtelligence Service",
        subtitle="C4 Level 2 — Runtime processes within EKS pod",
        rankdir="LR",
    )

    # Boundary group
    g.group("service", label="VINtelligence Service — EKS ps-production")

    # Person (actor)
    g.person("user", title="Browser User",
             detail="CDN-delivered\ninsurance site")

    # Internal containers (inside boundary)
    g.node("ingress", title="nginx-ps Ingress", subtitle="[nginx]",
           detail="TLS, host routing,\nrate limiting",
           fill="#3b82f6", stroke="#1e3a5f", group="service")
    g.node("http", title="HTTP Server", subtitle="[Go :8080]",
           detail="Handlers + middleware\n+ in-mem caches",
           fill="#3b82f6", stroke="#1e3a5f", group="service")
    g.node("consumer", title="Config Consumer", subtitle="[goroutine]",
           detail="Kafka topic reader",
           fill="#a7f3d0", stroke="#047857", group="service")
    g.node("metrics", title="Metrics Server", subtitle="[Go :9006]",
           detail="/metrics endpoint",
           fill="#ddd6fe", stroke="#6d28d9", group="service")

    # External systems (outside boundary)
    g.node("ihs", title="IHS Markit API", subtitle="[SOAP]",
           detail="Vehicle data\n(S&P Global)", tag="external system",
           fill="#fed7aa", stroke="#c2410c")
    g.node("kafka", title="Kafka Cluster",
           detail="Runtime config", tag="external system",
           fill="#fed7aa", stroke="#c2410c")
    g.node("prom", title="Prometheus",
           detail="Metrics scraping", tag="external system",
           fill="#fed7aa", stroke="#c2410c")

    # Edges
    g.edge("user", "ingress", label="HTTPS")
    g.edge("ingress", "http", label=":8080")
    g.edge("http", "ihs", label="SOAP")
    g.edge("kafka", "consumer", label="Config events")
    g.edge("consumer", "http", label="RuntimeStore")
    g.edge("prom", "metrics", label=":9006")

    g.build("/tmp/test.excalidraw")
    print("/tmp/test.excalidraw")
