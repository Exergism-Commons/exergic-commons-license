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
import re

import audit_schedule_reference_coverage as schedule

HEURISTIC_SOURCE = "jurisdiction-safe-canonical-name-or-alias"
POST_SCOPE_PUNCTUATED_CONNECTOR_RE = re.compile(r"[,;—–-]\s*(?:and|with)\b", re.I)
POST_SCOPE_STRONG_CONNECTOR_RE = re.compile(r"\b(?:including|plus|as\s+well\s+as|together\s+with)\b", re.I)


def has_including_clause(raw: str) -> bool:
    """Any rendered `including` clause is composite and requires explicit review."""
    return bool(re.search(r"\bincluding\b", raw, re.I))


def post_scope_tail(raw: str) -> str:
    """Return the portion after the first capacity/scope split used by the heuristic."""
    lower = raw.lower()
    positions = [lower.find(token) for token in schedule.CAPACITY_SPLITS if lower.find(token) >= 0]
    if not positions:
        return ""
    return raw[min(positions):]


def has_unsafe_post_scope_connector(raw: str) -> bool:
    tail = post_scope_tail(raw)
    if not tail:
        return False
    if POST_SCOPE_STRONG_CONNECTOR_RE.search(tail):
        return True
    return bool(POST_SCOPE_PUNCTUATED_CONNECTOR_RE.search(tail))


def exact_same_entity_head(head: str, aliases: set[str]) -> bool:
    """Accept an exact alias, optionally followed by another alias in parentheses."""
    if schedule.norm(head) in aliases:
        return True
    match = re.fullmatch(r"\s*(.+?)\s*\(([^()]+)\)\s*", head)
    if not match:
        return False
    base, parenthetical = match.groups()
    return schedule.norm(base) in aliases and schedule.norm(parenthetical) in aliases


def unsafe_reason(row: dict, by_id: dict[str, dict]) -> str | None:
    if row.get("resolution_source") != HEURISTIC_SOURCE:
        return None
    resolved_ids = row.get("resolved_ids") or []
    if len(resolved_ids) != 1:
        return "heuristic resolution must produce exactly one identity"
    entity = by_id.get(resolved_ids[0])
    if entity is None:
        return "heuristic resolution target is missing from the current ABox"
    aliases = set(entity.get("aliases") or [])
    head = row.get("identity_head") or ""
    if not exact_same_entity_head(head, aliases):
        return "heuristic match is not an exact canonical name/alias after capacity stripping"
    raw = row.get("raw") or ""
    if has_including_clause(raw):
        return "reference contains an including-clause and requires reviewed composite handling"
    if has_unsafe_post_scope_connector(raw):
        return "reference contains a post-scope composite connector and requires reviewed handling"
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
            "aliases": ["national police", "np"],
        }
    }
    exact = {
        "resolution_source": HEURISTIC_SOURCE,
        "resolved_ids": ["AGENCY-AAA-NATIONAL-POLICE"],
        "identity_head": "National Police",
        "raw": "National Police, only in qualifying cases",
    }
    assert unsafe_reason(exact, by_id) is None

    parenthetical_alias = {
        **exact,
        "identity_head": "National Police (NP)",
        "raw": "National Police (NP), only in qualifying cases",
    }
    assert unsafe_reason(parenthetical_alias, by_id) is None

    prefix = {
        **exact,
        "identity_head": "National Police and participating territorial units",
        "raw": "National Police and participating territorial units, only in qualifying cases",
    }
    assert "not an exact" in (unsafe_reason(prefix, by_id) or "")

    including_before_scope = {
        **exact,
        "identity_head": "National Police",
        "raw": "National Police, including Rescue Coordination Centre and other units, only in qualifying cases",
    }
    assert "including-clause" in (unsafe_reason(including_before_scope, by_id) or "")

    including_after_scope = {
        **exact,
        "identity_head": "National Police",
        "raw": "National Police, only in qualifying cases including Rescue Coordination Centre",
    }
    assert "including-clause" in (unsafe_reason(including_after_scope, by_id) or "")

    semicolon_and = {
        **exact,
        "raw": "National Police, only in qualifying cases; and Rescue Coordination Centre",
    }
    assert "post-scope composite" in (unsafe_reason(semicolon_and, by_id) or "")

    plus_unit = {
        **exact,
        "raw": "National Police, only in qualifying cases plus Rescue Coordination Centre",
    }
    assert "post-scope composite" in (unsafe_reason(plus_unit, by_id) or "")

    reviewed = {
        **including_after_scope,
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
