#!/usr/bin/env python3
# Fail closed when generated dossier text can paint outside its owning visual region.

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"

EXPECTED = {
    "evidence": {
        "source-box-clip": (52.0, 158.0, 276.0, 70.0, 3),
        "proposition-box-clip": (402.0, 158.0, 276.0, 70.0, 3),
        "identity-box-clip": (752.0, 158.0, 276.0, 70.0, 3),
        "boundary-box-clip": (172.0, 304.0, 828.0, 48.0, 2),
    },
    "status": {
        "status-name-clip": (54.0, 64.0, 800.0, 66.0, 2),
        "status-badge-clip": (54.0, 150.0, 300.0, 66.0, 2),
    },
}


def number(value: str | None) -> float:
    if value is None:
        raise ValueError("missing numeric SVG attribute")
    return float(value)


def clip_map(root: ET.Element) -> dict[str, ET.Element]:
    result: dict[str, ET.Element] = {}
    for clip in root.findall(f".//{NS}clipPath"):
        clip_id = clip.get("id")
        rect = clip.find(f"{NS}rect")
        if clip_id and rect is not None:
            result[clip_id] = rect
    return result


def clipped_text(root: ET.Element, clip_id: str) -> list[ET.Element]:
    token = f"url(#{clip_id})"
    return [node for node in root.findall(f".//{NS}text") if node.get("clip-path") == token]


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        return [f"{path}: invalid SVG/XML: {exc}"]

    name = path.name
    if name == "state-outcome-legend.svg":
        clips = clip_map(root)
        for idx in range(5):
            clip_id = f"legend-{idx}-clip"
            if clip_id not in clips:
                errors.append(f"{path}: missing {clip_id}")
                continue
            texts = clipped_text(root, clip_id)
            if len(texts) != 1:
                errors.append(f"{path}: {clip_id} must bound exactly one label text")
                continue
            if len(texts[0].findall(f"{NS}tspan")) > 2:
                errors.append(f"{path}: {clip_id} label exceeds two wrapped lines")
        return errors

    kind = "evidence" if name.endswith("-evidence.svg") else "status" if name.endswith("-status.svg") else None
    if kind is None:
        return errors

    clips = clip_map(root)
    for clip_id, (x, y, width, height, max_lines) in EXPECTED[kind].items():
        rect = clips.get(clip_id)
        if rect is None:
            errors.append(f"{path}: missing hard overflow guard {clip_id}")
            continue
        actual = (number(rect.get("x")), number(rect.get("y")), number(rect.get("width")), number(rect.get("height")))
        expected = (x, y, width, height)
        if actual != expected:
            errors.append(f"{path}: {clip_id} geometry {actual} != expected {expected}")
        texts = clipped_text(root, clip_id)
        if len(texts) != 1:
            errors.append(f"{path}: {clip_id} must bound exactly one dynamic text block")
            continue
        lines = texts[0].findall(f"{NS}tspan")
        if not lines:
            errors.append(f"{path}: {clip_id} text must use wrapped tspans")
        if len(lines) > max_lines:
            errors.append(f"{path}: {clip_id} uses {len(lines)} lines > allowed {max_lines}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, nargs="?", default=Path("dossiers/assets/generated"))
    args = parser.parse_args()

    errors: list[str] = []
    files = sorted(args.directory.glob("*.svg"))
    if not files:
        errors.append(f"{args.directory}: no SVG files found")
    for path in files:
        errors.extend(validate_file(path))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"dossier visual layout: OK ({len(files)} SVGs, hard clipping + wrapped text)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
