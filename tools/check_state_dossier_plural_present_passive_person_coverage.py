#!/usr/bin/env python3
"""Fail closed on named people hidden by plural-present or progressive passive custody prose.

The established simple-passive, appositive, expanded-particle, and perfect-passive Person
guards historically leave gaps around ``are`` and the progressive passive family
``is/are/was/were being``. This independent companion covers those constructions without
trusting the auxiliary lists that caused the bypass, while reusing the broader closed Person
name/list and bounded human-role appositive grammars.

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


# Keep direct plural-present ``are`` for the prior P1, and cover the complete ordinary
# progressive-passive family so the fix does not merely move the bypass between number/tense.
PASSIVE_AUX = r"(?i:is\s+being|are\s+being|was\s+being|were\s+being|are)"
PLURAL_PRESENT_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s+{PASSIVE_AUX}\s+(?i:{person.CUSTODY_STATE})\b"
)
PLURAL_PRESENT_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{PASSIVE_AUX}\s+(?i:{person.CUSTODY_STATE})\b"
)


def names_from_plural_present_passive(prose: str) -> list[str]:
    names: list[str] = []
    for regex in (PLURAL_PRESENT_PASSIVE_RE, PLURAL_PRESENT_PASSIVE_APPOSITIVE_RE):
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
                    "reason": (
                        "plural-present/progressive passive custody prose names an "
                        "unmaterialized person"
                    ),
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
    # Prior direct plural-present P1 remains closed.
    assert names_from_plural_present_passive("Jane Doe and John Roe are detained") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe and John Roe are imprisoned") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe and John Roe are incommunicado") == [
        "Jane Doe", "John Roe"
    ]

    # Current Codex P1 plus the complete ordinary progressive-passive tense/number family.
    assert names_from_plural_present_passive("Jane Doe and John Roe are being detained") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe is being detained") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe was being imprisoned") == ["Jane Doe"]
    assert names_from_plural_present_passive("Jane Doe and John Roe were being detained") == [
        "Jane Doe", "John Roe"
    ]

    # The guard uses the expanded name grammar, so common particle sequences remain complete.
    assert names_from_plural_present_passive(
        "Ursula von der Leyen and John le Carré are being detained"
    ) == ["Ursula von der Leyen", "John le Carré"]
    assert names_from_plural_present_passive(
        "Ali ibn Abi Talib and Jane Doe were being detained"
    ) == ["Ali ibn Abi Talib", "Jane Doe"]

    # Bounded role appositives are covered in direct and progressive constructions.
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe (journalists) are detained"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe, journalists, are being imprisoned"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_plural_present_passive(
        "Jane Doe, a journalist, was being detained"
    ) == ["Jane Doe"]

    # Other passive auxiliary families remain owned by their established guards.
    assert names_from_plural_present_passive("Jane Doe is detained") == []
    assert names_from_plural_present_passive("Jane Doe and John Roe were detained") == []
    assert names_from_plural_present_passive("Jane Doe and John Roe have been detained") == []

    # Active progressive prose must not be mistaken for passive identity debt.
    assert names_from_plural_present_passive("authorities are detaining Jane Doe") == []
    assert names_from_plural_present_passive("authorities were detaining Jane Doe") == []

    print("State dossier plural-present/progressive-passive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PLURAL_OR_PROGRESSIVE_PASSIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier plural-present/progressive-passive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
