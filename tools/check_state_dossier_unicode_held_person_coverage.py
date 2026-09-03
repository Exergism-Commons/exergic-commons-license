#!/usr/bin/env python3
"""Fail closed on Unicode Person names and passive ``held in custody`` clauses.

This companion is deliberately independent from the historical Latin-1 ``NAME_WORD`` in the
primary State named-person audit. It derives Unicode uppercase/titlecase code points from the
Unicode database, accepts Unicode letters in the remainder of name tokens, and reuses only the
closed legal/custody, role, list-coordinator and appositive contexts that already make Person
mentions high-confidence.

It also covers the narrow passive construction ``held in custody|detention`` (including
simple, progressive, perfect and bounded-adverb passive auxiliaries) without treating generic
``held`` prose such as ``held accountable`` as custody evidence.

Identity coverage is neutral and creates no attribution, participation, culpability, control,
operation, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata

import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_state_dossier_named_person_coverage as person
import check_state_dossier_passive_appositive_person_coverage as appositive
import check_state_dossier_plural_present_passive_person_coverage as passive
import identity_list_grammar as list_grammar


# Python's ``re`` has Unicode-aware ``\w`` but no ``\p{Lu}``. Build the finite uppercase/titlecase
# class from the Unicode database once at import time rather than hard-coding Latin blocks. This
# includes letters such as Ł/Ż/İ and extends naturally to Greek, Cyrillic and other scripts.
UNICODE_UPPER = re.escape(
    "".join(
        chr(codepoint)
        for codepoint in range(0x110000)
        if unicodedata.category(chr(codepoint)) in {"Lu", "Lt"}
    )
)
UNICODE_LETTER = r"[^\W\d_]"
UNICODE_NAME_WORD = (
    rf"(?:[{UNICODE_UPPER}](?:{UNICODE_LETTER}|['’\-]{UNICODE_LETTER}+)*|"
    rf"[{UNICODE_UPPER}]\.)"
)

# Keep the particle vocabulary closed and token-bounded, but allow common multi-token particle
# sequences. Non-particle words must begin with a Unicode uppercase/titlecase code point.
PARTICLE_WORDS = {
    "de", "del", "da", "do", "dos", "das", "van", "von", "der", "den", "ter", "ten",
    "bin", "binti", "ibn", "abu", "al", "el", "le", "la", "du", "di", "ap", "af", "zu",
    "zur", "zum", "st", "saint",
}
PARTICLE = rf"(?:{'|'.join(sorted(map(re.escape, PARTICLE_WORDS), key=len, reverse=True))})\b"
UNICODE_NAME_PHRASE = rf"{UNICODE_NAME_WORD}(?:\s+(?:{UNICODE_NAME_WORD}|{PARTICLE})){{1,11}}"
COORDINATOR = rf"(?i:{list_grammar.COORDINATOR_PATTERN})"
SEPARATOR = rf"(?:\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+)"
UNICODE_NAME_LIST = rf"{UNICODE_NAME_PHRASE}(?:{SEPARATOR}{UNICODE_NAME_PHRASE})*"
SPLIT_RE = re.compile(rf"\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+")

ROLE_PREFIX_RE = re.compile(rf"(?i:\b(?:{person.ROLE})\s+)")
ACTIVE_PREFIX_RE = re.compile(
    rf"(?i:\b(?:arrested|detained|prosecuted|convicted|sentenced|imprisoned|incarcerated|"
    rf"abducted|released|pardoned|executed|killed|freed|acquitted|cleared)\s+)"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)

# Use the already-hardened auxiliary/adverb grammar, but own Unicode names independently.
PASSIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s+{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}"
    rf"(?i:{person.CUSTODY_STATE})\b"
)
PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)

# ``held`` is intentionally not added as a generic custody-state verb. It is accepted only when
# immediately completed by the custody/detention complement, so ``held accountable`` and ordinary
# possession/event senses remain outside this identity gate.
HELD_CUSTODY = r"(?i:held\s+in\s+(?:custody|detention))"
HELD_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s+{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{HELD_CUSTODY}\b"
)
HELD_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{HELD_CUSTODY}\b"
)


def valid_unicode_name(value: str) -> bool:
    value = person.clean_candidate(value) or ""
    if not value or value.casefold() in person.LOCAL_STOP:
        return False
    if set(value.replace("-", " ").split()) & person.NON_PERSON_TERMS:
        return False
    if re.fullmatch(UNICODE_NAME_PHRASE, value) is None:
        return False
    tokens = strict.NAME_TOKEN_RE.findall(value)
    semantic = [token for token in tokens if token.casefold() not in PARTICLE_WORDS]
    return len(semantic) >= 2 and all(token and token[0].isupper() for token in semantic)


def split_names(value: str) -> list[str]:
    out: list[str] = []
    for raw in SPLIT_RE.split(value):
        candidate = person.clean_candidate(raw)
        if candidate and valid_unicode_name(candidate) and candidate not in out:
            out.append(candidate)
    return out


def leading_names(tail: str) -> list[str]:
    tail = tail.lstrip()
    if re.match(r"(?i)^(?:of\b|the\b)", tail):
        return []
    match = re.match(rf"(?P<names>{UNICODE_NAME_LIST})", tail)
    if match is None:
        return []
    remainder = tail[match.end():].lstrip()
    if re.match(r"(?i)^Law\b", remainder):
        return []
    return split_names(match.group("names"))


def unicode_and_held_names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            if value not in names:
                names.append(value)

    # Explicit human roles and legal/remedial cues provide a left boundary for Unicode names.
    for match in ROLE_PREFIX_RE.finditer(prose):
        add_many(leading_names(prose[match.end():]))
    for regex in (person.ACTION_OF_RE, person.ACTION_TARGET_RE, person.CASE_OF_RE, person.REMEDIAL_TARGET_RE):
        for match in regex.finditer(prose):
            add_many(leading_names(prose[match.end():]))
    for match in ACTIVE_PREFIX_RE.finditer(prose):
        add_many(leading_names(prose[match.end():]))

    # Passive custody provides a right boundary; cover plain/appositive and held-in-context forms.
    for regex in (
        PASSIVE_RE,
        PASSIVE_APPOSITIVE_RE,
        HELD_PASSIVE_RE,
        HELD_PASSIVE_APPOSITIVE_RE,
    ):
        for match in regex.finditer(prose):
            add_many(split_names(match.group("names")))
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in unicode_and_held_names_from_prose(prose):
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
                    "reason": "Unicode/held-custody high-confidence person mention lacks a State-safe Person identity",
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
    # Exact Codex Unicode examples and additional scripts prove the grammar is not Latin-block based.
    assert unicode_and_held_names_from_prose("journalist Łukasz Żak remains detained") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose("İdris Baluken was arrested") == ["İdris Baluken"]
    assert unicode_and_held_names_from_prose("journalist Željko Jovanović remains detained") == ["Željko Jovanović"]
    assert unicode_and_held_names_from_prose("journalist Γιάννης Αντετοκούνμπο remains detained") == ["Γιάννης Αντετοκούνμπο"]
    assert unicode_and_held_names_from_prose("journalist Олег Орлов remains detained") == ["Олег Орлов"]

    # Unicode names compose with lists, particle sequences, active cues and bounded appositives.
    assert unicode_and_held_names_from_prose(
        "journalists Łukasz Żak and İdris Baluken were detained"
    ) == ["Łukasz Żak", "İdris Baluken"]
    assert unicode_and_held_names_from_prose("authorities detained Łukasz Żak") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose(
        "Łukasz Żak (a journalist) was reportedly detained"
    ) == ["Łukasz Żak"]

    # Exact held-in-custody P1 family: simple, progressive, perfect, adverbial and appositive.
    assert unicode_and_held_names_from_prose("Jane Doe is being held in custody") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("Jane Doe was held in detention") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("Jane Doe has been held in custody") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "Jane Doe is currently being arbitrarily held in custody"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "Jane Doe, a journalist, was reportedly held in detention"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "Łukasz Żak and İdris Baluken are being held in custody"
    ) == ["Łukasz Żak", "İdris Baluken"]

    # ``held`` stays narrow: unrelated senses cannot create Person debt.
    assert unicode_and_held_names_from_prose("Jane Doe was held accountable") == []
    assert unicode_and_held_names_from_prose("Jane Doe held a meeting") == []
    assert unicode_and_held_names_from_prose("The event was held in detention hall") == []

    # Lowercase prose after a role/name remains a boundary, not part of the name.
    assert unicode_and_held_names_from_prose("journalist Łukasz Żak allegedly reported the detention") == ["Łukasz Żak"]

    print("State dossier Unicode/held-custody Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_UNICODE_OR_HELD_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier Unicode/held-custody Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
