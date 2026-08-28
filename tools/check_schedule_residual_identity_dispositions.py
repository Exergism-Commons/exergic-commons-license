#!/usr/bin/env python3
"""Validate exact reviewed dispositions for residual Schedule identity surfaces.

The primary Schedule disposition manifests remain authoritative for actor/project/scope role
bindings.  This companion overlay is deliberately narrower: it records an exact residual
identity surface that the adversarial parser found outside those role semantics, or a parser
stem inside an already-reviewed row.  `covered` means that exact surface is represented by an
ID already bound on the same audited row.  `deferred` means only that the identity boundary is
left explicitly open.  Neither disposition creates participation, hierarchy, culpability,
control, evidence, or a governance outcome.

Every residual source reuses the canonical Git-blob pin from the normal Schedule disposition
manifests.  There is therefore one source-pin authority, not two independently drifting copies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import audit_schedule_reference_coverage as schedule

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "knowledge" / "generated"
MANIFEST = GENERATED / "schedule-residual-identity-dispositions-v1.json"
ALLOWED_TOP_KEYS = {"version", "date", "purpose", "semantics", "entries"}
ALLOWED_ENTRY_KEYS = {
    "source", "state", "field", "raw", "identity_surface", "disposition", "covered_ids", "reason"
}
ALLOWED_DISPOSITIONS = {"covered", "deferred"}


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_source_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for path in sorted(GENERATED.glob(schedule.DISPOSITION_GLOB)):
        data = json.loads(path.read_text(encoding="utf-8"))
        source_blobs = data.get("source_blobs")
        assert isinstance(source_blobs, dict) and source_blobs, path
        for source, sha in source_blobs.items():
            assert isinstance(source, str) and source
            assert isinstance(sha, str) and len(sha) == 40
            previous = pins.setdefault(source, sha)
            assert previous == sha, f"conflicting canonical source pins for {source}: {previous} vs {sha}"
    return pins


def disposition_key(entry: dict) -> tuple[str, str, str, str, str]:
    return (
        entry["source"], entry["state"], entry["field"], entry["raw"], entry["identity_surface"]
    )


def load_dispositions() -> dict[tuple[str, str, str, str, str], dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    unexpected_top = sorted(set(data) - ALLOWED_TOP_KEYS)
    assert not unexpected_top, f"unexpected residual-disposition manifest keys: {unexpected_top}"
    assert data.get("version") == 1
    assert isinstance(data.get("date"), str) and data["date"].strip()
    assert isinstance(data.get("purpose"), str) and data["purpose"].strip()
    semantics = data.get("semantics")
    assert isinstance(semantics, dict) and semantics, "residual overlay must state its non-inference semantics"
    entries = data.get("entries")
    assert isinstance(entries, list), "residual overlay entries must be a list"

    pins = canonical_source_pins()
    entities, by_id, identity_index = schedule.load_entities()
    del entities
    checked_sources: set[str] = set()
    result: dict[tuple[str, str, str, str, str], dict] = {}

    for index, entry in enumerate(entries):
        assert isinstance(entry, dict), (index, entry)
        unexpected = sorted(set(entry) - ALLOWED_ENTRY_KEYS)
        missing = sorted(ALLOWED_ENTRY_KEYS - set(entry))
        assert not unexpected and not missing, (index, unexpected, missing)
        for field in ("source", "state", "field", "raw", "identity_surface", "disposition", "reason"):
            assert isinstance(entry[field], str) and entry[field].strip(), (index, field, entry[field])
        assert entry["disposition"] in ALLOWED_DISPOSITIONS, (index, entry["disposition"])
        assert isinstance(entry["covered_ids"], list)
        assert all(isinstance(item, str) and item for item in entry["covered_ids"])
        assert len(entry["covered_ids"]) == len(set(entry["covered_ids"])), (index, entry["covered_ids"])
        assert schedule.norm(entry["identity_surface"]) in schedule.norm(entry["raw"]), (
            index, entry["identity_surface"], entry["raw"]
        )

        source = entry["source"]
        assert source in pins, f"residual source lacks canonical reviewed source pin: {source}"
        if source not in checked_sources:
            source_path = ROOT / source
            assert source_path.is_file(), source_path
            actual = git_blob_sha(source_path.read_bytes())
            assert actual == pins[source], f"stale residual source pin for {source}: {actual} != {pins[source]}"
            checked_sources.add(source)

        if entry["disposition"] == "covered":
            assert entry["covered_ids"], f"covered residual must name at least one ID: {entry}"
        else:
            assert entry["covered_ids"] == [], f"deferred residual cannot bind IDs: {entry}"

        for entity_id in entry["covered_ids"]:
            entity = by_id.get(entity_id)
            assert entity is not None, f"unknown residual covered ID {entity_id}"
            assert entity.get("type") != "State", f"residual coverage cannot bind a State: {entity_id}"
            assert schedule.eligible_in_state(identity_index, entity_id, entry["state"]), (
                f"cross-State residual coverage: {entry['state']} -> {entity_id}"
            )

        key = disposition_key(entry)
        assert key not in result, f"duplicate residual disposition: {key}"
        result[key] = entry
    return result


def self_test() -> None:
    assert git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    synthetic = {
        "source": "x.yml", "state": "AAA", "field": "exclusions.[0]", "raw": "Operation Alpha activity",
        "identity_surface": "Operation Alpha", "disposition": "deferred", "covered_ids": [], "reason": "identity deferred",
    }
    assert disposition_key(synthetic) == (
        "x.yml", "AAA", "exclusions.[0]", "Operation Alpha activity", "Operation Alpha"
    )
    loaded = load_dispositions()
    covered = sum(row["disposition"] == "covered" for row in loaded.values())
    deferred = sum(row["disposition"] == "deferred" for row in loaded.values())
    print(f"Schedule residual disposition self-test: OK ({covered} covered; {deferred} deferred)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    dispositions = load_dispositions()
    covered = sum(row["disposition"] == "covered" for row in dispositions.values())
    deferred = sum(row["disposition"] == "deferred" for row in dispositions.values())
    if args.self_test:
        self_test()
        return 0
    print(
        f"Schedule residual disposition integrity: OK ({len(dispositions)} entries; "
        f"{covered} covered; {deferred} deferred)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
