#!/usr/bin/env python3
"""Shared jurisdiction-safe identity-name resolution for ECL audit tools.

Domestic identities are inferred from IDs whose first token after the entity-kind prefix is
one of the canonical State ISO3 codes, for example `AGENCY-USA-*` or
`INSTITUTION-SVK-*`. Their names and aliases resolve automatically only inside that State.
Identities without such a canonical State token are treated as transnational/global for
name-resolution purposes.

This is a resolver-scoping rule only. It does not assert jurisdiction, membership, partOf,
control, participation, operation, attribution or governance in the ontology.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable

DOMESTIC_ID_RE = re.compile(
    r"^(?:AGENCY|INSTITUTION|ORG|PROJECT|DEPLOYMENT|PERSON)-([A-Z]{3})(?:-|$)"
)


def infer_domestic_state(entity_id: str, state_codes: set[str]) -> str | None:
    match = DOMESTIC_ID_RE.match(entity_id)
    if not match:
        return None
    state = match.group(1)
    return state if state in state_codes else None


@dataclass
class NameIndex:
    global_names: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    state_names: dict[str, dict[str, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    by_id: dict[str, dict] = field(default_factory=dict)
    state_codes: set[str] = field(default_factory=set)


def build_name_index(
    entities: Iterable[dict], *, state_codes: set[str], normalizer: Callable[[str], str]
) -> NameIndex:
    index = NameIndex(state_codes=set(state_codes))
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str):
            continue
        index.by_id[entity_id] = entity
        scope = infer_domestic_state(entity_id, state_codes)
        values = [entity.get("name"), *(entity.get("aliases") or [])]
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = normalizer(value)
            if not normalized:
                continue
            if scope:
                index.state_names[scope][normalized].add(entity_id)
            else:
                index.global_names[normalized].add(entity_id)
    return index


def resolve_normalized(index: NameIndex, *, state: str, normalized: str) -> list[str]:
    """Resolve a normalized name without cross-State domestic leakage.

    A local domestic name shadows a same-text global name. Multiple matches remain
    ambiguous. Domestic identities from other States are never considered here; a
    cross-State domestic reference must be explicitly reviewed/bound by the caller's
    disposition surface.
    """
    local = index.state_names.get(state, {}).get(normalized, set())
    if local:
        return sorted(local)
    return sorted(index.global_names.get(normalized, set()))


def eligible_in_state(index: NameIndex, entity_id: str, state: str | None) -> bool:
    scope = infer_domestic_state(entity_id, index.state_codes)
    return scope is None or (state is not None and scope == state)


def self_test() -> None:
    def n(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())

    states = {"KAZ", "SVK", "AUS", "NRU"}
    entities = [
        {
            "id": "INSTITUTION-SVK-CONSTITUTIONAL-COURT",
            "name": "Constitutional Court of Slovakia",
            "aliases": ["Constitutional Court"],
        },
        {
            "id": "INSTITUTION-KAZ-CONSTITUTIONAL-COURT",
            "name": "Constitutional Court of Kazakhstan",
            "aliases": ["Constitutional Court"],
        },
        {
            "id": "INSTITUTION-AUS-HUMAN-RIGHTS-COMMISSION",
            "name": "Australian Human Rights Commission",
            "aliases": [],
        },
        {"id": "ORG-OHCHR", "name": "OHCHR", "aliases": ["UN Human Rights Office"]},
    ]
    index = build_name_index(entities, state_codes=states, normalizer=n)
    assert resolve_normalized(index, state="SVK", normalized=n("Constitutional Court")) == [
        "INSTITUTION-SVK-CONSTITUTIONAL-COURT"
    ]
    assert resolve_normalized(index, state="KAZ", normalized=n("Constitutional Court")) == [
        "INSTITUTION-KAZ-CONSTITUTIONAL-COURT"
    ]
    assert resolve_normalized(index, state="NRU", normalized=n("Constitutional Court")) == []
    # Cross-State domestic references require an explicit reviewed binding.
    assert resolve_normalized(index, state="NRU", normalized=n("Australian Human Rights Commission")) == []
    # Truly global/transnational identity names may resolve across State dossiers.
    assert resolve_normalized(index, state="NRU", normalized=n("OHCHR")) == ["ORG-OHCHR"]
    assert eligible_in_state(index, "INSTITUTION-SVK-CONSTITUTIONAL-COURT", "KAZ") is False
    assert eligible_in_state(index, "ORG-OHCHR", "KAZ") is True


if __name__ == "__main__":
    self_test()
    print("entity identity resolution self-test: OK")
