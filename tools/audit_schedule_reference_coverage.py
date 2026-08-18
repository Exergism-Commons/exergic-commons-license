#!/usr/bin/env python3
"""Audit ABox coverage of already-curated State Schedule freeze references.

Unlike the State dossier prose scanner, this consumes internal governance work products
that already contain reviewed `candidate_parties`, `identified_operators`,
`candidate_projects`, `identified_projects`, `schedule_identity`, and
`project_boundary` fields. Matching remains identity discovery only; it never creates a
Claim or propagates a governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "registry" / "schedule-state-s-freezes"
ENTITY_DIR = ROOT / "knowledge" / "entities"

ACTOR_FIELDS = ("candidate_parties", "identified_operators", "identified_parties")
PROJECT_FIELDS = ("candidate_projects", "identified_projects")
SCOPE_FIELDS = ("schedule_identity", "project_boundary")
CAPACITY_SPLITS = (", only ", ", including ", " only when ", " only in ", " only where ")


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def load_entities() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(ENTITY_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "State":
            continue
        names = [data.get("name"), *(data.get("aliases") or [])]
        aliases = sorted({norm(x) for x in names if isinstance(x, str) and norm(x)}, key=len, reverse=True)
        rows.append({"id": data["id"], "type": data["type"], "aliases": aliases})
    return rows


def records_from_document(data: object) -> list[dict]:
    if isinstance(data, dict):
        records = data.get("records")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
        if isinstance(data.get("state"), str):
            return [data]
    return []


def list_values(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def identity_head(raw: str) -> str:
    head = raw.strip()
    lower = head.lower()
    positions = [lower.find(token) for token in CAPACITY_SPLITS if lower.find(token) >= 0]
    if positions:
        head = head[: min(positions)]
    return head.strip(" .;:")


def resolve(raw: str, entities: list[dict], expected: str) -> list[str]:
    raw_norm = norm(raw)
    head_norm = norm(identity_head(raw))
    matches: list[tuple[int, str]] = []
    for entity in entities:
        is_project = entity["type"] in {"Project", "Deployment"}
        if expected == "actor" and is_project:
            continue
        if expected == "project" and not is_project:
            continue
        for alias in entity["aliases"]:
            if not alias:
                continue
            exact = alias == head_norm or alias == raw_norm
            prefix = len(alias) >= 6 and (head_norm.startswith(alias + " ") or raw_norm.startswith(alias + " "))
            contained = len(alias) >= 12 and f" {alias} " in f" {raw_norm} "
            if exact or prefix or contained:
                matches.append((len(alias), entity["id"]))
                break
    if not matches:
        return []
    best = max(score for score, _ in matches)
    return sorted({entity_id for score, entity_id in matches if score == best})


def audit() -> dict:
    entities = load_entities()
    references: list[dict] = []
    files = sorted(FREEZE_DIR.glob("*.yml")) + sorted(FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for record_index, record in enumerate(records_from_document(data)):
            state = record.get("state")
            outcome = record.get("outcome")
            for field in ACTOR_FIELDS:
                for raw in list_values(record.get(field)):
                    matches = resolve(raw, entities, "actor")
                    references.append({
                        "kind": "actor-reference",
                        "state": state,
                        "outcome": outcome,
                        "field": field,
                        "raw": raw,
                        "identity_head": identity_head(raw),
                        "resolved_ids": matches,
                        "status": "resolved" if len(matches) == 1 else ("ambiguous" if matches else "unresolved"),
                        "source": str(path.relative_to(ROOT)),
                        "record_index": record_index,
                    })
            for field in PROJECT_FIELDS:
                for raw in list_values(record.get(field)):
                    matches = resolve(raw, entities, "project")
                    references.append({
                        "kind": "project-reference",
                        "state": state,
                        "outcome": outcome,
                        "field": field,
                        "raw": raw,
                        "identity_head": identity_head(raw),
                        "resolved_ids": matches,
                        "status": "resolved" if len(matches) == 1 else ("ambiguous" if matches else "unresolved"),
                        "source": str(path.relative_to(ROOT)),
                        "record_index": record_index,
                    })
            for field in SCOPE_FIELDS:
                for raw in list_values(record.get(field)):
                    references.append({
                        "kind": "scope-reference",
                        "state": state,
                        "outcome": outcome,
                        "field": field,
                        "raw": raw,
                        "identity_head": None,
                        "resolved_ids": [],
                        "status": "context-only",
                        "source": str(path.relative_to(ROOT)),
                        "record_index": record_index,
                    })

    counted = [row for row in references if row["kind"] != "scope-reference"]
    statuses = Counter(row["status"] for row in counted)
    kinds = Counter(row["kind"] for row in counted)
    states = {row["state"] for row in counted if isinstance(row["state"], str)}
    return {
        "schema_version": 1,
        "semantics": {
            "purpose": "coverage audit of already-curated Schedule-preparation references",
            "non_inference": [
                "reference matching is not attribution",
                "identity resolution does not inherit the State outcome",
                "scope_reference fields are context only and are never coerced into an Actor or Project identity",
                "an unresolved reference is representation debt, not evidence of culpability",
            ],
        },
        "counts": {
            "freeze_files": len(files),
            "states_with_actor_or_project_references": len(states),
            "actor_references": kinds["actor-reference"],
            "project_references": kinds["project-reference"],
            "resolved": statuses["resolved"],
            "ambiguous": statuses["ambiguous"],
            "unresolved": statuses["unresolved"],
            "scope_context_references": sum(row["kind"] == "scope-reference" for row in references),
        },
        "references": references,
    }


def write_markdown(report: dict, path: Path) -> None:
    counts = report["counts"]
    rows = [
        "# Schedule freeze reference coverage",
        "",
        "> Identity-coverage audit only. Resolution has no governance or attribution effect.",
        "",
        f"- Freeze files: **{counts['freeze_files']}**",
        f"- States with actor/project references: **{counts['states_with_actor_or_project_references']}**",
        f"- Actor references: **{counts['actor_references']}**",
        f"- Project references: **{counts['project_references']}**",
        f"- Resolved: **{counts['resolved']}**",
        f"- Ambiguous: **{counts['ambiguous']}**",
        f"- Unresolved: **{counts['unresolved']}**",
        "",
        "## Unresolved / ambiguous curated references",
        "",
        "| State | Kind | Field | Identity head | Status | Source |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["references"]:
        if row["status"] not in {"unresolved", "ambiguous"}:
            continue
        head = (row["identity_head"] or row["raw"]).replace("|", "\\|")
        rows.append(
            f"| {row['state'] or ''} | {row['kind']} | {row['field']} | {head} | {row['status']} | {row['source']} |"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def self_test() -> None:
    assert identity_head("Zambia Police Service, only in qualifying cases") == "Zambia Police Service"
    assert identity_head("NISA only where evidence exists") == "NISA"
    print("Schedule reference audit self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = audit()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.markdown)
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
