#!/usr/bin/env python3
"""Fail closed on Schedule record fields that look identity-bearing but are unaudited."""
from __future__ import annotations

import argparse
import json
import re
from typing import Iterable

import yaml

import audit_schedule_reference_coverage as schedule

REFERENCE_FIELD_RE = re.compile(
    r"(?:party|parties|operator|operators|actor|actors|agency|agencies|authority|authorities|"
    r"institution|institutions|organization|organisation|company|companies|vendor|supplier|"
    r"project|projects|deployment|deployments|participant|participants|implementer|implementers|"
    r"entity|entities)",
    re.I,
)
KNOWN_REFERENCE_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)


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


def unknown_reference_fields() -> list[dict]:
    failures: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for record_index, record in enumerate(schedule.records_from_document(data)):
            for field_path, _ in walk_dict_fields(record):
                field = field_path[-1]
                top_level = len(field_path) == 1
                if top_level and field in KNOWN_REFERENCE_FIELDS:
                    continue
                if field in KNOWN_REFERENCE_FIELDS:
                    reason = "known identity-bearing field is nested outside the flat schema audited by coverage"
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
        print("UNAUDITED_SCHEDULE_REFERENCE_FIELDS=" + json.dumps(failures, sort_keys=True))
        return 2
    print("Schedule reference-field coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
