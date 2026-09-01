#!/usr/bin/env python3
"""Fail closed on actor lists embedded inside reviewed Schedule capacity tails.

The top-level actor-expression parser deliberately protects recognized capacity regions so
commas and conjunctions in legal/capacity prose are not mistaken for top-level actor-list
separators. That protection must not make an identity list *inside* the capacity prose opaque.

This companion guard therefore inspects only relational capacity tails (for example
``acting with``) and applies one protected list grammar covering the same separator families
accepted elsewhere by the Schedule actor parser: comma/Oxford-comma forms, ``and``, ``&``,
``or``, ``and/or`` / ``and / or`` / ``and-or``, ``as well as``, slash, and semicolon. A
separator is active only when it lies outside an exact current actor span or maximal
institution span, the left fragment already carries an actor-like surface, and the right
fragment starts with a high-confidence identity surface. Exact identity anchors remain
structurally visible even when preceded by contextual prose outside the closed prefix
vocabulary; unknown modifiers therefore cannot make later list members opaque, and they are
not silently promoted into accepted capacity syntax.

This is identity-completeness only. It creates no participation, control, operation, supply,
membership, culpability, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_actor_expression_completeness as expression
import check_schedule_named_identity_strictness as strict
import identity_list_grammar as list_grammar
from entity_identity_resolution import build_name_index


IDENTITY_CONTINUATION_WORDS = {
    "co", "company", "corp", "corporation", "inc", "incorporated", "llc", "llp",
    "ltd", "limited", "plc", "jr", "sr", "ii", "iii", "iv",
}
CAPACITY_LIST_SEPARATOR_RE = re.compile(
    rf"""
    \s*
    (?:
        ,\s*(?:(?:{list_grammar.COORDINATOR_PATTERN})\s+)?
      | \b{list_grammar.WORD_COORDINATOR_PATTERN}\b
      | &
      | /
      | ;
    )
    \s*
    """,
    re.I | re.X,
)
OPENING_IDENTITY_WRAPPERS = " \t\r\n\"'“‘([{*_`"
LEADING_IDENTITY_DETERMINERS = {"the", "a", "an"}
IDENTITY_SURFACE_STRIP = " \t\r\n,;:[]{}\"'“”‘’*_`."


def _leading_identity_prefix_allowed(prefix: str) -> bool:
    """Recognize the closed-world prefix syntax, without making it an audit prerequisite."""
    cleaned = prefix.strip(OPENING_IDENTITY_WRAPPERS)
    if not cleaned:
        return True
    tokens = [token.casefold().rstrip(".") for token in cleaned.split()]
    allowed = LEADING_IDENTITY_DETERMINERS | expression.SINGLE_CONTEXT_WORDS
    return bool(tokens) and all(token in allowed for token in tokens)


def _exact_identity_spans(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[tuple[int, int]]:
    """Return exact/current State-safe actor spans independent of contextual prefixes."""
    return expression.safe_actor_anchor_spans(
        text, entities, identity_index, state, bound_ids
    )


def _protected_identity_spans(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[tuple[int, int]]:
    """Protect exact identities first; never let a heuristic swallow a later list member."""
    exact_spans = _exact_identity_spans(text, entities, identity_index, state, bound_ids)
    heuristic_spans = expression.heuristic_institution_spans(text)
    filtered_heuristics: list[tuple[int, int]] = []
    for heuristic in heuristic_spans:
        shadowed = False
        for exact in exact_spans:
            if not (heuristic[0] <= exact[0] and heuristic[1] >= exact[1]):
                continue
            prefix = text[heuristic[0]:exact[0]]
            trailing = text[exact[1]:heuristic[1]]
            # The exact boundary is authoritative for known prefix syntax. It is also
            # authoritative whenever the heuristic would cross a capacity-list separator:
            # an unknown adjective such as "competent" must never cause the heuristic span
            # to swallow "& Globex" and thereby erase the trailing actor.
            if _leading_identity_prefix_allowed(prefix) or CAPACITY_LIST_SEPARATOR_RE.search(trailing):
                shadowed = True
                break
        if not shadowed:
            filtered_heuristics.append(heuristic)
    return expression._merge_spans(exact_spans + filtered_heuristics)


def _leading_protected_surface(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> str | None:
    spans = _protected_identity_spans(text, entities, identity_index, state, bound_ids)
    candidates: list[tuple[int, int]] = []
    for start, end in spans:
        # Known determiners/context words are syntax, not part of the identity surface.
        if _leading_identity_prefix_allowed(text[:start]):
            candidates.append((start, end))
    if not candidates:
        return None
    start, end = sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0])))[0]
    surface = text[start:end].strip(IDENTITY_SURFACE_STRIP)
    return surface or None


def _exact_surfaces_preserving_prefix_debt(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    """Keep exact anchors visible without silently accepting arbitrary leading modifiers.

    Closed-world prefix syntax is handled by `_leading_protected_surface`. If that path does
    not apply, exact identities still remain structural anchors for list segmentation. Any
    actor-like material before the first exact anchor is independently retained as debt; only
    non-identity contextual prose (for example ``competent``) is left uninterpreted.
    """
    exact_spans = sorted(_exact_identity_spans(text, entities, identity_index, state, bound_ids))
    if not exact_spans:
        return []
    out: list[str] = []
    first_start = exact_spans[0][0]
    prefix = text[:first_start].strip(OPENING_IDENTITY_WRAPPERS)
    if prefix:
        for surface in expression._capacity_fragment_surfaces(prefix):
            expression._add_unique(out, surface)
    for start, end in exact_spans:
        surface = text[start:end].strip(IDENTITY_SURFACE_STRIP)
        if surface:
            expression._add_unique(out, surface)
    return out


def _fragment_surfaces(
    fragment: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    protected = _leading_protected_surface(fragment, entities, identity_index, state, bound_ids)
    if protected:
        return [protected]
    exact_surfaces = _exact_surfaces_preserving_prefix_debt(
        fragment, entities, identity_index, state, bound_ids
    )
    if exact_surfaces:
        return exact_surfaces
    return expression._capacity_fragment_surfaces(fragment)


def _rhs_starts_identity(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> bool:
    match = expression.SINGLE_IDENTITY_RE.match(text.lstrip())
    if match:
        token = match.group(1)
        if token.casefold().rstrip(".") in IDENTITY_CONTINUATION_WORDS:
            return False
    return bool(_fragment_surfaces(text, entities, identity_index, state, bound_ids))


def _capacity_list_fragments(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    protected = _protected_identity_spans(text, entities, identity_index, state, bound_ids)
    pieces: list[str] = []
    start = 0
    for match in CAPACITY_LIST_SEPARATOR_RE.finditer(text):
        span = match.span()
        if expression._overlaps(span, protected):
            continue
        left = text[start:match.start()].strip()
        right = text[match.end():].lstrip()
        if not left or not right:
            continue
        if not _fragment_surfaces(left, entities, identity_index, state, bound_ids):
            continue
        if not _rhs_starts_identity(right, entities, identity_index, state, bound_ids):
            continue
        pieces.append(left)
        start = match.end()
    tail = text[start:].strip()
    if tail:
        pieces.append(tail)
    return pieces


def capacity_list_surfaces(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    out: list[str] = []
    for start, end in expression.capacity_spans(raw):
        region = raw[start:end]
        protected_region = _protected_identity_spans(
            region, entities, identity_index, state, bound_ids
        )
        for cue in expression.CAPACITY_IDENTITY_CUE_RE.finditer(region):
            if expression._overlaps(cue.span(), protected_region):
                continue
            tail = region[cue.end():]
            for fragment in _capacity_list_fragments(
                tail, entities, identity_index, state, bound_ids
            ):
                for surface in _fragment_surfaces(
                    fragment, entities, identity_index, state, bound_ids
                ):
                    expression._add_unique(out, surface)
    return out


def capacity_comma_surfaces(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    return capacity_list_surfaces(raw, entities, identity_index, state, bound_ids)


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        bound_ids = {item for item in row.get("resolved_ids") or [] if item in by_id}
        for surface in capacity_list_surfaces(raw, entities, identity_index, state, bound_ids):
            if expression._bound_identity_extends_surface(surface, raw, bound_ids, by_id):
                continue
            exact_ids = expression.exact_actor_ids_for_surface(
                surface, entities, identity_index, state, bound_ids
            )
            if exact_ids:
                missing = sorted(exact_ids - bound_ids)
                if not missing:
                    continue
                found.append({
                    "reason": "capacity-list actor matches exact current identity not present in row binding",
                    "state": state,
                    "field": row.get("field"),
                    "source": row.get("source"),
                    "raw": raw,
                    "identity_surface": surface,
                    "missing_ids": missing,
                    "resolved_ids": sorted(bound_ids),
                    "status": row.get("status"),
                    "resolution_source": row.get("resolution_source"),
                })
                continue
            if expression.explicitly_defers_surface(row, surface) or strict.explicitly_defers_complete_name(row, surface):
                continue
            found.append({
                "reason": "capacity-list actor lacks exact binding or explicit surface deferral",
                "state": state,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "identity_surface": surface,
                "resolved_ids": sorted(bound_ids),
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def _entity(entity_id: str, entity_type: str, name: str) -> dict:
    return {
        "id": entity_id,
        "type": entity_type,
        "name": name,
        "aliases": [schedule.norm(name)],
        "surface_forms": [{"text": name, "normalized": schedule.norm(name)}],
    }


def _row(raw: str, *, reason: str) -> dict:
    return {
        "kind": "actor-reference",
        "state": "AAA",
        "field": "candidate_parties",
        "source": "x.yml",
        "raw": raw,
        "status": "partial-deferred",
        "resolution_source": "reviewed-disposition",
        "resolved_ids": ["ORG-HRW"],
        "disposition_reason": reason,
    }


def self_test() -> None:
    entities = [
        _entity("ORG-HRW", "Organization", "Human Rights Watch"),
        _entity("ORG-ACME-INC", "Organization", "Acme, Inc."),
        _entity("ORG-SMITH-WESSON", "Organization", "Smith & Wesson"),
        _entity("INST-MOJHR", "Institution", "Ministry of Justice and Human Rights"),
        _entity("INST-REGIONAL-COUNCIL", "Institution", "Regional Council"),
        _entity("INST-INTERNATIONAL-COUNCIL", "Institution", "International Council"),
    ]
    raw_entities = [
        {"id": item["id"], "type": item["type"], "name": item["name"], "aliases": []}
        for item in entities
    ]
    identity_index = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    by_id = {item["id"]: item for item in entities}
    bound = {"ORG-HRW"}

    separator_cases = [
        "Acme, Globex",
        "Acme, and Globex",
        "Acme, or Globex",
        "Acme, & Globex",
        "Acme and Globex",
        "Acme & Globex",
        "Acme or Globex",
        "Acme and/or Globex",
        "Acme and / or Globex",
        "Acme and-or Globex",
        "Acme as well as Globex",
        "Acme, as well as Globex",
        "Acme / Globex",
        "Acme; Globex",
    ]
    for actor_list in separator_cases:
        raw = f"Human Rights Watch, acting with {actor_list}"
        assert capacity_list_surfaces(raw, entities, identity_index, "AAA", bound) == [
            "Acme", "Globex"
        ], actor_list

    reported_raw = "Human Rights Watch, acting together with Acme as well as Globex"
    assert capacity_list_surfaces(reported_raw, entities, identity_index, "AAA", bound) == [
        "Acme", "Globex"
    ]
    reported_row = _row(
        reported_raw,
        reason="Acme remains explicitly identity-deferred pending materialization.",
    )
    problems = failures({"references": [reported_row]}, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Globex"], problems

    raw = "Human Rights Watch, acting with Acme, Globex & Umbra"
    assert capacity_list_surfaces(raw, entities, identity_index, "AAA", bound) == [
        "Acme", "Globex", "Umbra"
    ]
    report = {"references": [_row(
        raw,
        reason=(
            "Acme remains explicitly identity-deferred pending materialization; "
            "Globex remains explicitly identity-deferred pending materialization."
        ),
    )]}
    problems = failures(report, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Umbra"]

    mixed = (
        "Human Rights Watch, acting with Acme, Globex & Umbra as well as Initech / "
        "Soylent; Vehement"
    )
    assert capacity_list_surfaces(mixed, entities, identity_index, "AAA", bound) == [
        "Acme", "Globex", "Umbra", "Initech", "Soylent", "Vehement"
    ]

    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Jane Doe, in an advisory capacity",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Jane Doe"]

    control_bound = bound | {
        "ORG-ACME-INC", "ORG-SMITH-WESSON", "INST-MOJHR",
        "INST-REGIONAL-COUNCIL", "INST-INTERNATIONAL-COUNCIL",
    }
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Smith & Wesson, Globex",
        entities,
        identity_index,
        "AAA",
        control_bound,
    ) == ["Smith & Wesson", "Globex"]
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Acme, Inc. and Globex",
        entities,
        identity_index,
        "AAA",
        control_bound,
    ) == ["Acme, Inc", "Globex"]
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Ministry of Justice and Human Rights & Globex",
        entities,
        identity_index,
        "AAA",
        control_bound,
    ) == ["Ministry of Justice and Human Rights", "Globex"]

    for raw, expected in [
        (
            "Human Rights Watch, acting with the Ministry of Justice and Human Rights & Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with The Ministry of Justice and Human Rights, Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with a Regional Council or Globex",
            ["Regional Council", "Globex"],
        ),
        (
            "Human Rights Watch, acting with an International Council / Globex",
            ["International Council", "Globex"],
        ),
        (
            "Human Rights Watch, acting with “the Ministry of Justice and Human Rights” & Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with relevant Ministry of Justice and Human Rights & Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with the relevant Ministry of Justice and Human Rights & Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with participating Regional Council or Globex",
            ["Regional Council", "Globex"],
        ),
        # Unknown modifiers are not added to the accepted prefix grammar; exact anchors are
        # preserved structurally so the modifier cannot make the rest of the list opaque.
        (
            "Human Rights Watch, acting with competent Ministry of Justice and Human Rights & Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
        (
            "Human Rights Watch, acting with former Ministry of Justice and Human Rights or Globex",
            ["Ministry of Justice and Human Rights", "Globex"],
        ),
    ]:
        assert capacity_list_surfaces(raw, entities, identity_index, "AAA", control_bound) == expected, raw

    # The vocabulary itself remains closed-world: unknown modifiers are not reclassified as
    # accepted capacity syntax merely because an exact identity follows.
    assert not _leading_identity_prefix_allowed("competent ")
    assert not _leading_identity_prefix_allowed("former ")

    # End-to-end P1 regression: binding HRW and the exact ministry cannot discharge Globex
    # merely because an unknown contextual modifier precedes the ministry.
    unknown_modifier_row = _row(
        "Human Rights Watch, acting with competent Ministry of Justice and Human Rights & Globex",
        reason="remaining context deferred",
    )
    unknown_modifier_row["resolved_ids"] = ["ORG-HRW", "INST-MOJHR"]
    problems = failures({"references": [unknown_modifier_row]}, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Globex"], problems

    no_acme_entity = [item for item in entities if item["id"] != "ORG-ACME-INC"]
    raw_no_acme = [
        {"id": item["id"], "type": item["type"], "name": item["name"], "aliases": []}
        for item in no_acme_entity
    ]
    no_acme_index = build_name_index(raw_no_acme, state_codes={"AAA"}, normalizer=schedule.norm)
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Acme, Inc.",
        no_acme_entity,
        no_acme_index,
        "AAA",
        bound,
    ) == ["Acme"]

    print("Schedule capacity-list actor completeness self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, by_id, identity_index = schedule.load_entities()
    problems = failures(schedule.audit(), entities, by_id, identity_index)
    if problems:
        print("SCHEDULE_CAPACITY_LIST_ACTOR_GAPS=" + json.dumps(problems, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule capacity-list actor completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
