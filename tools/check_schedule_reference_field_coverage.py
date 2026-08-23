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
    r"entity|entities)",
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


def unknown_reference_fields() -> list[dict]:
    failures: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    state_names = canonical_state_names()
    cross_ids = {field: registry_ids(path) for field, path in CROSS_ENTITY_LINK_FIELDS.items()}

    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for record_index, record in enumerate(schedule.records_from_document(data)):
            for field_path, value in walk_dict_fields(record):
                field = field_path[-1]
                top_level = len(field_path) == 1

                if top_level and field in KNOWN_REFERENCE_FIELDS:
                    continue
                if top_level and field in {"entity", *PROVENANCE_FIELDS}:
                    problem = metadata_failure(field, value, record, state_names)
                    if problem is None:
                        continue
                    failures.append({
                        "source": str(path.relative_to(schedule.ROOT)),
                        "record_index": record_index,
                        "field_path": field,
                        "reason": problem,
                    })
                    continue
                if top_level and field in CROSS_ENTITY_LINK_FIELDS:
                    if not isinstance(value, str) or value not in cross_ids[field]:
                        failures.append({
                            "source": str(path.relative_to(schedule.ROOT)),
                            "record_index": record_index,
                            "field_path": field,
                            "reason": f"cross-entity link does not resolve in {CROSS_ENTITY_LINK_FIELDS[field]}",
                        })
                    continue

                if field in KNOWN_REFERENCE_FIELDS or field in {"entity", *PROVENANCE_FIELDS, *CROSS_ENTITY_LINK_FIELDS}:
                    reason = "identity/provenance field is nested outside the flat schema audited by coverage"
                elif REFERENCE_FIELD_RE.search(field):
                    reason = "identity-bearing-looking field is not classified by the Schedule coverage schema"
                else:
                    continue
                failures.append({
                    "source": str(path.relative_to(schedule.ROOT)),
                    "record_index": record_index,
                    "field_path": ".".join(field_path),
                    "reason": reason,
                })

    dedup: dict[tuple[str, int, str], dict] = {
        (row["source"], row["record_index"], row["field_path"]): row for row in failures
    }
    return list(dedup.values())


def self_test() -> None:
    assert REFERENCE_FIELD_RE.search("candidate_actors")
    assert REFERENCE_FIELD_RE.search("deployment_owner")
    assert REFERENCE_FIELD_RE.search("responsible_authorities")
    assert not REFERENCE_FIELD_RE.search("legal_basis")
    assert "candidate_parties" in KNOWN_REFERENCE_FIELDS
    assert "project_boundary" in KNOWN_REFERENCE_FIELDS
    nested = list(walk_dict_fields({"details": {"candidate_parties": ["Agency"]}}))
    assert any(path == ("details", "candidate_parties") for path, _ in nested)
    assert "MITIGA-DETENTION-APPARATUS" in registry_ids("registry/projects.yml")
    assert "SDF-RADA" in registry_ids("registry/organizations.yml")
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
