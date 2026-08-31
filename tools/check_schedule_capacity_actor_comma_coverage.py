#!/usr/bin/env python3
"""Fail closed on comma-delimited identities inside reviewed Schedule capacity tails.

The top-level actor-expression parser deliberately protects recognized capacity regions so
commas and conjunctions in legal/capacity prose are not mistaken for actor-list separators.
That protection must not make an identity list *inside* the capacity prose opaque. This
companion guard therefore inspects only relational capacity tails (for example ``acting with``)
and treats a comma as an actor separator only when the following fragment starts with a
high-confidence identity token and the comma is not inside an exact/complete institution span.

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


# Common comma continuations that are part of a name/corporate style rather than a new actor.
# Lower-case prose never enters the comma-split path in the first place.
COMMA_CONTINUATION_WORDS = {
    "co", "company", "corp", "corporation", "inc", "incorporated", "llc", "llp",
    "ltd", "limited", "plc", "jr", "sr", "ii", "iii", "iv",
}
COMMA_RE = re.compile(r"\s*,\s*")


def _comma_rhs_starts_identity(text: str) -> bool:
    """Return true only for a high-confidence actor-like start after a comma."""
    match = expression.SINGLE_IDENTITY_RE.match(text.lstrip())
    if not match:
        return False
    token = match.group(1)
    folded = token.casefold().rstrip(".")
    if folded in COMMA_CONTINUATION_WORDS:
        return False
    return expression._specific_single_identity_token(token)


def _protected_identity_spans(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[tuple[int, int]]:
    """Protect commas proven to belong to an exact or maximal institution surface."""
    return expression._merge_spans(
        expression.safe_actor_anchor_spans(text, entities, identity_index, state, bound_ids)
        + expression.heuristic_institution_spans(text)
    )


def _comma_list_fragments(
    text: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    """Split a capacity fragment on actor-like commas without splitting ordinary prose."""
    protected = _protected_identity_spans(text, entities, identity_index, state, bound_ids)
    pieces: list[str] = []
    start = 0
    for match in COMMA_RE.finditer(text):
        span = match.span()
        if expression._overlaps(span, protected):
            continue
        left = text[start:match.start()].strip()
        right = text[match.end():].lstrip()
        if not left or not right:
            continue
        # The left side must already carry an actor-like surface. This prevents punctuation
        # in introductory prose from turning a later capitalized word into a list member.
        if not expression._capacity_fragment_surfaces(left):
            continue
        if not _comma_rhs_starts_identity(right):
            continue
        pieces.append(left)
        start = match.end()
    tail = text[start:].strip()
    if tail:
        pieces.append(tail)
    return pieces


def capacity_comma_surfaces(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    bound_ids: set[str],
) -> list[str]:
    """Return identities exposed by comma-delimited lists inside recognized capacity prose."""
    out: list[str] = []
    for start, end in expression.capacity_spans(raw):
        region = raw[start:end]
        for cue in expression.CAPACITY_IDENTITY_CUE_RE.finditer(region):
            tail = region[cue.end():]
            # Slash/semicolon remain unambiguous strong separators. Comma splitting is then
            # applied locally to each strong component with identity-span protection.
            for strong_fragment in expression.STRONG_ACTOR_SEPARATOR_RE.split(tail):
                for fragment in _comma_list_fragments(
                    strong_fragment, entities, identity_index, state, bound_ids
                ):
                    for surface in expression._capacity_fragment_surfaces(fragment):
                        expression._add_unique(out, surface)
    return out


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        bound_ids = {item for item in row.get("resolved_ids") or [] if item in by_id}
        for surface in capacity_comma_surfaces(raw, entities, identity_index, state, bound_ids):
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
                    "reason": "comma-delimited capacity actor matches exact current identity not present in row binding",
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
                "reason": "comma-delimited capacity actor lacks exact binding or explicit surface deferral",
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
    ]
    raw_entities = [
        {"id": item["id"], "type": item["type"], "name": item["name"], "aliases": []}
        for item in entities
    ]
    identity_index = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    by_id = {item["id"]: item for item in entities}
    bound = {"ORG-HRW"}

    # P1 regression: every comma-delimited actor after the relational capacity cue survives.
    raw = "Human Rights Watch, acting with Acme, Globex"
    assert capacity_comma_surfaces(raw, entities, identity_index, "AAA", bound) == ["Acme", "Globex"]

    report = {"references": [_row(
        raw,
        reason="Acme remains explicitly identity-deferred pending materialization.",
    )]}
    problems = failures(report, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Globex"]

    # N-way lists remain monotonic: deferring one member cannot discharge its neighbours.
    raw_three = "Human Rights Watch, acting with Acme, Globex, Umbra"
    assert capacity_comma_surfaces(raw_three, entities, identity_index, "AAA", bound) == [
        "Acme", "Globex", "Umbra"
    ]

    # Ordinary lower-case capacity/prose tails are not comma actor separators.
    assert capacity_comma_surfaces(
        "Human Rights Watch, acting with Jane Doe, in an advisory capacity",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Jane Doe"]

    # A comma that is part of an exact organization surface remains protected, and common
    # corporate/person suffixes are not promoted to independent one-token actors.
    assert capacity_comma_surfaces(
        "Human Rights Watch, acting with Acme, Inc.",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Acme"]

    # Existing strong separators continue to compose with the new comma list handling.
    assert capacity_comma_surfaces(
        "Human Rights Watch, acting with Jane Doe / John Smith, Alice Brown",
        entities,
        identity_index,
        "AAA",
        bound,
    ) == ["Jane Doe", "John Smith", "Alice Brown"]

    print("Schedule capacity comma actor completeness self-test: OK")


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
        print("SCHEDULE_CAPACITY_COMMA_ACTOR_GAPS=" + json.dumps(problems, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule capacity comma actor completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
