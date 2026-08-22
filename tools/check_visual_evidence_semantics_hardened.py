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
_original_visible_svg_text = _base.visible_svg_text


def _style_map(value: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for declaration in (value or "").split(";"):
        if ":" not in declaration:
            continue
        key, val = declaration.split(":", 1)
        result[key.strip().lower()] = val.strip().lower()
    return result


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


def _ancestor_paint_is_demonstrably_visible(
    element: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
) -> bool:
    node: ET.Element | None = element
    while node is not None:
        style = _style_map(node.get("style"))

        font_raw = node.get("font-size") or style.get("font-size")
        if font_raw is not None:
            font_size = _scalar(font_raw)
            if font_size is None or font_size < MIN_VISIBLE_FONT_SIZE:
                return False

        for attr in ("opacity", "fill-opacity"):
            raw = node.get(attr) or style.get(attr)
            if raw is None:
                continue
            opacity = _scalar(raw, percent=True)
            if opacity is None or opacity < MIN_VISIBLE_OPACITY:
                return False

        fill = (node.get("fill") or style.get("fill") or "").strip().lower()
        if fill in TRANSPARENT_PAINT:
            return False

        node = parent_map.get(node)
    return True


def visible_svg_text(path: Path) -> str | None:
    """Return only text whose visibility survives additional paint/geometry guards."""
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    if root.tag != f"{SVG_NS}svg":
        return None
    if not _positive_viewbox(root) or not _positive_clip_rectangles(root):
        return None

    parent_map = {child: parent for parent in root.iter() for child in parent}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in {"text", "tspan"}:
            continue
        if not _ancestor_paint_is_demonstrably_visible(element, parent_map):
            return None

    return _original_visible_svg_text(path)


_base.visible_svg_text = visible_svg_text


if __name__ == "__main__":
    raise SystemExit(_base.main())
