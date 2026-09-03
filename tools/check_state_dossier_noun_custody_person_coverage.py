#!/usr/bin/env python3
"""Fail closed on Person mentions in noun-form custody predicates.

The established passive Person grammar covers participial/adjectival states such as ``detained``
and a separate guard covers ``held in custody|detention``. This independent companion owns the
ordinary noun predicates ``in custody`` and ``in detention`` after the already reviewed passive
auxiliary family, including ``remains in detention`` and modal/perfect variants.

Identity coverage is neutral and creates no attribution, participation, culpability, control,
operation, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_state_dossier_fence_mononym_person_coverage as strong
import check_state_dossier_named_person_coverage as person
import check_state_dossier_passive_appositive_person_coverage as appositive
import check_state_dossier_plural_present_passive_person_coverage as passive
import check_state_dossier_unicode_held_person_coverage as unicode_guard


NOUN_CUSTODY_PREDICATE = r"(?i:in\s+(?:custody|detention))"

CASED_RE = re.compile(
    rf"\b(?P<names>{strong.STRONG_CASED_NAME_LIST})\s+"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{NOUN_CUSTODY_PREDICATE}\b"
)
CASED_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{strong.STRONG_CASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{NOUN_CUSTODY_PREDICATE}\b"
)
UNCASED_RE = re.compile(
    rf"\b(?P<names>{unicode_guard.UNCASED_NAME_LIST})\s+"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{NOUN_CUSTODY_PREDICATE}\b"
)
UNCASED_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{unicode_guard.UNCASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{NOUN_CUSTODY_PREDICATE}\b"
)


def noun_custody_names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            if value not in names:
                names.append(value)

    for regex in (CASED_RE, CASED_APPOSITIVE_RE):
        for match in regex.finditer(prose):
            add_many(strong.split_strong_cased_names(match.group("names")))
    for regex in (UNCASED_RE, UNCASED_APPOSITIVE_RE):
        for match in regex.finditer(prose):
            add_many(unicode_guard.split_uncased_names(match.group("names")))
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in noun_custody_names_from_prose(prose):
            if exact.materialized_person_ids_for_mention(name, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(name, entities, identity_index, state):
                continue
            key = (state, schedule.norm(name))
            row = failures_by_key.setdefault(
                key,
                {
                    "state": state,
                    "name": name,
                    "normalized": schedule.norm(name),
                    "reason": "noun-form custody predicate names an unmaterialized person",
                    "occurrences": [],
                },
            )
            row["occurrences"].append(
                {"source": source, "location": location, "snippet": snippet[:420]}
            )

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))

        for field in person.FRONTMATTER_PERSON_KEYS:
            value = front.get(field)
            if isinstance(value, str) and value.strip():
                inspect(
                    state=state,
                    source=source,
                    location=f"frontmatter:{field}",
                    prose=person.frontmatter_visible_prose(value),
                    snippet=value,
                )

        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        for rel_line, snippet, prose in strong.fence_safe_person_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    # Exact reported noun-form custody predicates.
    assert noun_custody_names_from_prose("Jane Doe remains in detention") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe remains in custody") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe and John Roe remain in detention") == [
        "Jane Doe", "John Roe"
    ]

    # The same narrow predicate composes with the reviewed passive auxiliary/adverb grammar.
    assert noun_custody_names_from_prose("Jane Doe is in custody") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe was reportedly in detention") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe has been in custody") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe may be in detention") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Jane Doe may not be in custody") == ["Jane Doe"]

    # Bounded appositives, cased mononyms and Unicode/uncased names remain covered.
    assert noun_custody_names_from_prose("Jane Doe, a journalist, remains in detention") == ["Jane Doe"]
    assert noun_custody_names_from_prose("Banksy remains in custody") == ["Banksy"]
    assert noun_custody_names_from_prose("Łukasz Żak remains in detention") == ["Łukasz Żak"]
    assert noun_custody_names_from_prose("أحمد منصور remains in custody") == ["أحمد منصور"]
    assert noun_custody_names_from_prose("王小明 remains in detention") == ["王小明"]

    # Precision controls: no generic ``in ...`` state and no active possession/event sense.
    assert noun_custody_names_from_prose("Jane Doe remains in office") == []
    assert noun_custody_names_from_prose("Jane Doe remains in court") == []
    assert noun_custody_names_from_prose("Jane Doe held a meeting in detention") == []
    print("State dossier noun-form custody Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_NOUN_CUSTODY_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier noun-form custody Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
