#!/usr/bin/env python3
"""Validate normative visible semantics of canonical dossier SVG evidence."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
PALETTE_PATH = ROOT / "knowledge/generated/dossier-visual-palette-v1.json"
SVG_NS = "{http://www.w3.org/2000/svg}"
TEXTUAL_EQUIVALENT_SECTIONS = ("## Evidence record", "## Evidence gaps", "## Sources")
GRANULARITY_LABELS = {
    "direct": "direct locator",
    "partial": "partial locator / explicit gap",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(value: str) -> str:
    return " ".join(value.split())


def visible_svg_text(path: Path) -> str | None:
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return None
    chunks: list[str] = []
    for element in root.iter(f"{SVG_NS}text"):
        chunks.extend(element.itertext())
    return normalized(" ".join(chunks))


def section_body(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}[ \t]*\n(.*?)(?=^##[ \t]+|\Z)",
        text,
    )
    return match.group(1).strip() if match else None


def one_visual(row: dict, suffix: str) -> str | None:
    visuals = row.get("visuals")
    if not isinstance(visuals, list):
        return None
    matches = [item for item in visuals if isinstance(item, str) and item.endswith(suffix)]
    return matches[0] if len(matches) == 1 else None


def main() -> int:
    errors: list[str] = []
    checked = 0
    palette = load_json(PALETTE_PATH)
    manifests = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )

    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        for row in manifest.get("entities", []):
            if not isinstance(row, dict):
                errors.append(f"{manifest_path.relative_to(ROOT)}: non-object migration row")
                continue
            entity_id = row.get("id", "<missing-id>")
            dossier = row.get("dossier")
            state = row.get("state")
            state_context = row.get("stateContext")
            source_granularity = row.get("sourceGranularity")

            if not isinstance(dossier, str) or not dossier:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: missing dossier")
                continue
            dossier_path = ROOT / dossier
            if not dossier_path.is_file():
                errors.append(f"{dossier}: dossier does not exist")
                continue
            dossier_text = dossier_path.read_text(encoding="utf-8")
            for heading in TEXTUAL_EQUIVALENT_SECTIONS:
                body = section_body(dossier_text, heading)
                if body is None:
                    errors.append(f"{dossier}: {entity_id}: missing textual-equivalent section {heading}")
                elif not body:
                    errors.append(f"{dossier}: {entity_id}: empty textual-equivalent section {heading}")

            status_rel = one_visual(row, "-status.svg")
            evidence_rel = one_visual(row, "-evidence.svg")
            if status_rel is None:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: requires exactly one status SVG")
            if evidence_rel is None:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: requires exactly one evidence SVG")

            if status_rel is not None:
                status_path = ROOT / status_rel
                status_text = visible_svg_text(status_path) if status_path.is_file() else None
                if status_text is None:
                    errors.append(f"{entity_id}: invalid or missing status SVG {status_rel}")
                elif state_context not in palette.get("states", {}):
                    errors.append(f"{entity_id}: unknown stateContext {state_context!r} for status semantics")
                else:
                    label = palette["states"][state_context].get("label")
                    expected_badge = normalized(f"{state_context} · {label}")
                    for required in (
                        "STATE DOSSIER CONTEXT",
                        expected_badge,
                        f"{state} State dossier",
                        "no entity-level governance inheritance",
                    ):
                        if required not in status_text:
                            errors.append(
                                f"{status_rel}: {entity_id}: visible status semantics missing {required!r}"
                            )
                    checked += 1

            if evidence_rel is not None:
                evidence_path = ROOT / evidence_rel
                evidence_text = visible_svg_text(evidence_path) if evidence_path.is_file() else None
                granularity_label = GRANULARITY_LABELS.get(source_granularity)
                if evidence_text is None:
                    errors.append(f"{entity_id}: invalid or missing evidence SVG {evidence_rel}")
                elif granularity_label is None:
                    errors.append(
                        f"{entity_id}: unsupported sourceGranularity {source_granularity!r} for evidence semantics"
                    )
                else:
                    for required in (
                        "DERIVED EVIDENCE DIAGRAM",
                        "textual equivalent is preserved in the dossier",
                        granularity_label,
                        "Identity ≠ participation / culpability",
                    ):
                        if required not in evidence_text:
                            errors.append(
                                f"{evidence_rel}: {entity_id}: visible evidence semantics missing {required!r}"
                            )
                    checked += 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"visual evidence semantics: FAILED ({len(errors)} error(s))")
        return 1

    print(f"visual evidence semantics: OK ({checked} status/evidence SVGs checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
