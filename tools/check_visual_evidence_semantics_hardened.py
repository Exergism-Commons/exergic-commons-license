#!/usr/bin/env python3
"""Fail-closed visibility wrapper for canonical SVG semantic extraction."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import check_visual_evidence_semantics as _base

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
    for clip in root.findall(f".//{SVG_NS}clipPath"):
        rect = clip.find(f"{SVG_NS}rect")
        if rect is None:
            return False
        try:
            width = float(rect.get("width", ""))
            height = float(rect.get("height", ""))
        except ValueError:
            return False
        if not (math.isfinite(width) and math.isfinite(height) and width > 0 and height > 0):
            return False
    return True


def _text_attributes_are_supported(element: ET.Element) -> bool:
    tag = element.tag.rsplit("}", 1)[-1]
    allowed = SAFE_TEXT_ATTRIBUTES if tag == "text" else SAFE_TSPAN_ATTRIBUTES
    return set(element.attrib).issubset(allowed)


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
    if not _positive_viewbox(root) or not _positive_clip_rectangles(root):
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

    return _original_visible_svg_text(path)


_base.visible_svg_text = visible_svg_text


if __name__ == "__main__":
    raise SystemExit(_base.main())
