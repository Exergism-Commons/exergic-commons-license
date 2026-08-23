#!/usr/bin/env python3
"""Reject exact identity-name collisions that could make resolution silently unsafe."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

import entity_identity_resolution as identity


def indexed_names() -> tuple[dict[tuple[str, str], list[dict]], dict[str, list[dict]]]:
    entities, _ = identity.load_repository_entities()
    state_codes, _ = identity.repository_state_names(entities)
    supersessions = identity.load_id_supersessions()
    by_scope: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_name: dict[str, list[dict]] = defaultdict(list)
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or entity.get("type") == "State" or entity_id in supersessions:
            continue
        scope = identity.infer_domestic_state(entity_id, state_codes) or "GLOBAL"
        values: list[tuple[str, str]] = []
        primary = entity.get("name")
        if isinstance(primary, str) and identity.default_normalizer(primary):
            values.append(("primary", primary))
        for alias in entity.get("aliases") or []:
            if isinstance(alias, str) and identity.default_normalizer(alias):
                values.append(("alias", alias))
        for kind, text in values:
            normalized = identity.default_normalizer(text)
            row = {"id": entity_id, "scope": scope, "kind": kind, "text": text}
            by_scope[(scope, normalized)].append(row)
            by_name[normalized].append(row)
    return by_scope, by_name


def collisions() -> list[dict]:
    by_scope, _ = indexed_names()
    failures: list[dict] = []
    for (scope, normalized), rows in sorted(by_scope.items()):
        ids = {row["id"] for row in rows}
        if len(ids) < 2 or not any(row["kind"] == "primary" for row in rows):
            continue
        failures.append({"scope": scope, "normalized": normalized, "matches": rows})
    return failures


def global_domestic_shadows() -> list[dict]:
    """A domestic exact name must never silently override an exact global name."""
    _, by_name = indexed_names()
    failures: list[dict] = []
    for normalized, rows in sorted(by_name.items()):
        global_ids = {row["id"] for row in rows if row["scope"] == "GLOBAL"}
        domestic_scopes = {row["scope"] for row in rows if row["scope"] != "GLOBAL"}
        if not global_ids or not domestic_scopes:
            continue
        failures.append({
            "normalized": normalized,
            "global_ids": sorted(global_ids),
            "domestic_scopes": sorted(domestic_scopes),
            "matches": rows,
        })
    return failures


def state_non_state_shadows() -> list[dict]:
    """Country names/aliases must not resolve as non-State identities in the prose index."""
    entities, _ = identity.load_repository_entities()
    supersessions = identity.load_id_supersessions()
    state_rows: dict[str, list[dict]] = defaultdict(list)
    non_state_rows: dict[str, list[dict]] = defaultdict(list)
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or entity_id in supersessions:
            continue
        values: list[tuple[str, str]] = []
        name = entity.get("name")
        if isinstance(name, str) and identity.default_normalizer(name):
            values.append(("primary", name))
        for alias in entity.get("aliases") or []:
            if isinstance(alias, str) and identity.default_normalizer(alias):
                values.append(("alias", alias))
        target = state_rows if entity.get("type") == "State" else non_state_rows
        for kind, text in values:
            target[identity.default_normalizer(text)].append({"id": entity_id, "kind": kind, "text": text})

    failures: list[dict] = []
    for normalized in sorted(set(state_rows) & set(non_state_rows)):
        failures.append({
            "normalized": normalized,
            "state_matches": state_rows[normalized],
            "non_state_matches": non_state_rows[normalized],
        })
    return failures


def self_test() -> None:
    sample = [
        {"id": "A", "kind": "primary", "text": "National Service"},
        {"id": "B", "kind": "alias", "text": "National Service"},
    ]
    assert len({row["id"] for row in sample}) == 2 and any(row["kind"] == "primary" for row in sample)
    shadow_sample = [
        {"id": "ORG-GLOBAL", "scope": "GLOBAL"},
        {"id": "AGENCY-AAA-LOCAL", "scope": "AAA"},
    ]
    assert any(row["scope"] == "GLOBAL" for row in shadow_sample)
    assert any(row["scope"] != "GLOBAL" for row in shadow_sample)
    print("identity collision/shadow self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    same_scope = collisions()
    shadows = global_domestic_shadows()
    state_shadows = state_non_state_shadows()
    if same_scope or shadows or state_shadows:
        print("IDENTITY_NAME_RESOLUTION_COLLISIONS=" + json.dumps({
            "same_scope_primary_alias": same_scope,
            "global_domestic_shadows": shadows,
            "state_non_state_shadows": state_shadows,
        }, ensure_ascii=False, sort_keys=True))
        return 2
    print("identity name-resolution collisions: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
