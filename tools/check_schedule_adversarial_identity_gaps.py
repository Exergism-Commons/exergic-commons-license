#!/usr/bin/env python3
"""Fail closed on residual named identities anywhere in Schedule freeze text.

This guard is identity coverage only. It never creates actor/project participation, hierarchy,
culpability, evidence, control, supply, or governance semantics. Reviewed residual overlays
are exact-source/exact-surface exceptions: primary-field `covered` IDs must already be role
bound by the normal reviewed Schedule row; extra context may only be explicitly deferred.
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
TAIL_WORD = rf"(?![A-ZÀ-ÖØ-Þ0-9'’.-]+\b){OBJECT_WORD}"
NAMED_OBJECT_RE = re.compile(
    rf"\b((?:Operation|Operação|Operación|Opération|Project|Programme|Program|System|Platform|Tool|Deployment|Initiative|Campaign)"
    rf"(?:\s+{OBJECT_WORD})+)\b"
)
INSTITUTION_TYPE = (
    r"Ministry|Department|Directorate|Bureau|Office|Commission|Committee|Council|Court|Tribunal|Agency|"
    r"Secretariat|Administration|Police|Prison|Penitentiary|Service|Force|Forces|Branch|Unit|Centre|Center|Board"
)
# Repeatable tails cover locators such as "Police of the Ministry of Internal Affairs".
# All-caps qualifiers such as POFMA stop the tail via TAIL_WORD.
INSTITUTION_SUFFIX = rf"(?:\s+(?:of|for|against|on)(?:\s+the)?(?:\s+{TAIL_WORD}){{1,6}})*"
MAXIMAL_INSTITUTION_RE = re.compile(
    rf"\b(Penitentiary\s+no\.\s*\d+\s+{OBJECT_WORD}"
    rf"|(?:{OBJECT_WORD}(?:\s+|[-/])){{0,6}}(?:{INSTITUTION_TYPE}){INSTITUTION_SUFFIX})\b"
)
SCOPE_OBJECT_FIELDS = {"schedule_identity", "project_boundary", "identified_incident", "identified_measure"}
AUDITED_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)
SKIP_EXTRA_FIELDS = {"identity_sources", "dossier", "linked_project_id", "linked_organization_id"}


def add_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def ambiguous_actor_list_mentions(raw: str) -> list[str]:
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
    for match in MAXIMAL_INSTITUTION_RE.finditer(raw):
        label = " ".join(match.group(1).split()).strip(" ,;:()[]{}\"'“”‘’")
        if label and label not in labels:
            labels.append(label)
    return labels


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
    haystack, needle = normalized_tokens(text), normalized_tokens(phrase)
    if not haystack or not needle or len(needle) > len(haystack):
        return 0
    width = len(needle)
    return sum(haystack[index:index + width] == needle for index in range(len(haystack) - width + 1))


def resolved_identity_covers_label(row: dict, label: str, by_id: dict[str, dict]) -> bool:
    raw = row.get("raw") or ""
    if token_phrase_occurrences(raw, label) != 1:
        return False
    for entity_id in row.get("resolved_ids") or []:
        entity = by_id.get(entity_id)
        if not entity:
            continue
        for form in entity.get("surface_forms") or []:
            form_text = form.get("text") or form.get("normalized") or ""
            if form_text and token_phrase_occurrences(raw, form_text) == 1 and token_phrase_occurrences(form_text, label) >= 1:
                return True
    return False


def string_leaves(value: object, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str]]:
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


def extra_rows_from_mapping(mapping: dict, *, source: str, state: str | None, record_index: int | None,
                            skip_fields: set[str], document_root: bool = False) -> list[dict]:
    rows: list[dict] = []
    common = {
        "kind": "extra-context-reference", "state": state, "source": source,
        "record_index": record_index, "resolved_ids": [], "status": "context-only",
        "resolution_source": None, "disposition_reason": None, "document_root": document_root,
    }
    for field, value in mapping.items():
        if field in skip_fields:
            continue
        field_text = str(field)
        if isinstance(field, str) and field.strip():
            rows.append({**common, "field": f"@key[{field}]", "raw": field})
        for nested_path, raw in mapping_key_surfaces(value, (field_text,)):
            rows.append({**common, "field": ".".join(nested_path), "raw": raw})
        for nested_path, raw in string_leaves(value, (field_text,)):
            rows.append({**common, "field": ".".join(nested_path), "raw": raw})
    return rows


def extra_context_rows() -> list[dict]:
    rows: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        source = str(path.relative_to(schedule.ROOT))
        if isinstance(data.get("records"), list):
            root = {key: value for key, value in data.items() if key != "records"}
            rows.extend(extra_rows_from_mapping(root, source=source, state=None, record_index=None,
                                                skip_fields=SKIP_EXTRA_FIELDS, document_root=True))
        for record_index, record in enumerate(schedule.records_from_document(data)):
            rows.extend(extra_rows_from_mapping(record, source=source, state=record.get("state"), record_index=record_index,
                                                skip_fields=AUDITED_FIELDS | SKIP_EXTRA_FIELDS))
    return rows


def residual_key(row: dict, label: str) -> tuple[str, str, str, str, str]:
    return (row.get("source") or "", row.get("state") or "", row.get("field") or "", row.get("raw") or "", label)


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    found: list[dict] = []
    overlays = residual.load_dispositions()
    overlay_uses: Counter = Counter()
    rows = list(report.get("references", [])) + extra_context_rows()
    for row in rows:
        if row.get("kind") not in {"actor-reference", "project-reference", "scope-reference", "scope-identity-reference", "extra-context-reference"}:
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        labels = contextual_labels(row)
        if row.get("document_root") and labels:
            for label in labels:
                found.append({
                    "reason": "identity-bearing multi-record document-root metadata is outside State-scoped Schedule audit; move it into a record",
                    "state": state, "kind": row.get("kind"), "field": row.get("field"), "source": row.get("source"),
                    "record_index": row.get("record_index"), "raw": raw, "identity_surface": label,
                })
            continue
        exact_ids = schedule.embedded_identity_matches(raw, entities, identity_index, "identity", state)
        if row.get("kind") == "extra-context-reference" and exact_ids:
            row = {**row, "resolved_ids": exact_ids, "resolution_source": "neutral-extra-field-exact-coverage"}
        for label in labels:
            if (exact.materialized_person_ids_for_mention(label, entities, identity_index, state)
                    or exact.materialized_non_person_ids_for_mention(label, entities, identity_index, state)
                    or resolved_identity_covers_label(row, label, by_id)
                    or strict.explicitly_defers_complete_name(row, label)):
                continue
            key = residual_key(row, label)
            disposition = overlays.get(key)
            if disposition is not None:
                overlay_uses[key] += 1
                if disposition["disposition"] == "covered":
                    if row.get("kind") == "extra-context-reference":
                        found.append({"reason": "residual covered disposition cannot create a role binding in extra context",
                                      "source": row.get("source"), "state": state, "field": row.get("field"),
                                      "raw": raw, "identity_surface": label})
                        continue
                    missing = sorted(set(disposition["covered_ids"]) - set(row.get("resolved_ids") or []))
                    if missing:
                        found.append({"reason": "residual covered IDs are not already resolved on the same audited row",
                                      "source": row.get("source"), "state": state, "field": row.get("field"),
                                      "raw": raw, "identity_surface": label, "missing_covered_ids": missing})
                    continue
                if disposition["disposition"] == "deferred":
                    continue
            found.append({
                "reason": "adversarial Schedule identity surface can bypass normal identity cues", "state": state,
                "kind": row.get("kind"), "field": row.get("field"), "source": row.get("source"),
                "record_index": row.get("record_index"), "raw": raw, "identity_surface": label,
                "status": row.get("status"), "resolution_source": row.get("resolution_source"),
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
    assert named_institution_labels("National Centre for Human Rights") == ["National Centre for Human Rights"]
    assert named_institution_labels("Yaoundé Military Tribunal life sentence") == ["Yaoundé Military Tribunal"]
    assert named_institution_labels("National Administration of Penitentiaries and staff") == ["National Administration of Penitentiaries"]
    assert named_institution_labels("High Court/Court of Appeal POFMA review") == ["High Court/Court of Appeal"]
    assert named_institution_labels("UN Committee against Torture findings") == ["UN Committee against Torture"]
    assert named_institution_labels("Police of the Ministry of Internal Affairs framework") == ["Police of the Ministry of Internal Affairs"]
    assert named_institution_labels("Penitentiary no. 2 Lipcani, no. 6 Soroca") == ["Penitentiary no. 2 Lipcani"]
    assert named_object_labels("Operation Alpha Bravo Charlie Delta Echo Foxtrot Golf") == ["Operation Alpha Bravo Charlie Delta Echo Foxtrot Golf"]
    assert "Jane Doe" in contextual_labels({"kind": "extra-context-reference", "status": "context-only", "field": "notes.detail", "raw": "detention of Jane Doe pending trial"})
    keyed = mapping_key_surfaces({"detention of Jane Doe pending trial": True}, ("review",))
    assert (("review", "@key[detention of Jane Doe pending trial]"), "detention of Jane Doe pending trial") in keyed
    root_rows = extra_rows_from_mapping({"note": "detention of Jane Doe pending trial", "Operation Silent Dawn": True},
                                        source="x.yml", state=None, record_index=None, skip_fields=set(), document_root=True)
    assert any(row["raw"] == "detention of Jane Doe pending trial" and row["document_root"] for row in root_rows)
    assert any(row["raw"] == "Operation Silent Dawn" and row["document_root"] for row in root_rows)
    phase = {"id": "PROJECT-BRA-PHASE", "type": "Project",
             "surface_forms": [{"text": "Operação Contenção — 28 October 2025 phase", "normalized": "operacao contencao 28 october 2025 phase"}]}
    assert resolved_identity_covers_label({"raw": "Operação Contenção — 28 October 2025 phase", "resolved_ids": [phase["id"]]},
                                          "Operação Contenção", {phase["id"]: phase})
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
    print(f"Schedule adversarial residual identity completeness: OK ({len(dispositions)} exact reviewed surfaces; {covered} covered; {deferred} deferred)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
