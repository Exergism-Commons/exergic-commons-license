#!/usr/bin/env python3
"""Reject exact same-scope collisions between one identity's primary name and another's alias."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

import entity_identity_resolution as identity


def collisions() -> list[dict]:
    entities, _ = identity.load_repository_entities()
    state_codes, _ = identity.repository_state_names(entities)
    supersessions = identity.load_id_supersessions()
    names: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or entity.get("type") == "State" or entity_id in supersessions:
            continue
        scope = identity.infer_domestic_state(entity_id, state_codes) or "GLOBAL"
        primary = entity.get("name")
        if isinstance(primary, str) and identity.default_normalizer(primary):
            names[(scope, identity.default_normalizer(primary))].append({"id": entity_id, "kind": "primary", "text": primary})
        for alias in entity.get("aliases") or []:
            if isinstance(alias, str) and identity.default_normalizer(alias):
                names[(scope, identity.default_normalizer(alias))].append({"id": entity_id, "kind": "alias", "text": alias})

    failures: list[dict] = []
    for (scope, normalized), rows in sorted(names.items()):
        ids = {row["id"] for row in rows}
        if len(ids) < 2 or not any(row["kind"] == "primary" for row in rows):
            continue
        failures.append({"scope": scope, "normalized": normalized, "matches": rows})
    return failures


def self_test() -> None:
    sample = [
        {"id": "A", "kind": "primary", "text": "National Service"},
        {"id": "B", "kind": "alias", "text": "National Service"},
    ]
    assert len({row["id"] for row in sample}) == 2 and any(row["kind"] == "primary" for row in sample)
    print("identity primary/alias collision self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = collisions()
    if failures:
        print("PRIMARY_ALIAS_IDENTITY_COLLISIONS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("identity primary/alias collisions: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
