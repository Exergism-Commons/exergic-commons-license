#!/usr/bin/env python3
"""Adversarial residual guard for Schedule identity surfaces.

The primary Schedule audit and the exact/strict companion checks intentionally use
high-precision heuristics. This final guard targets syntactic gaps that can otherwise hide
inside context-only *or already-resolved* rows: bare values in `schedule_identity`, named
operations/projects in project/scope fields, person-labelled matters, and multi-name actor
lists whose components are joined by ambiguous separators.

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


def named_object_labels(raw: str) -> list[str]:
    labels: list[str] = []
    for match in NAMED_OBJECT_RE.finditer(raw):
        label = " ".join(match.group(1).split())
        if label not in labels:
            labels.append(label)
    return labels


def contextual_labels(row: dict) -> list[str]:
    raw = row.get("raw") or ""
    labels: list[str] = []
    kind = row.get("kind")

    # Actor-list debt can be hidden inside a row that otherwise resolved/reviewed, so it is
    # checked regardless of row status.
    if kind == "actor-reference":
        labels.extend(ambiguous_actor_list_mentions(raw))

    # A reviewed/resolved project composite can hide a second named project just as easily as
    # a scope row can. Named object surfaces therefore run on project rows regardless of status.
    if kind == "project-reference":
        labels.extend(label for label in named_object_labels(raw) if label not in labels)

    if kind not in {"scope-reference", "scope-identity-reference"}:
        return labels

    # Bare schedule_identity values are useful only as a residual context-only detector;
    # strict named-person completeness already runs on identity-bearing scope rows.
    if row.get("status") == "context-only" and row.get("field") == "schedule_identity":
        bare = strict.full_name_phrase(raw, allow_all_caps=True)
        if bare and bare not in labels:
            labels.append(bare)

    # Named projects/operations and named matters must be inspected even when another identity
    # already made the scope row `resolved`. `resolved_project_covers_label()` below suppresses
    # only the same occurrence when an exact, more-specific Project/Deployment identity already
    # covers it; unrelated resolved identities cannot hide a second named object.
    if row.get("field") in SCOPE_OBJECT_FIELDS:
        labels.extend(label for label in named_object_labels(raw) if label not in labels)
        for match in strict.MATTER_NAME_RE.finditer(raw):
            label = " ".join(match.group(1).split())
            if strict.valid_name(label, allow_all_caps=True) and label not in labels:
                labels.append(label)
    return labels


def normalized_phrase_occurrences(raw: str, label: str) -> int:
    raw_norm = schedule.norm(raw)
    label_norm = schedule.norm(label)
    if not raw_norm or not label_norm:
        return 0
    return f" {raw_norm} ".count(f" {label_norm} ")


def resolved_project_covers_label(row: dict, label: str, by_id: dict[str, dict]) -> bool:
    """Suppress a residual stem only when the row's resolved Project covers that same occurrence.

    Example: the exact materialized Project `Operação Contenção — 28 October 2025 ... phase`
    legitimately covers the shorter parser stem `Operação Contenção`. We require the complete
    Project/Deployment surface to be embedded in the raw row and the residual label to occur
    only once. That last condition prevents `Operation Alpha / Operation Alpha Beta` from
    letting the resolved second project erase debt for the distinct first occurrence.
    """
    if normalized_phrase_occurrences(row.get("raw") or "", label) != 1:
        return False
    raw_norm = schedule.norm(row.get("raw") or "")
    label_norm = schedule.norm(label)
    padded_raw = f" {raw_norm} "
    padded_label = f" {label_norm} "
    for entity_id in row.get("resolved_ids") or []:
        entity = by_id.get(entity_id)
        if not entity or entity.get("type") not in {"Project", "Deployment"}:
            continue
        for form in entity.get("surface_forms") or []:
            form_norm = form.get("normalized") or schedule.norm(form.get("text") or "")
            if not form_norm:
                continue
            padded_form = f" {form_norm} "
            if padded_form not in padded_raw:
                continue
            if padded_label in padded_form:
                return True
    return False


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
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
                continue
            if resolved_project_covers_label(row, label, by_id):
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

    context = {"kind": "scope-reference", "status": "context-only", "field": "schedule_identity", "raw": "Jane Doe"}
    assert contextual_labels(context) == ["Jane Doe"]
    assert "Operation Silent Dawn" in contextual_labels({
        "kind": "scope-reference", "status": "context-only", "field": "identified_incident", "raw": "Operation Silent Dawn"
    })
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
        "kind": "scope-reference", "status": "context-only", "field": "identified_incident", "raw": "2026 Jane Doe matter"
    })

    phase = {
        "id": "PROJECT-BRA-PHASE", "type": "Project", "aliases": ["operacao contencao 28 october 2025 phase"],
        "surface_forms": [{
            "text": "Operação Contenção — 28 October 2025 phase",
            "normalized": "operacao contencao 28 october 2025 phase",
        }],
    }
    phase_row = {
        "kind": "scope-identity-reference", "status": "resolved", "field": "schedule_identity",
        "raw": "Operação Contenção — 28 October 2025 phase", "resolved_ids": ["PROJECT-BRA-PHASE"],
    }
    assert resolved_project_covers_label(phase_row, "Operação Contenção", {phase["id"]: phase})
    duplicate_row = {
        "kind": "project-reference", "status": "resolved", "field": "candidate_projects",
        "raw": "Operation Alpha / Operation Alpha Beta", "resolved_ids": ["PROJECT-ALPHA-BETA"],
    }
    alpha_beta = {
        "id": "PROJECT-ALPHA-BETA", "type": "Project", "aliases": ["operation alpha beta"],
        "surface_forms": [{"text": "Operation Alpha Beta", "normalized": "operation alpha beta"}],
    }
    assert not resolved_project_covers_label(duplicate_row, "Operation Alpha", {alpha_beta["id"]: alpha_beta})

    entities: list[dict] = []
    by_id: dict[str, dict] = {}
    index = {"by_id": {}, "by_name": {}}
    report = {"references": [{
        "kind": "scope-reference", "state": "AAA", "field": "schedule_identity", "source": "x.yml",
        "raw": "Jane Doe", "status": "context-only", "resolution_source": None,
        "resolved_ids": [], "disposition_reason": None,
    }]}
    assert failures(report, entities, by_id, index)[0]["identity_surface"] == "Jane Doe"

    hidden_scope = {"references": [{
        "kind": "scope-identity-reference", "state": "AAA", "field": "identified_incident", "source": "x.yml",
        "raw": "UNHCR / Operation Silent Dawn", "status": "resolved",
        "resolution_source": "state-safe-exact-embedded-name-or-alias", "resolved_ids": ["ORG-UNHCR"],
        "disposition_reason": None,
    }]}
    assert failures(hidden_scope, entities, {"ORG-UNHCR": {"id": "ORG-UNHCR", "type": "Organization"}}, index)[0]["identity_surface"] == "Operation Silent Dawn"

    hidden_project = {"references": [{
        "kind": "project-reference", "state": "AAA", "field": "candidate_projects", "source": "x.yml",
        "raw": "Known Project / Operation Silent Dawn", "status": "resolved",
        "resolution_source": "reviewed-disposition", "resolved_ids": ["PROJECT-KNOWN"],
        "disposition_reason": "Known Project is bound; remaining context reviewed.",
    }]}
    assert failures(hidden_project, entities, {"PROJECT-KNOWN": {"id": "PROJECT-KNOWN", "type": "Project", "surface_forms": []}}, index)[0]["identity_surface"] == "Operation Silent Dawn"

    reviewed = report["references"][0]
    reviewed.update({
        "kind": "scope-identity-reference",
        "status": "partial-deferred",
        "resolution_source": "reviewed-disposition",
        "disposition_reason": "Jane Doe remains explicitly identity-deferred pending materialization.",
    })
    assert failures(report, entities, by_id, index) == []
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
