#!/usr/bin/env python3
"""Fail closed on simple-present active custody/remedial Person mentions.

This companion owns the finite active-present forms omitted by the historical past-tense and
progressive State dossier Person guards. It deliberately reuses the hardened Unicode/uncased,
honorific, particle and identity-list parser from ``check_state_dossier_unicode_held_person_coverage``
while keeping the action vocabulary closed to the same custody/remedial family already reviewed by
that guard.

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
import check_state_dossier_named_person_coverage as person
import check_state_dossier_unicode_held_person_coverage as unicode_guard


# Keep base and third-person-singular forms explicit rather than relying on a permissive stemming
# rule. These are the finite simple-present counterparts of the already-reviewed past/progressive
# custody and remedial actions.
ACTIVE_PRESENT_VERB = (
    r"arrest|arrests|"
    r"detain|detains|"
    r"charge|charges|"
    r"prosecute|prosecutes|"
    r"convict|convicts|"
    r"sentence|sentences|"
    r"imprison|imprisons|"
    r"incarcerate|incarcerates|"
    r"abduct|abducts|"
    r"release|releases|"
    r"pardon|pardons|"
    r"execute|executes|"
    r"kill|kills|"
    r"free|frees|"
    r"acquit|acquits|"
    r"clear|clears"
)
ACTIVE_PRESENT_PREFIX_RE = re.compile(
    rf"(?i:\b(?:{ACTIVE_PRESENT_VERB})\s+)"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)


def simple_present_active_names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            if value not in names:
                names.append(value)

    for match in ACTIVE_PRESENT_PREFIX_RE.finditer(prose):
        tail = prose[match.end():]
        add_many(unicode_guard.leading_names(tail))
        add_many(unicode_guard.leading_uncased_names(tail))
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in simple_present_active_names_from_prose(prose):
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
                    "reason": "simple-present active custody/remedial person mention lacks a State-safe Person identity",
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
    # Exact Codex examples: both base and third-person-singular finite forms are owned here.
    assert simple_present_active_names_from_prose("authorities detain Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("police arrest Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("prosecutors charge Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("the prosecutor charges Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("the government prosecutes Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("the court sentences Jane Doe") == ["Jane Doe"]

    # The complete hardened name grammar composes with present actions: lists, roles, honorifics,
    # cased Unicode names and scripts without letter case all remain complete canonical surfaces.
    assert simple_present_active_names_from_prose(
        "authorities detain Jane Doe and John Roe"
    ) == ["Jane Doe", "John Roe"]
    assert simple_present_active_names_from_prose(
        "authorities arrest journalists Jane Doe and John Roe"
    ) == ["Jane Doe", "John Roe"]
    assert simple_present_active_names_from_prose("authorities charge Dr. Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("authorities detain Dr. Jane Doe") == ["Jane Doe"]
    assert simple_present_active_names_from_prose("authorities detain Łukasz Żak") == ["Łukasz Żak"]
    assert simple_present_active_names_from_prose("authorities detain أحمد منصور") == ["أحمد منصور"]
    assert simple_present_active_names_from_prose("authorities detain 王小明") == ["王小明"]

    # Unrelated present-tense actions remain outside the closed identity-completeness signal.
    assert simple_present_active_names_from_prose("authorities interview Jane Doe") == []
    assert simple_present_active_names_from_prose("authorities monitor Jane Doe") == []

    print("State dossier simple-present active Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_SIMPLE_PRESENT_ACTIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier simple-present active Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
