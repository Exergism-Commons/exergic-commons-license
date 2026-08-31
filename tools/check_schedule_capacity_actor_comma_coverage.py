#!/usr/bin/env python3
"""Fail closed on actor lists embedded inside reviewed Schedule capacity tails.

The top-level actor-expression parser deliberately protects recognized capacity regions so
commas and conjunctions in legal/capacity prose are not mistaken for top-level actor-list
separators. That protection must not make an identity list *inside* the capacity prose opaque.

This companion guard therefore inspects only relational capacity tails (for example
``acting with``) and applies one protected list grammar covering the same separator families
accepted elsewhere by the Schedule actor parser: comma/Oxford-comma forms, ``and``, ``&``,
``or``, ``and/or`` / ``and / or`` / ``and-or``, slash, and semicolon. A separator is active
only when it lies outside an exact current actor span or maximal institution span, the left
fragment already carries an actor-like surface, and the right fragment starts with a
high-confidence identity surface. This keeps commas/conjunctions inside proven identity names
opaque while preventing neighbouring capacity-list members from disappearing.

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
from entity_identity_resolution import build_name_index


# Common continuations that are part of a name/corporate style rather than a new actor.
# Lower-case prose never enters the split path in the first place.
IDENTITY_CONTINUATION_WORDS = {
    "co", "company", "corp", "corporation", "inc", "incorporated", "llc", "llp",
    "ltd", "limited", "plc", "jr", "sr", "ii", "iii", "iv",
}

# One grammar for every actor-list separator family currently recognized by the Schedule
# parser. The comma alternative absorbs an optional coordinator so Oxford forms such as
# ``Acme, and Globex`` cannot leave a leading ``and`` attached to the next member.
CAPACITY_LIST_SEPARATOR_RE = re.compile(
    r"""
    \s*
    (?:
        ,\s*(?:(?:and\s*/\s*or|and-or|and/or|and|or|&)\s+)?
      | \band\s*/\s*or\b
      | \band-or\b
      | \band/or\b
      | \band\b
      | \bor\b
      | &
      | /
      | ;
    )
    \s*
    """,
    re.I | re.X,
)
OPENING_IDENTITY_WRAPPERS = " \t\r\n\"'“‘([{*_`"


def _protected_identity_spans(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[tuple[int, int]]:
    """Protect separators proven to belong to an exact or maximal institution surface."""
    return expression._merge_spans(
        expression.safe_actor_anchor_spans(text, entities, identity_index, state, bound_ids)
        + expression.heuristic_institution_spans(text)
    )


def _leading_protected_surface(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> str | None:
    """Return a complete protected identity when one begins the fragment.

    This is important for names whose own spelling contains a separator, e.g. an exact
    ``Smith & Wesson`` or ``Acme, Inc.`` surface, and for maximal institution names with
    internal conjunctions. Protecting the separator is insufficient if the fallback leading
    name parser would then truncate the same identity.
    """
    spans = _protected_identity_spans(text, entities, identity_index, state, bound_ids)
    candidates: list[tuple[int, int]] = []
    for start, end in spans:
        prefix = text[:start].strip(OPENING_IDENTITY_WRAPPERS)
        if not prefix:
            candidates.append((start, end))
    if not candidates:
        return None
    start, end = sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0])))[0]
    surface = text[start:end].strip(" \t\r\n,;:[]{}\"'“”‘’*_`.")
    return surface or None


def _fragment_surfaces(
    fragment: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    """Return the complete leading actor surface carried by one capacity-list fragment."""
    protected = _leading_protected_surface(fragment, entities, identity_index, state, bound_ids)
    if protected:
        return [protected]
    return expression._capacity_fragment_surfaces(fragment)


def _rhs_starts_identity(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> bool:
    """Require a high-confidence actor-like start after a candidate separator."""
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
    """Split one relational capacity tail on protected actor-list separators.

    Separator recognition is deliberately conditional rather than a blind ``re.split``:
    separators inside exact/maximal identity spans are ignored, and every accepted split must
    be locally supported by actor-like material on both sides. This gives all supported
    separator spellings the same fail-closed semantics without turning legal prose into a list.
    """
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
    """Return identities exposed by any supported list syntax inside capacity prose."""
    out: list[str] = []
    for start, end in expression.capacity_spans(raw):
        region = raw[start:end]
        for cue in expression.CAPACITY_IDENTITY_CUE_RE.finditer(region):
            tail = region[cue.end():]
            for fragment in _capacity_list_fragments(
                tail, entities, identity_index, state, bound_ids
            ):
                for surface in _fragment_surfaces(
                    fragment, entities, identity_index, state, bound_ids
                ):
                    expression._add_unique(out, surface)
    return out


# Backward-compatible name for any local callers introduced with the original comma-only
# guard. Semantics are intentionally widened to the complete protected capacity-list grammar.
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
    ]
    raw_entities = [
        {"id": item["id"], "type": item["type"], "name": item["name"], "aliases": []}
        for item in entities
    ]
    identity_index = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    by_id = {item["id"]: item for item in entities}
    bound = {"ORG-HRW"}

    # Every separator family recognized by the Schedule actor grammar is covered inside a
    # relational capacity tail. These are deliberately table-driven so adding a separator to
    # one branch without the others breaks the self-test instead of creating another bypass.
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
        "Acme / Globex",
        "Acme; Globex",
    ]
    for actor_list in separator_cases:
        raw = f"Human Rights Watch, acting with {actor_list}"
        assert capacity_list_surfaces(raw, entities, identity_index, "AAA", bound) == [
            "Acme", "Globex"
        ], actor_list

    # Original comma P1 plus the ampersand follow-up: every neighbour remains independent.
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

    # Mixed/N-way composition: no separator family can make a later member disappear.
    mixed = (
        "Human Rights Watch, acting with Acme, Globex & Umbra and/or Initech / "
        "Soylent; Vehement"
    )
    assert capacity_list_surfaces(mixed, entities, identity_index, "AAA", bound) == [
        "Acme", "Globex", "Umbra", "Initech", "Soylent", "Vehement"
    ]

    # Ordinary lower-case capacity/prose tails do not become actor members.
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Jane Doe, in an advisory capacity",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Jane Doe"]

    # Exact/maximal identity spans protect their own separators. The extraction path must also
    # preserve the *complete* protected surface rather than truncating at the internal symbol.
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Smith & Wesson, Globex",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Smith & Wesson", "Globex"]
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Acme, Inc. and Globex",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Acme, Inc", "Globex"]
    assert capacity_list_surfaces(
        "Human Rights Watch, acting with Ministry of Justice and Human Rights & Globex",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Ministry of Justice and Human Rights", "Globex"]

    # A suffix-like continuation is never promoted as a fresh one-token actor when no exact
    # protected identity proves that the comma belongs to a larger current surface.
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
