#!/usr/bin/env python3
"""Fail closed on Schedule record fields that look identity-bearing but are unaudited."""
from __future__ import annotations

import argparse
import json
import re

import yaml

import audit_schedule_reference_coverage as schedule

REFERENCE_FIELD_RE = re.compile(
    r"(?:party|parties|operator|operators|actor|actors|agency|agencies|institution|institutions|"
    r"organization|organisation|company|companies|vendor|supplier|project|projects|deployment|deployments)",
    re.I,
)
KNOWN_REFERENCE_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)


def unknown_reference_fields() -> list[dict]:
    failures: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for record_index, record in enumerate(schedule.records_from_document(data)):
            for field in record:
                if field in KNOWN_REFERENCE_FIELDS or not REFERENCE_FIELD_RE.search(field):
                    continue
                failures.append({
                    "source": str(path.relative_to(schedule.ROOT)),
                    "record_index": record_index,
                    "field": field,
                })
    dedup: dict[tuple[str, int, str], dict] = {
        (row["source"], row["record_index"], row["field"]): row for row in failures
    }
    return list(dedup.values())


def self_test() -> None:
    assert REFERENCE_FIELD_RE.search("candidate_actors")
    assert REFERENCE_FIELD_RE.search("deployment_owner")
    assert not REFERENCE_FIELD_RE.search("legal_basis")
    assert "candidate_parties" in KNOWN_REFERENCE_FIELDS
    assert "project_boundary" in KNOWN_REFERENCE_FIELDS
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
