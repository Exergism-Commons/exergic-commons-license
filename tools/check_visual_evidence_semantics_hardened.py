#!/usr/bin/env python3
"""Fail-closed visibility wrapper for canonical SVG semantic extraction."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import check_visual_evidence_semantics as _base
import dossier_svg_metrics as metrics

for _name, _value in vars(_base).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

SVG_NS = "{http://www.w3.org/2000/svg}"
MIN_VISIBLE_FONT_SIZE = 8.0
MIN_VISIBLE_OPACITY = 0.05
TRANSPARENT_PAINT = {
    "transparent",
    "rgba(0,0,0,0)",
    "rgba(0, 0, 0, 0)",
    "#0000",
    "#00000000",
}
UNVERIFIABLE_PAINT = {"currentcolor", "context-fill", "context-stroke"}
SAFE_TEXT_ATTRIBUTES = {
    "x", "y", "dx", "dy", "font-family", "font-size", "font-weight",
    "fill", "fill-opacity", "opacity", "clip-path", "display", "visibility",
}
SAFE_TSPAN_ATTRIBUTES = {
    "x", "y", "dx", "dy", "font-family", "font-size", "font-weight",
    "fill", "fill-opacity", "opacity", "clip-path", "display", "visibility",
}
SAFE_CLIP_PATH_ATTRIBUTES = {"id", "clipPathUnits"}
SAFE_CLIP_RECT_ATTRIBUTES = {"x", "y", "width", "height", "rx", "ry"}
UNSUPPORTED_TEXT_LAYOUT_ATTRIBUTES = {
    "text-anchor", "direction", "unicode-bidi", "writing-mode",
    "glyph-orientation-horizontal", "glyph-orientation-vertical",
    "letter-spacing", "word-spacing", "kerning",
}
CANONICAL_FONT_FAMILY = "Arial, Helvetica, sans-serif"
CANONICAL_VIEWPORTS = {"status": (960.0, 300.0), "evidence": (1100.0, 390.0), "legend": (1000.0, 245.0)}
_original_visible_svg_text = _base.visible_svg_text


def _style_map(value: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for declaration in (value or "").split(";"):
        if ":" not in declaration:
            continue
        key, val = declaration.split(":", 1)
        result[key.strip().lower()] = val.strip().lower()
    return result


def _css_value(node: ET.Element, style: dict[str, str], name: str) -> str | None:
    if name in style:
        return style[name]
    return node.get(name)


def _scalar(value: str | None, *, percent: bool = False) -> float | None:
    if value is None:
        return None
    raw = value.strip().lower()
    try:
        if raw.endswith("%"):
            number = float(raw[:-1])
            return number / 100.0 if percent else None
        number = float(raw)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _unit_interval(value: str | None) -> float | None:
    number = _scalar(value, percent=True)
    if number is None or number < 0 or number > 1:
        return None
    return number


def _functional_alpha(raw: str) -> float | None:
    value = raw.strip().lower()
    if not value.endswith(")"):
        return None
    inner = value[value.find("(") + 1 : -1].strip()
    if "/" in inner:
        return _unit_interval(inner.rsplit("/", 1)[1].strip())
    if value.startswith(("rgba(", "hsla(")):
        parts = [part.strip() for part in inner.split(",")]
        if len(parts) != 4:
            return None
        return _unit_interval(parts[3])
    return 1.0


def _paint_alpha(value: str | None) -> float | None:
    raw = (value or "").strip().lower()
    if not raw:
        return 1.0
    if raw == "none" or raw in TRANSPARENT_PAINT:
        return 0.0
    if raw in UNVERIFIABLE_PAINT or raw.startswith("url(") or raw.startswith("var("):
        return None
    if raw.startswith("#"):
        digits = raw[1:]
        if not re.fullmatch(r"[0-9a-f]+", digits):
            return None
        if len(digits) == 4:
            return int(digits[3], 16) / 15.0
        if len(digits) == 8:
            return int(digits[6:8], 16) / 255.0
        if len(digits) in {3, 6}:
            return 1.0
        return None
    if raw.startswith(("rgb(", "rgba(", "hsl(", "hsla(")):
        return _functional_alpha(raw)
    if "(" in raw or ")" in raw:
        return None
    return 1.0


def _positive_viewbox(root: ET.Element) -> bool:
    raw = root.get("viewBox")
    if not raw:
        return False
    parts = re.split(r"[ ,]+", raw.strip())
    if len(parts) != 4:
        return False
    try:
        _x, _y, width, height = map(float, parts)
    except ValueError:
        return False
    return all(math.isfinite(value) for value in (_x, _y, width, height)) and width > 0 and height > 0


def _positive_clip_rectangles(root: ET.Element) -> bool:
    parent_map = {child: parent for parent in root.iter() for child in parent}
    for clip in root.findall(f".//{SVG_NS}clipPath"):
        if not set(clip.attrib).issubset(SAFE_CLIP_PATH_ATTRIBUTES):
            return False
        parent = parent_map.get(clip)
        if parent is None or parent.tag != f"{SVG_NS}defs" or parent_map.get(parent) is not root:
            return False
        children = list(clip)
        if len(children) != 1 or children[0].tag != f"{SVG_NS}rect":
            return False
        rect = children[0]
        if not set(rect.attrib).issubset(SAFE_CLIP_RECT_ATTRIBUTES):
            return False
        try:
            x = float(rect.get("x", ""))
            y = float(rect.get("y", ""))
            width = float(rect.get("width", ""))
            height = float(rect.get("height", ""))
            rx = float(rect.get("rx", rect.get("ry", "0")))
            ry = float(rect.get("ry", rect.get("rx", "0")))
        except ValueError:
            return False
        if not all(math.isfinite(value) for value in (x, y, width, height, rx, ry)):
            return False
        if width <= 0 or height <= 0 or rx < 0 or ry < 0 or rx > width / 2 or ry > height / 2:
            return False
    return True


def _text_attributes_are_supported(element: ET.Element) -> bool:
    tag = element.tag.rsplit("}", 1)[-1]
    allowed = SAFE_TEXT_ATTRIBUTES if tag == "text" else SAFE_TSPAN_ATTRIBUTES
    if not set(element.attrib).issubset(allowed):
        return False
    family = element.get("font-family")
    return family is None or family == CANONICAL_FONT_FAMILY


def _canonical_viewport_matches(path: Path, root: ET.Element) -> bool:
    if path.name == "state-outcome-legend.svg":
        kind = "legend"
    elif path.name.endswith("-status.svg"):
        kind = "status"
    elif path.name.endswith("-evidence.svg"):
        kind = "evidence"
    else:
        return True
    expected = CANONICAL_VIEWPORTS[kind]
    try:
        width = float(root.get("width", ""))
        height = float(root.get("height", ""))
    except ValueError:
        return False
    parts = re.split(r"[ ,]+", root.get("viewBox", "").strip())
    if len(parts) != 4:
        return False
    try:
        x, y, vb_width, vb_height = map(float, parts)
    except ValueError:
        return False
    return (width, height) == expected and (x, y, vb_width, vb_height) == (0.0, 0.0, *expected)


def _layout_surface_supported(root: ET.Element) -> bool:
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if any(name in element.attrib for name in UNSUPPORTED_TEXT_LAYOUT_ATTRIBUTES):
            return False
        if "font-family" in element.attrib and tag not in {"text", "tspan"}:
            return False
    return True


def _rect_box(element: ET.Element) -> tuple[float, float, float, float] | None:
    try:
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        width = float(element.get("width", ""))
        height = float(element.get("height", ""))
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return x, y, x + width, y + height


def _effective_fill(element: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> str | None:
    node: ET.Element | None = element
    while node is not None:
        value = node.get("fill")
        if value is not None:
            return value.strip()
        node = parent_map.get(node)
    return "black"


def _intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _text_line_boxes(text: ET.Element) -> list[tuple[float, float, float, float]]:
    size = _scalar(text.get("font-size"))
    if size is None or size <= 0:
        return []
    boxes: list[tuple[float, float, float, float]] = []
    tspans = text.findall(f"{SVG_NS}tspan")
    if not tspans:
        x = _scalar(text.get("x"))
        y = _scalar(text.get("y"))
        if x is None or y is None or not (text.text or "").strip():
            return []
        width = metrics.measured_width(text.text or "", size)
        boxes.append((x, y - 0.80 * size, x + width, y + 0.25 * size))
        return boxes
    cursor_y: float | None = None
    for tspan in tspans:
        x = _scalar(tspan.get("x"))
        if x is None:
            return []
        if tspan.get("y") is not None:
            cursor_y = _scalar(tspan.get("y"))
        elif tspan.get("dy") is not None and cursor_y is not None:
            dy = _scalar(tspan.get("dy"))
            cursor_y = None if dy is None else cursor_y + dy
        else:
            return []
        if cursor_y is None:
            return []
        value = "".join(tspan.itertext())
        width = metrics.measured_width(value, size)
        boxes.append((x, cursor_y - 0.80 * size, x + width, cursor_y + 0.25 * size))
    return boxes


def _canonical_scene_is_perceptible(path: Path, root: ET.Element) -> bool:
    if not (path.name == "state-outcome-legend.svg" or path.name.endswith("-status.svg") or path.name.endswith("-evidence.svg")):
        return True
    parent_map = {child: parent for parent in root.iter() for child in parent}
    ordered = list(root.iter())
    order = {element: index for index, element in enumerate(ordered)}
    rects: list[tuple[int, ET.Element, tuple[float, float, float, float], str]] = []
    for element in ordered:
        if element.tag != f"{SVG_NS}rect":
            continue
        node = parent_map.get(element)
        under_defs = False
        while node is not None:
            if node.tag == f"{SVG_NS}defs":
                under_defs = True
                break
            node = parent_map.get(node)
        if under_defs:
            continue
        box = _rect_box(element)
        fill = element.get("fill")
        if box is not None and isinstance(fill, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", fill):
            rects.append((order[element], element, box, fill))

    for text in root.findall(f".//{SVG_NS}text"):
        fill = _effective_fill(text, parent_map)
        if fill is None or re.fullmatch(r"#[0-9A-Fa-f]{6}", fill) is None:
            return False
        boxes = _text_line_boxes(text)
        if not boxes:
            return False
        text_index = order[text]
        for box in boxes:
            center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            backgrounds = [
                (index, background)
                for index, _rect, rect_box, background in rects
                if index < text_index
                and rect_box[0] <= center[0] <= rect_box[2]
                and rect_box[1] <= center[1] <= rect_box[3]
            ]
            if not backgrounds:
                return False
            _index, background = max(backgrounds, key=lambda item: item[0])
            try:
                if metrics.contrast_ratio(fill, background) < 4.5:
                    return False
            except ValueError:
                return False
            if any(index > text_index and _intersects(box, rect_box) for index, _rect, rect_box, _fill in rects):
                return False
    return True


def _ancestor_paint_is_demonstrably_visible(
    element: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
) -> bool:
    """Resolve inherited fill and multiplicative opacity without CSS indirection."""
    chain: list[ET.Element] = []
    node: ET.Element | None = element
    while node is not None:
        chain.append(node)
        node = parent_map.get(node)
    chain.reverse()

    effective_opacity = 1.0
    font_size: float | None = None
    fill = "black"
    fill_opacity = 1.0

    for node in chain:
        style = _style_map(node.get("style"))

        display = (_css_value(node, style, "display") or "").strip().lower()
        visibility = (_css_value(node, style, "visibility") or "").strip().lower()
        if display == "none" or visibility in {"hidden", "collapse"}:
            return False

        opacity_raw = _css_value(node, style, "opacity")
        if opacity_raw is not None:
            opacity = _unit_interval(opacity_raw)
            if opacity is None:
                return False
            effective_opacity *= opacity

        font_raw = _css_value(node, style, "font-size")
        if font_raw is not None:
            font_size = _scalar(font_raw)
            if font_size is None:
                return False

        fill_raw = _css_value(node, style, "fill")
        if fill_raw is not None:
            fill = fill_raw.strip().lower()
        fill_opacity_raw = _css_value(node, style, "fill-opacity")
        if fill_opacity_raw is not None:
            parsed = _unit_interval(fill_opacity_raw)
            if parsed is None:
                return False
            fill_opacity = parsed

    if font_size is not None and font_size < MIN_VISIBLE_FONT_SIZE:
        return False
    if effective_opacity < MIN_VISIBLE_OPACITY:
        return False

    fill_alpha = _paint_alpha(fill)
    if fill_alpha is None:
        return False
    return fill_alpha * fill_opacity * effective_opacity >= MIN_VISIBLE_OPACITY


def visible_svg_text(path: Path) -> str | None:
    """Return only text whose visibility survives strict paint/geometry guards."""
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    if root.tag != f"{SVG_NS}svg":
        return None
    if (
        not _positive_viewbox(root)
        or not _positive_clip_rectangles(root)
        or not _canonical_viewport_matches(path, root)
        or not _layout_surface_supported(root)
    ):
        return None
    # Canonical generated SVGs do not need inline CSS. Reject it entirely so CSS
    # comments/escapes/cascade cannot create a second, unmodelled visibility surface.
    if any("style" in element.attrib for element in root.iter()):
        return None

    parent_map = {child: parent for parent in root.iter() for child in parent}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in {"text", "tspan"}:
            continue
        if not _text_attributes_are_supported(element):
            return None
        if not _ancestor_paint_is_demonstrably_visible(element, parent_map):
            return None

    if not _canonical_scene_is_perceptible(path, root):
        return None
    return _original_visible_svg_text(path)


_base.visible_svg_text = visible_svg_text


if __name__ == "__main__":
    raise SystemExit(_base.main())
