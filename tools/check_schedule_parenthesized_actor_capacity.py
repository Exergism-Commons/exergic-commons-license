#!/usr/bin/env python3
"""Fail closed on named actors followed by parenthesized capacity prose.

The main named-identity parser recognizes ordinary actor components and reviewed comma
capacity tails. This companion guard independently covers the equally natural form
``Jane Doe (in an advisory capacity)`` including terminal sentence punctuation. It is
identity-completeness only: it never creates actor participation, control, operation,
supply, culpability, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


PAREN_COMPONENT_RE = re.compile(r"^(.+?)\s*\(([^()]*)\)\s*[.!?,:]?\s*$", re.UNICODE)


def parenthesized_actor_mentions(raw: str) -> list[str]:
    """Return complete names whose trailing parentheses contain recognized capacity prose."""
    out: list[str] = []
    for fragment in re.split(r"\s*(?:/|;)\s*", raw):
        match = PAREN_COMPONENT_RE.fullmatch(fragment.strip())
        if not match:
            continue
        if not strict.CAPACITY_TAIL_RE.match(match.group(2).strip()):
            continue
        mention = strict.full_name_phrase(match.group(1).strip(), allow_all_caps=True)
        if mention and mention not in out:
            out.append(mention)
    return out


def failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        for mention in parenthesized_actor_mentions(raw):
            if exact.materialized_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if strict.explicitly_defers_complete_name(row, mention):
                continue
            found.append({
                "reason": "parenthesized-capacity actor lacks exact materialization or explicit complete-name deferral",
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
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (in an advisory capacity)"
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / JANE DOE (acting only where participation is established)."
    ) == ["JANE DOE"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (serving in an advisory capacity)!"
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (unreviewed arbitrary prose)"
    ) == []
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (case note)."
    ) == []
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe-Smith (in an advisory capacity),"
    ) == ["Jane Doe-Smith"]
    print("Schedule parenthesized actor-capacity self-test: OK")


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
    print("Schedule parenthesized actor-capacity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
