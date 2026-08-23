#!/usr/bin/env python3
"""Fail closed when a curated Schedule reference is only partially heuristic-resolved.

The Schedule coverage audit intentionally permits automatic resolution for simple exact
canonical names/aliases. Composite locators, parent/sub-unit phrases and references that
name additional or non-enumerated actors/projects require an explicit reviewed disposition.
This guard prevents the heuristic resolver from declaring a whole reference covered merely
because one known identity appears as a prefix or contained substring.
"""
from __future__ import annotations

import argparse
import json

import audit_schedule_reference_coverage as schedule

HEURISTIC_SOURCE = "jurisdiction-safe-canonical-name-or-alias"
SCOPE_ONLY_SPLITS = (", only ", " only when ", " only in ", " only where ")


def pre_scope_including(raw: str) -> bool:
    lower = raw.lower()
    include = lower.find(", including ")
    if include < 0:
        return False
    scope_positions = [lower.find(token) for token in SCOPE_ONLY_SPLITS if lower.find(token) >= 0]
    return not scope_positions or include < min(scope_positions)


def unsafe_reason(row: dict, by_id: dict[str, dict]) -> str | None:
    if row.get("resolution_source") != HEURISTIC_SOURCE:
        return None
    resolved_ids = row.get("resolved_ids") or []
    if len(resolved_ids) != 1:
        return "heuristic resolution must produce exactly one identity"
    entity = by_id.get(resolved_ids[0])
    if entity is None:
        return "heuristic resolution target is missing from the current ABox"
    head_norm = schedule.norm(row.get("identity_head") or "")
    aliases = set(entity.get("aliases") or [])
    if head_norm not in aliases:
        return "heuristic match is not an exact canonical name/alias after capacity stripping"
    if pre_scope_including(row.get("raw") or ""):
        return "reference introduces an including-clause before capacity scope and requires reviewed composite handling"
    return None


def unsafe_rows(report: dict, by_id: dict[str, dict]) -> list[dict]:
    failures: list[dict] = []
    for row in report.get("references", []):
        reason = unsafe_reason(row, by_id)
        if reason:
            failures.append({
                "state": row.get("state"),
                "field": row.get("field"),
                "raw": row.get("raw"),
                "resolved_ids": row.get("resolved_ids") or [],
                "reason": reason,
                "source": row.get("source"),
                "record_index": row.get("record_index"),
            })
    return failures


def self_test() -> None:
    by_id = {
        "AGENCY-AAA-NATIONAL-POLICE": {
            "id": "AGENCY-AAA-NATIONAL-POLICE",
            "aliases": ["national police"],
        }
    }
    exact = {
        "resolution_source": HEURISTIC_SOURCE,
        "resolved_ids": ["AGENCY-AAA-NATIONAL-POLICE"],
        "identity_head": "National Police",
        "raw": "National Police, only in qualifying cases",
    }
    assert unsafe_reason(exact, by_id) is None

    prefix = {
        **exact,
        "identity_head": "National Police and participating territorial units",
        "raw": "National Police and participating territorial units, only in qualifying cases",
    }
    assert "not an exact" in (unsafe_reason(prefix, by_id) or "")

    including = {
        **exact,
        "identity_head": "National Police",
        "raw": "National Police, including Rescue Coordination Centre and other units, only in qualifying cases",
    }
    assert "including-clause" in (unsafe_reason(including, by_id) or "")

    reviewed = {
        **including,
        "resolution_source": "reviewed-disposition",
    }
    assert unsafe_reason(reviewed, by_id) is None
    print("Schedule heuristic-resolution safety self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    report = schedule.audit()
    _, by_id, _ = schedule.load_entities()
    failures = unsafe_rows(report, by_id)
    if failures:
        print("UNSAFE_HEURISTIC_SCHEDULE_RESOLUTIONS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule heuristic-resolution safety: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
