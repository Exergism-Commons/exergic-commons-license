#!/usr/bin/env python3
"""Verify that newly introduced dossier migrations only change the ABox dossier pointer.

The check is intentionally PR-relative. Migration rows already present in the
pull-request base are historical and are not re-policed here: their manifests
are protected by the append-only history guard, while their ABox review metadata
must remain free to evolve in later work. Rows newly introduced by this PR must
refer to an identity that already exists in the base and may change only the
``dossier`` field.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
ENTITY_DIR = ROOT / "knowledge/entities"
ALLOWED_CHANGED_FIELDS = {"dossier"}
MANIFEST_RE = re.compile(r"^knowledge/generated/canonical-entity-dossier-migration-v\d+\.json$")
_MISSING = object()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_show(ref: str, rel: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{rel}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else None


def git_json(ref: str, path: Path) -> dict | None:
    content = git_show(ref, path.relative_to(ROOT).as_posix())
    return json.loads(content) if content is not None else None


def base_migrated_ids(ref: str) -> set[str]:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "knowledge/generated"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"cannot list migration manifests at {ref}: {proc.stderr.strip()}")

    ids: set[str] = set()
    for rel in proc.stdout.splitlines():
        if not MANIFEST_RE.match(rel):
            continue
        content = git_show(ref, rel)
        if content is None:
            raise RuntimeError(f"cannot read historical migration manifest {rel} at {ref}")
        manifest = json.loads(content)
        rows = manifest.get("entities")
        if not isinstance(rows, list):
            raise RuntimeError(f"historical migration manifest {rel} has invalid entities payload")
        for row in rows:
            entity_id = row.get("id") if isinstance(row, dict) else None
            if not isinstance(entity_id, str) or not entity_id:
                raise RuntimeError(f"historical migration manifest {rel} contains a row without id")
            ids.add(entity_id)
    return ids


def field_value(record: dict, key: str) -> object:
    return record[key] if key in record else _MISSING


def display_value(record: dict, key: str) -> str:
    return repr(record[key]) if key in record else "<absent>"


def changed_fields(before: dict, after: dict) -> list[str]:
    return sorted(
        key for key in set(before) | set(after)
        if field_value(before, key) != field_value(after, key)
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
    newly_migrated: set[str] = set()

    try:
        historical_ids = base_migrated_ids(args.base_ref)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        for row in manifest.get("entities", []):
            entity_id = row.get("id") if isinstance(row, dict) else None
            if not isinstance(entity_id, str) or not entity_id:
                errors.append(f"{manifest_path.relative_to(ROOT)}: missing entity id")
                continue
            if entity_id in seen:
                errors.append(
                    f"{manifest_path.relative_to(ROOT)}: duplicate migrated entity across manifests: {entity_id}"
                )
                continue
            seen.add(entity_id)

            # Historical migration rows are immutable at the manifest layer, but
            # their ABox records may legitimately receive later review updates.
            if entity_id in historical_ids:
                continue

            newly_migrated.add(entity_id)
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
                    f"{field}: {display_value(before, field)} -> {display_value(after, field)}"
                    for field in illegal
                )
                errors.append(f"{entity_id}: non-dossier ABox mutation: {details}")
            if "dossier" not in changed:
                errors.append(f"{entity_id}: newly introduced migration row does not change the dossier pointer")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"canonical migration preservation: FAILED ({len(errors)} error(s))")
        return 1

    print(
        "canonical migration preservation: OK "
        f"({len(newly_migrated)} newly migrated entities checked against {args.base_ref}; "
        f"{len(historical_ids & seen)} historical migrated entities skipped; "
        "new migrations change only dossier pointers)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
