#!/usr/bin/env python3
"""Fail closed when a high-confidence State-dossier person list exceeds the primary bound.

The primary named-person checker deliberately uses a bounded NAME_LIST regex. This companion
checks the exact continuation immediately after that bounded match and reports any additional
complete name-shaped members that would otherwise fall outside the primary capture. The guard
therefore remains effective for arbitrarily long custody/legal/role-led lists without changing
that parser's established matching behavior.

Identity coverage is neutral: named people are materialized as identities only; this checker
never infers culpability, participation, control, operation, supply, membership, or governance.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_private_org_mentions as rendered
import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_state_dossier_named_person_coverage as named


CONTINUATION_RE = re.compile(
    rf"^(?P<separator>{named.NAME_SEPARATOR})(?P<name>{named.NAME_PHRASE})"
)
BOUNDED_LIST_RE = re.compile(rf"(?P<names>{named.NAME_LIST})")


def continuation_names(remainder: str) -> list[str]:
    """Return every complete name member continuing a bounded NAME_LIST match."""
    out: list[str] = []
    tail = remainder
    while True:
        match = CONTINUATION_RE.match(tail)
        if match is None:
            break
        value = named.clean_candidate(match.group("name"))
        if value and value not in out:
            out.append(value)
        tail = tail[match.end():]
    return out


def overflow_names(prose: str) -> list[str]:
    """Find person-list members hidden beyond the primary NAME_LIST capture ceiling."""
    found: list[str] = []

    def add_from_remainder(remainder: str) -> None:
        for value in continuation_names(remainder):
            if value not in found:
                found.append(value)

    # These regexes already establish the high-confidence custody/action context and expose
    # the bounded names group. Inspect immediately after that group, not after the whole match
    # (PASSIVE_ACTION_RE continues into the custody-state verb).
    for regex in (named.PASSIVE_ACTION_RE, named.ACTIVE_ACTION_RE):
        for match in regex.finditer(prose):
            add_from_remainder(prose[match.end("names"):])

    # Role-led and legal/remedial cue paths parse NAME_LIST from the cue tail separately in the
    # primary checker. Reproduce only that bounded-list boundary, then inspect its continuation.
    for prefix_re in (
        named.ROLE_RE,
        named.ACTION_OF_RE,
        named.ACTION_TARGET_RE,
        named.CASE_OF_RE,
        named.REMEDIAL_TARGET_RE,
    ):
        for prefix in prefix_re.finditer(prose):
            tail = prose[prefix.end():].lstrip()
            if re.match(r"(?i)^(?:of\b|the\b)", tail):
                continue
            match = BOUNDED_LIST_RE.match(tail)
            if match is None:
                continue
            remainder = tail[match.end("names"):]
            if re.match(r"(?i)^\s*Law\b", remainder):
                continue
            add_from_remainder(remainder)

    return found


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in overflow_names(prose):
            if exact.materialized_person_ids_for_mention(name, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(name, entities, identity_index, state):
                continue
            normalized = schedule.norm(name)
            key = (state, normalized)
            row = failures_by_key.setdefault(key, {
                "state": state,
                "name": name,
                "normalized": normalized,
                "reason": "named person appears beyond bounded person-list capture and lacks neutral ABox identity",
                "occurrences": [],
            })
            row["occurrences"].append({
                "source": source,
                "location": location,
                "snippet": snippet[:420],
            })

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))

        for field in named.FRONTMATTER_PERSON_KEYS:
            value = front.get(field)
            if isinstance(value, str) and value.strip():
                inspect(
                    state=state,
                    source=source,
                    location=f"frontmatter:{field}",
                    prose=named.frontmatter_visible_prose(value),
                    snippet=value,
                )

        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        for rel_line, snippet, prose in rendered.rendered_prose_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    five = "authorities detained Jane Doe, John Roe, Mary Major, Alice Brown, Carlos Green"
    assert overflow_names(five) == [], overflow_names(five)

    six = five + ", Sarah White after the protest"
    assert overflow_names(six) == ["Sarah White"], overflow_names(six)

    eight = five + ", Sarah White, Peter Black, Laura Gold after the protest"
    assert overflow_names(eight) == ["Sarah White", "Peter Black", "Laura Gold"], overflow_names(eight)

    passive = "Jane Doe, John Roe, Mary Major, Alice Brown, Carlos Green, Sarah White were detained"
    assert overflow_names(passive) == ["Sarah White"], overflow_names(passive)

    role_led = "journalists Jane Doe, John Roe, Mary Major, Alice Brown, Carlos Green, Sarah White reported the detention"
    assert overflow_names(role_led) == ["Sarah White"], overflow_names(role_led)

    alternative = "authorities detained Jane Doe, John Roe, Mary Major, Alice Brown, Carlos Green or Sarah White"
    assert overflow_names(alternative) == ["Sarah White"], overflow_names(alternative)

    print("State dossier person-list overflow coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PERSON_LIST_OVERFLOW=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier person-list overflow completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
