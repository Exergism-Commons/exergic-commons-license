#!/usr/bin/env python3
"""Fail closed on named people hidden by perfect passive custody constructions.

The established Person guards cover simple passives such as ``Jane Doe was detained`` and
bounded appositives such as ``Jane Doe (a journalist) was detained``. This independent guard
covers the perfect-passive family ``has/have/had been <custody-state>`` without depending on
the simple-auxiliary regex that caused the bypass. It deliberately reuses the broader closed
particle/list grammar so names such as ``Ursula von der Leyen`` are covered in the same pass.

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


PERFECT_PASSIVE_AUX = r"(?i:has\s+been|have\s+been|had\s+been)"
PERFECT_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s+{PERFECT_PASSIVE_AUX}\s+"
    rf"(?i:{person.CUSTODY_STATE})\b"
)
PERFECT_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{PERFECT_PASSIVE_AUX}\s+(?i:{person.CUSTODY_STATE})\b"
)


def names_from_perfect_passive(prose: str) -> list[str]:
    names: list[str] = []
    for regex in (PERFECT_PASSIVE_RE, PERFECT_PASSIVE_APPOSITIVE_RE):
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
        for name in names_from_perfect_passive(prose):
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
                    "reason": "perfect-passive custody prose names an unmaterialized person",
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
    assert names_from_perfect_passive("Jane Doe has been detained") == ["Jane Doe"]
    assert names_from_perfect_passive("Jane Doe had been imprisoned") == ["Jane Doe"]
    assert names_from_perfect_passive("Jane Doe has been incommunicado") == ["Jane Doe"]
    assert names_from_perfect_passive("Jane Doe and John Roe have been detained") == [
        "Jane Doe", "John Roe"
    ]

    # The same perfect-passive gate covers bounded appositives.
    assert names_from_perfect_passive("Jane Doe (a journalist) has been detained") == ["Jane Doe"]
    assert names_from_perfect_passive("Jane Doe, a journalist, had been imprisoned") == ["Jane Doe"]
    assert names_from_perfect_passive(
        "Jane Doe and John Roe (journalists) have been detained"
    ) == ["Jane Doe", "John Roe"]

    # And it does not inherit the primary guard's narrower particle vocabulary.
    assert names_from_perfect_passive("Ursula von der Leyen has been detained") == [
        "Ursula von der Leyen"
    ]
    assert names_from_perfect_passive("John le Carré, a writer, had been imprisoned") == [
        "John le Carré"
    ]
    assert names_from_perfect_passive("Ali ibn Abi Talib has been detained") == [
        "Ali ibn Abi Talib"
    ]

    # This guard is intentionally specific to passive perfect constructions.
    assert names_from_perfect_passive("Jane Doe was detained") == []
    assert names_from_perfect_passive("authorities have detained Jane Doe") == []
    assert names_from_perfect_passive("Project Aurora has been detained") == []

    print("State dossier perfect-passive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PERFECT_PASSIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier perfect-passive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
