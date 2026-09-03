#!/usr/bin/env python3
"""Fail closed on named people hidden by plural present passive custody prose.

The established simple-passive, appositive, and expanded-particle Person guards historically
omit the auxiliary ``are``. This independent companion covers the exact plural-present family
without trusting those auxiliary lists, while reusing the broader closed Person name/list
and bounded human-role appositive grammars.

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


PLURAL_PRESENT_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s+(?i:are)\s+(?i:{person.CUSTODY_STATE})\b"
)
PLURAL_PRESENT_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{expanded.NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"(?i:are)\s+(?i:{person.CUSTODY_STATE})\b"
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
                    "reason": "plural present passive custody prose names an unmaterialized person",
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
    assert names_from_plural_present_passive("Jane Doe and John Roe are detained") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe and John Roe are imprisoned") == [
        "Jane Doe", "John Roe"
    ]
    assert names_from_plural_present_passive("Jane Doe and John Roe are incommunicado") == [
        "Jane Doe", "John Roe"
    ]

    # The guard uses the expanded name grammar, so common particle sequences remain complete.
    assert names_from_plural_present_passive(
        "Ursula von der Leyen and John le Carré are detained"
    ) == ["Ursula von der Leyen", "John le Carré"]
    assert names_from_plural_present_passive(
        "Ali ibn Abi Talib and Jane Doe are detained"
    ) == ["Ali ibn Abi Talib", "Jane Doe"]

    # Bounded role appositives are covered in the same plural-present construction.
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe (journalists) are detained"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_plural_present_passive(
        "Jane Doe and John Roe, journalists, are imprisoned"
    ) == ["Jane Doe", "John Roe"]

    # Other auxiliary families remain owned by their established guards.
    assert names_from_plural_present_passive("Jane Doe is detained") == []
    assert names_from_plural_present_passive("Jane Doe and John Roe were detained") == []
    assert names_from_plural_present_passive("Jane Doe and John Roe have been detained") == []
    assert names_from_plural_present_passive("authorities are detaining Jane Doe") == []

    print("State dossier plural-present-passive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PLURAL_PRESENT_PASSIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier plural-present-passive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
