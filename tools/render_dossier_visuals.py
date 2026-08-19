#!/usr/bin/env python3
"""Render dossier visuals while preserving legacy bytes through v39.

v40+ uses a normalized identity-boundary visual template. Entity-specific
identity and evidence metadata remain in manifests/dossiers; the SVG template
only renders State-context class and the non-inheritance boundary.
"""
from __future__ import annotations

from pathlib import Path

import render_dossier_visuals_legacy as legacy

_GENERIC_NAME = "Canonical non-State identity"
_GENERIC_MODEL = {
    "source": "Linked State dossier + ABox identity record",
    "proposition": "Dedicated dossier migration preserves an identity-only non-State record",
    "boundary": "No entity-level governance inference",
}

_original_load_entities = legacy.load_entities
_original_status_svg = legacy.status_svg
_original_evidence_svg = legacy.evidence_svg


def load_entities(manifest_dir: Path) -> list[dict]:
    rows = _original_load_entities(manifest_dir)
    normalized_ids: set[str] = set()
    for path in manifest_dir.glob("canonical-entity-dossier-migration-v*.json"):
        version = int(path.stem.rsplit("v", 1)[1])
        if version < 40:
            continue
        manifest = legacy.load_json(path)
        normalized_ids.update(row["id"] for row in manifest["entities"])
    for row in rows:
        if row["id"] in normalized_ids:
            row["_normalized_visual_v40"] = True
    return rows


def normalized(entity: dict) -> dict:
    if not entity.get("_normalized_visual_v40"):
        return entity
    rendered = dict(entity)
    rendered["name"] = _GENERIC_NAME
    rendered["state"] = "Referenced"
    rendered["sourceGranularity"] = "partial"
    rendered["visualModel"] = dict(_GENERIC_MODEL)
    return rendered


def status_svg(entity: dict, palette: dict) -> str:
    return _original_status_svg(normalized(entity), palette)


def evidence_svg(entity: dict) -> str:
    return _original_evidence_svg(normalized(entity))


legacy.load_entities = load_entities
legacy.status_svg = status_svg
legacy.evidence_svg = evidence_svg


if __name__ == "__main__":
    raise SystemExit(legacy.main())
