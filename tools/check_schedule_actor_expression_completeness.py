#!/usr/bin/env python3
"""Fail closed on actor-expression components that other Schedule parsers can drop.

This guard treats actor-list segmentation as an identity-completeness concern only. It never
creates participation, control, operation, supply, membership, culpability, or governance
semantics. Exact actor surfaces protect separators that are genuinely part of a current
identity, while closed-world capacity spans protect legal/capacity prose from being mistaken
for actor alternatives. Every identity-like component exposed outside those spans must then
be exactly bound or explicitly deferred by surface.

The design deliberately enforces two monotonicity properties:

* materializing one actor cannot make neighbouring actor debt disappear; and
* deferring one actor cannot discharge a different actor component.

Recognized capacity prose is not opaque: high-confidence named identities introduced inside
it (for example ``acting with Jane Doe``) are independently audited so moving a name into a
capacity tail cannot bypass completeness checks.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_adversarial_identity_gaps as adversarial
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_schedule_parenthesized_actor_capacity as parenthesized
from entity_identity_resolution import build_name_index, eligible_in_state


ALTERNATIVE_SEPARATOR_RE = re.compile(r"\s+(?:and\s*/\s*or|and-or|or)\s+", re.I)
STRONG_ACTOR_SEPARATOR_RE = re.compile(r"\s*(?:/|;)\s*")
INLINE_CAPACITY_RE = re.compile(
    r"(?i)(?:,\s*only\b|\s+only\s+(?:when|where|in|to\s+the\s+extent)\b)"
)
CAPACITY_IDENTITY_CUE_RE = re.compile(
    r"(?i)\b(?:assisted\s+by|represented\s+by|together\s+with|alongside|with|through|by|or|and)\s+"
)
SINGLE_IDENTITY_RE = re.compile(
    r"^[\"'“‘([{*_`]*([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]{1,})\b",
    re.UNICODE,
)
WHOLE_SINGLE_IDENTITY_RE = re.compile(
    r"^[\"'“‘([{*_`]*([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]{1,})[\"'”’)]}*_`.,:;!?]*$",
    re.UNICODE,
)
TITLE_TOKEN_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*$", re.UNICODE)
SINGLE_CONTEXT_WORDS = {
    "federal", "regional", "local", "national", "state", "successor", "relevant",
    "participating", "materially", "specific", "protected", "territorial", "municipal",
}


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(set(spans)):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < other_end and other_start < end for other_start, other_end in spans)


def _literal_surface_pattern(text: str) -> str:
    """Match one exact surface with flexible whitespace but no structural punctuation jumps."""
    out: list[str] = []
    in_space = False
    for char in text:
        if char.isspace():
            if not in_space:
                out.append(r"\s+")
                in_space = True
            continue
        in_space = False
        if char in "'’":
            out.append("['’]")
        elif char == "-":
            out.append("[-‐‑]")
        else:
            out.append(re.escape(char))
    return "".join(out)


def safe_actor_anchor_spans(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    row_bound_ids: set[str] | None = None,
) -> list[tuple[int, int]]:
    """Return exact actor spans without allowing an anchor to cross actor separators.

    State-safe entities are anchors automatically. A reviewed row may also bind an exact
    cross-State identity deliberately, so its actual ``resolved_ids`` are eligible anchors
    even when normal heuristic State eligibility would reject them.
    """
    bound = row_bound_ids or set()
    spans: list[tuple[int, int]] = []
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            continue
        if entity.get("type") in {"Project", "Deployment"}:
            continue
        if entity_id not in bound and not eligible_in_state(identity_index, entity_id, state):
            continue
        forms = entity.get("surface_forms") or [
            {"text": value}
            for value in [entity.get("name"), *(entity.get("aliases") or [])]
            if isinstance(value, str) and value.strip()
        ]
        for form in forms:
            text = form.get("text") or ""
            if not text.strip():
                continue
            if exact.looks_like_acronym_surface(text):
                pattern = rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])"
                flags = 0
            else:
                pattern = rf"(?<!\w){_literal_surface_pattern(text)}(?!\w)"
                flags = re.I | re.UNICODE
            spans.extend(match.span() for match in re.finditer(pattern, raw, flags))
    return _merge_spans(spans)


def parenthesized_capacity_spans(raw: str) -> list[tuple[int, int]]:
    """Protect balanced parenthesized text only when it begins with closed-world capacity syntax."""
    stack: list[int] = []
    spans: list[tuple[int, int]] = []
    for index, char in enumerate(raw):
        if char == "(":
            stack.append(index)
        elif char == ")" and stack:
            start = stack.pop()
            inner = raw[start + 1:index].strip()
            if strict.CAPACITY_TAIL_RE.match(inner):
                spans.append((start, index + 1))
    return _merge_spans(spans)


def capacity_spans(raw: str) -> list[tuple[int, int]]:
    """Return terminal capacity regions whose internal conjunctions are not actor separators."""
    spans = parenthesized_capacity_spans(raw)
    for match in re.finditer(r",", raw):
        tail = raw[match.end():].lstrip()
        if strict.CAPACITY_TAIL_RE.match(tail):
            spans.append((match.start(), len(raw)))
    inline = INLINE_CAPACITY_RE.search(raw)
    if inline:
        spans.append((inline.start(), len(raw)))
    return _merge_spans(spans)


def structural_separator_spans(
    raw: str,
    anchor_spans: list[tuple[int, int]],
    capacity_regions: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Return non-overlapping actor separators outside exact anchors and capacity prose."""
    protected = _merge_spans(anchor_spans + capacity_regions)
    candidates: list[tuple[int, int, int]] = []

    # Alternatives have highest priority so ``and / or`` is one separator rather than a
    # conjunction plus a slash.
    for priority, regex in (
        (0, ALTERNATIVE_SEPARATOR_RE),
        (1, strict.ACTOR_LIST_SEPARATOR_RE),
        (2, STRONG_ACTOR_SEPARATOR_RE),
    ):
        for match in regex.finditer(raw):
            span = match.span()
            if _overlaps(span, protected):
                continue
            candidates.append((span[0], span[1], priority))

    selected: list[tuple[int, int]] = []
    for start, end, priority in sorted(candidates, key=lambda item: (item[0], item[2], -(item[1] - item[0]))):
        span = (start, end)
        if _overlaps(span, selected):
            continue
        selected.append(span)
    return sorted(selected)


def actor_components(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    row_bound_ids: set[str] | None = None,
) -> list[str]:
    """Split every top-level actor-list component without requiring a materialized anchor."""
    anchors = safe_actor_anchor_spans(raw, entities, identity_index, state, row_bound_ids)
    capacities = capacity_spans(raw)
    separators = structural_separator_spans(raw, anchors, capacities)
    if not separators:
        return []

    pieces: list[str] = []
    start = 0
    for sep_start, sep_end in separators:
        piece = raw[start:sep_start].strip()
        if piece:
            pieces.append(piece)
        start = sep_end
    piece = raw[start:].strip()
    if piece:
        pieces.append(piece)
    return pieces


def _add_unique(out: list[str], value: str | None) -> None:
    if value:
        cleaned = " ".join(value.split()).strip(" \t\r\n,;:[]{}\"'“”‘’*_`.")
        if cleaned and cleaned not in out:
            out.append(cleaned)


def _specific_single_identity_token(token: str) -> bool:
    """Reject title-cased legal adjectives while retaining real one-token actor surfaces."""
    folded = token.casefold()
    if folded in strict.STOPWORDS or folded in strict.PARTICLES or folded in SINGLE_CONTEXT_WORDS:
        return False
    if "-" in token:
        parts = [part for part in token.split("-") if part]
        if len(parts) < 2 or not all(part[0].isupper() for part in parts):
            return exact.looks_like_acronym_surface(token)
    return True


def _complete_institution_surface(component: str, label: str) -> str | None:
    """Accept only a maximal institution surface, never a stem extracted from richer prose."""
    cleaned = parenthesized.normalized_component(component).strip(" \t\r\n\"'“”‘’[]{}*_`")
    if not cleaned.casefold().startswith(label.casefold()):
        return None
    suffix = cleaned[len(label):].strip()
    if not suffix:
        return label

    # Parenthesized translated/acronym locators may follow an otherwise complete surface.
    if suffix.startswith("(") and suffix.endswith(")") and suffix.count("(") == suffix.count(")") == 1:
        return label

    # The adversarial institution parser can stop before a final proper locator token
    # (e.g. ``Rescue Coordination Centre Malta``). Extend only when the entire remaining
    # component is a short title-cased suffix; never swallow an em-dash locator or prose.
    suffix_tokens = suffix.split()
    if 1 <= len(suffix_tokens) <= 3 and all(TITLE_TOKEN_RE.fullmatch(token) for token in suffix_tokens):
        return f"{label} {suffix}".strip()
    return None


def component_identity_surfaces(component: str) -> list[str]:
    """Return high-confidence complete identity surfaces carried by one actor component."""
    out: list[str] = []
    normalized = parenthesized.normalized_component(component)

    candidate = parenthesized.parenthesized_actor_component(normalized)
    if candidate is None:
        candidate = strict.actor_component_name(normalized)
    _add_unique(out, candidate)

    for label in adversarial.named_institution_labels(normalized):
        complete = _complete_institution_surface(normalized, label)
        if complete and len(schedule.norm(complete).split()) >= 2:
            _add_unique(out, complete)

    _add_unique(out, strict.full_name_phrase(normalized, allow_all_caps=True))

    single = WHOLE_SINGLE_IDENTITY_RE.fullmatch(normalized.strip())
    if single:
        token = single.group(1)
        if _specific_single_identity_token(token):
            _add_unique(out, token)
    return out


def capacity_identity_surfaces(raw: str) -> list[str]:
    """Find named actors introduced inside recognized capacity prose.

    Generic legal alternatives remain ignored because the cue must be followed by a
    title-cased/name-like surface. This catches moves such as ``acting with Jane Doe`` or
    ``acting as adviser or John Smith`` without treating ``or successor powers`` as an actor.
    """
    out: list[str] = []
    for start, end in capacity_spans(raw):
        region = raw[start:end]
        for cue in CAPACITY_IDENTITY_CUE_RE.finditer(region):
            tail = region[cue.end():].lstrip()
            candidate = strict.leading_name_phrase(tail, allow_all_caps=True)
            if candidate:
                _add_unique(out, candidate)
                continue

            for label in adversarial.named_institution_labels(tail[:160]):
                complete = _complete_institution_surface(tail[:160], label)
                if complete:
                    _add_unique(out, complete)
                    break
            else:
                single = SINGLE_IDENTITY_RE.match(tail)
                if single:
                    token = single.group(1)
                    if _specific_single_identity_token(token):
                        _add_unique(out, token)
    return out


def exact_actor_ids_for_surface(
    surface: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    row_bound_ids: set[str],
) -> set[str]:
    """Return exact actor IDs for a complete surface, including reviewed cross-State bindings."""
    surface_norm = schedule.norm(surface)
    matches: set[str] = set()
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or entity.get("type") in {"Project", "Deployment"}:
            continue
        if entity_id not in row_bound_ids and not eligible_in_state(identity_index, entity_id, state):
            continue
        forms = entity.get("surface_forms") or [
            {"text": value, "normalized": schedule.norm(value)}
            for value in [entity.get("name"), *(entity.get("aliases") or [])]
            if isinstance(value, str) and value.strip()
        ]
        for form in forms:
            text = form.get("text") or ""
            normalized = form.get("normalized") or schedule.norm(text)
            if normalized and normalized == surface_norm:
                matches.add(entity_id)
                break
    return matches


def _bound_identity_extends_surface(surface: str, raw: str, bound_ids: set[str], by_id: dict[str, dict]) -> bool:
    """Suppress only a parser stem proven to sit inside a longer exact bound surface in raw."""
    surface_tokens = schedule.norm(surface).split()
    raw_tokens = schedule.norm(raw).split()
    if not surface_tokens:
        return False
    for entity_id in bound_ids:
        entity = by_id.get(entity_id) or {}
        forms = entity.get("surface_forms") or [
            {"text": value, "normalized": schedule.norm(value)}
            for value in [entity.get("name"), *(entity.get("aliases") or [])]
            if isinstance(value, str) and value.strip()
        ]
        for form in forms:
            normalized = form.get("normalized") or schedule.norm(form.get("text") or "")
            form_tokens = normalized.split()
            if len(form_tokens) <= len(surface_tokens) or form_tokens[:len(surface_tokens)] != surface_tokens:
                continue
            width = len(form_tokens)
            if any(raw_tokens[index:index + width] == form_tokens for index in range(len(raw_tokens) - width + 1)):
                return True
    return False


def explicitly_defers_surface(row: dict, surface: str) -> bool:
    """Require the exact complete surface immediately followed by explicit deferral grammar."""
    if row.get("resolution_source") != "reviewed-disposition":
        return False
    if row.get("status") not in {"deferred", "partial-deferred"}:
        return False
    mention_tokens = strict.reason_tokens(surface)
    reason_tokens = strict.reason_tokens(row.get("disposition_reason") or "")
    if not mention_tokens or not reason_tokens:
        return False
    n = len(mention_tokens)
    bridges = set(strict.DEFER_BRIDGE) | {"are"}
    for index in range(0, len(reason_tokens) - n + 1):
        if reason_tokens[index:index + n] != mention_tokens:
            continue
        tail = reason_tokens[index + n:index + n + 7]
        if not tail or tail[0] not in bridges | strict.DEFER_WORDS:
            continue
        for token in tail:
            if token in strict.DEFER_WORDS or token.endswith("-deferred"):
                return True
            if token not in bridges:
                break
    return False


def failures(report: dict, entities: list[dict], by_id: dict[str, dict], identity_index) -> list[dict]:
    """Reject structural actor components that are silently dropped by other guards."""
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        bound_ids = {item for item in row.get("resolved_ids") or [] if item in by_id}

        surfaces: list[str] = []
        for component in actor_components(raw, entities, identity_index, state, bound_ids):
            for surface in component_identity_surfaces(component):
                _add_unique(surfaces, surface)
        for surface in capacity_identity_surfaces(raw):
            _add_unique(surfaces, surface)

        for surface in surfaces:
            if _bound_identity_extends_surface(surface, raw, bound_ids, by_id):
                continue
            exact_ids = exact_actor_ids_for_surface(surface, entities, identity_index, state, bound_ids)
            if exact_ids:
                missing = sorted(exact_ids - bound_ids)
                if not missing:
                    continue
                found.append({
                    "reason": "actor-expression component matches exact current identity not present in row binding",
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

            if explicitly_defers_surface(row, surface) or strict.explicitly_defers_complete_name(row, surface):
                continue
            found.append({
                "reason": "actor-expression component lacks exact binding or explicit surface deferral",
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


def _row(raw: str, *, resolved_ids: list[str] | None = None, reason: str = "remaining actor context is deferred.") -> dict:
    return {
        "kind": "actor-reference",
        "state": "AAA",
        "field": "candidate_parties",
        "source": "x.yml",
        "raw": raw,
        "status": "partial-deferred" if resolved_ids else "deferred",
        "resolution_source": "reviewed-disposition",
        "resolved_ids": resolved_ids or [],
        "disposition_reason": reason,
    }


def self_test() -> None:
    entities = [
        _entity("ORG-HRW", "Organization", "Human Rights Watch"),
        _entity("ORG-TRUTH", "Organization", "Truth or Reconciliation Institute"),
        _entity("ORG-LEGER", "Organization", "Leger des Heils Jeugdbescherming & Reclassering"),
        _entity("AGENCY-AAA-MINISTRY", "Agency", "Ministry of Interior and Narcotics Control"),
        _entity("AGENCY-AAA-MEDIA", "Agency", "Maldives Media and Broadcasting Commission"),
        _entity("AGENCY-AAA-RCC", "Agency", "Rescue Coordination Centre Malta"),
        _entity("PERSON-ESRA", "Person", "Esra Işık"),
        _entity("ORG-META", "Organization", "Meta"),
    ]
    raw_entities = [
        {"id": item["id"], "type": item["type"], "name": item["name"], "aliases": []}
        for item in entities
    ]
    identity_index = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    by_id = {item["id"]: item for item in entities}

    assert actor_components("Jane Doe or John Smith", entities, identity_index, "AAA") == ["Jane Doe", "John Smith"]
    assert actor_components("Jane Doe and/or John Smith", entities, identity_index, "AAA") == ["Jane Doe", "John Smith"]
    assert actor_components("Jane Doe and / or John Smith", entities, identity_index, "AAA") == ["Jane Doe", "John Smith"]
    assert actor_components("Jane Doe or John Smith or Alice Brown", entities, identity_index, "AAA") == [
        "Jane Doe", "John Smith", "Alice Brown"
    ]
    assert actor_components("Human Rights Watch and Jane Doe or John Smith", entities, identity_index, "AAA") == [
        "Human Rights Watch", "Jane Doe", "John Smith"
    ]
    assert actor_components("Human Rights Watch / Jane Doe or John Smith", entities, identity_index, "AAA") == [
        "Human Rights Watch", "Jane Doe", "John Smith"
    ]
    assert actor_components("Truth or Reconciliation Institute or Jane Doe", entities, identity_index, "AAA") == [
        "Truth or Reconciliation Institute", "Jane Doe"
    ]
    assert actor_components("Ministry of Interior and Narcotics Control or Jane Doe", entities, identity_index, "AAA") == [
        "Ministry of Interior and Narcotics Control", "Jane Doe"
    ]
    assert actor_components("Leger des Heils Jeugdbescherming & Reclassering", entities, identity_index, "AAA") == []

    # Exact anchors are literal enough that actor punctuation cannot be normalized through.
    assert safe_actor_anchor_spans("Human / Rights Watch or Jane Doe", entities, identity_index, "AAA") == []

    # Institution extraction must keep a complete proper locator rather than a parser stem.
    assert component_identity_surfaces("Rescue Coordination Centre Malta") == ["Rescue Coordination Centre Malta"]
    assert component_identity_surfaces(
        "Police Directorate (Ravnateljstvo policije) — Border Directorate (Uprava za granicu)"
    ) == []

    # Parenthesized and terminal capacity prose protects its own conjunctions, while an
    # external alternative remains structural.
    assert actor_components(
        "Jane Doe (acting as adviser or observer) or John Smith", entities, identity_index, "AAA"
    ) == ["Jane Doe (acting as adviser or observer)", "John Smith"]
    assert actor_components(
        "Maldives Media and Broadcasting Commission, only when enforcing Act 16/2025 or successor powers",
        entities,
        identity_index,
        "AAA",
    ) == []
    assert capacity_identity_surfaces("Jane Doe, acting as adviser or observer") == []
    assert capacity_identity_surfaces("Jane Doe, acting as adviser or John Smith") == ["John Smith"]
    assert capacity_identity_surfaces("Jane Doe (acting with John Smith)") == ["John Smith"]
    assert capacity_identity_surfaces("Jane Doe, only where assisted by John Smith") == ["John Smith"]
    assert capacity_identity_surfaces("Jane Doe, acting with Meta") == ["Meta"]
    assert capacity_identity_surfaces("Jane Doe, only where enforcing statute or State-security offences") == []

    # P1: no materialized anchor is required. Generic review cannot discharge either name.
    report = {"references": [_row("Jane Doe or John Smith")]}
    problems = failures(report, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Jane Doe", "John Smith"]

    # Deferral locality: naming John Smith does not discharge Jane Doe.
    report["references"][0]["disposition_reason"] = "John Smith remains explicitly identity-deferred pending materialization."
    problems = failures(report, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Jane Doe"]
    report["references"][0]["disposition_reason"] = (
        "Jane Doe remains explicitly identity-deferred; John Smith remains explicitly identity-deferred."
    )
    assert failures(report, entities, by_id, identity_index) == []

    # Materialization monotonicity: binding HRW may discharge HRW itself, never its neighbours.
    raw = "Human Rights Watch and Jane Doe or John Smith"
    unmaterialized_entities = [item for item in entities if item["id"] != "ORG-HRW"]
    unmaterialized_raw = [item for item in raw_entities if item["id"] != "ORG-HRW"]
    unmaterialized_index = build_name_index(unmaterialized_raw, state_codes={"AAA"}, normalizer=schedule.norm)
    before = []
    for component in actor_components(raw, unmaterialized_entities, unmaterialized_index, "AAA"):
        before.extend(component_identity_surfaces(component))
    after = []
    for component in actor_components(raw, entities, identity_index, "AAA", {"ORG-HRW"}):
        after.extend(component_identity_surfaces(component))
    assert {"Jane Doe", "John Smith"} <= set(before)
    assert {"Jane Doe", "John Smith"} <= set(after)

    mixed = {"references": [_row(
        raw,
        resolved_ids=["ORG-HRW"],
        reason="Human Rights Watch is bound exactly; John Smith remains explicitly identity-deferred.",
    )]}
    problems = failures(mixed, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["Jane Doe"]

    # Moving an actor name into recognized capacity prose still leaves explicit identity debt.
    hidden = {"references": [_row(
        "Human Rights Watch / Jane Doe, acting with John Smith",
        resolved_ids=["ORG-HRW"],
        reason="Jane Doe remains explicitly identity-deferred.",
    )]}
    problems = failures(hidden, entities, by_id, identity_index)
    assert [problem["identity_surface"] for problem in problems] == ["John Smith"]

    print("Schedule actor-expression completeness self-test: OK")


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
        print("SCHEDULE_ACTOR_EXPRESSION_GAPS=" + json.dumps(problems, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule actor-expression completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
