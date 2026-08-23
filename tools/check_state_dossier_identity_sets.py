#!/usr/bin/env python3
"""Require exact set equality and identity integrity for canonical State dossiers."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIERS = ROOT / "dossiers" / "states"
ENTITIES = ROOT / "knowledge" / "entities"
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
DOSSIER_ID = re.compile(r"^ECL-STATE-([A-Z]{3})$")
ENTITY_ID = re.compile(r"^STATE-([A-Z]{3})$")


def norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONT.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def main() -> int:
    dossier_by_iso: dict[str, str] = {}
    for path in sorted(DOSSIERS.glob("*.md")):
        data = frontmatter(path)
        match = DOSSIER_ID.fullmatch(data.get("id", ""))
        if not match or data.get("iso3") != match.group(1):
            continue
        iso = match.group(1)
        if path.stem != iso:
            continue
        if iso in dossier_by_iso:
            print(f"duplicate canonical dossier for {iso}: {dossier_by_iso[iso]} and {path}")
            return 2
        dossier_by_iso[iso] = str(path.relative_to(ROOT))

    identity_by_iso: dict[str, str] = {}
    state_names: dict[str, set[str]] = defaultdict(set)
    for path in sorted(ENTITIES.glob("STATE-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") != "State":
            continue
        match = ENTITY_ID.fullmatch(data.get("id", ""))
        if not match:
            print(f"malformed State identity id in {path.relative_to(ROOT)}: {data.get('id')!r}")
            return 3
        iso = match.group(1)
        entity_id = data["id"]
        if path.stem != entity_id:
            print(f"State identity filename/id mismatch: {path.relative_to(ROOT)} -> {entity_id!r}")
            return 4
        if data.get("iso3") != iso:
            print(f"State identity iso3/id mismatch: {path.relative_to(ROOT)} -> {data.get('iso3')!r} vs {iso}")
            return 5
        if data.get("iri") != f"ecl:{entity_id}":
            print(f"State identity iri/id mismatch: {path.relative_to(ROOT)} -> {data.get('iri')!r}")
            return 6
        name = data.get("name")
        aliases = data.get("aliases")
        if not isinstance(name, str) or not name.strip():
            print(f"State identity missing canonical name: {path.relative_to(ROOT)}")
            return 7
        if not isinstance(aliases, list) or not all(isinstance(item, str) and item.strip() for item in aliases):
            print(f"State identity aliases must be a string list: {path.relative_to(ROOT)}")
            return 8
        if iso not in aliases:
            print(f"State identity must preserve ISO3 as alias: {path.relative_to(ROOT)} -> {aliases!r}")
            return 9
        dossier_value = data.get("dossier")
        if not isinstance(dossier_value, str):
            print(f"State identity missing dossier path: {path.relative_to(ROOT)}")
            return 10
        resolved_dossier = (path.parent / dossier_value).resolve()
        expected_dossier = (DOSSIERS / f"{iso}.md").resolve()
        if resolved_dossier != expected_dossier or not resolved_dossier.is_file():
            print(
                f"State identity dossier mismatch: {path.relative_to(ROOT)} -> {dossier_value!r}; "
                f"expected {expected_dossier.relative_to(ROOT)}"
            )
            return 11
        if iso in identity_by_iso:
            print(f"duplicate State identity for {iso}: {identity_by_iso[iso]} and {path}")
            return 12
        identity_by_iso[iso] = str(path.relative_to(ROOT))
        for value in [name, *aliases]:
            normalized = norm(value)
            if normalized:
                state_names[normalized].add(iso)

    collisions = [
        {"normalized_name_or_alias": value, "states": sorted(states)}
        for value, states in sorted(state_names.items())
        if len(states) > 1
    ]
    if collisions:
        print("AMBIGUOUS_STATE_NAMES_OR_ALIASES=" + json.dumps(collisions, ensure_ascii=False, sort_keys=True))
        return 13

    dossier_set = set(dossier_by_iso)
    identity_set = set(identity_by_iso)
    missing_identity = sorted(dossier_set - identity_set)
    missing_dossier = sorted(identity_set - dossier_set)
    report = {
        "canonical_state_dossiers": len(dossier_set),
        "state_identities": len(identity_set),
        "dossiers_without_state_identity": [
            {"iso3": iso, "dossier": dossier_by_iso[iso]} for iso in missing_identity
        ],
        "state_identities_without_dossier": [
            {"iso3": iso, "entity": identity_by_iso[iso]} for iso in missing_dossier
        ],
        "state_name_or_alias_collisions": 0,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if missing_identity or missing_dossier else 0


if __name__ == "__main__":
    sys.exit(main())
