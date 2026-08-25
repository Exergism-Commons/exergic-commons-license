#!/usr/bin/env python3
"""Adversarial residual guard for Schedule identity surfaces.

The primary Schedule audit and the exact/strict companion checks intentionally use
high-precision heuristics. This final guard targets syntactic gaps that can otherwise stay
`context-only`: bare values in `schedule_identity`, named operations/projects in scope
fields, person-labelled matters, and multi-name actor lists whose components are joined by
ambiguous separators.

It is identity coverage only. A detected name/object is not attributed to conduct and does
not inherit any State governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


OBJECT_WORD = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*"
NAMED_OBJECT_RE = re.compile(
    rf"\b((?:Operation|Operação|Operación|Opération|Project|Programme|Program|System|Platform|Tool|Deployment|Initiative|Campaign)"
    rf"(?:\s+{OBJECT_WORD}){{1,6}})\b"
)
SCOPE_OBJECT_FIELDS = {"schedule_identity", "project_boundary", "identified_incident", "identified_measure"}


def ambiguous_actor_list_mentions(raw: str) -> list[str]:
    """Return >=2 name-shaped actor components joined by comma/and/&.

    Requiring two independently valid components avoids treating a single conjunction in an
    institutional name as a person list. Exact/materialized organizations are filtered later.
    """
    separators: list[tuple[int, int]] = []
    for match in strict.ACTOR_LIST_SEPARATOR_RE.finditer(raw):
        if match.group(0).lstrip().startswith(",") and strict.CAPACITY_TAIL_RE.match(raw[match.end():].lstrip()):
            continue
        separators.append(match.span())
    if not separators:
        return []

    pieces: list[str] = []
    start = 0
    for sep_start, sep_end in separators:
        pieces.append(raw[start:sep_start])
        start = sep_end
    pieces.append(raw[start:])

    mentions: list[str] = []
    for piece in pieces:
        candidate = strict.actor_component_name(piece)
        if candidate and candidate not in mentions:
            mentions.append(candidate)
    return mentions if len(mentions) >= 2 else []


def contextual_labels(row: dict) -> list[str]:
    raw = row.get("raw") or ""
    labels: list[str] = []

    if row.get("kind") == "actor-reference":
        labels.extend(ambiguous_actor_list_mentions(raw))

    if row.get("field") == "schedule_identity":
        bare = strict.full_name_phrase(raw, allow_all_caps=True)
        if bare and bare not in labels:
            labels.append(bare)

    if row.get("kind") in {"scope-reference", "scope-identity-reference"} and row.get("field") in SCOPE_OBJECT_FIELDS:
        for match in NAMED_OBJECT_RE.finditer(raw):
            label = " ".join(match.group(1).split())
            if label not in labels:
                labels.append(label)
        for match in strict.MATTER_NAME_RE.finditer(raw):
            label = " ".join(match.group(1).split())
            if strict.valid_name(label, allow_all_caps=True) and label not in labels:
                labels.append(label)
    return labels


def failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") not in {"actor-reference", "project-reference", "scope-reference", "scope-identity-reference"}:
            continue
        state = row.get("state")
        for label in contextual_labels(row):
            person_ids = exact.materialized_person_ids_for_mention(label, entities, identity_index, state)
            non_person_ids = exact.materialized_non_person_ids_for_mention(label, entities, identity_index, state)
            materialized_ids = sorted(set(person_ids) | set(non_person_ids))
            if materialized_ids:
                # Exact-current identities are enforced by the existing exact/strict gates.
                continue
            if strict.explicitly_defers_complete_name(row, label):
                continue
            found.append({
                "reason": "adversarial Schedule identity surface can bypass normal identity cues",
                "state": state,
                "kind": row.get("kind"),
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": row.get("raw"),
                "identity_surface": label,
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def self_test() -> None:
    assert ambiguous_actor_list_mentions("Jane Doe and John Roe") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Jane Doe, John Roe, acting only where authorized") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Ministry of Interior and Narcotics Control") == []
    assert contextual_labels({"kind": "scope-reference", "field": "schedule_identity", "raw": "Jane Doe"}) == ["Jane Doe"]
    assert "Operation Silent Dawn" in contextual_labels({
        "kind": "scope-reference", "field": "identified_incident", "raw": "Operation Silent Dawn"
    })
    assert "Operação Contenção" in contextual_labels({
        "kind": "scope-reference", "field": "schedule_identity", "raw": "Operação Contenção — 28 October 2025 phase"
    })
    assert "Jane Doe" in contextual_labels({
        "kind": "scope-reference", "field": "identified_incident", "raw": "2026 Jane Doe matter"
    })

    entities: list[dict] = []
    index = {"by_id": {}, "by_name": {}}
    report = {"references": [{
        "kind": "scope-reference", "state": "AAA", "field": "schedule_identity", "source": "x.yml",
        "raw": "Jane Doe", "status": "context-only", "resolution_source": None,
        "resolved_ids": [], "disposition_reason": None,
    }]}
    assert failures(report, entities, index)[0]["identity_surface"] == "Jane Doe"

    reviewed = report["references"][0]
    reviewed.update({
        "status": "partial-deferred",
        "resolution_source": "reviewed-disposition",
        "disposition_reason": "Jane Doe remains explicitly identity-deferred pending materialization.",
    })
    assert failures(report, entities, index) == []
    print("Schedule adversarial residual identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    report = schedule.audit()
    entities, _, identity_index = schedule.load_entities()
    found = failures(report, entities, identity_index)
    if found:
        print("ADVERSARIAL_SCHEDULE_IDENTITY_GAPS=" + json.dumps(found, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule adversarial residual identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
