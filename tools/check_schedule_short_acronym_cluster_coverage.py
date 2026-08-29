#!/usr/bin/env python3
"""Fail closed on acronym members hidden inside slash-delimited Schedule context.

This guard is activated either by a 2-3 character uppercase/alphanumeric member adjacent to
``/`` or by an all-long acronym cluster whose member is hidden behind balanced punctuation
wrappers. Once activated, every connected uppercase/alphanumeric acronym-sized member in that
cluster is audited. This catches mixed clusters such as ``NPM/IMIS`` and wrapped all-long
clusters such as ``NAPOLCOM/(IMIS)`` without duplicating ordinary unwrapped all-long cluster
coverage already provided by the adversarial residual-identity guard. Balanced punctuation
wrappers around cluster members are ignored for slash adjacency, while alphanumeric/hyphen
compound boundaries remain excluded.

Current exact State-safe ABox identities need no overlay; otherwise each emitted surface must
have an exact blob-pinned reviewed disposition of ``deferred`` or ``rejected``. Multi-record
document-root metadata is always rejected before materialization is considered because it has
no State scope.

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
ACRONYM_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{1,})(?![A-Za-z0-9-])")
VALID_DISPOSITIONS = {"deferred", "rejected"}
WRAPPER_PAIRS = {
    "(": ")",
    "[": "]",
    "{": "}",
    '"': '"',
    "'": "'",
    "“": "”",
    "‘": "’",
}


def _wrapped_span(raw: str, start: int, end: int) -> tuple[int, int]:
    """Expand an acronym token across immediately balanced punctuation wrappers."""
    while True:
        left = start
        while left > 0 and raw[left - 1].isspace():
            left -= 1
        right = end
        while right < len(raw) and raw[right].isspace():
            right += 1
        if left <= 0 or right >= len(raw):
            return start, end
        opening = raw[left - 1]
        closing = raw[right]
        if WRAPPER_PAIRS.get(opening) != closing:
            return start, end
        start, end = left - 1, right + 1


def slash_cluster_acronyms(raw: str) -> list[str]:
    """Return acronym members from short-activated or wrapper-hidden slash clusters.

    Every eligible token must be a complete uppercase/alphanumeric surface, not a fragment of
    an alphanumeric or hyphenated compound. A slash can be separated from a token by whitespace
    and balanced wrappers such as ``(NPM)``, ``[AB]`` or ``“IMIS”``.

    Ordinary all-long unwrapped clusters remain out of scope here so the adversarial residual
    checker remains their single owner. An all-long component is activated here only when it
    contains at least two connected acronym members and at least one member is actually wrapped.
    """
    candidates: list[dict] = []
    for match in ACRONYM_TOKEN_RE.finditer(raw):
        wrapped_start, wrapped_end = _wrapped_span(raw, match.start(), match.end())
        candidates.append({
            "token": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "wrapped_start": wrapped_start,
            "wrapped_end": wrapped_end,
        })
    if not candidates:
        return []

    graph: dict[int, set[int]] = {index: set() for index in range(len(candidates))}
    touched: set[int] = set()

    for slash_index, char in enumerate(raw):
        if char != "/":
            continue
        left_candidates = [
            index for index, candidate in enumerate(candidates)
            if candidate["wrapped_end"] <= slash_index
            and not raw[candidate["wrapped_end"]:slash_index].strip()
        ]
        right_candidates = [
            index for index, candidate in enumerate(candidates)
            if candidate["wrapped_start"] > slash_index
            and not raw[slash_index + 1:candidate["wrapped_start"]].strip()
        ]
        left = max(left_candidates, key=lambda index: candidates[index]["wrapped_end"], default=None)
        right = min(right_candidates, key=lambda index: candidates[index]["wrapped_start"], default=None)
        if left is not None:
            touched.add(left)
        if right is not None:
            touched.add(right)
        if left is not None and right is not None:
            graph[left].add(right)
            graph[right].add(left)

    active: set[int] = set()
    visited: set[int] = set()
    for index in sorted(touched):
        if index in visited:
            continue
        stack = [index]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            visited.add(current)
            stack.extend(graph[current] - component)

        has_short_member = any(2 <= len(candidates[item]["token"]) <= 3 for item in component)
        has_wrapped_member = any(
            candidates[item]["wrapped_start"] != candidates[item]["start"]
            or candidates[item]["wrapped_end"] != candidates[item]["end"]
            for item in component
        )
        wrapped_all_long_cluster = (
            len(component) >= 2
            and all(len(candidates[item]["token"]) >= 4 for item in component)
            and has_wrapped_member
        )
        if has_short_member or wrapped_all_long_cluster:
            active.update(component)

    labels: list[str] = []
    for index, candidate in enumerate(candidates):
        token = candidate["token"]
        if index in active and token not in labels:
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
        if not isinstance(label, str) or not ACRONYM_TOKEN_RE.fullmatch(label):
            raise ValueError(f"invalid slash-acronym identity_surface at #{index}: {label!r}")
        if label not in slash_cluster_acronyms(entry["raw"]):
            raise ValueError(f"slash-acronym surface is not in an audited slash cluster at #{index}: {label!r}")
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
        for label in slash_cluster_acronyms(raw):
            key = overlay_key(row, label)
            entry = by_key.get(key)

            if row.get("document_root"):
                found.append({
                    "reason": "identity-like slash acronym in multi-record document-root metadata is outside State-scoped audit",
                    "state": state, "kind": row.get("kind"), "field": row.get("field"),
                    "source": row.get("source"), "record_index": row.get("record_index"),
                    "raw": raw, "identity_surface": label,
                })
                continue

            materialized = exact_materialized_ids(label, entities, identity_index, state)
            if materialized:
                if entry is not None:
                    found.append({
                        "reason": "slash acronym now materializes exactly but still has a reviewed disposition",
                        "state": state, "kind": row.get("kind"), "field": row.get("field"),
                        "source": row.get("source"), "record_index": row.get("record_index"),
                        "raw": raw, "identity_surface": label, "materialized_ids": materialized,
                    })
                    uses[key] += 1
                continue

            if entry is None:
                found.append({
                    "reason": "unmaterialized slash acronym in audited cluster lacks exact reviewed disposition",
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
                "reason": "slash-acronym reviewed disposition is stale or non-unique",
                "source": entry["source"], "state": entry["state"], "field": entry["field"],
                "record_index": entry["record_index"], "raw": entry["raw"],
                "identity_surface": entry["identity_surface"], "uses": count,
            })
    return found


def self_test() -> None:
    assert slash_cluster_acronyms("National Human Rights Commission/NPM") == ["NPM"]
    assert slash_cluster_acronyms("National Human Rights Commission/NPM.") == ["NPM"]
    assert slash_cluster_acronyms("National Human Rights Commission/(NPM)") == ["NPM"]
    assert slash_cluster_acronyms("relevant maritime/SAR units") == ["SAR"]
    assert slash_cluster_acronyms("actual PTA/counterterrorism detention") == ["PTA"]
    assert slash_cluster_acronyms("NCHR/AB.") == ["NCHR", "AB"]
    assert slash_cluster_acronyms("NCHR/[AB]") == ["NCHR", "AB"]
    assert slash_cluster_acronyms("NCHR/“AB”") == ["NCHR", "AB"]
    assert slash_cluster_acronyms("NPM/IMIS") == ["NPM", "IMIS"]
    assert slash_cluster_acronyms("M23/SEMAR") == ["M23", "SEMAR"]
    assert slash_cluster_acronyms("M23/oversight") == ["M23"]
    assert slash_cluster_acronyms("DGM / CESFRONT") == ["DGM", "CESFRONT"]
    assert slash_cluster_acronyms("FARDC-backed CMC-FDP / Wazalendo") == []
    assert slash_cluster_acronyms("NPM-X/oversight") == []
    # Ordinary all-long clusters remain owned by the adversarial residual checker.
    assert slash_cluster_acronyms("NAPOLCOM/IMIS") == []
    # Wrapper-hidden all-long clusters are owned here because the ordinary residual regex
    # cannot see across the wrapper between slash and acronym.
    assert slash_cluster_acronyms("NAPOLCOM/(IMIS)") == ["NAPOLCOM", "IMIS"]
    assert slash_cluster_acronyms("NAPOLCOM/[IMIS]") == ["NAPOLCOM", "IMIS"]
    assert slash_cluster_acronyms("NAPOLCOM/“IMIS”") == ["NAPOLCOM", "IMIS"]
    assert slash_cluster_acronyms("(NAPOLCOM)/IMIS") == ["NAPOLCOM", "IMIS"]
    # A single wrapped long token next to lowercase prose is not promoted into cluster debt.
    assert slash_cluster_acronyms("(IMIS)/oversight") == []
    overlay = load_overlay()
    assert {entry["identity_surface"] for entry in overlay} == {"SAR", "PTA", "NPM", "ICT"}
    print("Schedule slash-acronym cluster coverage self-test: OK")


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
        "Schedule slash-acronym cluster coverage: OK "
        f"({len(overlay)} reviewed; {counts['deferred']} deferred; {counts['rejected']} rejected)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
