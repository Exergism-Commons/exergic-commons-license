#!/usr/bin/env python3
"""Fail closed on Unicode, honorific-bearing, active-progressive and held-custody Person mentions.

This companion is deliberately independent from the historical Latin-1 ``NAME_WORD`` in the
primary State named-person audit. It derives Unicode uppercase/titlecase code points from the
Unicode database, adds a separate high-confidence path for scripts whose letters have no case,
strips only a closed set of common honorifics, and reuses the closed legal/custody, role,
list-coordinator and bounded appositive contexts that already make Person mentions high-confidence.

It additionally covers narrowly bounded active-progressive custody verbs (including perfect
progressive ``has|have|had been`` forms) and passive ``held in custody|detention`` clauses without
treating generic progressive or ``held`` prose as custody evidence.

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
# includes letters such as Ł/Ż/İ and extends naturally to Greek, Cyrillic and other cased scripts.
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


def _unicode_class_ranges(predicate) -> str:
    """Return a compact regex character-class body for Unicode code points satisfying predicate."""
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None
    for codepoint in range(0x110000):
        if not predicate(chr(codepoint)):
            continue
        if start is None:
            start = previous = codepoint
        elif previous is not None and codepoint == previous + 1:
            previous = codepoint
        else:
            assert previous is not None
            ranges.append((start, previous))
            start = previous = codepoint
    if start is not None:
        assert previous is not None
        ranges.append((start, previous))

    def escaped(codepoint: int) -> str:
        if codepoint <= 0xFFFF:
            return f"\\u{codepoint:04X}"
        return f"\\U{codepoint:08X}"

    return "".join(
        escaped(first) if first == last else f"{escaped(first)}-{escaped(last)}"
        for first, last in ranges
    )


# Casing is not a universal property of writing systems. Build a separate class containing only
# alphabetic code points whose upper/lower mappings are identical (Arabic, Han and other uncased
# scripts). This deliberately excludes ordinary lowercase Latin/Greek/Cyrillic prose, so the
# uncased path remains confined to the same high-confidence role/legal/custody contexts.
UNICODE_UNCASED = _unicode_class_ranges(
    lambda char: char.isalpha() and char.lower() == char.upper()
)
UNCASED_NAME_WORD = rf"[{UNICODE_UNCASED}]+(?:['’\-][{UNICODE_UNCASED}]+)*"
# Uncased scripts may encode a complete personal name in one token (for example Han), while Arabic
# and similar scripts commonly use several whitespace-separated tokens. Keep a small bounded run.
UNCASED_NAME_PHRASE = rf"{UNCASED_NAME_WORD}(?:\s+{UNCASED_NAME_WORD}){{0,5}}"

# Keep the particle vocabulary closed and token-bounded, but allow common multi-token particle
# sequences. Non-particle words must begin with a Unicode uppercase/titlecase code point.
PARTICLE_WORDS = {
    "de", "del", "da", "do", "dos", "das", "van", "von", "der", "den", "ter", "ten",
    "bin", "binti", "ibn", "abu", "al", "el", "le", "la", "du", "di", "ap", "af", "zu",
    "zur", "zum", "st", "saint",
}
PARTICLE = rf"(?:{'|'.join(sorted(map(re.escape, PARTICLE_WORDS), key=len, reverse=True))})\b"
UNICODE_NAME_PHRASE = rf"{UNICODE_NAME_WORD}(?:\s+(?:{UNICODE_NAME_WORD}|{PARTICLE})){{1,11}}"

# Honorifics are syntax, not part of the canonical Person surface. Keep this deliberately closed,
# token-bounded and capped at two consecutive titles so arbitrary lowercase prose is never stripped.
# Dotted and undotted spellings are both common in dossiers.
HONORIFIC_WORD = (
    r"Mr|Mrs|Ms|Miss|Dr|Prof|Professor|Rev|Revd|Fr|Sir|Dame|Judge|Justice|Hon|Honorable"
)
HONORIFIC_PREFIX = rf"(?:(?i:{HONORIFIC_WORD})\.?\s+){{0,2}}"
HONORIFIC_STRIP_RE = re.compile(rf"^(?:(?i:{HONORIFIC_WORD})\.?\s+){{1,2}}")
UNICODE_PERSON_MENTION = rf"{HONORIFIC_PREFIX}{UNICODE_NAME_PHRASE}"
UNCASED_PERSON_MENTION = rf"{HONORIFIC_PREFIX}{UNCASED_NAME_PHRASE}"

COORDINATOR = rf"(?i:{list_grammar.COORDINATOR_PATTERN})"
SEPARATOR = rf"(?:\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+)"
UNICODE_NAME_LIST = rf"{UNICODE_PERSON_MENTION}(?:{SEPARATOR}{UNICODE_PERSON_MENTION})*"
UNCASED_NAME_LIST = rf"{UNCASED_PERSON_MENTION}(?:{SEPARATOR}{UNCASED_PERSON_MENTION})*"
SPLIT_RE = re.compile(rf"\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+")

ROLE_PREFIX_RE = re.compile(rf"(?i:\b(?:{person.ROLE})\s+)")
ACTIVE_PREFIX_RE = re.compile(
    rf"(?i:\b(?:arrested|detained|charged|prosecuted|convicted|sentenced|imprisoned|incarcerated|"
    rf"abducted|released|pardoned|executed|killed|freed|acquitted|cleared)\s+)"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)

# Active progressive is owned explicitly rather than weakening passive grammar. Accept both the
# ordinary simple-progressive auxiliaries and perfect-progressive ``has|have|had been`` family,
# with the same closed/bounded adverb sequence already reviewed for passive clauses.
ACTIVE_PROGRESSIVE_VERB = (
    r"arresting|detaining|charging|prosecuting|convicting|sentencing|imprisoning|incarcerating|"
    r"abducting|releasing|pardoning|executing|killing|freeing|acquitting|clearing"
)
ACTIVE_PROGRESSIVE_AUX = (
    rf"(?:"
    rf"(?i:is|are|was|were)\s+{passive.ADVERB_SEQ}|"
    rf"(?i:has|have|had)\s+{passive.ADVERB_SEQ}(?i:been)\s+{passive.ADVERB_SEQ}"
    rf")"
)
ACTIVE_PROGRESSIVE_PREFIX_RE = re.compile(
    rf"\b{ACTIVE_PROGRESSIVE_AUX}(?i:{ACTIVE_PROGRESSIVE_VERB})\s+"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)

# Use the already-hardened auxiliary/adverb grammar, but own Unicode/honorific names independently.
PASSIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s+{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}"
    rf"(?i:{person.CUSTODY_STATE})\b"
)
PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{UNICODE_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)
# Uncased names use a wholly separate lexical class. A one-token Han name is valid here, while
# lowercase cased-script prose cannot enter this regex at all.
UNCASED_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{UNCASED_NAME_LIST})\s+{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}"
    rf"(?i:{person.CUSTODY_STATE})\b"
)
UNCASED_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{UNCASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
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
UNCASED_HELD_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{UNCASED_NAME_LIST})\s+{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{HELD_CUSTODY}\b"
)
UNCASED_HELD_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{UNCASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{HELD_CUSTODY}\b"
)


def strip_honorifics(value: str) -> str:
    return HONORIFIC_STRIP_RE.sub("", value.strip(), count=1)


def valid_unicode_name(value: str) -> bool:
    value = person.clean_candidate(strip_honorifics(value)) or ""
    if not value or value.casefold() in person.LOCAL_STOP:
        return False
    if set(value.replace("-", " ").split()) & person.NON_PERSON_TERMS:
        return False
    if re.fullmatch(UNICODE_NAME_PHRASE, value) is None:
        return False
    tokens = strict.NAME_TOKEN_RE.findall(value)
    semantic = [token for token in tokens if token.casefold() not in PARTICLE_WORDS]
    return len(semantic) >= 2 and all(token and token[0].isupper() for token in semantic)


def valid_uncased_name(value: str) -> bool:
    value = person.clean_candidate(strip_honorifics(value)) or ""
    if not value or value.casefold() in person.LOCAL_STOP:
        return False
    if re.fullmatch(UNCASED_NAME_PHRASE, value) is None:
        return False
    # Han and other uncased scripts can form a complete name without whitespace. Require at least
    # two alphabetic code points overall so a single one-character token does not become Person debt.
    letters = [char for char in value if char.isalpha()]
    return len(letters) >= 2 and all(char.lower() == char.upper() for char in letters)


def split_names(value: str) -> list[str]:
    out: list[str] = []
    for raw in SPLIT_RE.split(value):
        candidate = person.clean_candidate(strip_honorifics(raw))
        if candidate and valid_unicode_name(candidate) and candidate not in out:
            out.append(candidate)
    return out


def split_uncased_names(value: str) -> list[str]:
    out: list[str] = []
    for raw in SPLIT_RE.split(value):
        candidate = person.clean_candidate(strip_honorifics(raw))
        if candidate and valid_uncased_name(candidate) and candidate not in out:
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


def leading_uncased_names(tail: str) -> list[str]:
    tail = tail.lstrip()
    match = re.match(rf"(?P<names>{UNCASED_NAME_LIST})", tail)
    if match is None:
        return []
    return split_uncased_names(match.group("names"))


def unicode_and_held_names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            if value not in names:
                names.append(value)

    # Explicit human roles and legal/remedial cues provide a left boundary. The uncased lexical path
    # cannot match ordinary cased-script lowercase prose, so it can safely share these strong cues.
    for match in ROLE_PREFIX_RE.finditer(prose):
        add_many(leading_names(prose[match.end():]))
        add_many(leading_uncased_names(prose[match.end():]))
    for regex in (person.ACTION_OF_RE, person.ACTION_TARGET_RE, person.CASE_OF_RE, person.REMEDIAL_TARGET_RE):
        for match in regex.finditer(prose):
            add_many(leading_names(prose[match.end():]))
            add_many(leading_uncased_names(prose[match.end():]))
    for regex in (ACTIVE_PREFIX_RE, ACTIVE_PROGRESSIVE_PREFIX_RE):
        for match in regex.finditer(prose):
            add_many(leading_names(prose[match.end():]))
            add_many(leading_uncased_names(prose[match.end():]))

    # Passive custody provides a right boundary; cover cased/uncased, plain/appositive and
    # held-in-context forms independently.
    for regex, splitter in (
        (PASSIVE_RE, split_names),
        (PASSIVE_APPOSITIVE_RE, split_names),
        (HELD_PASSIVE_RE, split_names),
        (HELD_PASSIVE_APPOSITIVE_RE, split_names),
        (UNCASED_PASSIVE_RE, split_uncased_names),
        (UNCASED_PASSIVE_APPOSITIVE_RE, split_uncased_names),
        (UNCASED_HELD_PASSIVE_RE, split_uncased_names),
        (UNCASED_HELD_PASSIVE_APPOSITIVE_RE, split_uncased_names),
    ):
        for match in regex.finditer(prose):
            add_many(splitter(match.group("names")))
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
                    "reason": "Unicode/uncased/honorific/progressive/held high-confidence person mention lacks a State-safe Person identity",
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
    # Exact Codex Unicode examples and additional cased scripts prove the grammar is not Latin-block based.
    assert unicode_and_held_names_from_prose("journalist Łukasz Żak remains detained") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose("İdris Baluken was arrested") == ["İdris Baluken"]
    assert unicode_and_held_names_from_prose("journalist Željko Jovanović remains detained") == ["Željko Jovanović"]
    assert unicode_and_held_names_from_prose("journalist Γιάννης Αντετοκούνμπο remains detained") == ["Γιάννης Αντετοκούνμπο"]
    assert unicode_and_held_names_from_prose("journalist Олег Орлов remains detained") == ["Олег Орлов"]

    # Scripts without letter case have a separate high-confidence lexical path. Arabic may use
    # several name tokens; Han can encode a complete name in one token.
    assert unicode_and_held_names_from_prose("journalist أحمد منصور remains detained") == ["أحمد منصور"]
    assert unicode_and_held_names_from_prose("journalist 王小明 remains detained") == ["王小明"]
    assert unicode_and_held_names_from_prose("authorities detained أحمد منصور") == ["أحمد منصور"]
    assert unicode_and_held_names_from_prose("王小明 was detained") == ["王小明"]
    assert unicode_and_held_names_from_prose(
        "أحمد منصور and محمد علي were detained"
    ) == ["أحمد منصور", "محمد علي"]
    # Ordinary lowercase cased-script prose is not accepted by the uncased branch.
    assert leading_uncased_names("jane doe") == []

    # Unicode names compose with lists, particle sequences, active cues and bounded appositives.
    assert unicode_and_held_names_from_prose(
        "journalists Łukasz Żak and İdris Baluken were detained"
    ) == ["Łukasz Żak", "İdris Baluken"]
    assert unicode_and_held_names_from_prose("authorities charged Łukasz Żak") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose("authorities detained Łukasz Żak") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose(
        "Łukasz Żak (a journalist) was reportedly detained"
    ) == ["Łukasz Żak"]

    # Active progressive custody/legal family, including bounded adverbs, perfect progressives and lists.
    assert unicode_and_held_names_from_prose("authorities are charging Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("authorities are detaining Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("authorities were arresting Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "authorities are currently charging Dr. Jane Doe"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "authorities are currently detaining Jane Doe and John Roe"
    ) == ["Jane Doe", "John Roe"]
    assert unicode_and_held_names_from_prose(
        "authorities were reportedly prosecuting Łukasz Żak"
    ) == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose(
        "authorities have been charging Jane Doe"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "authorities have been detaining Jane Doe"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "authorities had been prosecuting Jane Doe"
    ) == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "authorities have reportedly been arbitrarily detaining Jane Doe and John Roe"
    ) == ["Jane Doe", "John Roe"]
    assert unicode_and_held_names_from_prose(
        "authorities have been detaining أحمد منصور"
    ) == ["أحمد منصور"]

    # Charged passive semantics reuse the shared custody-state pattern across auxiliaries, Unicode,
    # honorifics and uncased scripts rather than introducing a charge-specific passive checker.
    assert unicode_and_held_names_from_prose("Jane Doe was charged") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("Dr. Jane Doe is being charged") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("Łukasz Żak has been charged") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose("أحمد منصور was charged") == ["أحمد منصور"]

    # Closed honorific syntax is stripped before enforcing the complete canonical name, and composes
    # with direct action, action-of, passive, Unicode and lists.
    assert unicode_and_held_names_from_prose("authorities charged Dr. Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("authorities detained Dr. Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("the arrest of Ms. Jane Doe") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose("authorities arrested Prof. Łukasz Żak") == ["Łukasz Żak"]
    assert unicode_and_held_names_from_prose("Dr. Jane Doe was detained") == ["Jane Doe"]
    assert unicode_and_held_names_from_prose(
        "Dr. Jane Doe and Ms. John Roe were detained"
    ) == ["Jane Doe", "John Roe"]

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
    assert unicode_and_held_names_from_prose("أحمد منصور is being held in custody") == ["أحمد منصور"]

    # ``held`` stays narrow: unrelated senses cannot create Person debt.
    assert unicode_and_held_names_from_prose("Jane Doe was held accountable") == []
    assert unicode_and_held_names_from_prose("Jane Doe held a meeting") == []
    assert unicode_and_held_names_from_prose("The event was held in detention hall") == []

    # Unknown progressive verbs remain outside the closed high-confidence action grammar, including
    # the perfect-progressive family.
    assert unicode_and_held_names_from_prose("authorities are interviewing Jane Doe") == []
    assert unicode_and_held_names_from_prose("authorities have been interviewing Jane Doe") == []

    # Lowercase prose after a role/name remains a boundary, not part of the cased name.
    assert unicode_and_held_names_from_prose("journalist Łukasz Żak allegedly reported the detention") == ["Łukasz Żak"]

    print("State dossier Unicode/uncased/honorific/progressive/held Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_UNICODE_OR_CUSTODY_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier Unicode/uncased/honorific/progressive/held Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
