#!/usr/bin/env python3
"""Fail closed on named people hidden by bounded appositives before passive custody verbs.

The primary State named-person grammar recognizes ``Jane Doe was detained``. A common bounded
appositive such as ``Jane Doe (a journalist) was detained`` or ``Jane Doe, a journalist, was
detained`` used to break that adjacency and hide an otherwise high-confidence Person mention.

This independent companion reuses the reviewed name-list and human-role vocabularies, accepts
only a tightly bounded human-role appositive, and applies the same neutral materialization rules
as the primary named-person audit. It creates no culpability, participation, attribution, or
governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_state_dossier_named_person_coverage as person


ROLE_APPOSITIVE = "|".join(
    sorted(
        (re.escape(role) for role in (*person.SINGULAR_ROLES, *person.PLURAL_ROLES)),
        key=len,
        reverse=True,
    )
)
APPOSITIVE = (
    rf"(?:"
    rf"\(\s*(?:(?i:a|an|the)\s+)?(?i:{ROLE_APPOSITIVE})\s*\)"
    rf"|"
    rf",\s*(?:(?i:a|an|the)\s+)?(?i:{ROLE_APPOSITIVE})\s*,"
    rf")"
)
PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{person.NAME_LIST})\s*{APPOSITIVE}\s*"
    rf"(?i:was|were|is|remains|remain|remained)\s+(?i:{person.CUSTODY_STATE})\b"
)


def names_from_passive_appositive(prose: str) -> list[str]:
    names: list[str] = []
    for match in PASSIVE_APPOSITIVE_RE.finditer(prose):
        for candidate in person.split_name_list(match.group("names")):
            person.add_name(names, candidate)
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_passive_appositive(prose):
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
                    "reason": "passive-custody appositive names an unmaterialized person",
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
        for rel_line, snippet, prose in person.person_rendered_prose_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    parenthetical = names_from_passive_appositive("Jane Doe (a journalist) was detained")
    assert parenthetical == ["Jane Doe"], parenthetical

    comma = names_from_passive_appositive("Jane Doe, a journalist, was detained")
    assert comma == ["Jane Doe"], comma

    plural = names_from_passive_appositive(
        "Jane Doe and John Roe (journalists) were imprisoned"
    )
    assert plural == ["Jane Doe", "John Roe"], plural

    title = names_from_passive_appositive("Jane Doe, the opposition leader, remains detained")
    assert title == ["Jane Doe"], title

    # Arbitrary parenthetical prose is not discarded as an appositive.
    arbitrary = names_from_passive_appositive("Jane Doe (according to reports) was detained")
    assert arbitrary == [], arbitrary

    # Non-person title surfaces remain filtered by the shared person candidate guard.
    non_person = names_from_passive_appositive("Project Aurora (a journalist) was detained")
    assert non_person == [], non_person

    print("State dossier passive-appositive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PASSIVE_APPOSITIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier passive-appositive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
