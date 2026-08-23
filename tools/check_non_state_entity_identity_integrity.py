#!/usr/bin/env python3
"""Validate structural identity integrity for every non-State ABox entity file."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import entity_identity_resolution as identity

ROOT = identity.ROOT
ENTITY_DIR = identity.ENTITY_DIR
DOSSIER_ROOT = (ROOT / "dossiers").resolve()
TYPE_PREFIX = {
    "Agency": "AGENCY-",
    "Institution": "INSTITUTION-",
    "Organization": "ORG-",
    "Person": "PERSON-",
    "Project": "PROJECT-",
    "Deployment": "DEPLOYMENT-",
}
ID_RE = re.compile(r"^[A-Z][A-Z0-9-]*[A-Z0-9]$")


def inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate() -> list[dict]:
    failures: list[dict] = []
    ids: dict[str, list[str]] = defaultdict(list)

    for path in sorted(ENTITY_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "State":
            continue
        rel = str(path.relative_to(ROOT))
        entity_id = data.get("id")
        entity_type = data.get("type")
        if not isinstance(entity_id, str) or not entity_id or not ID_RE.fullmatch(entity_id):
            failures.append({"file": rel, "reason": "missing or malformed stable id", "value": entity_id})
            continue
        ids[entity_id].append(rel)
        if path.stem != entity_id:
            failures.append({"file": rel, "id": entity_id, "reason": "filename/id mismatch"})
        expected_prefix = TYPE_PREFIX.get(entity_type)
        if expected_prefix is None:
            failures.append({"file": rel, "id": entity_id, "reason": "unsupported non-State entity type", "value": entity_type})
        elif not entity_id.startswith(expected_prefix):
            failures.append({
                "file": rel, "id": entity_id, "reason": "type/id-prefix mismatch",
                "type": entity_type, "expected_prefix": expected_prefix,
            })
        if data.get("iri") != f"ecl:{entity_id}":
            failures.append({"file": rel, "id": entity_id, "reason": "iri/id mismatch", "value": data.get("iri")})
        if data.get("@context") != "../../ontology/ecl-context.jsonld":
            failures.append({"file": rel, "id": entity_id, "reason": "unexpected JSON-LD context", "value": data.get("@context")})

        name = data.get("name")
        aliases = data.get("aliases")
        if not isinstance(name, str) or not name.strip():
            failures.append({"file": rel, "id": entity_id, "reason": "missing canonical name"})
        if not isinstance(aliases, list) or not all(isinstance(item, str) and item.strip() for item in aliases):
            failures.append({"file": rel, "id": entity_id, "reason": "aliases must be a list of non-empty strings"})
        elif len({identity.default_normalizer(item) for item in aliases}) != len(aliases):
            failures.append({"file": rel, "id": entity_id, "reason": "duplicate normalized aliases within identity"})

        dossier = data.get("dossier")
        if not isinstance(dossier, str) or not dossier:
            failures.append({"file": rel, "id": entity_id, "reason": "missing dossier provenance path"})
        else:
            target = (path.parent / dossier).resolve()
            if not target.is_file():
                failures.append({"file": rel, "id": entity_id, "reason": "dossier provenance target does not exist", "value": dossier})
            elif not inside(target, DOSSIER_ROOT):
                failures.append({"file": rel, "id": entity_id, "reason": "dossier provenance escapes dossiers/", "value": dossier})

    for entity_id, files in sorted(ids.items()):
        if len(files) > 1:
            failures.append({"id": entity_id, "reason": "duplicate stable id across entity files", "files": files})
    return failures


def self_test() -> None:
    assert TYPE_PREFIX["Agency"] == "AGENCY-"
    assert ID_RE.fullmatch("AGENCY-AAA-EXAMPLE")
    assert not ID_RE.fullmatch("agency-aaa-example")
    assert inside((DOSSIER_ROOT / "states" / "AAA.md").resolve(), DOSSIER_ROOT)
    print("non-State entity identity integrity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = validate()
    if failures:
        print("NON_STATE_ENTITY_INTEGRITY_ERRORS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("non-State entity identity integrity: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
