#!/usr/bin/env python3
"""Shared fail-closed contract helpers for canonical non-State dossiers."""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

TYPE_DIR = {
    "Agency": "agencies",
    "Institution": "institutions",
    "Organization": "organizations",
    "Person": "persons",
    "Project": "projects",
    "Deployment": "projects",
}
ENTITY_SUFFIXES = {".json", ".jsonld"}
MANIFEST_NAME_RE = re.compile(r"^canonical-entity-dossier-migration-v([1-9][0-9]*)\.json$")
MANIFEST_PREFIX = "canonical-entity-dossier-migration-v"
RASTER_FACSIMILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SVG_NS = "{http://www.w3.org/2000/svg}"


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def entity_paths(root: Path) -> list[Path]:
    entity_dir = root / "knowledge/entities"
    return sorted(
        path for path in entity_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in ENTITY_SUFFIXES
    )


def strict_manifest_paths(root: Path) -> tuple[list[Path], list[str]]:
    directory = root / "knowledge/generated"
    errors: list[str] = []
    accepted: list[tuple[int, Path]] = []
    if not directory.exists():
        return [], ["knowledge/generated: missing manifest directory"]
    for path in sorted(directory.iterdir()):
        if not path.is_file() or not path.name.startswith(MANIFEST_PREFIX):
            continue
        if not path.name.endswith(".json"):
            errors.append(f"{path.relative_to(root)}: canonical migration manifest must end in .json")
            continue
        match = MANIFEST_NAME_RE.fullmatch(path.name)
        if match is None:
            errors.append(
                f"{path.relative_to(root)}: invalid canonical migration manifest filename; "
                "expected canonical-entity-dossier-migration-v<N>.json with N >= 1"
            )
            continue
        accepted.append((int(match.group(1)), path))
    accepted.sort(key=lambda item: item[0])
    return [path for _, path in accepted], errors


def resolve_repo_ref(root: Path, owner_file: Path, ref: object) -> Path | None:
    if not isinstance(ref, str) or not ref:
        return None
    absolute = (owner_file.parent / ref).resolve()
    try:
        return absolute.relative_to(root.resolve())
    except ValueError:
        return None


def canonical_visuals(entity_id: str) -> tuple[str, str]:
    base = "dossiers/assets/generated"
    return (
        f"{base}/{entity_id}-status.svg",
        f"{base}/{entity_id}-evidence.svg",
    )


def validate_universe(root: Path) -> list[str]:
    """Validate identity-to-dossier binding for every supported non-State entity."""
    errors: list[str] = []
    seen: dict[str, Path] = {}
    for path in entity_paths(root):
        try:
            record = load_json(path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            continue
        entity_id = record.get("id")
        entity_type = record.get("type")
        if not isinstance(entity_id, str) or not entity_id:
            errors.append(f"{path.relative_to(root)}: entity id is required")
            continue
        if entity_id in seen:
            errors.append(
                f"duplicate canonical entity id {entity_id}: "
                f"{seen[entity_id].relative_to(root)} and {path.relative_to(root)}"
            )
            continue
        seen[entity_id] = path
        if entity_type not in TYPE_DIR:
            continue
        rel = resolve_repo_ref(root, path, record.get("dossier"))
        expected_dir = TYPE_DIR[entity_type]
        if rel is None or len(rel.parts) < 3 or rel.parts[:2] != ("dossiers", expected_dir) or rel.suffix != ".md":
            errors.append(
                f"{entity_id}: dossier must resolve under dossiers/{expected_dir}/ as Markdown"
            )
            continue
        dossier = root / rel
        if not dossier.is_file():
            errors.append(f"{entity_id}: dedicated dossier does not exist: {rel.as_posix()}")
            continue
        fm = frontmatter(dossier.read_text(encoding="utf-8"))
        if fm.get("id") != f"ECL-{entity_id}":
            errors.append(
                f"{entity_id}: dossier {rel.as_posix()} frontmatter id {fm.get('id')!r} "
                f"!= {f'ECL-{entity_id}'!r}"
            )
        name = record.get("name")
        if "entity" in fm and isinstance(name, str) and fm.get("entity") != name:
            errors.append(
                f"{entity_id}: dossier {rel.as_posix()} frontmatter entity {fm.get('entity')!r} != ABox name {name!r}"
            )
        if "entity_type" in fm and fm.get("entity_type") != str(entity_type).lower():
            errors.append(
                f"{entity_id}: dossier {rel.as_posix()} frontmatter entity_type {fm.get('entity_type')!r} "
                f"!= {str(entity_type).lower()!r}"
            )
    return errors


def validate_manifest_visual_paths(root: Path) -> list[str]:
    errors: list[str] = []
    paths, naming_errors = strict_manifest_paths(root)
    errors.extend(naming_errors)
    for manifest_path in paths:
        try:
            manifest = load_json(manifest_path)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
            continue
        for row in manifest.get("entities", []):
            if not isinstance(row, dict):
                continue
            entity_id = row.get("id")
            visuals = row.get("visuals")
            if not isinstance(entity_id, str) or not entity_id:
                continue
            expected = list(canonical_visuals(entity_id))
            if visuals != expected:
                errors.append(
                    f"{manifest_path.relative_to(root)}: {entity_id}: visuals must be exactly {expected!r}, got {visuals!r}"
                )
    return errors


def validate_evidence_image_surface(root: Path) -> list[str]:
    """Evidence facsimiles are provenance-controlled raster files only."""
    errors: list[str] = []
    directory = root / "dossiers/evidence-images"
    if not directory.exists():
        return errors
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if path.name == "README.md" or path.suffix.lower() == ".json":
            continue
        if path.suffix.lower() not in RASTER_FACSIMILE_EXTENSIONS:
            errors.append(
                f"{rel}: unsupported source-facsimile file type; only PNG/JPEG/WebP raster assets are allowed"
            )
            continue
        sidecar = path.with_suffix(".json")
        if not sidecar.is_file():
            errors.append(f"{rel}: missing provenance sidecar {sidecar.name}")
    return errors


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _clip_rects(svg_root: ET.Element) -> dict[str, tuple[float, float, float, float]]:
    result: dict[str, tuple[float, float, float, float]] = {}
    for clip in svg_root.findall(f".//{SVG_NS}clipPath"):
        clip_id = clip.get("id")
        rect = clip.find(f"{SVG_NS}rect")
        if not clip_id or rect is None:
            continue
        x, y, w, h = (_float(rect.get(k)) for k in ("x", "y", "width", "height"))
        if None not in (x, y, w, h) and w is not None and h is not None and w >= 0 and h >= 0:
            result[clip_id] = (x or 0.0, y or 0.0, (x or 0.0) + w, (y or 0.0) + h)
    return result


def _clip_id(value: str | None) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"url\(#([A-Za-z0-9_.:-]+)\)", value.strip())
    return match.group(1) if match else None


def _inside(rect: tuple[float, float, float, float], x: float, y: float) -> bool:
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def validate_generated_svg_clipping(root: Path) -> list[str]:
    errors: list[str] = []
    directory = root / "dossiers/assets/generated"
    if not directory.exists():
        return ["dossiers/assets/generated: missing generated visual directory"]
    for path in sorted(directory.glob("*.svg")):
        try:
            svg = ET.parse(path).getroot()
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: invalid SVG: {exc}")
            continue
        for element in svg.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag in {"foreignObject", "textPath", "use"}:
                errors.append(f"{path.relative_to(root)}: unsupported SVG indirection element <{tag}>")
            if any(name in element.attrib for name in ("mask", "filter")):
                errors.append(f"{path.relative_to(root)}: unsupported SVG visibility indirection on <{tag}>")
        clips = _clip_rects(svg)
        parent_map = {child: parent for parent in svg.iter() for child in parent}
        for text in svg.findall(f".//{SVG_NS}text"):
            clip = _clip_id(text.get("clip-path"))
            if clip is None:
                parent = parent_map.get(text)
                while parent is not None and clip is None:
                    clip = _clip_id(parent.get("clip-path"))
                    parent = parent_map.get(parent)
            if clip is None:
                continue
            rect = clips.get(clip)
            if rect is None:
                errors.append(f"{path.relative_to(root)}: text references unknown clipPath {clip!r}")
                continue
            positions: list[tuple[float, float]] = []
            x, y = _float(text.get("x")), _float(text.get("y"))
            if x is not None and y is not None:
                positions.append((x, y))
            for tspan in text.findall(f".//{SVG_NS}tspan"):
                tx, ty = _float(tspan.get("x")), _float(tspan.get("y"))
                if tx is not None and ty is not None:
                    positions.append((tx, ty))
            if not positions:
                errors.append(f"{path.relative_to(root)}: clipped text has no statically verifiable anchor")
                continue
            for px, py in positions:
                if not _inside(rect, px, py):
                    errors.append(
                        f"{path.relative_to(root)}: clipped text anchor ({px:g}, {py:g}) is outside clipPath {clip}"
                    )
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_universe(root))
    errors.extend(validate_manifest_visual_paths(root))
    errors.extend(validate_evidence_image_surface(root))
    errors.extend(validate_generated_svg_clipping(root))
    return errors
