#!/usr/bin/env python3
"""Validate exact reviewed dispositions for residual Schedule identity surfaces.

The primary Schedule disposition manifests remain authoritative for actor/project/scope role
bindings. This companion overlay is deliberately narrower: it records an exact residual
identity surface that the adversarial parser found outside those role semantics, or a parser
stem inside an already-reviewed row. `covered` means that exact surface is represented by an
ID already bound on the same audited row. `deferred` means only that the identity boundary is
left explicitly open. Neither disposition creates participation, hierarchy, culpability,
control, evidence, or a governance outcome.

Every residual source has its own exact Git-blob pin. If the same source is also pinned by a
normal Schedule disposition manifest, the two independent review surfaces must agree on the
same blob exactly. Any source edit therefore invalidates both overlays until re-review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import audit_schedule_reference_coverage as schedule

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "knowledge" / "generated"
MANIFEST = GENERATED / "schedule-residual-identity-dispositions-v1.json"
PIN_MANIFEST = GENERATED / "schedule-residual-identity-source-pins-v1.json"
ALLOWED_TOP_KEYS = {"version", "date", "purpose", "semantics", "entries"}
ALLOWED_PIN_KEYS = {"version", "date", "purpose", "source_blobs"}
ALLOWED_ENTRY_KEYS = {
    "source", "state", "field", "raw", "identity_surface", "disposition", "covered_ids", "reason"
}
ALLOWED_DISPOSITIONS = {"covered", "deferred"}
PRIMARY_FIELDS = set(schedule.ACTOR_FIELDS) | set(schedule.PROJECT_FIELDS) | set(schedule.SCOPE_FIELDS)


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


def residual_source_pins() -> dict[str, str]:
    data = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))
    unexpected = sorted(set(data) - ALLOWED_PIN_KEYS)
    assert not unexpected, f"unexpected residual source-pin keys: {unexpected}"
    assert data.get("version") == 1
    assert isinstance(data.get("date"), str) and data["date"].strip()
    assert isinstance(data.get("purpose"), str) and data["purpose"].strip()
    source_blobs = data.get("source_blobs")
    assert isinstance(source_blobs, dict) and source_blobs
    result: dict[str, str] = {}
    for source, sha in source_blobs.items():
        assert isinstance(source, str) and source
        assert isinstance(sha, str) and len(sha) == 40 and all(ch in "0123456789abcdef" for ch in sha)
        result[source] = sha
    return result


def token_phrase_present(raw: str, surface: str) -> bool:
    haystack = schedule.norm(raw).split()
    needle = schedule.norm(surface).split()
    if not needle or len(needle) > len(haystack):
        return False
    width = len(needle)
    return any(haystack[index:index + width] == needle for index in range(len(haystack) - width + 1))


def entity_surface_contains(entity: dict, surface: str) -> bool:
    """True only when a current canonical name/alias structurally contains the residual surface."""
    for form in entity.get("surface_forms") or []:
        form_text = form.get("text") or form.get("normalized") or ""
        if form_text and token_phrase_present(form_text, surface):
            return True
    return False


def covered_surface_candidate_ids(row: dict, surface: str, by_id: dict[str, dict]) -> list[str]:
    """Re-derive every same-row binding whose current ABox surface represents this residual stem."""
    candidates: list[str] = []
    for entity_id in row.get("resolved_ids") or []:
        entity = by_id.get(entity_id)
        if entity is not None and entity_surface_contains(entity, surface):
            candidates.append(entity_id)
    return sorted(set(candidates))


def disposition_key(entry: dict) -> tuple[str, str, str, str, str]:
    return (
        entry["source"], entry["state"], entry["field"], entry["raw"], entry["identity_surface"]
    )


def primary_row_key(row: dict) -> tuple[str, str, str, str]:
    return (row.get("source") or "", row.get("state") or "", row.get("field") or "", row.get("raw") or "")


def entry_primary_key(entry: dict) -> tuple[str, str, str, str]:
    return (entry["source"], entry["state"], entry["field"], entry["raw"])


def current_primary_rows() -> dict[tuple[str, str, str, str], list[dict]]:
    rows: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in schedule.audit().get("references", []):
        if row.get("field") in PRIMARY_FIELDS:
            rows[primary_row_key(row)].append(row)
    return rows


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

    normal_pins = canonical_source_pins()
    pins = residual_source_pins()
    entities, by_id, identity_index = schedule.load_entities()
    del entities
    primary_rows = current_primary_rows()
    checked_sources: set[str] = set()
    used_sources: set[str] = set()
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
        assert token_phrase_present(entry["raw"], entry["identity_surface"]), (
            index, entry["identity_surface"], entry["raw"]
        )

        source = entry["source"]
        used_sources.add(source)
        assert source in pins, f"residual source lacks an exact residual source pin: {source}"
        if source in normal_pins:
            assert normal_pins[source] == pins[source], (
                f"residual/normal source pin disagreement for {source}: {pins[source]} != {normal_pins[source]}"
            )
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

        if entry["field"] in PRIMARY_FIELDS:
            matches = primary_rows.get(entry_primary_key(entry), [])
            assert len(matches) == 1, (
                f"residual disposition must match exactly one current primary Schedule row: "
                f"{entry_primary_key(entry)} -> {len(matches)} matches"
            )
            row = matches[0]
            assert row.get("resolution_source") == "reviewed-disposition", (
                f"residual overlay cannot suppress an unreviewed primary Schedule row: {entry_primary_key(entry)} "
                f"-> {row.get('resolution_source')!r}"
            )
            if entry["disposition"] == "covered":
                actual_candidates = covered_surface_candidate_ids(row, entry["identity_surface"], by_id)
                expected_candidates = sorted(entry["covered_ids"])
                assert actual_candidates, (
                    f"no same-row bound identity has a current ABox surface representing residual "
                    f"{entry['identity_surface']!r}: {entry_primary_key(entry)}"
                )
                assert actual_candidates == expected_candidates, (
                    f"residual covered IDs must equal the complete same-row surface-derived candidate set: "
                    f"{entry_primary_key(entry)} surface={entry['identity_surface']!r} "
                    f"expected={actual_candidates} declared={expected_candidates}"
                )
        else:
            assert entry["disposition"] == "deferred", (
                f"extra-context residual surfaces may only be explicitly deferred, never bound: {entry}"
            )

        key = disposition_key(entry)
        assert key not in result, f"duplicate residual disposition: {key}"
        result[key] = entry

    unused_pins = sorted(set(pins) - used_sources)
    assert not unused_pins, f"unused residual source pins: {unused_pins}"
    return result


def self_test() -> None:
    assert git_blob_sha(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    assert token_phrase_present("unrelated Operation Alpha activity", "Operation Alpha")
    assert not token_phrase_present("unrelated Operation Alphabet activity", "Operation Alpha")
    synthetic_entity = {
        "id": "PROJECT-AAA-ALPHA", "type": "Project",
        "surface_forms": [{"text": "Operation Alpha — phase one", "normalized": "operation alpha phase one"}],
    }
    unrelated_entity = {
        "id": "PROJECT-AAA-BETA", "type": "Project",
        "surface_forms": [{"text": "Operation Beta", "normalized": "operation beta"}],
    }
    assert entity_surface_contains(synthetic_entity, "Operation Alpha")
    assert not entity_surface_contains(unrelated_entity, "Operation Alpha")
    synthetic_row = {"resolved_ids": ["PROJECT-AAA-ALPHA", "PROJECT-AAA-BETA"]}
    assert covered_surface_candidate_ids(
        synthetic_row, "Operation Alpha",
        {"PROJECT-AAA-ALPHA": synthetic_entity, "PROJECT-AAA-BETA": unrelated_entity},
    ) == ["PROJECT-AAA-ALPHA"]
    assert entry_primary_key({
        "source": "x.yml", "state": "AAA", "field": "schedule_identity", "raw": "Operation Alpha"
    }) == ("x.yml", "AAA", "schedule_identity", "Operation Alpha")
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
        f"{covered} covered; {deferred} deferred; {len(residual_source_pins())} pinned sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
