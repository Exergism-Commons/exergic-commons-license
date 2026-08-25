#!/usr/bin/env python3
"""Adversarial residual guard for Schedule identity surfaces.

The primary Schedule audit and the exact/strict companion checks intentionally use
high-precision heuristics. This final guard targets syntactic gaps that can otherwise hide
inside context-only, already-resolved, or otherwise-unclassified Schedule text: named
operations/projects, named institutions, person-labelled matters, and multi-name actor lists.

It is identity coverage only. A detected name/object is not attributed to conduct and does
not inherit any State governance outcome. Exclusions and residual scope are scanned for
representation just like positive scope, without converting them into actor/project roles.
"""
from __future__ import annotations

import argparse
import json
import re

import yaml

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


OBJECT_WORD = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*"
NAMED_OBJECT_RE = re.compile(
    rf"\b((?:Operation|Operação|Operación|Opération|Project|Programme|Program|System|Platform|Tool|Deployment|Initiative|Campaign)"
    rf"(?:\s+{OBJECT_WORD}){{1,6}})\b"
)
SCOPE_OBJECT_FIELDS = {"schedule_identity", "project_boundary", "identified_incident", "identified_measure"}
AUDITED_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)
# Provenance/foreign-key surfaces are identifiers or locators, not prose identity claims.
SKIP_EXTRA_FIELDS = {
    "identity_sources", "dossier", "linked_project_id", "linked_organization_id",
}


def ambiguous_actor_list_mentions(raw: str) -> list[str]:
    """Return >=2 name-shaped actor components joined by comma/and/&."""
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


def named_object_labels(raw: str) -> list[str]:
    labels: list[str] = []
    for match in NAMED_OBJECT_RE.finditer(raw):
        label = " ".join(match.group(1).split())
        if label not in labels:
            labels.append(label)
    return labels


def named_institution_labels(raw: str) -> list[str]:
    labels: list[str] = []
    for match in schedule.SCOPE_NAMED_IDENTITY_RE.finditer(raw):
        label = " ".join(match.group(0).split()).strip(" ,;:()[]{}\"'“”‘’")
        if label and label not in labels:
            labels.append(label)
    return labels


def add_unique(labels: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in labels:
            labels.append(value)


def contextual_labels(row: dict) -> list[str]:
    raw = row.get("raw") or ""
    labels: list[str] = []
    kind = row.get("kind")

    if kind == "actor-reference":
        add_unique(labels, ambiguous_actor_list_mentions(raw))

    if kind == "project-reference":
        add_unique(labels, named_object_labels(raw))

    if kind in {"scope-reference", "scope-identity-reference", "extra-context-reference"}:
        # High-precision institutional and person cues run regardless of whether another exact
        # identity already made the row resolved. This is what closes the "known identity +
        # unknown named identity" bypass.
        add_unique(labels, named_institution_labels(raw))
        add_unique(labels, strict.strict_named_mentions(raw, "scope-reference"))

        if kind == "scope-reference" and row.get("status") == "context-only" and row.get("field") == "schedule_identity":
            bare = strict.full_name_phrase(raw, allow_all_caps=True)
            if bare:
                add_unique(labels, [bare])

        if kind == "extra-context-reference" or row.get("field") in SCOPE_OBJECT_FIELDS:
            add_unique(labels, named_object_labels(raw))
            for match in strict.MATTER_NAME_RE.finditer(raw):
                label = " ".join(match.group(1).split())
                if strict.valid_name(label, allow_all_caps=True):
                    add_unique(labels, [label])
    return labels


def normalized_tokens(value: str) -> list[str]:
    return schedule.norm(value).split()


def token_phrase_occurrences(text: str, phrase: str) -> int:
    haystack = normalized_tokens(text)
    needle = normalized_tokens(phrase)
    if not haystack or not needle or len(needle) > len(haystack):
        return 0
    width = len(needle)
    return sum(haystack[index:index + width] == needle for index in range(len(haystack) - width + 1))


def resolved_identity_covers_label(row: dict, label: str, by_id: dict[str, dict]) -> bool:
    """Suppress a parser stem only when one resolved exact identity covers that same occurrence."""
    raw = row.get("raw") or ""
    if token_phrase_occurrences(raw, label) != 1:
        return False
    for entity_id in row.get("resolved_ids") or []:
        entity = by_id.get(entity_id)
        if not entity:
            continue
        for form in entity.get("surface_forms") or []:
            form_text = form.get("text") or form.get("normalized") or ""
            if not form_text:
                continue
            if token_phrase_occurrences(raw, form_text) != 1:
                continue
            if token_phrase_occurrences(form_text, label) >= 1:
                return True
    return False


def extra_context_rows() -> list[dict]:
    """Expose every top-level textual freeze field outside the primary reference audit."""
    rows: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        source = str(path.relative_to(schedule.ROOT))
        for record_index, record in enumerate(schedule.records_from_document(data)):
            state = record.get("state")
            for field, value in record.items():
                if field in AUDITED_FIELDS or field in SKIP_EXTRA_FIELDS:
                    continue
                for raw in schedule.list_values(value):
                    rows.append({
                        "kind": "extra-context-reference", "state": state, "field": field,
                        "source": source, "record_index": record_index, "raw": raw,
                        "resolved_ids": [], "status": "context-only", "resolution_source": None,
                        "disposition_reason": None,
                    })
    return rows


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    found: list[dict] = []
    rows = list(report.get("references", [])) + extra_context_rows()
    for row in rows:
        if row.get("kind") not in {
            "actor-reference", "project-reference", "scope-reference", "scope-identity-reference", "extra-context-reference"
        }:
            continue
        raw = row.get("raw") or ""
        state = row.get("state")

        # Exact current identities in an unclassified field are already represented. We do not
        # require them to become actor/project role bindings merely because they are mentioned
        # in exclusions/capacity text.
        exact_ids = schedule.embedded_identity_matches(raw, entities, identity_index, "identity", state)
        if row.get("kind") == "extra-context-reference" and exact_ids:
            row = {**row, "resolved_ids": exact_ids, "resolution_source": "neutral-extra-field-exact-coverage"}

        for label in contextual_labels(row):
            person_ids = exact.materialized_person_ids_for_mention(label, entities, identity_index, state)
            non_person_ids = exact.materialized_non_person_ids_for_mention(label, entities, identity_index, state)
            if person_ids or non_person_ids:
                continue
            if resolved_identity_covers_label(row, label, by_id):
                continue
            if strict.explicitly_defers_complete_name(row, label):
                continue
            found.append({
                "reason": "adversarial Schedule identity surface can bypass normal identity cues",
                "state": state,
                "kind": row.get("kind"),
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "identity_surface": label,
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def self_test() -> None:
    assert ambiguous_actor_list_mentions("Jane Doe and John Roe") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Jane Doe, John Roe, acting only where authorized") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Ministry of Interior and Narcotics Control") == []
    assert "National Accountability Commission" in named_institution_labels("UNHCR / National Accountability Commission")

    context = {"kind": "scope-reference", "status": "context-only", "field": "schedule_identity", "raw": "Jane Doe"}
    assert contextual_labels(context) == ["Jane Doe"]
    assert "Operation Silent Dawn" in contextual_labels({
        "kind": "scope-identity-reference", "status": "resolved", "field": "identified_incident",
        "raw": "UNHCR / Operation Silent Dawn"
    })
    assert "Operation Silent Dawn" in contextual_labels({
        "kind": "project-reference", "status": "resolved", "field": "candidate_projects",
        "raw": "Known Project / Operation Silent Dawn"
    })
    assert "Operação Contenção" in contextual_labels({
        "kind": "scope-reference", "status": "context-only", "field": "schedule_identity",
        "raw": "Operação Contenção — 28 October 2025 phase"
    })
    assert "Jane Doe" in contextual_labels({
        "kind": "extra-context-reference", "status": "context-only", "field": "exclusions",
        "raw": "detention of Jane Doe pending trial"
    })

    assert token_phrase_occurrences("Operação Contenção — 28 October 2025 phase", "Operação Contenção") == 1
    assert token_phrase_occurrences("Operation Alpha / Operation Alpha Beta", "Operation Alpha") == 2

    phase = {
        "id": "PROJECT-BRA-PHASE", "type": "Project",
        "surface_forms": [{"text": "Operação Contenção — 28 October 2025 phase", "normalized": "operacao contencao 28 october 2025 phase"}],
    }
    phase_row = {
        "kind": "scope-identity-reference", "status": "resolved", "field": "schedule_identity",
        "raw": "Operação Contenção — 28 October 2025 phase", "resolved_ids": ["PROJECT-BRA-PHASE"],
    }
    assert resolved_identity_covers_label(phase_row, "Operação Contenção", {phase["id"]: phase})

    duplicate_row = {
        "kind": "project-reference", "status": "resolved", "field": "candidate_projects",
        "raw": "Operation Alpha / Operation Alpha Beta", "resolved_ids": ["PROJECT-ALPHA-BETA"],
    }
    alpha_beta = {
        "id": "PROJECT-ALPHA-BETA", "type": "Project",
        "surface_forms": [{"text": "Operation Alpha Beta", "normalized": "operation alpha beta"}],
    }
    assert not resolved_identity_covers_label(duplicate_row, "Operation Alpha", {alpha_beta["id"]: alpha_beta})

    entities: list[dict] = []
    by_id: dict[str, dict] = {}
    index = {"by_id": {}, "by_name": {}}
    report = {"references": [{
        "kind": "scope-reference", "state": "AAA", "field": "schedule_identity", "source": "x.yml",
        "raw": "Jane Doe", "status": "context-only", "resolution_source": None,
        "resolved_ids": [], "disposition_reason": None,
    }]}
    # Avoid reading the real corpus in synthetic tests by testing the row parser directly here.
    assert contextual_labels(report["references"][0]) == ["Jane Doe"]

    hidden_scope = {
        "kind": "scope-identity-reference", "state": "AAA", "field": "identified_incident", "source": "x.yml",
        "raw": "UNHCR / Operation Silent Dawn", "status": "resolved",
        "resolution_source": "state-safe-exact-embedded-name-or-alias", "resolved_ids": ["ORG-UNHCR"],
        "disposition_reason": None,
    }
    assert "Operation Silent Dawn" in contextual_labels(hidden_scope)

    hidden_institution = {
        "kind": "scope-identity-reference", "state": "AAA", "field": "project_boundary", "source": "x.yml",
        "raw": "UNHCR / National Accountability Commission", "status": "resolved",
        "resolution_source": "state-safe-exact-embedded-name-or-alias", "resolved_ids": ["ORG-UNHCR"],
        "disposition_reason": None,
    }
    assert "National Accountability Commission" in contextual_labels(hidden_institution)

    print("Schedule adversarial residual identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    report = schedule.audit()
    entities, by_id, identity_index = schedule.load_entities()
    found = failures(report, entities, by_id, identity_index)
    if found:
        print("ADVERSARIAL_SCHEDULE_IDENTITY_GAPS=" + json.dumps(found, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule adversarial residual identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
