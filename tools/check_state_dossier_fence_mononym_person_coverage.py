#!/usr/bin/env python3
"""Fail closed on fenced-code parser drift and cased mononyms in strong Person contexts.

This companion is deliberately independent from the historical State-dossier Person segmenter.
It (1) tracks the full CommonMark fenced-code marker and opening run length so a shorter fence
inside a longer fence cannot hide all later prose, and (2) permits one-token cased personal names
only inside the same explicit human-role/legal/custody contexts already used by the reviewed
Unicode Person guard.

Identity coverage is neutral and creates no attribution, participation, culpability, control,
operation, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_private_org_mentions as rendered
import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_state_dossier_named_person_coverage as person
import check_state_dossier_passive_appositive_person_coverage as appositive
import check_state_dossier_plural_present_passive_person_coverage as passive
import check_state_dossier_simple_present_active_person_coverage as simple_present
import check_state_dossier_unicode_held_person_coverage as unicode_guard
import identity_list_grammar as list_grammar


# Widen the cased name grammar from >=2 semantic tokens to >=1 *only* inside the strong contexts
# below. This is not exported back into the historical/general Person parser.
STRONG_CASED_NAME_PHRASE = (
    rf"{unicode_guard.UNICODE_NAME_WORD}"
    rf"(?:\s+(?:{unicode_guard.UNICODE_NAME_WORD}|{unicode_guard.PARTICLE})){{0,11}}"
)
STRONG_CASED_PERSON_MENTION = (
    rf"{unicode_guard.HONORIFIC_PREFIX}{STRONG_CASED_NAME_PHRASE}"
)
COORDINATOR = rf"(?i:{list_grammar.COORDINATOR_PATTERN})"
SEPARATOR = rf"(?:\s*,\s*(?:{COORDINATOR}\s+)?|\s+{COORDINATOR}\s+)"
STRONG_CASED_NAME_LIST = (
    rf"{STRONG_CASED_PERSON_MENTION}"
    rf"(?:{SEPARATOR}{STRONG_CASED_PERSON_MENTION})*"
)

# A one-token cased name needs a particularly strong lexical context. Reuse only unambiguous
# singular human-role cues here; plural role nouns and adjective/rank-like tokens such as
# ``general``/``major`` are deliberately excluded because ordinary prose can follow them with a
# capitalized common noun ("Prosecutors Resolution", "general State collapse").
MONONYM_ROLES = (
    "human-rights defender", "human rights defender", "rights defender", "peace activist",
    "opposition leader", "attorney general", "public defender", "prime minister",
    "deputy minister", "vice president", "member of parliament", "trade unionist",
    "journalist", "reporter", "activist", "lawyer", "attorney", "writer", "blogger",
    "defender", "critic", "dissident", "politician", "academic", "researcher", "student",
    "unionist", "cleric", "pastor", "imam", "priest", "doctor", "physician", "president",
    "governor", "mayor", "judge", "justice", "prosecutor", "ombudsperson", "senator",
)
MONONYM_ROLE = "|".join(
    sorted((re.escape(role) for role in MONONYM_ROLES), key=len, reverse=True)
)
MONONYM_ROLE_PREFIX_RE = re.compile(rf"(?i:\b(?:{MONONYM_ROLE})\s+)")
MONONYM_NON_PERSON = {
    "state", "resolution", "judgment", "judgement", "court", "government", "law",
    "parliament", "police", "agency", "commission", "council", "project", "operation",
}

# CommonMark closing fences use the same marker character and at least the opening run length,
# with no info string. Keep this stricter than the generic opener regex.
CLOSING_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})[ \t]*$")

STRONG_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{STRONG_CASED_NAME_LIST})\s+"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)
STRONG_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{STRONG_CASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}(?i:{person.CUSTODY_STATE})\b"
)
STRONG_HELD_PASSIVE_RE = re.compile(
    rf"\b(?P<names>{STRONG_CASED_NAME_LIST})\s+"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{unicode_guard.HELD_CUSTODY}\b"
)
STRONG_HELD_PASSIVE_APPOSITIVE_RE = re.compile(
    rf"\b(?P<names>{STRONG_CASED_NAME_LIST})\s*{appositive.APPOSITIVE}\s*"
    rf"{passive.PASSIVE_AUX}{passive.ADVERB_SEQ}{unicode_guard.HELD_CUSTODY}\b"
)


def valid_strong_cased_name(value: str) -> bool:
    value = person.clean_candidate(unicode_guard.strip_honorifics(value)) or ""
    if not value or value.casefold() in person.LOCAL_STOP:
        return False
    if set(value.replace("-", " ").split()) & person.NON_PERSON_TERMS:
        return False
    if re.fullmatch(STRONG_CASED_NAME_PHRASE, value) is None:
        return False
    tokens = strict.NAME_TOKEN_RE.findall(value)
    semantic = [
        token for token in tokens
        if token.casefold() not in unicode_guard.PARTICLE_WORDS
    ]
    if not semantic or not all(token and token[0].isupper() for token in semantic):
        return False
    # Exclude a lone initial such as "A." while permitting cased mononyms such as Banksy/Łukasz.
    if len(semantic) == 1:
        token = semantic[0].strip(".")
        if sum(char.isalpha() for char in token) < 2:
            return False
        if token.isupper() or token.casefold() in MONONYM_NON_PERSON:
            return False
        # Precision-first mononym rule: plural-looking common/group nouns are far more common in
        # custody prose than personal mononyms. Keep them out unless a future reviewed case adds
        # a narrower positive grammar.
        folded = token.casefold()
        if folded.endswith("s") and not folded.endswith("ss"):
            return False
        return True
    return True


def split_strong_cased_names(value: str) -> list[str]:
    out: list[str] = []
    for raw in unicode_guard.SPLIT_RE.split(value):
        candidate = person.clean_candidate(unicode_guard.strip_honorifics(raw))
        if candidate and valid_strong_cased_name(candidate) and candidate not in out:
            out.append(candidate)
    return out


def leading_strong_cased_names(tail: str) -> list[str]:
    tail = tail.lstrip()
    if re.match(r"(?i)^(?:of\b|the\b)", tail):
        return []
    match = re.match(rf"(?P<names>{STRONG_CASED_NAME_LIST})", tail)
    if match is None:
        return []
    remainder = tail[match.end():].lstrip()
    if re.match(r"(?i)^Law\b", remainder):
        return []
    return split_strong_cased_names(match.group("names"))


def strong_cased_names_from_prose(prose: str) -> list[str]:
    """Return cased names, including mononyms, only from explicit Person-bearing contexts."""
    names: list[str] = []

    def add_many(values: list[str]) -> None:
        for value in values:
            if value not in names:
                names.append(value)

    for match in MONONYM_ROLE_PREFIX_RE.finditer(prose):
        add_many(leading_strong_cased_names(prose[match.end():]))

    for regex in (
        person.ACTION_OF_RE,
        person.ACTION_TARGET_RE,
        person.CASE_OF_RE,
        person.REMEDIAL_TARGET_RE,
    ):
        for match in regex.finditer(prose):
            add_many(leading_strong_cased_names(prose[match.end():]))

    for regex in (
        unicode_guard.ACTIVE_PREFIX_RE,
        unicode_guard.ACTIVE_PROGRESSIVE_PREFIX_RE,
        simple_present.ACTIVE_PRESENT_PREFIX_RE,
    ):
        for match in regex.finditer(prose):
            add_many(leading_strong_cased_names(prose[match.end():]))

    for regex in (
        STRONG_PASSIVE_RE,
        STRONG_PASSIVE_APPOSITIVE_RE,
        STRONG_HELD_PASSIVE_RE,
        STRONG_HELD_PASSIVE_APPOSITIVE_RE,
    ):
        for match in regex.finditer(prose):
            add_many(split_strong_cased_names(match.group("names")))

    return names


def fence_safe_person_segments(body: str) -> list[tuple[int, str, str]]:
    """Render Person-bearing prose while obeying full CommonMark fenced-code run lengths."""
    result: list[tuple[int, str, str]] = []
    buffer: list[str] = []
    raw_buffer: list[str] = []
    start_line: int | None = None
    fence_marker: str | None = None
    fence_length = 0

    def flush() -> None:
        nonlocal buffer, raw_buffer, start_line
        if buffer and start_line is not None:
            parts = [rendered.rendered_line_fragment(part) for part in buffer]
            assembled = " ".join(part for part in parts if part)
            prose = person.person_visible_prose(assembled)
            if prose.strip():
                result.append((
                    start_line,
                    " ".join(part.strip() for part in raw_buffer)[:420],
                    prose,
                ))
        buffer = []
        raw_buffer = []
        start_line = None

    for line_no, raw in enumerate(body.splitlines(), 1):
        stripped = raw.strip()

        if fence_marker is not None:
            close = CLOSING_FENCE_RE.match(raw)
            if close:
                run = close.group(1)
                if run[0] == fence_marker and len(run) >= fence_length:
                    fence_marker = None
                    fence_length = 0
            continue

        opener = rendered.FENCE_RE.match(raw)
        if opener:
            flush()
            run = opener.group(1)
            fence_marker = run[0]
            fence_length = len(run)
            continue

        if not stripped:
            flush()
            continue
        if rendered.HEADING_RE.match(raw):
            flush()
            heading = rendered.HEADING_RE.sub("", raw, count=1)
            prose = person.person_visible_prose(heading)
            if prose.strip():
                result.append((line_no, raw.strip()[:420], prose))
            continue
        if rendered.TABLE_SEPARATOR_RE.match(raw) or (
            stripped.startswith("|") and stripped.endswith("|")
        ):
            flush()
            if not rendered.TABLE_SEPARATOR_RE.match(raw):
                prose = person.person_visible_prose(raw)
                if prose.strip():
                    result.append((line_no, raw.strip()[:420], prose))
            continue

        list_match = rendered.LIST_RE.match(raw)
        if list_match:
            flush()
            start_line = line_no
            buffer.append(raw[list_match.end():])
            raw_buffer.append(raw)
            continue

        quote = re.sub(r"^\s{0,3}(?:>\s*)+", "", raw)
        if start_line is None:
            start_line = line_no
        buffer.append(quote)
        raw_buffer.append(raw)

    flush()
    return result


def names_from_safe_prose(prose: str) -> list[str]:
    """Compose the established Person parsers with the strong cased-mononym path."""
    out: list[str] = []
    for extractor in (
        person.names_from_prose,
        unicode_guard.unicode_and_held_names_from_prose,
        simple_present.simple_present_active_names_from_prose,
        strong_cased_names_from_prose,
    ):
        for value in extractor(prose):
            if value not in out:
                out.append(value)
    return out


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_safe_prose(prose):
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
                        "fence-safe or cased-mononym high-confidence Person mention lacks "
                        "a State-safe Person identity"
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
        for rel_line, snippet, prose in fence_safe_person_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    # Exact fenced-code P1: a shorter same-marker run does not close a longer opening fence.
    body = (
        "````text\n"
        "journalist Hidden Person remains detained\n"
        "```\n"
        "still fenced\n"
        "````\n"
        "Jane Doe was detained\n"
    )
    segments = fence_safe_person_segments(body)
    assert all("Hidden Person" not in prose for _, _, prose in segments), segments
    assert any("Jane Doe" in names_from_safe_prose(prose) for _, _, prose in segments), segments

    # Equal or longer same-marker closers work; a different marker cannot close the fence.
    longer_close = fence_safe_person_segments(
        "```text\nHidden Person was detained\n````\nJane Doe was detained"
    )
    assert any("Jane Doe" in names_from_safe_prose(prose) for _, _, prose in longer_close)
    different_marker = fence_safe_person_segments(
        "~~~~text\nHidden Person was detained\n````\nstill fenced\n~~~~\nJane Doe was detained"
    )
    assert all("Hidden Person" not in prose for _, _, prose in different_marker)
    assert any("Jane Doe" in names_from_safe_prose(prose) for _, _, prose in different_marker)
    assert fence_safe_person_segments(
        "````text\nJane Doe was detained\n```\nJohn Roe was detained\n````"
    ) == []

    # Exact mononym P1 and adjacent strong-context families.
    assert strong_cased_names_from_prose("activist Banksy was detained") == ["Banksy"]
    assert strong_cased_names_from_prose("authorities detained Banksy") == ["Banksy"]
    assert strong_cased_names_from_prose("Banksy was detained") == ["Banksy"]
    assert strong_cased_names_from_prose("the arrest of Banksy") == ["Banksy"]
    assert strong_cased_names_from_prose("authorities detain Banksy") == ["Banksy"]
    assert strong_cased_names_from_prose("authorities are detaining Banksy") == ["Banksy"]
    assert strong_cased_names_from_prose("authorities have been detaining Banksy") == ["Banksy"]
    assert strong_cased_names_from_prose("Banksy is being held in custody") == ["Banksy"]
    assert strong_cased_names_from_prose("activist Łukasz was detained") == ["Łukasz"]

    # Lists can mix mononyms and ordinary multi-token cased names without truncating the latter.
    assert strong_cased_names_from_prose(
        "authorities detained Banksy and Bono"
    ) == ["Banksy", "Bono"]
    assert strong_cased_names_from_prose(
        "authorities detained Jane Doe and Banksy"
    ) == ["Jane Doe", "Banksy"]
    assert strong_cased_names_from_prose("Jane Doe was detained") == ["Jane Doe"]

    # No strong context, a lone initial, and institutional/common-noun surfaces remain outside debt.
    assert strong_cased_names_from_prose("Banksy exhibition opened") == []
    assert strong_cased_names_from_prose("activist A. was detained") == []
    assert strong_cased_names_from_prose("Project was detained") == []
    assert strong_cased_names_from_prose("Prosecutors Resolution 310 sets standards") == []
    assert strong_cased_names_from_prose("Hundreds were arrested") == []
    assert strong_cased_names_from_prose("Christians remained detained") == []
    assert strong_cased_names_from_prose("Palestinians were detained") == []
    assert strong_cased_names_from_prose("general State collapse continued") == []
    assert strong_cased_names_from_prose("Judgments were released") == []
    assert strong_cased_names_from_prose("EXCLUSIONS were released") == []

    print("State dossier fenced-code and cased-mononym Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    failures = audit()
    if failures:
        print(
            "UNMATERIALIZED_STATE_DOSSIER_FENCE_OR_MONONYM_PEOPLE="
            + json.dumps(failures, ensure_ascii=False, sort_keys=True)
        )
        return 2
    print("State dossier fenced-code and cased-mononym Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
