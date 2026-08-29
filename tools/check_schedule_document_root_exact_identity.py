#!/usr/bin/env python3
"""Reject exact current identities in multi-record Schedule document-root metadata.

Multi-record root metadata has no State scope. Identity-bearing text must live inside a
record where the normal Schedule identity audit can assign jurisdiction and review debt.
This guard is representational only and creates no role, participation, culpability, or
governance semantics.
"""
from __future__ import annotations

import argparse
import json

import audit_schedule_reference_coverage as schedule
import check_schedule_adversarial_identity_gaps as adversarial


def failures(rows: list[dict], entities: list[dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in rows:
        if not row.get("document_root"):
            continue
        raw = row.get("raw") or ""
        exact_ids = schedule.embedded_identity_matches(raw, entities, identity_index, "identity", None)
        if not exact_ids:
            continue
        found.append({
            "reason": "exact identity in multi-record document-root metadata is outside State-scoped Schedule audit",
            "source": row.get("source"),
            "field": row.get("field"),
            "record_index": row.get("record_index"),
            "raw": raw,
            "exact_ids": sorted(exact_ids),
        })
    return found


def self_test() -> None:
    entities, _, identity_index = schedule.load_entities()
    rows = [
        {
            "kind": "extra-context-reference",
            "state": None,
            "source": "synthetic.yml",
            "field": "notes",
            "record_index": None,
            "raw": "Source: Human Rights Watch",
            "document_root": True,
        },
        {
            "kind": "extra-context-reference",
            "state": None,
            "source": "synthetic.yml",
            "field": "notes",
            "record_index": None,
            "raw": "Source note without a named identity",
            "document_root": True,
        },
    ]
    problems = failures(rows, entities, identity_index)
    assert len(problems) == 1
    assert "ORG-HUMAN-RIGHTS-WATCH" in problems[0]["exact_ids"]
    assert failures([{**rows[0], "document_root": False}], entities, identity_index) == []
    print("Schedule document-root exact-identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, _, identity_index = schedule.load_entities()
    problems = failures(adversarial.extra_context_rows(), entities, identity_index)
    if problems:
        print(json.dumps(problems, indent=2, ensure_ascii=False, sort_keys=True))
        return 1
    print("Schedule document-root exact-identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
