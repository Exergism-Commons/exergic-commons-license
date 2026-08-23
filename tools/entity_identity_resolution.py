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

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
ENTITY_DIR = ROOT / "knowledge" / "entities"
GENERATED_DIR = ROOT / "knowledge" / "generated"
SUPERSESSION_GLOB = "entity-id-supersessions-v*.json"

DOMESTIC_ID_RE = re.compile(
    r"^(?:AGENCY|INSTITUTION|ORG|PROJECT|DEPLOYMENT|PERSON)-([A-Z]{3})(?:-|$)"
)


def infer_domestic_state(entity_id: str, state_codes: set[str]) -> str | None:
    match = DOMESTIC_ID_RE.match(entity_id)
    if not match:
        return None
    state = match.group(1)
    return state if state in state_codes else None


def load_id_supersessions() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted(GENERATED_DIR.glob(SUPERSESSION_GLOB)):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data.get("version"), int) and data["version"] >= 1, path
        for row in data.get("supersessions", []):
            source = row.get("from")
            target = row.get("to")
            reason = row.get("reason")
            assert isinstance(source, str) and source, (path, row)
            assert isinstance(target, str) and target and target != source, (path, row)
            assert isinstance(reason, str) and reason.strip(), (path, row)
            assert source.split("-", 1)[0] == target.split("-", 1)[0], (
                "supersession must preserve identity kind", path, row
            )
            assert source not in mapping, f"duplicate identity supersession source: {source}"
            mapping[source] = target

    chained = sorted(source for source, target in mapping.items() if target in mapping)
    assert not chained, f"identity supersession chains are forbidden: {chained}"
    return mapping


def canonicalize_id(entity_id: str, supersessions: dict[str, str]) -> str:
    return supersessions.get(entity_id, entity_id)


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
    supersessions = load_id_supersessions()
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or entity_id in supersessions:
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
    local = index.state_names.get(state, {}).get(normalized, set())
    if local:
        return sorted(local)
    return sorted(index.global_names.get(normalized, set()))


def eligible_in_state(index: NameIndex, entity_id: str, state: str | None) -> bool:
    scope = infer_domestic_state(entity_id, index.state_codes)
    return scope is None or (state is not None and scope == state)


def default_normalizer(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def load_repository_entities() -> tuple[list[dict], set[str]]:
    entities: list[dict] = []
    entity_ids: set[str] = set()
    for path in sorted(ENTITY_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        entities.append(data)
        entity_id = data.get("id")
        if isinstance(entity_id, str):
            entity_ids.add(entity_id)
    return entities, entity_ids


def repository_state_names(entities: list[dict]) -> tuple[set[str], dict[str, str]]:
    states: set[str] = set()
    names: dict[str, str] = {}
    for data in entities:
        entity_id = data.get("id")
        name = data.get("name")
        if data.get("type") != "State" or not isinstance(entity_id, str) or not entity_id.startswith("STATE-"):
            continue
        state = entity_id.removeprefix("STATE-")
        if len(state) != 3 or not isinstance(name, str):
            continue
        states.add(state)
        names[state] = default_normalizer(name)
    return states, names


def audit_repository_primary_name_uniqueness() -> list[dict[str, object]]:
    entities, _ = load_repository_entities()
    state_codes, _ = repository_state_names(entities)
    supersessions = load_id_supersessions()
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for entity in entities:
        entity_id = entity.get("id")
        name = entity.get("name")
        if not isinstance(entity_id, str) or not isinstance(name, str) or entity_id in supersessions:
            continue
        normalized = default_normalizer(name)
        if not normalized:
            continue
        scope = infer_domestic_state(entity_id, state_codes) or "GLOBAL"
        groups[(scope, normalized)].add(entity_id)
    return [
        {"scope": scope, "normalized_name": normalized, "ids": sorted(ids)}
        for (scope, normalized), ids in sorted(groups.items())
        if len(ids) > 1
    ]


def domestic_primary_signature(name: str, state_name: str) -> str:
    """Strip only an exact leading/trailing State name from a domestic primary name.

    This catches equivalent naming order such as `South Sudan National Security Service`
    versus `National Security Service (South Sudan)` without fuzzy matching unrelated bodies.
    """
    normalized = default_normalizer(name)
    state = default_normalizer(state_name)
    if not normalized or not state:
        return normalized
    if normalized.startswith(state + " "):
        normalized = normalized[len(state) + 1 :]
    elif normalized.endswith(" of " + state):
        normalized = normalized[: -(len(state) + 4)]
    elif normalized.endswith(" " + state):
        normalized = normalized[: -(len(state) + 1)]
    return normalized.strip()


def audit_domestic_state_qualified_primary_duplicates() -> list[dict[str, object]]:
    entities, _ = load_repository_entities()
    state_codes, state_names = repository_state_names(entities)
    supersessions = load_id_supersessions()
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for entity in entities:
        entity_id = entity.get("id")
        name = entity.get("name")
        if not isinstance(entity_id, str) or not isinstance(name, str) or entity_id in supersessions:
            continue
        scope = infer_domestic_state(entity_id, state_codes)
        if scope is None:
            continue
        signature = domestic_primary_signature(name, state_names[scope])
        if len(signature) < 6:
            continue
        groups[(scope, signature)].add(entity_id)
    return [
        {"state": state, "state_stripped_primary": signature, "ids": sorted(ids)}
        for (state, signature), ids in sorted(groups.items())
        if len(ids) > 1
    ]


def audit_supersession_integrity() -> dict[str, list[str]]:
    _, entity_ids = load_repository_entities()
    supersessions = load_id_supersessions()
    return {
        "missing_targets": sorted(target for target in supersessions.values() if target not in entity_ids),
        "materialized_sources": sorted(source for source in supersessions if source in entity_ids),
    }


def self_test() -> None:
    states = {"KAZ", "SVK", "AUS", "NRU"}
    entities = [
        {"id":"INSTITUTION-SVK-CONSTITUTIONAL-COURT","name":"Constitutional Court of Slovakia","aliases":["Constitutional Court"]},
        {"id":"INSTITUTION-KAZ-CONSTITUTIONAL-COURT","name":"Constitutional Court of Kazakhstan","aliases":["Constitutional Court"]},
        {"id":"INSTITUTION-AUS-HUMAN-RIGHTS-COMMISSION","name":"Australian Human Rights Commission","aliases":[]},
        {"id":"ORG-OHCHR","name":"OHCHR","aliases":["UN Human Rights Office"]},
    ]
    index = build_name_index(entities, state_codes=states, normalizer=default_normalizer)
    assert resolve_normalized(index, state="SVK", normalized=default_normalizer("Constitutional Court")) == ["INSTITUTION-SVK-CONSTITUTIONAL-COURT"]
    assert resolve_normalized(index, state="KAZ", normalized=default_normalizer("Constitutional Court")) == ["INSTITUTION-KAZ-CONSTITUTIONAL-COURT"]
    assert resolve_normalized(index, state="NRU", normalized=default_normalizer("Constitutional Court")) == []
    assert resolve_normalized(index, state="NRU", normalized=default_normalizer("Australian Human Rights Commission")) == []
    assert resolve_normalized(index, state="NRU", normalized=default_normalizer("OHCHR")) == ["ORG-OHCHR"]
    assert eligible_in_state(index, "INSTITUTION-SVK-CONSTITUTIONAL-COURT", "KAZ") is False
    assert eligible_in_state(index, "ORG-OHCHR", "KAZ") is True
    assert canonicalize_id("AGENCY-OLD", {"AGENCY-OLD": "AGENCY-NEW"}) == "AGENCY-NEW"
    assert domestic_primary_signature("South Sudan National Security Service", "South Sudan") == "national security service"
    assert domestic_primary_signature("National Security Service (South Sudan)", "South Sudan") == "national security service"
    assert domestic_primary_signature("Constitutional Court of Slovakia", "Slovakia") == "constitutional court"


if __name__ == "__main__":
    self_test()
    supersession_integrity = audit_supersession_integrity()
    if supersession_integrity["missing_targets"] or supersession_integrity["materialized_sources"]:
        print("INVALID_SUPERSESSIONS=" + json.dumps(supersession_integrity, sort_keys=True))
        raise SystemExit(1)
    duplicates = audit_repository_primary_name_uniqueness()
    if duplicates:
        print("DUPLICATE_PRIMARY_IDENTITIES=" + json.dumps(duplicates, sort_keys=True))
        raise SystemExit(1)
    qualified_duplicates = audit_domestic_state_qualified_primary_duplicates()
    if qualified_duplicates:
        print("DUPLICATE_STATE_QUALIFIED_IDENTITIES=" + json.dumps(qualified_duplicates, sort_keys=True))
        raise SystemExit(1)
    print("entity identity resolution self-test: OK; supersessions valid; repository identity names unique")
