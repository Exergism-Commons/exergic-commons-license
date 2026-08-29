#!/usr/bin/env python3
"""Fail closed on named actors followed by parenthesized capacity prose.

The main named-identity parser recognizes ordinary actor components and reviewed comma
capacity tails. This companion guard independently covers the equally natural form
``Jane Doe (in an advisory capacity)`` including terminal punctuation, common
quote/Markdown wrappers, an optional second comma-delimited capacity condition, and
high-confidence lists whose separator follows a completed parenthesized component. It
is identity-completeness only: it never creates actor participation, control, operation,
supply, culpability, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


PAREN_COMPONENT_RE = re.compile(r"^(.+?)\s*\(([^()]*)\)(.*)$", re.UNICODE)
# `and`/`&`/comma are ambiguous inside ordinary organization names. They become strong
# separators here only *after* a closed parenthesized component and before a new
# capitalized/name-wrapped component. A lowercase second capacity tail such as
# `), only where ...` therefore remains attached to the first actor.
POST_CAPACITY_SEPARATOR_RE = re.compile(
    r"(?<=\))\s*(?:and\b|&|,|—|–)\s+(?=[A-ZÀ-ÖØ-Þ\"'“‘\[\{*_`])",
    re.UNICODE,
)
TRAILING_WRAPPERS = "\"'”’]}*_`"
TRAILING_PUNCTUATION = ".!?,:"


def normalized_component(fragment: str) -> str:
    """Remove only terminal punctuation/wrappers that cannot belong to the actor name."""
    cleaned = fragment.strip()
    # Accept either `...)”.` or `...).”`-style ordering without stripping semantic prose.
    for _ in range(2):
        cleaned = cleaned.rstrip()
        cleaned = cleaned.rstrip(TRAILING_PUNCTUATION)
        cleaned = cleaned.rstrip()
        cleaned = cleaned.rstrip(TRAILING_WRAPPERS)
    return cleaned.strip()


def actor_capacity_fragments(raw: str) -> list[str]:
    """Split only on separators that are unambiguous for this parenthesized-capacity form."""
    out: list[str] = []
    for strong in re.split(r"\s*(?:/|;)\s*", raw):
        out.extend(part for part in POST_CAPACITY_SEPARATOR_RE.split(strong) if part.strip())
    return out


def parenthesized_actor_mentions(raw: str) -> list[str]:
    """Return complete names whose trailing parentheses contain recognized capacity prose."""
    out: list[str] = []
    for fragment in actor_capacity_fragments(raw):
        match = PAREN_COMPONENT_RE.fullmatch(normalized_component(fragment))
        if not match:
            continue
        if not strict.CAPACITY_TAIL_RE.match(match.group(2).strip()):
            continue

        suffix = match.group(3).strip()
        # Quotes/Markdown/brackets may close the actor component immediately after `)`.
        suffix = suffix.lstrip(TRAILING_WRAPPERS).strip()
        if suffix:
            # A second tail is allowed only through the same closed-world capacity grammar.
            if not suffix.startswith(","):
                continue
            second_tail = suffix[1:].strip()
            if not second_tail or not strict.CAPACITY_TAIL_RE.match(second_tail):
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
        'Human Rights Watch / “Jane Doe (in an advisory capacity)”.'
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / **Jane Doe (in an advisory capacity)**"
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / [Jane Doe (in an advisory capacity)]"
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (in an advisory capacity), only where participation is established"
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        'Human Rights Watch / “Jane Doe (in an advisory capacity)”, acting only where participation is established'
    ) == ["Jane Doe"]
    assert parenthesized_actor_mentions(
        "Jane Doe (in an advisory capacity) and John Smith (serving only where participation is established)"
    ) == ["Jane Doe", "John Smith"]
    assert parenthesized_actor_mentions(
        "Jane Doe (in an advisory capacity), John Smith (serving only where participation is established)"
    ) == ["Jane Doe", "John Smith"]
    assert parenthesized_actor_mentions(
        "Jane Doe (in an advisory capacity) — John Smith (serving only where participation is established)"
    ) == ["Jane Doe", "John Smith"]
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (unreviewed arbitrary prose)"
    ) == []
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (case note)."
    ) == []
    assert parenthesized_actor_mentions(
        "Human Rights Watch / Jane Doe (in an advisory capacity), unrelated prose"
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
