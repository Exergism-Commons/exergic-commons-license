#!/usr/bin/env python3
"""Fail closed on State-dossier Person names hidden by common multiword particles.

The primary named-person grammar deliberately uses a closed particle vocabulary. This
companion covers a broader but still closed set of common surname/patronymic particles and
particle sequences in the same high-confidence legal/custody and human-role contexts. It is
specifically defense in depth for names such as ``Ursula von der Leyen``, ``John le Carré``
and ``Ali ibn Abi Talib``.

Identity coverage is neutral: detecting a name never implies participation, attribution,
culpability, control, or governance.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_state_dossier_named_person_coverage as person
import check_state_dossier_passive_appositive_person_coverage as appositive
import identity_list_grammar as list_grammar


# Every particle is token-bounded. Multiple particles remain valid because NAME_PHRASE admits
# them as separate consecutive components: ``von der``, ``de la``, ``van den``, etc.
PARTICLE = (
    r"(?:de|del|da|do|dos|das|van|von|der|den|ter|ten|bin|binti|ibn|abu|al|el|"
    r"le|la|du|di|ap|af|zu|zur|zum|st|saint)\b"
)
NAME_PHRASE = rf"{person.NAME_WORD}(?:\s+(?:{person.NAME_WORD}|{PARTICLE})){{1,11}}"
COORDINATOR = rf"(?i:{list_grammar.COORDINATOR_PATTERN})"
SEPARATOR = rf"(?:\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+)"
NAME_LIST = rf"{NAME_PHRASE}(?:{SEPARATOR}{NAME_PHRASE})*"
SPLIT_RE = re.compile(rf"\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+")
ROLE_PREFIX_RE = re.compile(rf"(?i:\b(?:{person.ROLE})\s+)")
ACTIVE_PREFIX_RE = re.compile(
    rf"(?i:\b(?:arrested|detained|prosecuted|convicted|sentenced|imprisoned|incarcerated|"
    rf"abducted|released|pardoned|executed|killed|freed|acquitted|cleared)\s+)"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)
PASSIVE_RE = re.compile(
    rf"\b(?P<names>{NAME_LIST})\s+(?i:was|were|is|remains|remain|remained)\s+"
    rf"(?i:{person.CUSTODY_STATE})\b"
)
PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"(?i:was|were|is|remains|remain|remained)\s+(?i:{person.CUSTODY_STATE})\b"
)


def valid_expanded_name(value: str) -> bool:
    value = person.clean_candidate(value) or ""
    if not value or value.casefold() in person.LOCAL_STOP:
        return False
    if set(value.replace("-", " ").split()) & person.NON_PERSON_TERMS:
        return False
    return re.fullmatch(NAME_PHRASE, value) is not None


def split_names(value: str) -> list[str]:
    out: list[str] = []
    for raw in SPLIT_RE.split(value):
        candidate = person.clean_candidate(raw)
        if candidate and valid_expanded_name(candidate) and candidate not in out:
            out.append(candidate)
    return out


def leading_names(tail: str) -> list[str]:
    tail = tail.lstrip()
    if re.match(r"(?i)^(?:of\b|the\b)", tail):
        return []
    match = re.match(rf"(?P<names>{NAME_LIST})", tail)
    if match is None:
        return []
    remainder = tail[match.end():].lstrip()
    if re.match(r"(?i)^Law\b", remainder):
        return []
    return split_names(match.group("names"))


def expanded_names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            # This guard exists for particle-bearing names the primary closed grammar may miss.
            # Re-reporting a primary name is harmless for materialized identities but avoid
            # duplicate diagnostics within one prose surface.
            if value not in names:
                names.append(value)

    for match in ROLE_PREFIX_RE.finditer(prose):
        add_many(leading_names(prose[match.end():]))

    for regex in (person.ACTION_OF_RE, person.ACTION_TARGET_RE, person.CASE_OF_RE, person.REMEDIAL_TARGET_RE):
        for match in regex.finditer(prose):
            add_many(leading_names(prose[match.end():]))

    for match in ACTIVE_PREFIX_RE.finditer(prose):
        add_many(leading_names(prose[match.end():]))

    for regex in (PASSIVE_RE, PASSIVE_APPOSITIVE_RE):
        for match in regex.finditer(prose):
            add_many(split_names(match.group("names")))

    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in expanded_names_from_prose(prose):
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
                    "reason": "common particle-bearing name is not materialized as a State-safe Person",
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
    cases = {
        "journalist Ursula von der Leyen remained detained": ["Ursula von der Leyen"],
        "journalist John le Carré was detained": ["John le Carré"],
        "journalist Ali ibn Abi Talib was detained": ["Ali ibn Abi Talib"],
        "authorities detained Ursula von der Leyen": ["Ursula von der Leyen"],
        "Ursula von der Leyen (a journalist) was detained": ["Ursula von der Leyen"],
        "John le Carré, a writer, remained imprisoned": ["John le Carré"],
        "journalists Ursula von der Leyen and John le Carré were detained": [
            "Ursula von der Leyen", "John le Carré"
        ],
    }
    for prose, expected in cases.items():
        actual = expanded_names_from_prose(prose)
        assert actual == expected, (prose, actual, expected)

    # Token boundaries prevent ordinary prose prefixes from being consumed as particles.
    assert expanded_names_from_prose("journalist Jane Doe allegedly reported the detention") == ["Jane Doe"]
    assert expanded_names_from_prose("journalist Jane Doe delayed reporting") == ["Jane Doe"]

    print("State dossier multiword name-particle coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PARTICLE_BEARING_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier common name-particle Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
