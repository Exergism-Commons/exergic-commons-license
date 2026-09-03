#!/usr/bin/env python3
"""Fail closed on named people hidden by passive custody prose variants.

The established State Person guards historically left auxiliary/adverb gaps across simple,
perfect, and progressive passive custody clauses. This independent companion covers the
ordinary passive auxiliary families plus a deliberately closed, bounded adverb vocabulary,
while reusing the broader closed Person name/list and bounded human-role appositive grammars.

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
import check_state_dossier_multiword_name_particle_coverage as expanded
import check_state_dossier_named_person_coverage as person
import check_state_dossier_passive_appositive_person_coverage as appositive


# Closed adverb vocabulary: enough for ordinary temporal/evidentiary/legal modifiers without
# turning arbitrary lowercase prose into part of the passive grammar. At most three modifiers
# may occur in either slot: before ``being/been`` and immediately before the custody state.
PASSIVE_ADVERB = (
    r"allegedly|arbitrarily|currently|reportedly|unlawfully|wrongfully|temporarily|briefly|"
    r"continuously|repeatedly|immediately|still|now|presently|subsequently|previously|"
    r"formally|officially|effectively|forcibly|secretly"
)
ADVERB_SEQ = rf"(?:(?i:{PASSIVE_ADVERB})\s+){{0,3}}"

# This companion now owns the ordinary simple/progressive/perfect passive families so an adverb
# cannot move the same identity bypass from one auxiliary-specific guard to another.
PASSIVE_AUX = (
    rf"(?:"
    rf"(?i:is|are|was|were)\s+(?:{ADVERB_SEQ}(?i:being)\s+)?|"
    rf"(?i:has|have|had)\s+{ADVERB_SEQ}(?i:been)\s+|"
    rf"(?i:remains|remained)\s+"
    rf")"
)
PASSIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s+{PASSIVE_AUX}{ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)
PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{PASSIVE_AUX}{ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)


def names_from_plural_present_passive(prose: str) -> list[str]:
    names: list[str] = []
    for regex in (PASSIVE_RE, PASSIVE_APPOSITIVE_RE):
        for match in regex.finditer(prose):
            for candidate in expanded.split_names(match.group("names")):
                if candidate not in names:
                    names.append(candidate)
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_plural_present_passive(prose):
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
                    "reason": "passive custody prose names an unmaterialized person",
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
    # Simple passive family, including the prior plural-present P1 and adverb insertion.
    assert names_from_plural_present_passive("Jane Doe and John Roe are detained") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe is arbitrarily detained") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe was reportedly imprisoned") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe and John Roe are currently detained") == [
        "Jane Doe", "John Roe"
    ]

    # Progressive passive: adverbs are accepted both before ``being`` and before custody state.
    assert names_from_plural_present_passive("Jane Doe and John Roe are being detained") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe is being arbitrarily detained") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe is currently being detained") == ["Jane Doe"]
    assert names_from_plural_present_passive(
        "Jane Doe is currently being arbitrarily detained"
    ) == ["Jane Doe"]
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe were reportedly being unlawfully detained"
    ) == ["Jane Doe", "John Roe"]

    # Perfect passive is covered here as defense in depth, including adverb slots.
    assert names_from_plural_present_passive("Jane Doe has been detained") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe has been arbitrarily detained") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe has reportedly been detained") == ["Jane Doe"]
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe have reportedly been arbitrarily detained"
    ) == ["Jane Doe", "John Roe"]

    # The expanded name grammar keeps common particle sequences complete.
    assert names_from_plural_present_passive(
        "Ursula von der Leyen and John le Carré are currently being detained"
    ) == ["Ursula von der Leyen", "John le Carré"]
    assert names_from_plural_present_passive(
        "Ali ibn Abi Talib and Jane Doe had reportedly been detained"
    ) == ["Ali ibn Abi Talib", "Jane Doe"]

    # Bounded role appositives compose with simple, progressive, perfect, and adverbial forms.
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe (journalists) are arbitrarily detained"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe, journalists, are currently being imprisoned"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_plural_present_passive(
        "Jane Doe, a journalist, has reportedly been arbitrarily detained"
    ) == ["Jane Doe"]

    # Closed-world/bounded controls: unknown prose and excessive modifier chains do not widen.
    assert names_from_plural_present_passive("Jane Doe is conspicuously detained") == []
    assert names_from_plural_present_passive(
        "Jane Doe is currently reportedly allegedly secretly being detained"
    ) == []

    # Active progressive prose must not be mistaken for passive identity debt.
    assert names_from_plural_present_passive("authorities are detaining Jane Doe") == []
    assert names_from_plural_present_passive("authorities were currently detaining Jane Doe") == []

    print("State dossier adverb-aware passive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PASSIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier adverb-aware passive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
