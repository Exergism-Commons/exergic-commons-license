#!/usr/bin/env python3
"""Fail closed on exact non-Project identities embedded in Schedule project rows.

Project-reference ``resolved_ids`` remain Project/Deployment role bindings.  Exact current
State-safe Agency/Institution/Organization surfaces that merely co-occur in the same text
must be recorded separately in a blob-pinned reviewed overlay.  This is identity coverage
only and creates no participation, control, operation, membership, supply, culpability,
evidence, or governance inference.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
from entity_identity_resolution import eligible_in_state

OVERLAY = schedule.ROOT / "knowledge" / "generated" / "schedule-project-cross-role-identity-coverage-v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PROJECT_TYPES = {"Project", "Deployment"}
CROSS_ROLE_TYPES = {"Agency", "Institution", "Organization"}


def row_key(row: dict) -> tuple[str, str, str, int, str]:
    return (
        row.get("source") or "",
        row.get("state") or "",
        row.get("field") or "",
        int(row.get("record_index") if row.get("record_index") is not None else -1),
        row.get("raw") or "",
    )


def load_overlay() -> list[dict]:
    data = json.loads(OVERLAY.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"unexpected project cross-role coverage version: {data.get('version')!r}")
    source_blobs = data.get("source_blobs")
    if not isinstance(source_blobs, dict) or not source_blobs:
        raise ValueError("project cross-role coverage must pin source_blobs")

    for source, expected_sha in source_blobs.items():
        if not isinstance(source, str) or not source or not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise ValueError(f"invalid project cross-role source pin: {source!r} -> {expected_sha!r}")
        path = schedule.ROOT / source
        if not path.is_file():
            raise ValueError(f"project cross-role pinned source does not exist: {source}")
        actual_sha = schedule.git_blob_sha1(path.read_bytes())
        if actual_sha != expected_sha:
            raise ValueError(
                f"project cross-role reviewed source changed: {source}; expected blob {expected_sha}, got {actual_sha}"
            )

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("project cross-role coverage entries must be a list")

    seen: set[tuple[str, str, str, int, str]] = set()
    referenced_sources: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"project cross-role entry is not an object: #{index}")
        required = {"source", "state", "field", "record_index", "raw", "identity_coverage_ids", "reason"}
        missing = required - set(entry)
        if missing:
            raise ValueError(f"project cross-role entry missing fields #{index}: {sorted(missing)}")
        if entry["field"] not in schedule.PROJECT_FIELDS:
            raise ValueError(f"project cross-role entry is not a Project field #{index}: {entry['field']!r}")
        if entry["source"] not in source_blobs:
            raise ValueError(f"project cross-role entry source is not pinned #{index}: {entry['source']!r}")
        ids = entry["identity_coverage_ids"]
        if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
            raise ValueError(f"project cross-role identity_coverage_ids must be a non-empty string list #{index}")
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate project cross-role identity_coverage_ids #{index}: {ids}")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ValueError(f"missing project cross-role reason #{index}")
        key = row_key(entry)
        if key in seen:
            raise ValueError(f"duplicate project cross-role coverage row: {key}")
        seen.add(key)
        referenced_sources.add(entry["source"])

    stale_pins = sorted(set(source_blobs) - referenced_sources)
    if stale_pins:
        raise ValueError(f"unused project cross-role source pins: {stale_pins}")
    return entries


def exact_cross_role_ids(raw: str, state: str | None, entities: list[dict], identity_index) -> list[str]:
    candidates = [entity for entity in entities if entity.get("type") in CROSS_ROLE_TYPES]
    return exact.independent_exact_matches(raw, candidates, identity_index, "identity", state)


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index, entries: list[dict]) -> list[dict]:
    found: list[dict] = []
    by_key = {row_key(entry): entry for entry in entries}
    uses: Counter = Counter()

    for row in report.get("references", []):
        if row.get("kind") != "project-reference":
            continue
        key = row_key(row)
        exact_ids = set(exact_cross_role_ids(row.get("raw") or "", row.get("state"), entities, identity_index))
        entry = by_key.get(key)

        if not exact_ids:
            if entry is not None:
                found.append({
                    "reason": "stale project cross-role coverage entry no longer corresponds to an exact current identity",
                    "source": row.get("source"), "state": row.get("state"), "field": row.get("field"),
                    "record_index": row.get("record_index"), "raw": row.get("raw"),
                    "declared_ids": entry.get("identity_coverage_ids"),
                })
                uses[key] += 1
            continue

        if entry is None:
            found.append({
                "reason": "project-reference contains exact non-Project identity without separate reviewed coverage",
                "source": row.get("source"), "state": row.get("state"), "field": row.get("field"),
                "record_index": row.get("record_index"), "raw": row.get("raw"),
                "missing_identity_coverage_ids": sorted(exact_ids),
                "project_role_ids": row.get("resolved_ids") or [],
            })
            continue

        uses[key] += 1
        declared = set(entry.get("identity_coverage_ids") or [])
        if declared != exact_ids:
            found.append({
                "reason": "project cross-role reviewed coverage must equal the complete exact non-Project identity set",
                "source": row.get("source"), "state": row.get("state"), "field": row.get("field"),
                "record_index": row.get("record_index"), "raw": row.get("raw"),
                "expected_ids": sorted(exact_ids), "declared_ids": sorted(declared),
            })
            continue

        for entity_id in sorted(declared):
            entity = by_id.get(entity_id)
            if entity is None:
                found.append({"reason": "project cross-role coverage target does not resolve", "entity_id": entity_id, "raw": row.get("raw")})
                continue
            if entity.get("type") not in CROSS_ROLE_TYPES:
                found.append({
                    "reason": "project cross-role coverage target has invalid type",
                    "entity_id": entity_id, "type": entity.get("type"), "raw": row.get("raw"),
                })
            if not eligible_in_state(identity_index, entity_id, row.get("state")):
                found.append({
                    "reason": "project cross-role coverage target is not State-safe",
                    "entity_id": entity_id, "state": row.get("state"), "raw": row.get("raw"),
                })

    for key, entry in by_key.items():
        if uses[key] != 1:
            found.append({
                "reason": "unused or non-unique project cross-role coverage entry",
                "source": entry["source"], "state": entry["state"], "field": entry["field"],
                "record_index": entry["record_index"], "raw": entry["raw"], "uses": uses[key],
            })
    return found


def self_test() -> None:
    entries = load_overlay()
    assert entries
    assert all(entry["identity_coverage_ids"] for entry in entries)
    print(f"Schedule project cross-role identity coverage self-test: OK ({len(entries)} reviewed rows)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    entities, by_id, identity_index = schedule.load_entities()
    report = schedule.audit()
    entries = load_overlay()
    found = failures(report, entities, by_id, identity_index, entries)
    if found:
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return 1

    covered_ids = sum(len(entry["identity_coverage_ids"]) for entry in entries)
    print(
        "Schedule project cross-role identity coverage: OK "
        f"({len(entries)} reviewed project rows; {covered_ids} exact non-Project identities)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
