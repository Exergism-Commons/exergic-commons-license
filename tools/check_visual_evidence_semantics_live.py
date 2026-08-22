#!/usr/bin/env python3
"""Visible semantic checks with live State-context status and fail-closed prose/visual guards."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from markdown_it import MarkdownIt

import canonical_dossier_contract as contract
import check_visual_evidence_semantics_hardened as base

ROOT = Path(__file__).resolve().parents[1]
VALID = {"R", "S", "U", "N"}
EXPLICIT_STATE_OUTCOME_RE = re.compile(
    r"(?<![A-Z0-9])([RSUN])\s*(?:—|–|-|·)\s*(?=[A-Za-z])"
)
STATE_DOSSIER_RE = re.compile(r"\b([A-Z]{3})\s+State dossier\b")
TOKEN_RE = re.compile(r"[a-z0-9]+")
MODEL_STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on",
    "or", "the", "to", "with", "canonical", "dossier", "entity", "identity", "record",
    "source", "surface", "abox", "existing", "dedicated", "non", "only", "no", "state",
    "set", "batch", "freeze", "frozen", "locator", "context", "exact", "official",
    "candidate", "material", "without", "ready", "base", "party", "surface", "promoted",
}
TOKEN_ALIASES = {
    "inherited": "inherit",
    "inheritance": "inherit",
    "inherits": "inherit",
    "powers": "power",
    "participation": "participate",
    "participates": "participate",
    "participating": "participate",
    "reviews": "review",
    "reviewing": "review",
    "reviewed": "review",
    "referrals": "refer",
    "referral": "refer",
    "remedial": "remedy",
    "remediation": "remedy",
}


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


def _visible_inline_text(token) -> str:
    pieces: list[str] = []
    for child in token.children or []:
        if child.type in {"text", "code_inline"}:
            pieces.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            pieces.append(" ")
        elif child.type == "image":
            pieces.append(child.content)
    return base.normalized("".join(pieces))


def commonmark_section_visible_text(source: str, heading: str) -> str | None:
    """Return rendered inline prose for one H2 section, ignoring fenced/indented code."""
    tokens = MarkdownIt("commonmark").parse(source)
    in_section = False
    found = False
    chunks: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and token.tag == "h2" and i + 1 < len(tokens):
            title = base.normalized(tokens[i + 1].content)
            if in_section and title != heading:
                break
            in_section = title == heading
            found = found or in_section
            i += 3
            continue
        if in_section and token.type == "inline":
            text = _visible_inline_text(token)
            if text:
                chunks.append(text)
        i += 1
    if not found:
        return None
    return base.normalized(" ".join(chunks))


def validate_live_state_context_text(
    dossier_text: str,
    dossier: str,
    entity_id: str,
    state: str,
    live: str,
    label: str,
) -> list[str]:
    """Reject stale visible State outcome codes regardless of Markdown formatting."""
    body = commonmark_section_visible_text(dossier_text, "State governance context")
    if body is None:
        return []

    errors: list[str] = []
    for match in EXPLICIT_STATE_OUTCOME_RE.finditer(body):
        stated_code = match.group(1)
        if stated_code == live:
            continue
        errors.append(
            f"{dossier}: {entity_id}: State governance context text is stale: "
            f"states {stated_code}, but current {state} State dossier is {live} · {label}; "
            "update the prose or make it outcome-neutral"
        )
    return errors


def _stem_token(token: str) -> str:
    token = TOKEN_ALIASES.get(token, token)
    if token in TOKEN_ALIASES.values():
        return token
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _terms(value: str) -> set[str]:
    return {
        _stem_token(token)
        for token in TOKEN_RE.findall(value.casefold())
        if token not in MODEL_STOPWORDS and len(token) >= 3
    }


def _section_text(source: str, *headings: str) -> str:
    chunks = [
        value
        for heading in headings
        if (value := commonmark_section_visible_text(source, heading))
    ]
    return " ".join(chunks)


def validate_visual_model_textual_anchor(
    dossier_text: str,
    dossier: str,
    entity_id: str,
    version: int,
    visual_model: object,
) -> list[str]:
    """Require legacy free-form visual summaries to be lexically anchored in dossier prose.

    v40+ rows use canonical identity-only templates and are validated elsewhere.
    v1-v39 retain their historical free-form summaries, so each field must share
    an auditable lexical anchor with the section(s) that constitute its textual support.
    """
    if version >= 40:
        return []
    if not isinstance(visual_model, dict):
        return [f"{dossier}: {entity_id}: visualModel must be an object"]

    targets = {
        "source": _section_text(dossier_text, "Evidence record", "Sources"),
        "proposition": _section_text(
            dossier_text, "Identity scope", "Evidence record", "Evidence gaps"
        ),
        "boundary": _section_text(
            dossier_text,
            "State governance context",
            "Attribution and exclusions",
            "Governance boundary",
        ),
    }
    errors: list[str] = []
    for field, target_text in targets.items():
        value = visual_model.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{dossier}: {entity_id}: visualModel.{field} must be non-empty")
            continue
        model_terms = _terms(value)
        target_terms = _terms(target_text)
        if not model_terms:
            errors.append(
                f"{dossier}: {entity_id}: visualModel.{field} has no auditable significant terms"
            )
            continue
        matched = model_terms & target_terms
        if field == "boundary" and re.fullmatch(
            r"No State [RSUN] inheritance", value.strip(), flags=re.I
        ):
            continue
        required = 1 if field == "source" else min(2, len(model_terms))
        if len(matched) < required:
            errors.append(
                f"{dossier}: {entity_id}: visualModel.{field} is not textually anchored: "
                f"matched {sorted(matched)!r}, required {required} of {sorted(model_terms)!r}"
            )
    return errors


def _validate_preledger_state_prose(ledger_ids: set[str]) -> list[str]:
    """Extend live prose coherence to dedicated canonical dossiers outside v1-v49."""
    errors: list[str] = []
    for path in contract.entity_paths(ROOT):
        try:
            record = contract.load_json(path)
        except Exception:
            continue
        entity_id = record.get("id")
        entity_type = record.get("type")
        if (
            not isinstance(entity_id, str)
            or entity_id in ledger_ids
            or entity_type not in contract.TYPE_DIR
        ):
            continue
        rel = contract.resolve_repo_ref(ROOT, path, record.get("dossier"))
        if rel is None:
            continue
        dossier = ROOT / rel
        if not dossier.is_file():
            continue
        text = dossier.read_text(encoding="utf-8")
        body = commonmark_section_visible_text(text, "State governance context")
        if body is None or EXPLICIT_STATE_OUTCOME_RE.search(body) is None:
            continue
        fm = frontmatter(dossier)
        state = fm.get("jurisdiction") or fm.get("state")
        if not isinstance(state, str) or re.fullmatch(r"[A-Z]{3}", state) is None:
            match = STATE_DOSSIER_RE.search(body)
            state = match.group(1) if match else None
        if not isinstance(state, str):
            errors.append(
                f"{rel}: {entity_id}: explicit State outcome prose has no auditable State code"
            )
            continue
        live = current_state_outcome(state)
        if live is None:
            errors.append(
                f"{rel}: {entity_id}: cannot resolve current {state} State dossier outcome"
            )
            continue
        errors.extend(
            validate_live_state_context_text(
                text, rel.as_posix(), entity_id, state, live, state
            )
        )
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(contract.validate_generated_svg_clipping(ROOT))
    checked = 0
    palette = base.load_json(base.PALETTE_PATH)
    ledger_ids: set[str] = set()
    manifests = sorted(
        base.MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )
    for manifest_path in manifests:
        version = int(manifest_path.stem.rsplit("v", 1)[1])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in manifest.get("entities", []):
            if not isinstance(row, dict):
                errors.append(f"{manifest_path.relative_to(ROOT)}: non-object migration row")
                continue
            entity_id = row.get("id", "<missing-id>")
            if isinstance(entity_id, str):
                ledger_ids.add(entity_id)
            dossier = row.get("dossier")
            state = row.get("state")
            source_granularity = row.get("sourceGranularity")
            if not isinstance(dossier, str) or not (ROOT / dossier).is_file():
                errors.append(f"{entity_id}: missing dossier {dossier!r}")
                continue
            dossier_text = (ROOT / dossier).read_text(encoding="utf-8")
            for heading in base.TEXTUAL_EQUIVALENT_SECTIONS:
                body = commonmark_section_visible_text(
                    dossier_text, heading.removeprefix("## ")
                )
                if body is None or not body:
                    errors.append(
                        f"{dossier}: {entity_id}: missing/empty textual-equivalent section {heading}"
                    )
            errors.extend(
                validate_visual_model_textual_anchor(
                    dossier_text,
                    dossier,
                    str(entity_id),
                    version,
                    row.get("visualModel"),
                )
            )

            status_rel = base.one_visual(row, "-status.svg")
            evidence_rel = base.one_visual(row, "-evidence.svg")
            if status_rel is None or evidence_rel is None:
                errors.append(f"{entity_id}: requires exactly one status and one evidence SVG")
                continue

            status_text = (
                base.visible_svg_text(ROOT / status_rel)
                if (ROOT / status_rel).is_file()
                else None
            )
            live = current_state_outcome(state) if isinstance(state, str) else None
            if status_text is None or live not in palette.get("states", {}):
                errors.append(f"{entity_id}: invalid status SVG or current State outcome")
            else:
                label = palette["states"][live].get("label")
                if not isinstance(label, str) or not label:
                    errors.append(
                        f"{entity_id}: live State outcome {live!r} has no canonical palette label"
                    )
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
                            errors.append(
                                f"{status_rel}: {entity_id}: visible status semantics missing {required!r}"
                            )
                    checked += 1

            evidence_text = (
                base.visible_svg_text(ROOT / evidence_rel)
                if (ROOT / evidence_rel).is_file()
                else None
            )
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
                        errors.append(
                            f"{evidence_rel}: {entity_id}: visible evidence semantics missing {required!r}"
                        )
                checked += 1

    errors.extend(_validate_preledger_state_prose(ledger_ids))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"visual evidence semantics: FAILED ({len(errors)} error(s))")
        return 1
    print(
        f"visual evidence semantics: OK ({checked} status/evidence SVGs checked; "
        "CommonMark live State prose + legacy visualModel textual anchors + cumulative clips)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
