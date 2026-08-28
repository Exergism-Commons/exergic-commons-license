#!/usr/bin/env python3
"""Adversarial residual guard for Schedule identity surfaces.

The primary Schedule audit and the exact/strict companion checks intentionally use
high-precision heuristics. This final guard targets syntactic gaps that can otherwise hide
inside context-only, already-resolved, or otherwise-unclassified Schedule text: named
operations/projects, named institutions, person-labelled matters, and multi-name actor lists.

It is identity coverage only. A detected name/object is not attributed to conduct and does
not inherit any State governance outcome. Exclusions and residual scope are scanned for
representation just like positive scope, without converting them into actor/project roles.
Residual reviewed dispositions are exact-surface, exact-source overlays and cannot create a
new role binding: `covered` IDs must already be resolved on the same primary-audit row.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

import yaml

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_schedule_residual_identity_dispositions as residual


OBJECT_WORD = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*"
NAMED_OBJECT_RE = re.compile(
    rf"\b((?:Operation|Operação|Operación|Opération|Project|Programme|Program|System|Platform|Tool|Deployment|Initiative|Campaign)"
    rf"(?:\s+{OBJECT_WORD})+)\b"
)
INSTITUTION_TYPE = (
    r"Ministry|Department|Directorate|Bureau|Office|Commission|Committee|Council|Court|Tribunal|Agency|"
    r"Secretariat|Administration|Police|Prison|Penitentiary|Service|Force|Forces|Branch|Unit|Centre|Center|Board"
)
INSTITUTION_SUFFIX = rf"(?:\s+(?:of|for|against|on)(?:\s+the)?(?:\s+{OBJECT_WORD}){{1,6}})?"
MAXIMAL_INSTITUTION_RE = re.compile(
    rf"\b((?:{OBJECT_WORD}(?:\s+|[-/])){{0,6}}(?:{INSTITUTION_TYPE}){INSTITUTION_SUFFIX}"
    rf"|Penitentiary\s+no\.\s*\d+\s+{OBJECT_WORD})\b"
)
SCOPE_OBJECT_FIELDS = {"schedule_identity", "project_boundary", "identified_incident", "identified_measure"}
AUDITED_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)
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
    """Return maximal high-precision institution phrases, including Unicode prefixes and of/for tails."""
    labels: list[str] = []
    for match in MAXIMAL_INSTITUTION_RE.finditer(raw):
        label = " ".join(match.group(1).split()).strip(" ,;:()[]{}\"'“”‘’")
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


def string_leaves(value: object, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    """Return every non-empty string value leaf from arbitrary Schedule context."""
    leaves: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, str):
        if value.strip():
            leaves.append((prefix, value))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaves.extend(string_leaves(child, (*prefix, f"[{index}]")))
    elif isinstance(value, dict):
        for key, child in value.items():
            leaves.extend(string_leaves(child, (*prefix, str(key))))
    return leaves


def mapping_key_surfaces(value: object, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
    """Return textual mapping keys as auditable surfaces, recursively."""
    surfaces: list[tuple[tuple[str, ...], str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if isinstance(key, str) and key.strip():
                surfaces.append(((*prefix, f"@key[{key_text}]"), key))
            surfaces.extend(mapping_key_surfaces(child, (*prefix, key_text)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            surfaces.extend(mapping_key_surfaces(child, (*prefix, f"[{index}]")))
    return surfaces


def extra_rows_from_mapping(
    mapping: dict,
    *,
    source: str,
    state: str | None,
    record_index: int | None,
    skip_fields: set[str],
    document_root: bool = False,
) -> list[dict]:
    """Expose free-form mapping keys and string values using the same residual detectors."""
    rows: list[dict] = []
    for field, value in mapping.items():
        if field in skip_fields:
            continue
        if isinstance(field, str) and field.strip():
            rows.append({
                "kind": "extra-context-reference", "state": state,
                "field": f"@key[{field}]", "source": source, "record_index": record_index,
                "raw": field, "resolved_ids": [], "status": "context-only", "resolution_source": None,
                "disposition_reason": None, "document_root": document_root,
            })
        for nested_path, raw in mapping_key_surfaces(value, (str(field),)):
            rows.append({
                "kind": "extra-context-reference", "state": state,
                "field": ".".join(nested_path), "source": source, "record_index": record_index,
                "raw": raw, "resolved_ids": [], "status": "context-only", "resolution_source": None,
                "disposition_reason": None, "document_root": document_root,
            })
        for nested_path, raw in string_leaves(value, (str(field),)):
            rows.append({
                "kind": "extra-context-reference", "state": state,
                "field": ".".join(nested_path), "source": source, "record_index": record_index,
                "raw": raw, "resolved_ids": [], "status": "context-only", "resolution_source": None,
                "disposition_reason": None, "document_root": document_root,
            })
    return rows


def extra_context_rows() -> list[dict]:
    """Expose textual freeze surfaces outside the primary reference audit, including document root."""
    rows: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        source = str(path.relative_to(schedule.ROOT))
        if not isinstance(data, dict):
            continue

        raw_records = data.get("records")
        if isinstance(raw_records, list):
            # Root metadata of a multi-record document has no single State identity scope. Any
            # named identity found there must fail closed and be moved into an audited record.
            root = {key: value for key, value in data.items() if key != "records"}
            rows.extend(extra_rows_from_mapping(
                root, source=source, state=None, record_index=None,
                skip_fields=SKIP_EXTRA_FIELDS, document_root=True,
            ))

        for record_index, record in enumerate(schedule.records_from_document(data)):
            state = record.get("state")
            rows.extend(extra_rows_from_mapping(
                record, source=source, state=state, record_index=record_index,
                skip_fields=AUDITED_FIELDS | SKIP_EXTRA_FIELDS,
            ))
    return rows


def residual_key(row: dict, label: str) -> tuple[str, str, str, str, str]:
    return (
        row.get("source") or "", row.get("state") or "", row.get("field") or "",
        row.get("raw") or "", label,
    )


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    found: list[dict] = []
    overlays = residual.load_dispositions()
    overlay_uses: Counter = Counter()
    rows = list(report.get("references", [])) + extra_context_rows()
    for row in rows:
        if row.get("kind") not in {
            "actor-reference", "project-reference", "scope-reference", "scope-identity-reference", "extra-context-reference"
        }:
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        labels = contextual_labels(row)

        if row.get("document_root") and labels:
            for label in labels:
                found.append({
                    "reason": "identity-bearing multi-record document-root metadata is outside State-scoped Schedule audit; move it into a record",
                    "state": state, "kind": row.get("kind"), "field": row.get("field"),
                    "source": row.get("source"), "record_index": row.get("record_index"),
                    "raw": raw, "identity_surface": label,
                })
            continue

        exact_ids = schedule.embedded_identity_matches(raw, entities, identity_index, "identity", state)
        if row.get("kind") == "extra-context-reference" and exact_ids:
            row = {**row, "resolved_ids": exact_ids, "resolution_source": "neutral-extra-field-exact-coverage"}

        for label in labels:
            person_ids = exact.materialized_person_ids_for_mention(label, entities, identity_index, state)
            non_person_ids = exact.materialized_non_person_ids_for_mention(label, entities, identity_index, state)
            if person_ids or non_person_ids:
                continue
            if resolved_identity_covers_label(row, label, by_id):
                continue
            if strict.explicitly_defers_complete_name(row, label):
                continue

            key = residual_key(row, label)
            disposition = overlays.get(key)
            if disposition is not None:
                overlay_uses[key] += 1
                if disposition["disposition"] == "covered":
                    if row.get("kind") == "extra-context-reference":
                        found.append({
                            "reason": "residual covered disposition cannot create a role binding in extra context",
                            "source": row.get("source"), "state": state, "field": row.get("field"),
                            "raw": raw, "identity_surface": label,
                        })
                        continue
                    missing = sorted(set(disposition["covered_ids"]) - set(row.get("resolved_ids") or []))
                    if missing:
                        found.append({
                            "reason": "residual covered IDs are not already resolved on the same audited row",
                            "source": row.get("source"), "state": state, "field": row.get("field"),
                            "raw": raw, "identity_surface": label, "missing_covered_ids": missing,
                        })
                    continue
                if disposition["disposition"] == "deferred":
                    continue

            found.append({
                "reason": "adversarial Schedule identity surface can bypass normal identity cues",
                "state": state, "kind": row.get("kind"), "field": row.get("field"),
                "source": row.get("source"), "record_index": row.get("record_index"),
                "raw": raw, "identity_surface": label, "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })

    for key, disposition in overlays.items():
        uses = overlay_uses[key]
        if uses != 1:
            found.append({
                "reason": "residual identity disposition is stale or non-unique; exact surface must be consumed once",
                "source": disposition["source"], "state": disposition["state"], "field": disposition["field"],
                "raw": disposition["raw"], "identity_surface": disposition["identity_surface"],
                "disposition": disposition["disposition"], "use_count": uses,
            })
    return found


def self_test() -> None:
    assert ambiguous_actor_list_mentions("Jane Doe and John Roe") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Jane Doe, John Roe, acting only where authorized") == ["Jane Doe", "John Roe"]
    assert ambiguous_actor_list_mentions("Ministry of Interior and Narcotics Control") == []
    assert named_institution_labels("National Centre for Human Rights") == ["National Centre for Human Rights"]
    assert named_institution_labels("Yaoundé Military Tribunal life sentence") == ["Yaoundé Military Tribunal"]
    assert named_institution_labels("National Administration of Penitentiaries and staff") == [
        "National Administration of Penitentiaries"
    ]
    assert named_institution_labels("High Court/Court of Appeal POFMA review") == ["High Court/Court of Appeal"]

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
    assert named_object_labels("Operation Alpha Bravo Charlie Delta Echo Foxtrot Golf") == [
        "Operation Alpha Bravo Charlie Delta Echo Foxtrot Golf"
    ]
    assert "Operação Contenção" in contextual_labels({
        "kind": "scope-reference", "status": "context-only", "field": "schedule_identity",
        "raw": "Operação Contenção — 28 October 2025 phase"
    })
    assert "Jane Doe" in contextual_labels({
        "kind": "extra-context-reference", "status": "context-only", "field": "exclusions",
        "raw": "detention of Jane Doe pending trial"
    })

    nested = string_leaves({"review": {"notes": ["ordinary text", {"detail": "detention of Jane Doe pending trial"}]}})
    assert (("review", "notes", "[1]", "detail"), "detention of Jane Doe pending trial") in nested
    nested_row = {
        "kind": "extra-context-reference", "status": "context-only", "field": "notes.detail",
        "raw": "detention of Jane Doe pending trial",
    }
    assert "Jane Doe" in contextual_labels(nested_row)

    keyed = mapping_key_surfaces({"detention of Jane Doe pending trial": True}, ("review",))
    assert (("review", "@key[detention of Jane Doe pending trial]"), "detention of Jane Doe pending trial") in keyed
    keyed_row = {
        "kind": "extra-context-reference", "status": "context-only",
        "field": "review.@key[detention of Jane Doe pending trial]",
        "raw": "detention of Jane Doe pending trial",
    }
    assert "Jane Doe" in contextual_labels(keyed_row)
    top_level_key_row = {
        "kind": "extra-context-reference", "status": "context-only",
        "field": "@key[Operation Silent Dawn]", "raw": "Operation Silent Dawn",
    }
    assert "Operation Silent Dawn" in contextual_labels(top_level_key_row)
    assert contextual_labels({
        "kind": "extra-context-reference", "status": "context-only", "field": "@key[review]", "raw": "review",
    }) == []

    root_rows = extra_rows_from_mapping(
        {"note": "detention of Jane Doe pending trial", "Operation Silent Dawn": True},
        source="x.yml", state=None, record_index=None, skip_fields=set(), document_root=True,
    )
    assert any(row["raw"] == "detention of Jane Doe pending trial" and row["document_root"] for row in root_rows)
    assert any(row["raw"] == "Operation Silent Dawn" and row["document_root"] for row in root_rows)

    assert residual_key(
        {"source": "x.yml", "state": "AAA", "field": "exclusions.[0]", "raw": "Operation Alpha activity"},
        "Operation Alpha",
    ) == ("x.yml", "AAA", "exclusions.[0]", "Operation Alpha activity", "Operation Alpha")

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

    hidden_scope = {
        "kind": "scope-identity-reference", "state": "AAA", "field": "identified_incident", "source": "x.yml",
        "raw": "UNHCR / Operation Silent Dawn", "status": "resolved",
        "resolution_source": "state-safe-exact-embedded-name-or-alias", "resolved_ids": ["ORG-UNHCR"],
        "disposition_reason": None,
    }
    assert "Operation Silent Dawn" in contextual_labels(hidden_scope)

    print("Schedule adversarial residual identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        residual.load_dispositions()
        self_test()
        return 0

    report = schedule.audit()
    entities, by_id, identity_index = schedule.load_entities()
    found = failures(report, entities, by_id, identity_index)
    if found:
        print("ADVERSARIAL_SCHEDULE_IDENTITY_GAPS=" + json.dumps(found, ensure_ascii=False, sort_keys=True))
        return 2
    dispositions = residual.load_dispositions()
    covered = sum(row["disposition"] == "covered" for row in dispositions.values())
    deferred = sum(row["disposition"] == "deferred" for row in dispositions.values())
    print(
        f"Schedule adversarial residual identity completeness: OK "
        f"({len(dispositions)} exact reviewed surfaces; {covered} covered; {deferred} deferred)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
