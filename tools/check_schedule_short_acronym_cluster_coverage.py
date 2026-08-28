#!/usr/bin/env python3
"""Fail closed on short acronym members hidden inside slash-delimited Schedule context.

Only 2-3 character uppercase/alphanumeric tokens immediately adjacent to ``/`` are in
scope here. This deliberately narrow syntax catches identity-like members such as ``NPM``
without turning standalone statutes/codes into identity debt. Current exact State-safe
ABox identities need no overlay; otherwise each surface must have an exact blob-pinned
reviewed disposition of ``deferred`` or ``rejected``.

This guard is representational only. It never creates actor/project roles, participation,
control, operation, membership, supply, culpability, evidence, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

import audit_schedule_reference_coverage as schedule
import check_schedule_adversarial_identity_gaps as adversarial
import check_schedule_exact_identity_completeness as exact

OVERLAY = schedule.ROOT / "knowledge" / "generated" / "schedule-short-acronym-cluster-dispositions-v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHORT_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9.-])([A-Z][A-Z0-9]{1,2})(?![A-Za-z0-9.-])")
VALID_DISPOSITIONS = {"deferred", "rejected"}


def short_slash_acronyms(raw: str) -> list[str]:
    """Return distinct 2-3 char uppercase members directly adjacent to a slash."""
    labels: list[str] = []
    for match in SHORT_TOKEN_RE.finditer(raw):
        before = raw[:match.start()].rstrip()
        after = raw[match.end():].lstrip()
        if not (before.endswith("/") or after.startswith("/")):
            continue
        token = match.group(1)
        if token not in labels:
            labels.append(token)
    return labels


def overlay_key(row: dict, label: str) -> tuple[str, str, str, int, str, str]:
    return (
        row.get("source") or "",
        row.get("state") or "",
        row.get("field") or "",
        int(row.get("record_index") if row.get("record_index") is not None else -1),
        row.get("raw") or "",
        label,
    )


def load_overlay() -> list[dict]:
    data = json.loads(OVERLAY.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"unexpected short-acronym disposition version: {data.get('version')!r}")
    source_blobs = data.get("source_blobs")
    if not isinstance(source_blobs, dict) or not source_blobs:
        raise ValueError("short-acronym dispositions must pin source_blobs")

    for source, expected_sha in source_blobs.items():
        if not isinstance(source, str) or not source or not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise ValueError(f"invalid short-acronym source pin: {source!r} -> {expected_sha!r}")
        path = schedule.ROOT / source
        if not path.is_file():
            raise ValueError(f"short-acronym pinned source does not exist: {source}")
        actual_sha = schedule.git_blob_sha1(path.read_bytes())
        if actual_sha != expected_sha:
            raise ValueError(
                f"short-acronym reviewed source changed: {source}; expected blob {expected_sha}, got {actual_sha}"
            )

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("short-acronym disposition entries must be a list")

    seen: set[tuple[str, str, str, int, str, str]] = set()
    referenced_sources: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"short-acronym disposition is not an object: #{index}")
        required = {
            "source", "state", "field", "record_index", "raw",
            "identity_surface", "disposition", "reason",
        }
        missing = required - set(entry)
        if missing:
            raise ValueError(f"short-acronym disposition missing fields at #{index}: {sorted(missing)}")
        if entry["source"] not in source_blobs:
            raise ValueError(f"short-acronym disposition source is not pinned at #{index}: {entry['source']!r}")
        if entry["disposition"] not in VALID_DISPOSITIONS:
            raise ValueError(f"invalid short-acronym disposition at #{index}: {entry['disposition']!r}")
        if not isinstance(entry["state"], str) or not entry["state"]:
            raise ValueError(f"invalid short-acronym State at #{index}: {entry['state']!r}")
        if not isinstance(entry["field"], str) or not entry["field"]:
            raise ValueError(f"invalid short-acronym field at #{index}: {entry['field']!r}")
        if not isinstance(entry["record_index"], int) or entry["record_index"] < 0:
            raise ValueError(f"invalid short-acronym record_index at #{index}: {entry['record_index']!r}")
        if not isinstance(entry["raw"], str) or not entry["raw"]:
            raise ValueError(f"invalid short-acronym raw value at #{index}")
        label = entry["identity_surface"]
        if not isinstance(label, str) or not SHORT_TOKEN_RE.fullmatch(label):
            raise ValueError(f"invalid short-acronym identity_surface at #{index}: {label!r}")
        if label not in short_slash_acronyms(entry["raw"]):
            raise ValueError(f"short-acronym surface is not slash-adjacent in raw value at #{index}: {label!r}")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ValueError(f"missing short-acronym reason at #{index}")
        key = (
            entry["source"], entry["state"], entry["field"], entry["record_index"],
            entry["raw"], entry["identity_surface"],
        )
        if key in seen:
            raise ValueError(f"duplicate short-acronym disposition key: {key}")
        seen.add(key)
        referenced_sources.add(entry["source"])

    stale_pins = sorted(set(source_blobs) - referenced_sources)
    if stale_pins:
        raise ValueError(f"unused short-acronym source pins: {stale_pins}")
    return entries


def exact_materialized_ids(label: str, entities: list[dict], identity_index, state: str | None) -> list[str]:
    return sorted(set(
        exact.materialized_person_ids_for_mention(label, entities, identity_index, state)
        + exact.materialized_non_person_ids_for_mention(label, entities, identity_index, state)
    ))


def failures(report: dict, entities: list[dict], identity_index, overlay: list[dict]) -> list[dict]:
    found: list[dict] = []
    rows = list(report.get("references", [])) + adversarial.extra_context_rows()
    by_key: dict[tuple[str, str, str, int, str, str], dict] = {}
    for entry in overlay:
        key = (
            entry["source"], entry["state"], entry["field"], entry["record_index"],
            entry["raw"], entry["identity_surface"],
        )
        by_key[key] = entry

    uses: Counter = Counter()
    for row in rows:
        raw = row.get("raw") or ""
        state = row.get("state")
        for label in short_slash_acronyms(raw):
            materialized = exact_materialized_ids(label, entities, identity_index, state)
            key = overlay_key(row, label)
            entry = by_key.get(key)

            if materialized:
                if entry is not None:
                    found.append({
                        "reason": "short slash acronym now materializes exactly but still has a reviewed disposition",
                        "state": state, "kind": row.get("kind"), "field": row.get("field"),
                        "source": row.get("source"), "record_index": row.get("record_index"),
                        "raw": raw, "identity_surface": label, "materialized_ids": materialized,
                    })
                    uses[key] += 1
                continue

            if row.get("document_root"):
                found.append({
                    "reason": "identity-like short slash acronym in multi-record document-root metadata is outside State-scoped audit",
                    "state": state, "kind": row.get("kind"), "field": row.get("field"),
                    "source": row.get("source"), "record_index": row.get("record_index"),
                    "raw": raw, "identity_surface": label,
                })
                continue

            if entry is None:
                found.append({
                    "reason": "unmaterialized short slash acronym lacks exact reviewed disposition",
                    "state": state, "kind": row.get("kind"), "field": row.get("field"),
                    "source": row.get("source"), "record_index": row.get("record_index"),
                    "raw": raw, "identity_surface": label,
                })
                continue
            uses[key] += 1

    for key, entry in by_key.items():
        count = uses[key]
        if count != 1:
            found.append({
                "reason": "short-acronym reviewed disposition is stale or non-unique",
                "source": entry["source"], "state": entry["state"], "field": entry["field"],
                "record_index": entry["record_index"], "raw": entry["raw"],
                "identity_surface": entry["identity_surface"], "uses": count,
            })
    return found


def self_test() -> None:
    assert short_slash_acronyms("National Human Rights Commission/NPM") == ["NPM"]
    assert short_slash_acronyms("relevant maritime/SAR units") == ["SAR"]
    assert short_slash_acronyms("actual PTA/counterterrorism detention") == ["PTA"]
    assert short_slash_acronyms("DGM / CESFRONT") == ["DGM"]
    assert short_slash_acronyms("FARDC-backed CMC-FDP / Wazalendo") == []
    assert short_slash_acronyms("NAPOLCOM/IMIS") == []
    overlay = load_overlay()
    assert {entry["identity_surface"] for entry in overlay} == {"SAR", "PTA", "NPM", "ICT"}
    print("Schedule short slash-acronym coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, _, identity_index = schedule.load_entities()
    report = schedule.audit()
    overlay = load_overlay()
    problems = failures(report, entities, identity_index, overlay)
    if problems:
        print(json.dumps(problems, indent=2, ensure_ascii=False, sort_keys=True))
        return 1

    counts = Counter(entry["disposition"] for entry in overlay)
    print(
        "Schedule short slash-acronym coverage: OK "
        f"({len(overlay)} reviewed; {counts['deferred']} deferred; {counts['rejected']} rejected)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
