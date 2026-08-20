#!/usr/bin/env python3
"""Validate the canonical dossier migration history as an exact append-only ratchet."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
EXPECTED_FINAL_VERSION = 49
EXPECTED_MIGRATED_ENTITIES = 242
PRE_MIGRATION_MISSING = 242


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def version_from_path(path: Path) -> int:
    return int(path.stem.rsplit("v", 1)[1])


def main() -> int:
    errors: list[str] = []
    paths = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=version_from_path,
    )
    versions = [version_from_path(path) for path in paths]
    expected_versions = list(range(1, EXPECTED_FINAL_VERSION + 1))
    if versions != expected_versions:
        missing = sorted(set(expected_versions) - set(versions))
        extra = sorted(set(versions) - set(expected_versions))
        errors.append(
            "migration manifest sequence must be exactly v1-v49; "
            f"missing={missing}, extra={extra}, observed={versions}"
        )

    cumulative = 0
    seen: set[str] = set()
    for path in paths:
        version = version_from_path(path)
        manifest = load_json(path)
        if manifest.get("version") != version:
            errors.append(
                f"{path.relative_to(ROOT)}: internal version {manifest.get('version')!r} "
                f"!= filename version {version}"
            )
        rows = manifest.get("entities")
        if not isinstance(rows, list) or not rows:
            errors.append(f"{path.relative_to(ROOT)}: entities must be a non-empty list")
            rows = []

        for row in rows:
            entity_id = row.get("id") if isinstance(row, dict) else None
            if not isinstance(entity_id, str) or not entity_id:
                errors.append(f"{path.relative_to(ROOT)}: migration row missing id")
                continue
            if entity_id in seen:
                errors.append(
                    f"{path.relative_to(ROOT)}: duplicate migrated entity across manifests: {entity_id}"
                )
            seen.add(entity_id)

        cumulative += len(rows)
        expected_remaining = PRE_MIGRATION_MISSING - cumulative
        actual_remaining = manifest.get("maxMissingDedicatedDossiers")
        if actual_remaining != expected_remaining:
            errors.append(
                f"{path.relative_to(ROOT)}: maxMissingDedicatedDossiers "
                f"{actual_remaining!r} != exact ratchet value {expected_remaining} "
                f"after {cumulative} migrated rows"
            )
        if expected_remaining < 0:
            errors.append(
                f"{path.relative_to(ROOT)}: cumulative migration rows exceed "
                f"pre-migration missing count {PRE_MIGRATION_MISSING}"
            )

    if cumulative != EXPECTED_MIGRATED_ENTITIES:
        errors.append(
            f"migration row count {cumulative} != expected {EXPECTED_MIGRATED_ENTITIES}"
        )
    if len(seen) != EXPECTED_MIGRATED_ENTITIES:
        errors.append(
            f"unique migrated entity count {len(seen)} != expected {EXPECTED_MIGRATED_ENTITIES}"
        )
    if paths:
        final = load_json(paths[-1]).get("maxMissingDedicatedDossiers")
        if final != 0:
            errors.append(f"final migration ratchet must be 0, got {final!r}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "canonical migration history: OK "
        f"(v1-v{EXPECTED_FINAL_VERSION}; {EXPECTED_MIGRATED_ENTITIES} unique rows; ratchet 242 -> 0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
