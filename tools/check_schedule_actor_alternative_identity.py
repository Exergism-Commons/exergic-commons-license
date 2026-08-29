#!/usr/bin/env python3
"""Fail closed on named actors hidden behind `or` / `and-or` alternatives.

Alternative separators are ambiguous inside organization names, so this guard only splits
outside exact current non-Person actor spans, mirroring the anchored-list protection used by
the strict checker. It is identity-completeness only and creates no role, participation,
culpability, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_schedule_parenthesized_actor_capacity as parenthesized

ALT_SEPARATOR_RE = re.compile(r"\s+(?:and\s*/\s*or|and-or|and/or|or)\s+", re.I)


def alternative_actor_mentions(raw: str, entities: list[dict], identity_index, state: str | None) -> list[str]:
    anchor_spans = strict.exact_non_person_actor_spans(raw, entities, identity_index, state)
    if not anchor_spans:
        return []

    separators: list[tuple[int, int]] = []
    for match in ALT_SEPARATOR_RE.finditer(raw):
        if strict._inside_span(match.start(), anchor_spans):
            continue
        separators.append(match.span())
    if not separators:
        return []

    segments: list[tuple[int, int, str]] = []
    start = 0
    for sep_start, sep_end in separators:
        segments.append((start, sep_start, raw[start:sep_start]))
        start = sep_end
    segments.append((start, len(raw), raw[start:]))

    anchored_segments = {
        index
        for index, (seg_start, seg_end, _) in enumerate(segments)
        if any(seg_start <= anchor_start and anchor_end <= seg_end for anchor_start, anchor_end in anchor_spans)
    }
    if not anchored_segments:
        return []

    out: list[str] = []
    for index, (_, _, segment) in enumerate(segments):
        if index in anchored_segments:
            continue
        normalized = parenthesized.normalized_component(segment)
        candidate = strict.actor_component_name(normalized)
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        for mention in alternative_actor_mentions(raw, entities, identity_index, state):
            if exact.materialized_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if strict.explicitly_defers_complete_name(row, mention):
                continue
            found.append({
                "reason": "or-delimited actor alternative lacks exact materialization or explicit complete-name deferral",
                "state": state,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "name": mention,
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def self_test() -> None:
    entities, _, identity_index = schedule.load_entities()
    state = None
    assert alternative_actor_mentions("Human Rights Watch or Jane Doe", entities, identity_index, state) == ["Jane Doe"]
    assert alternative_actor_mentions("Human Rights Watch and/or Jane Doe", entities, identity_index, state) == ["Jane Doe"]
    assert alternative_actor_mentions("Human Rights Watch and-or Jane Doe.", entities, identity_index, state) == ["Jane Doe"]
    assert alternative_actor_mentions("Human Rights Watch or Jane Doe (in an advisory capacity).", entities, identity_index, state) == ["Jane Doe"]
    # An alternative word inside the exact organization span must never split that organization.
    assert alternative_actor_mentions("Human Rights Watch", entities, identity_index, state) == []
    print("Schedule actor-alternative identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, _, identity_index = schedule.load_entities()
    problems = failures(schedule.audit(), entities, identity_index)
    if problems:
        print(json.dumps(problems, indent=2, ensure_ascii=False, sort_keys=True))
        return 1
    print("Schedule actor-alternative identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
