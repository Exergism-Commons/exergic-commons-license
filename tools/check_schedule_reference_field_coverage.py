#!/usr/bin/env python3
"""Fail closed on Schedule fields that can carry identity but are outside audited semantics."""
from __future__ import annotations

import argparse
import json
import re
from typing import Iterable

import yaml

import audit_schedule_reference_coverage as schedule
import entity_identity_resolution as identity

REFERENCE_FIELD_RE = re.compile(
    r"(?:party|parties|operator|operators|actor|actors|agency|agencies|authority|authorities|"
    r"institution|institutions|organization|organisation|company|companies|vendor|supplier|"
    r"project|projects|deployment|deployments|participant|participants|implementer|implementers|"
    r"entity|entities|owner|owners|controller|controllers|body|bodies|unit|units|department|"
    r"departments|directorate|directorates|service|services|force|forces|office|offices|bureau|"
    r"bureaux|command|commands|ministry|ministries)",
    re.I,
)
KNOWN_REFERENCE_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)
PROVENANCE_FIELDS = {"identity_sources"}
CROSS_ENTITY_LINK_FIELDS = {
    "linked_project_id": "registry/projects.yml",
    "linked_organization_id": "registry/organizations.yml",
}


def walk_dict_fields(value: object, prefix: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], object]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                continue
            path = (*prefix, key)
            yield path, child
            yield from walk_dict_fields(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_dict_fields(child, (*prefix, f"[{index}]"))


def registry_ids(relative_path: str) -> set[str]:
    data = yaml.safe_load((schedule.ROOT / relative_path).read_text(encoding="utf-8"))
    outcomes = data.get("outcomes") if isinstance(data, dict) else None
    assert isinstance(outcomes, dict), relative_path
    values: set[str] = set()
    for rows in outcomes.values():
        if isinstance(rows, list):
            values.update(item for item in rows if isinstance(item, str))
    return values


def canonical_state_names() -> dict[str, str]:
    entities, _ = identity.load_repository_entities()
    result: dict[str, str] = {}
    for entity in entities:
        entity_id = entity.get("id")
        name = entity.get("name")
        if entity.get("type") == "State" and isinstance(entity_id, str) and entity_id.startswith("STATE-") and isinstance(name, str):
            result[entity_id.removeprefix("STATE-")] = name
    return result


def metadata_failure(field: str, value: object, record: dict, state_names: dict[str, str]) -> str | None:
    if field == "entity":
        state = record.get("state")
        expected = state_names.get(state) if isinstance(state, str) else None
        if not isinstance(value, str) or expected is None or identity.default_normalizer(value) != identity.default_normalizer(expected):
            return f"entity metadata must equal the canonical State name for {state!r}"
        return None
    if field in PROVENANCE_FIELDS:
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
            return f"{field} provenance must be a non-empty string list"
        return None
    return "not-metadata"


def reference_value_failure(field: str, value: object) -> str | None:
    """Known identity/scope fields must not rely on list_values() silently dropping data."""
    if isinstance(value, str):
        return None if value.strip() else f"{field} must not be an empty string"
    if isinstance(value, list):
        if not value:
            return f"{field} must not be an empty list"
        if not all(isinstance(item, str) and item.strip() for item in value):
            return f"{field} must be a non-empty string or a list of non-empty strings"
        return None
    return f"{field} must be a string or list of strings; got {type(value).__name__}"


def append_failure(failures: list[dict], *, path, record_index: int | None, field_path: tuple[str, ...], reason: str) -> None:
    row = {
        "source": str(path.relative_to(schedule.ROOT)),
        "field_path": ".".join(field_path),
        "reason": reason,
    }
    if record_index is not None:
        row["record_index"] = record_index
    failures.append(row)


def validate_record_fields(path, record_index: int, record: dict, state_names: dict[str, str], cross_ids: dict[str, set[str]], failures: list[dict]) -> None:
    state = record.get("state")
    if not isinstance(state, str) or state not in state_names:
        append_failure(
            failures, path=path, record_index=record_index, field_path=("state",),
            reason=f"Schedule record must name one canonical State ISO3; got {state!r}",
        )

    for field_path, value in walk_dict_fields(record):
        field = field_path[-1]
        top_level = len(field_path) == 1

        if top_level and field in KNOWN_REFERENCE_FIELDS:
            problem = reference_value_failure(field, value)
            if problem is not None:
                append_failure(failures, path=path, record_index=record_index, field_path=field_path, reason=problem)
            continue
        if top_level and field in {"entity", *PROVENANCE_FIELDS}:
            problem = metadata_failure(field, value, record, state_names)
            if problem is None:
                continue
            append_failure(failures, path=path, record_index=record_index, field_path=field_path, reason=problem)
            continue
        if top_level and field in CROSS_ENTITY_LINK_FIELDS:
            if not isinstance(value, str) or value not in cross_ids[field]:
                append_failure(
                    failures, path=path, record_index=record_index, field_path=field_path,
                    reason=f"cross-entity link does not resolve in {CROSS_ENTITY_LINK_FIELDS[field]}",
                )
            continue

        if field in KNOWN_REFERENCE_FIELDS or field in {"entity", *PROVENANCE_FIELDS, *CROSS_ENTITY_LINK_FIELDS}:
            reason = "identity/provenance field is nested outside the flat schema audited by coverage"
        elif REFERENCE_FIELD_RE.search(field):
            reason = "identity-bearing-looking field is not classified by the Schedule coverage schema"
        else:
            continue
        append_failure(failures, path=path, record_index=record_index, field_path=field_path, reason=reason)


def validate_document_root(path, data: object, failures: list[dict]) -> None:
    """Validate document shape and keep multi-record metadata from becoming a second identity surface."""
    if not isinstance(data, dict):
        append_failure(
            failures, path=path, record_index=None, field_path=("<document>",),
            reason="Schedule freeze document must be a mapping/object",
        )
        return
    if "records" in data:
        records = data.get("records")
        if not isinstance(records, list) or not records:
            append_failure(
                failures, path=path, record_index=None, field_path=("records",),
                reason="multi-record Schedule document must contain a non-empty records list",
            )
            return
        for index, item in enumerate(records):
            if not isinstance(item, dict):
                append_failure(
                    failures, path=path, record_index=index, field_path=("records", f"[{index}]"),
                    reason="Schedule records entries must be mappings/objects",
                )
        root = {key: value for key, value in data.items() if key != "records"}
        for field_path, _ in walk_dict_fields(root):
            field = field_path[-1]
            if field in KNOWN_REFERENCE_FIELDS or field in {"entity", *PROVENANCE_FIELDS, *CROSS_ENTITY_LINK_FIELDS} or REFERENCE_FIELD_RE.search(field):
                append_failure(
                    failures, path=path, record_index=None, field_path=field_path,
                    reason="identity-bearing field appears at multi-record document root outside audited records",
                )
    elif not isinstance(data.get("state"), str):
        append_failure(
            failures, path=path, record_index=None, field_path=("state",),
            reason="single-record Schedule document must contain a State field",
        )


def unknown_reference_fields() -> list[dict]:
    failures: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    state_names = canonical_state_names()
    cross_ids = {field: registry_ids(path) for field, path in CROSS_ENTITY_LINK_FIELDS.items()}

    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_document_root(path, data, failures)
        if not isinstance(data, dict):
            continue
        raw_records = data.get("records")
        if isinstance(raw_records, list):
            records = [item for item in raw_records if isinstance(item, dict)]
        elif isinstance(data.get("state"), str):
            records = [data]
        else:
            records = []
        for record_index, record in enumerate(records):
            validate_record_fields(path, record_index, record, state_names, cross_ids, failures)

    dedup: dict[tuple[str, object, str], dict] = {
        (row["source"], row.get("record_index"), row["field_path"]): row for row in failures
    }
    return list(dedup.values())


def self_test() -> None:
    assert REFERENCE_FIELD_RE.search("candidate_actors")
    assert REFERENCE_FIELD_RE.search("deployment_owner")
    assert REFERENCE_FIELD_RE.search("responsible_authorities")
    assert REFERENCE_FIELD_RE.search("responsible_unit")
    assert REFERENCE_FIELD_RE.search("controlling_department")
    assert REFERENCE_FIELD_RE.search("security_service")
    assert not REFERENCE_FIELD_RE.search("legal_basis")
    assert "candidate_parties" in KNOWN_REFERENCE_FIELDS
    assert "project_boundary" in KNOWN_REFERENCE_FIELDS
    assert reference_value_failure("candidate_parties", ["Agency"]) is None
    assert reference_value_failure("candidate_parties", ["Agency", 7]) is not None
    assert reference_value_failure("candidate_parties", {"name": "Agency"}) is not None
    nested = list(walk_dict_fields({"details": {"candidate_parties": ["Agency"]}}))
    assert any(path == ("details", "candidate_parties") for path, _ in nested)
    assert "MITIGA-DETENTION-APPARATUS" in registry_ids("registry/projects.yml")
    assert "SDF-RADA" in registry_ids("registry/organizations.yml")
    synthetic_failures: list[dict] = []
    validate_document_root(
        schedule.ROOT / "registry" / "schedule-state-s-freezes" / "synthetic.yml",
        {"records": [{}], "candidate_parties": ["Agency"]}, synthetic_failures,
    )
    assert any(row["field_path"] == "candidate_parties" for row in synthetic_failures)
    malformed_failures: list[dict] = []
    validate_document_root(
        schedule.ROOT / "registry" / "schedule-state-s-freezes" / "synthetic.yml",
        {"records": ["not-a-record"]}, malformed_failures,
    )
    assert malformed_failures
    print("Schedule reference-field coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = unknown_reference_fields()
    if failures:
        print("UNAUDITED_SCHEDULE_REFERENCE_FIELDS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule reference-field coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
