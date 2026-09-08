#!/usr/bin/env python3
"""Fail closed on named actors followed by parenthesized capacity prose.

The main named-identity parser recognizes ordinary actor components and reviewed comma
capacity tails. This companion guard independently covers the equally natural form
``Jane Doe (in an advisory capacity)`` including terminal punctuation, common
quote/Markdown wrappers, an optional second comma-delimited capacity condition, and
high-confidence actor lists. Ambiguous comma/``and`` separators are accepted only outside
an exact current State-safe actor anchor. Both non-Person and Person anchors are supported,
while separators inside a materialized organization remain protected.

This is identity-completeness only: it never creates actor participation, control,
operation, supply, culpability, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


PAREN_COMPONENT_RE = re.compile(r"^(.+?)\s*\(([^()]*)\)(.*)$", re.UNICODE)
POST_CAPACITY_SEPARATOR_RE = re.compile(
    r"(?<=\))\s*(?:and\b|&|,|—|–)\s+(?=[A-ZÀ-ÖØ-Þ\"'“‘\[\{*_`])",
    re.UNICODE,
)
TRAILING_WRAPPERS = "\"'”’]}*_`"
TRAILING_PUNCTUATION = ".!?,:"


def normalized_component(fragment: str) -> str:
    """Remove only terminal punctuation/wrappers that cannot belong to the actor name."""
    cleaned = fragment.strip()
    for _ in range(2):
        cleaned = cleaned.rstrip()
        cleaned = cleaned.rstrip(TRAILING_PUNCTUATION)
        cleaned = cleaned.rstrip()
        cleaned = cleaned.rstrip(TRAILING_WRAPPERS)
    return cleaned.strip()


def parenthesized_actor_component(fragment: str) -> str | None:
    """Parse one complete actor component with a closed-world parenthesized capacity tail."""
    match = PAREN_COMPONENT_RE.fullmatch(normalized_component(fragment))
    if not match:
        return None
    if not strict.CAPACITY_TAIL_RE.match(match.group(2).strip()):
        return None

    suffix = match.group(3).strip()
    suffix = suffix.lstrip(TRAILING_WRAPPERS).strip()
    if suffix:
        if not suffix.startswith(","):
            return None
        second_tail = suffix[1:].strip()
        if not second_tail or not strict.CAPACITY_TAIL_RE.match(second_tail):
            return None

    return strict.full_name_phrase(match.group(1).strip(), allow_all_caps=True)


def actor_capacity_fragments(raw: str) -> list[str]:
    """Split only on separators that are unambiguous for this parenthesized-capacity form."""
    out: list[str] = []
    for strong in re.split(r"\s*(?:/|;)\s*", raw):
        out.extend(part for part in POST_CAPACITY_SEPARATOR_RE.split(strong) if part.strip())
    return out


def parenthesized_actor_mentions(raw: str) -> list[str]:
    """Return complete parenthesized-capacity names from unambiguous component boundaries."""
    out: list[str] = []
    for fragment in actor_capacity_fragments(raw):
        mention = parenthesized_actor_component(fragment)
        if mention and mention not in out:
            out.append(mention)
    return out


def _anchored_segments(raw: str, anchor_spans: list[tuple[int, int]]) -> list[str]:
    """Return non-anchor actor-list segments while protecting separators inside anchors."""
    if not anchor_spans:
        return []
    separators: list[tuple[int, int]] = []
    for match in strict.ACTOR_LIST_SEPARATOR_RE.finditer(raw):
        if strict._inside_span(match.start(), anchor_spans):
            continue
        token = match.group(0)
        if token.lstrip().startswith(",") and strict.CAPACITY_TAIL_RE.match(raw[match.end():].lstrip()):
            continue
        separators.append(match.span())
    if not separators:
        return []

    segments: list[tuple[int, int, str]] = []
    start = 0
    for sep_start, sep_end in separators:
        segments.append((start, sep_start, raw[start:sep_start]))
        start = sep_end
    segments.append((start, len(raw), raw[start:]))

    anchored_indexes = {
        index
        for index, (seg_start, seg_end, _) in enumerate(segments)
        if any(seg_start <= anchor_start and anchor_end <= seg_end for anchor_start, anchor_end in anchor_spans)
    }
    return [segment for index, (_, _, segment) in enumerate(segments) if index not in anchored_indexes]


def exact_person_actor_spans(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[tuple[int, int]]:
    """Return spans of exact current State-safe Person identities in actor text.

    Match from the original Unicode surface rather than ``schedule.norm``: that normalizer is
    intentionally ASCII-only and would corrupt names such as ``Esra Işık``. Word components
    from the canonical name/alias are preserved and punctuation between them is flexible, so
    initials, apostrophes and hyphenation remain equivalent without broad substring matching.
    """
    spans: list[tuple[int, int]] = []
    for entity in entities:
        if entity.get("type") != "Person":
            continue
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not strict.eligible_in_state(identity_index, entity_id, state):
            continue

        forms = entity.get("surface_forms")
        if not forms:
            values = [entity.get("name"), *(entity.get("aliases") or [])]
            forms = [{"text": value} for value in values if isinstance(value, str) and value.strip()]
        for form in forms:
            text = form.get("text") or ""
            if not text:
                continue
            tokens = re.findall(r"[^\W_]+", text, re.UNICODE)
            if not tokens:
                continue
            pattern = r"(?<!\w)" + r"[\W_]+".join(map(re.escape, tokens)) + r"(?!\w)"
            spans.extend(match.span() for match in re.finditer(pattern, raw, re.I | re.UNICODE))
    return sorted(set(spans))


def exact_actor_anchor_spans(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[tuple[int, int]]:
    """Combine exact non-Person and Person actor anchors without changing row bindings."""
    return sorted(set(
        strict.exact_non_person_actor_spans(raw, entities, identity_index, state)
        + exact_person_actor_spans(raw, entities, identity_index, state)
    ))


def anchored_parenthesized_actor_mentions(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    """Parse parenthesized actors after ambiguous separators only when an exact actor anchor exists."""
    anchor_spans = exact_actor_anchor_spans(raw, entities, identity_index, state)
    out: list[str] = []
    for segment in _anchored_segments(raw, anchor_spans):
        mention = parenthesized_actor_component(segment)
        if mention and mention not in out:
            out.append(mention)
    return out


def failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        mentions = parenthesized_actor_mentions(raw)
        for mention in anchored_parenthesized_actor_mentions(raw, entities, identity_index, state):
            if mention not in mentions:
                mentions.append(mention)
        for mention in mentions:
            if exact.materialized_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if strict.explicitly_defers_complete_name(row, mention):
                continue
            found.append({
                "reason": "parenthesized-capacity actor lacks exact materialization or explicit complete-name deferral",
                "state": state,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "name": mention,
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def self_test() -> None:
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (in an advisory capacity)") == ["Jane Doe"]
    assert parenthesized_actor_mentions("Human Rights Watch / JANE DOE (acting only where participation is established).") == ["JANE DOE"]
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (serving in an advisory capacity)!") == ["Jane Doe"]
    assert parenthesized_actor_mentions('Human Rights Watch / “Jane Doe (in an advisory capacity)”.') == ["Jane Doe"]
    assert parenthesized_actor_mentions("Human Rights Watch / **Jane Doe (in an advisory capacity)**") == ["Jane Doe"]
    assert parenthesized_actor_mentions("Human Rights Watch / [Jane Doe (in an advisory capacity)]") == ["Jane Doe"]
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (in an advisory capacity), only where participation is established") == ["Jane Doe"]
    assert parenthesized_actor_mentions('Human Rights Watch / “Jane Doe (in an advisory capacity)”, acting only where participation is established') == ["Jane Doe"]
    assert parenthesized_actor_mentions("Jane Doe (in an advisory capacity) and John Smith (serving only where participation is established)") == ["Jane Doe", "John Smith"]
    assert parenthesized_actor_mentions("Jane Doe (in an advisory capacity), John Smith (serving only where participation is established)") == ["Jane Doe", "John Smith"]
    assert parenthesized_actor_mentions("Jane Doe (in an advisory capacity) — John Smith (serving only where participation is established)") == ["Jane Doe", "John Smith"]

    anchored = "Human Rights Watch and Jane Doe (in an advisory capacity)."
    hrw_span = (0, len("Human Rights Watch"))
    assert [parenthesized_actor_component(part) for part in _anchored_segments(anchored, [hrw_span])] == ["Jane Doe"]
    ministry = "Ministry of Interior and Narcotics Control and Jane Doe (in an advisory capacity)."
    ministry_span = (0, len("Ministry of Interior and Narcotics Control"))
    assert [parenthesized_actor_component(part) for part in _anchored_segments(ministry, [ministry_span])] == ["Jane Doe"]

    fake_entities = [{"id": "PERSON-TUR-ESRA-ISIK", "type": "Person", "name": "Esra Işık", "aliases": []}]
    fake_index = strict.build_name_index(fake_entities, state_codes={"TUR", "USA"}, normalizer=schedule.norm)
    person_raw = "Esra Işık and Jane Doe (in an advisory capacity)."
    assert exact_person_actor_spans(person_raw, fake_entities, fake_index, "TUR") == [(0, len("Esra Işık"))]
    assert exact_person_actor_spans(person_raw, fake_entities, fake_index, "USA") == []
    esra_span = (0, len("Esra Işık"))
    assert [parenthesized_actor_component(part) for part in _anchored_segments(person_raw, [esra_span])] == ["Jane Doe"]

    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (unreviewed arbitrary prose)") == []
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (case note).") == []
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe (in an advisory capacity), unrelated prose") == []
    assert parenthesized_actor_mentions("Human Rights Watch / Jane Doe-Smith (in an advisory capacity),") == ["Jane Doe-Smith"]
    print("Schedule parenthesized actor-capacity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, _, identity_index = schedule.load_entities()
    problems = failures(schedule.audit(), entities, identity_index)
    if problems:
        print(json.dumps(problems, indent=2, ensure_ascii=False, sort_keys=True))
        return 1
    print("Schedule parenthesized actor-capacity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
