#!/usr/bin/env python3
"""Verify that canonical dossier migration changes only the ABox dossier pointer.

This check is intentionally PR-relative: it compares every entity listed in the
canonical migration manifests against the pull request base revision and permits
only the ``dossier`` field to differ. It prevents dossier materialization from
silently refreshing review timestamps or mutating identity/review metadata.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
ENTITY_DIR = ROOT / "knowledge/entities"
ALLOWED_CHANGED_FIELDS = {"dossier"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_json(ref: str, path: Path) -> dict | None:
    rel = path.relative_to(ROOT).as_posix()
    proc = subprocess.run(
        ["git", "show", f"{ref}:{rel}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


def changed_fields(before: dict, after: dict) -> list[str]:
    return sorted(
        key for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()

    manifests = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )
    errors: list[str] = []
    seen: set[str] = set()

    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        for row in manifest.get("entities", []):
            entity_id = row.get("id")
            if not isinstance(entity_id, str) or not entity_id:
                errors.append(f"{manifest_path.relative_to(ROOT)}: missing entity id")
                continue
            if entity_id in seen:
                continue
            seen.add(entity_id)

            entity_path = ENTITY_DIR / f"{entity_id}.json"
            if not entity_path.is_file():
                errors.append(f"{entity_id}: current ABox entity file is missing")
                continue
            before = git_json(args.base_ref, entity_path)
            if before is None:
                errors.append(
                    f"{entity_id}: entity did not exist at PR base {args.base_ref}; "
                    "canonical dossier migration must not create ABox identities"
                )
                continue
            after = load_json(entity_path)
            changed = changed_fields(before, after)
            illegal = [field for field in changed if field not in ALLOWED_CHANGED_FIELDS]
            if illegal:
                details = ", ".join(
                    f"{field}: {before.get(field)!r} -> {after.get(field)!r}"
                    for field in illegal
                )
                errors.append(f"{entity_id}: non-dossier ABox mutation: {details}")
            if "dossier" not in changed:
                errors.append(f"{entity_id}: migration row does not change the dossier pointer")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"canonical migration preservation: FAILED ({len(errors)} error(s))")
        return 1

    print(
        "canonical migration preservation: OK "
        f"({len(seen)} migrated entities; only dossier pointers differ from {args.base_ref})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
