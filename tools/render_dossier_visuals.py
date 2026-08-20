#!/usr/bin/env python3
"""Render dossier visuals while preserving legacy bytes through v39.

v40+ uses a normalized identity-boundary visual body. Entity identity, State
provenance and source granularity remain authoritative metadata; the body
normalizes only proposition/evidence wording so visual adjacency cannot imply
entity-level governance or culpability.
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
    # Keep state and sourceGranularity unchanged: both are provenance data.
    # The visible identity label stays generic, while the real entity name is
    # restored into SVG metadata below as required by VISUAL-EVIDENCE.md.
    rendered["name"] = _GENERIC_NAME
    rendered["visualModel"] = dict(_GENERIC_MODEL)
    return rendered


def _restore_metadata_name(svg: str, entity: dict) -> str:
    generic = legacy.esc(_GENERIC_NAME)
    actual = legacy.esc(entity["name"])
    svg = svg.replace(
        f'<title id="title">{generic} —',
        f'<title id="title">{actual} —',
        1,
    )
    # status_svg also mentions the normalized name in its accessibility desc.
    svg = svg.replace(
        f'not inherited by {generic}.</desc>',
        f'not inherited by {actual}.</desc>',
        1,
    )
    return svg


def status_svg(entity: dict, palette: dict) -> str:
    if not entity.get("_normalized_visual_v40"):
        return _original_status_svg(entity, palette)
    return _restore_metadata_name(_original_status_svg(normalized(entity), palette), entity)


def evidence_svg(entity: dict) -> str:
    if not entity.get("_normalized_visual_v40"):
        return _original_evidence_svg(entity)
    return _restore_metadata_name(_original_evidence_svg(normalized(entity)), entity)


legacy.load_entities = load_entities
legacy.status_svg = status_svg
legacy.evidence_svg = evidence_svg


if __name__ == "__main__":
    raise SystemExit(legacy.main())
