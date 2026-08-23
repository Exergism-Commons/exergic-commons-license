#!/usr/bin/env python3
"""Validate versioned Schedule-reference review manifests independently of matching logic."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import audit_schedule_reference_coverage as schedule

ROOT = schedule.ROOT
GENERATED = ROOT / "knowledge" / "generated"
MANIFEST_RE = re.compile(r"^schedule-reference-dispositions-v([1-9][0-9]*)\.json$")
STATE_RE = re.compile(r"^[A-Z]{3}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VALID_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS)
VALID_DISPOSITIONS = {"bound", "deferred", "partial-deferred"}
REQUIRED_ENTRY_FIELDS = {"source", "state", "field", "match_prefix", "disposition", "resolved_ids", "reason"}


def manifests() -> list[tuple[int, Path]]:
    result: list[tuple[int, Path]] = []
    for path in GENERATED.glob("schedule-reference-dispositions-v*.json"):
        match = MANIFEST_RE.fullmatch(path.name)
        if not match:
            raise ValueError(f"malformed Schedule disposition manifest filename: {path.name}")
        result.append((int(match.group(1)), path))
    result.sort()
    if not result:
        raise ValueError("no Schedule disposition manifests")
    versions = [version for version, _ in result]
    if versions != list(range(1, versions[-1] + 1)):
        raise ValueError(f"non-contiguous Schedule disposition versions: {versions}")
    return result


def validate() -> dict[str, int]:
    files = manifests()
    previous: Path | None = None
    entry_keys: set[tuple[str, str, str, str]] = set()
    source_pins: dict[str, str] = {}
    entry_count = 0

    for version, path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != version:
            raise ValueError(
                f"Schedule disposition version/file mismatch: {path.relative_to(ROOT)} -> {data.get('version')!r}"
            )
        if previous is None:
            if data.get("follows"):
                raise ValueError(f"v1 Schedule dispositions must not follow another manifest: {path.relative_to(ROOT)}")
        else:
            expected = str(previous.relative_to(ROOT))
            if data.get("follows") != expected:
                raise ValueError(
                    f"broken Schedule disposition follows chain at {path.relative_to(ROOT)}: "
                    f"expected {expected!r}, got {data.get('follows')!r}"
                )

        source_blobs = data.get("source_blobs")
        if not isinstance(source_blobs, dict) or not source_blobs:
            raise ValueError(f"Schedule disposition manifest must pin source_blobs: {path.relative_to(ROOT)}")
        for source, sha in source_blobs.items():
            if not isinstance(source, str) or not source:
                raise ValueError(f"invalid source path in {path.relative_to(ROOT)}: {source!r}")
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                raise ValueError(f"invalid source blob SHA in {path.relative_to(ROOT)}: {source!r} -> {sha!r}")
            prior = source_pins.get(source)
            if prior is not None and prior != sha:
                raise ValueError(f"conflicting Schedule source pins for {source}: {prior} vs {sha}")
            source_pins[source] = sha

        entries = data.get("entries")
        if not isinstance(entries, list):
            raise ValueError(f"Schedule disposition entries must be a list: {path.relative_to(ROOT)}")
        for index, row in enumerate(entries):
            if not isinstance(row, dict):
                raise ValueError(f"Schedule disposition row is not an object: {path.relative_to(ROOT)}#{index}")
            missing = REQUIRED_ENTRY_FIELDS - set(row)
            if missing:
                raise ValueError(f"missing Schedule disposition fields at {path.relative_to(ROOT)}#{index}: {sorted(missing)}")
            source = row["source"]
            state = row["state"]
            field = row["field"]
            prefix = row["match_prefix"]
            disposition = row["disposition"]
            resolved_ids = row["resolved_ids"]
            reason = row["reason"]
            if not isinstance(source, str) or source not in source_blobs:
                raise ValueError(f"un-pinned Schedule disposition source at {path.relative_to(ROOT)}#{index}: {source!r}")
            if not isinstance(state, str) or not STATE_RE.fullmatch(state):
                raise ValueError(f"invalid Schedule disposition State at {path.relative_to(ROOT)}#{index}: {state!r}")
            if field not in VALID_FIELDS:
                raise ValueError(f"invalid Schedule disposition field at {path.relative_to(ROOT)}#{index}: {field!r}")
            if not isinstance(prefix, str) or not prefix.strip() or prefix != prefix.strip():
                raise ValueError(f"invalid Schedule disposition match_prefix at {path.relative_to(ROOT)}#{index}: {prefix!r}")
            if disposition not in VALID_DISPOSITIONS:
                raise ValueError(f"invalid Schedule disposition at {path.relative_to(ROOT)}#{index}: {disposition!r}")
            if not isinstance(resolved_ids, list) or not all(isinstance(item, str) and item for item in resolved_ids):
                raise ValueError(f"resolved_ids must be a string list at {path.relative_to(ROOT)}#{index}")
            if len(resolved_ids) != len(set(resolved_ids)):
                raise ValueError(f"duplicate resolved_ids at {path.relative_to(ROOT)}#{index}: {resolved_ids}")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"missing Schedule disposition reason at {path.relative_to(ROOT)}#{index}")
            if disposition == "bound" and not resolved_ids:
                raise ValueError(f"bound Schedule disposition needs a target at {path.relative_to(ROOT)}#{index}")
            if disposition == "deferred" and resolved_ids:
                raise ValueError(f"deferred Schedule disposition cannot contain targets at {path.relative_to(ROOT)}#{index}")
            if disposition == "partial-deferred" and not resolved_ids:
                raise ValueError(f"partial-deferred Schedule disposition needs an exact target at {path.relative_to(ROOT)}#{index}")

            key = (source, state, field, prefix)
            if key in entry_keys:
                raise ValueError(f"duplicate Schedule disposition key: {key}")
            entry_keys.add(key)
            entry_count += 1
        previous = path

    return {"manifests": len(files), "entries": entry_count, "pinned_sources": len(source_pins)}


def self_test() -> None:
    assert MANIFEST_RE.fullmatch("schedule-reference-dispositions-v1.json")
    assert not MANIFEST_RE.fullmatch("schedule-reference-dispositions-v01.json")
    assert "candidate_parties" in VALID_FIELDS
    assert "candidate_projects" in VALID_FIELDS
    print("Schedule disposition manifest integrity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = validate()
    print("Schedule disposition manifest integrity: " + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
