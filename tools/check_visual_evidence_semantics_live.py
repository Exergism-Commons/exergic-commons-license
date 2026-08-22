#!/usr/bin/env python3
"""Visible semantic checks with live State-context status and cumulative clipping guard."""
from __future__ import annotations

import json
import re
from pathlib import Path

import canonical_dossier_contract as contract
import check_visual_evidence_semantics as base

ROOT = Path(__file__).resolve().parents[1]
VALID = {"R", "S", "U", "N"}
EXPLICIT_STATE_OUTCOME_RE = re.compile(
    r"\*\*([RSUN])\s+(?:—|–|-|·)\s+([^*\n]+?)\*\*"
)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def current_state_outcome(state: str) -> str | None:
    path = ROOT / "dossiers/states" / f"{state}.md"
    if not path.is_file():
        return None
    value = frontmatter(path).get("provisional_outcome")
    return value if value in VALID else None


def validate_live_state_context_text(
    dossier_text: str,
    dossier: str,
    entity_id: str,
    state: str,
    live: str,
    label: str,
) -> list[str]:
    """Reject stale present-tense State outcome codes embedded in dossier prose.

    Outcome-neutral prose is allowed. If the State-governance section chooses to
    state an explicit ``R/S/U/N — description`` value, the outcome code becomes
    part of the live surface and must agree with the current State dossier. The
    human-readable description may remain contextual or historically specific.
    """
    body = base.section_body(dossier_text, "## State governance context")
    if body is None:
        return []

    errors: list[str] = []
    for stated_code, stated_label in EXPLICIT_STATE_OUTCOME_RE.findall(body):
        if stated_code == live:
            continue
        errors.append(
            f"{dossier}: {entity_id}: State governance context text is stale: "
            f"states {stated_code} · {stated_label.strip()}, but current {state} State dossier "
            f"is {live} · {label}; update the prose or make it outcome-neutral"
        )
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(contract.validate_generated_svg_clipping(ROOT))
    checked = 0
    palette = base.load_json(base.PALETTE_PATH)
    manifests = sorted(
        base.MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in manifest.get("entities", []):
            if not isinstance(row, dict):
                errors.append(f"{manifest_path.relative_to(ROOT)}: non-object migration row")
                continue
            entity_id = row.get("id", "<missing-id>")
            dossier = row.get("dossier")
            state = row.get("state")
            source_granularity = row.get("sourceGranularity")
            if not isinstance(dossier, str) or not (ROOT / dossier).is_file():
                errors.append(f"{entity_id}: missing dossier {dossier!r}")
                continue
            dossier_text = (ROOT / dossier).read_text(encoding="utf-8")
            for heading in base.TEXTUAL_EQUIVALENT_SECTIONS:
                body = base.section_body(dossier_text, heading)
                if body is None or not body:
                    errors.append(f"{dossier}: {entity_id}: missing/empty textual-equivalent section {heading}")

            status_rel = base.one_visual(row, "-status.svg")
            evidence_rel = base.one_visual(row, "-evidence.svg")
            if status_rel is None or evidence_rel is None:
                errors.append(f"{entity_id}: requires exactly one status and one evidence SVG")
                continue

            status_text = base.visible_svg_text(ROOT / status_rel) if (ROOT / status_rel).is_file() else None
            live = current_state_outcome(state) if isinstance(state, str) else None
            if status_text is None or live not in palette.get("states", {}):
                errors.append(f"{entity_id}: invalid status SVG or current State outcome")
            else:
                label = palette["states"][live].get("label")
                if not isinstance(label, str) or not label:
                    errors.append(f"{entity_id}: live State outcome {live!r} has no canonical palette label")
                else:
                    errors.extend(
                        validate_live_state_context_text(
                            dossier_text,
                            dossier,
                            str(entity_id),
                            str(state),
                            live,
                            label,
                        )
                    )
                    for required in (
                        "STATE DOSSIER CONTEXT",
                        base.normalized(f"{live} · {label}"),
                        f"{state} State dossier",
                        "no entity-level governance inheritance",
                    ):
                        if required not in status_text:
                            errors.append(f"{status_rel}: {entity_id}: visible status semantics missing {required!r}")
                    checked += 1

            evidence_text = base.visible_svg_text(ROOT / evidence_rel) if (ROOT / evidence_rel).is_file() else None
            granularity_label = base.GRANULARITY_LABELS.get(source_granularity)
            if evidence_text is None or granularity_label is None:
                errors.append(f"{entity_id}: invalid evidence SVG/sourceGranularity")
            else:
                for required in (
                    "DERIVED EVIDENCE DIAGRAM",
                    "textual equivalent is preserved in the dossier",
                    granularity_label,
                    "Identity ≠ participation / culpability",
                ):
                    if required not in evidence_text:
                        errors.append(f"{evidence_rel}: {entity_id}: visible evidence semantics missing {required!r}")
                checked += 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"visual evidence semantics: FAILED ({len(errors)} error(s))")
        return 1
    print(
        f"visual evidence semantics: OK ({checked} status/evidence SVGs checked; "
        "live State context + dossier prose coherence + cumulative clips)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
