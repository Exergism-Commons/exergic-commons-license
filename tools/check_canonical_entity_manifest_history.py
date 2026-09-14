#!/usr/bin/env python3
"""Validate canonical dossier and identity-supersession history as immutable append-only ratchets."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
MANIFEST_PREFIX = "knowledge/generated/canonical-entity-dossier-migration-v"
SUPERSESSION_PREFIX = "knowledge/generated/entity-id-supersessions-v"
ENTITY_REL_DIR = "knowledge/entities"
ENTITY_SUFFIXES = {".json", ".jsonld"}
FROZEN_FINAL_VERSION = 49
FROZEN_MIGRATED_ENTITIES = 242
PRE_MIGRATION_MISSING = 242


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def version_from_path(path: Path) -> int:
    return int(path.stem.rsplit("v", 1)[1])


def git_paths(ref: str, rel_dir: str) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", rel_dir],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"cannot list {rel_dir} at {ref}: {proc.stderr.strip()}")
    return proc.stdout.splitlines()


def git_versioned_paths(ref: str, prefix: str, label: str) -> list[str]:
    result: list[str] = []
    for line in git_paths(ref, "knowledge/generated"):
        if line.startswith(prefix) and line.endswith(".json"):
            suffix = line[len(prefix):-5]
            if suffix.isdigit() and not suffix.startswith("0"):
                result.append(line)
    return sorted(result, key=lambda rel: int(rel[len(prefix):-5]))


def git_manifest_paths(ref: str) -> list[str]:
    return git_versioned_paths(ref, MANIFEST_PREFIX, "migration")


def git_supersession_paths(ref: str) -> list[str]:
    return git_versioned_paths(ref, SUPERSESSION_PREFIX, "identity supersession")


def git_bytes(ref: str, rel: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{rel}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else None


def _git_json(ref: str, rel: str, label: str) -> dict:
    raw = git_bytes(ref, rel)
    if raw is None:
        raise RuntimeError(f"cannot read {label} {rel} at {ref}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"cannot parse {label} {rel} at {ref}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} {rel} at {ref} must be a JSON object")
    return value


def git_curated_identity_ids(
    base_ref: str,
    base_manifest_paths: list[str],
    base_supersession_paths: list[str],
) -> set[str]:
    """Return identities that were already curated before new supersession versions."""
    curated: set[str] = set()
    for rel in git_paths(base_ref, ENTITY_REL_DIR):
        if Path(rel).suffix not in ENTITY_SUFFIXES:
            continue
        record = _git_json(base_ref, rel, "ABox entity")
        entity_id = record.get("id")
        if isinstance(entity_id, str) and entity_id:
            curated.add(entity_id)

    for rel in base_manifest_paths:
        manifest = _git_json(base_ref, rel, "migration manifest")
        rows = manifest.get("entities")
        if not isinstance(rows, list):
            raise RuntimeError(f"migration manifest {rel} at {base_ref} has invalid entities payload")
        for row in rows:
            entity_id = row.get("id") if isinstance(row, dict) else None
            if isinstance(entity_id, str) and entity_id:
                curated.add(entity_id)

    # An immutable historical supersession manifest is itself curated identity history.
    # Including both endpoints keeps pre-existing normalization history traceable while
    # the direct-map validator continues to forbid duplicate sources and chains.
    for rel in base_supersession_paths:
        manifest = _git_json(base_ref, rel, "identity supersession manifest")
        rows = manifest.get("supersessions")
        if not isinstance(rows, list):
            raise RuntimeError(f"identity supersession manifest {rel} at {base_ref} has invalid supersessions payload")
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("from", "to"):
                entity_id = row.get(key)
                if isinstance(entity_id, str) and entity_id:
                    curated.add(entity_id)
    return curated


def validate_new_supersession_sources(
    *,
    current_paths: list[Path],
    base_paths: list[str],
    curated_ids: set[str],
) -> list[str]:
    """Reject new aliases whose source identity has no history at the comparison base."""
    errors: list[str] = []
    base_versions = [int(rel[len(SUPERSESSION_PREFIX):-5]) for rel in base_paths]
    max_base_version = max(base_versions, default=0)
    for path in current_paths:
        if version_from_path(path) <= max_base_version:
            continue
        manifest = load_json(path)
        rows = manifest.get("supersessions")
        if not isinstance(rows, list):
            errors.append(f"{path.relative_to(ROOT)}: supersessions must be a list")
            continue
        for index, row in enumerate(rows):
            source = row.get("from") if isinstance(row, dict) else None
            if not isinstance(source, str) or not source:
                continue
            if source not in curated_ids:
                errors.append(
                    f"{path.relative_to(ROOT)}: supersession row {index} source {source!r} has no curated "
                    "identity history in the PR base ABox, canonical migration ledger, or published supersession history"
                )
    return errors


def validate_base_versioned_history(
    *,
    base_ref: str,
    current_paths: list[Path],
    base_paths: list[str],
    prefix: str,
    label: str,
) -> list[str]:
    """Freeze every version already published in the comparison base and allow append-only versions."""
    errors: list[str] = []
    current_by_rel = {path.relative_to(ROOT).as_posix(): path for path in current_paths}
    for rel in base_paths:
        current = current_by_rel.get(rel)
        if current is None:
            errors.append(f"{rel}: historical {label} manifest from PR base was deleted")
            continue
        before = git_bytes(base_ref, rel)
        after = current.read_bytes()
        if before is None:
            errors.append(f"{rel}: could not read historical {label} manifest from PR base {base_ref}")
        elif before != after:
            errors.append(
                f"{rel}: historical {label} manifest is immutable once present in the PR base; "
                "append a new version instead"
            )

    base_versions = [int(rel[len(prefix):-5]) for rel in base_paths]
    max_base_version = max(base_versions, default=0)
    current_versions = [version_from_path(path) for path in current_paths]
    new_versions = [version for version in current_versions if version > max_base_version]
    expected_new = (
        list(range(max_base_version + 1, current_versions[-1] + 1)) if current_versions else []
    )
    if new_versions != expected_new:
        errors.append(
            f"new {label} manifests must append contiguously after the PR base; "
            f"base_max=v{max_base_version}, new={new_versions}, expected={expected_new}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref")
    args = parser.parse_args()

    errors: list[str] = []
    paths = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=version_from_path,
    )
    versions = [version_from_path(path) for path in paths]

    if not versions:
        errors.append("no canonical entity dossier migration manifests found")
    else:
        expected_versions = list(range(1, versions[-1] + 1))
        if versions != expected_versions:
            missing = sorted(set(expected_versions) - set(versions))
            errors.append(
                "migration manifest sequence must be contiguous from v1; "
                f"missing={missing}, observed={versions}"
            )
        if versions[-1] < FROZEN_FINAL_VERSION:
            errors.append(
                f"migration history must retain frozen prefix v1-v{FROZEN_FINAL_VERSION}; "
                f"latest observed version is v{versions[-1]}"
            )

    cumulative = 0
    frozen_cumulative: int | None = None
    seen: set[str] = set()
    previous_ceiling: int | None = None

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
        actual_ceiling = manifest.get("maxMissingDedicatedDossiers")
        if not isinstance(actual_ceiling, int) or actual_ceiling < 0:
            errors.append(
                f"{path.relative_to(ROOT)}: maxMissingDedicatedDossiers must be a non-negative integer"
            )
        elif version <= FROZEN_FINAL_VERSION:
            expected_remaining = PRE_MIGRATION_MISSING - cumulative
            if actual_ceiling != expected_remaining:
                errors.append(
                    f"{path.relative_to(ROOT)}: maxMissingDedicatedDossiers "
                    f"{actual_ceiling!r} != frozen ratchet value {expected_remaining} "
                    f"after {cumulative} migrated rows"
                )
            if expected_remaining < 0:
                errors.append(
                    f"{path.relative_to(ROOT)}: frozen-prefix migration rows exceed "
                    f"pre-migration missing count {PRE_MIGRATION_MISSING}"
                )
        else:
            # v49 closed the known backlog. Later identity additions must arrive
            # with their dedicated dossier atomically, so the ceiling stays 0.
            if actual_ceiling != 0:
                errors.append(
                    f"{path.relative_to(ROOT)}: post-v{FROZEN_FINAL_VERSION} manifests "
                    f"must preserve the closed dossier ceiling at 0, got {actual_ceiling!r}"
                )

        if previous_ceiling is not None and isinstance(actual_ceiling, int):
            if actual_ceiling > previous_ceiling:
                errors.append(
                    f"{path.relative_to(ROOT)}: dossier ceiling regressed "
                    f"{previous_ceiling} -> {actual_ceiling}"
                )
        if isinstance(actual_ceiling, int):
            previous_ceiling = actual_ceiling

        if version == FROZEN_FINAL_VERSION:
            frozen_cumulative = cumulative
            if actual_ceiling != 0:
                errors.append(
                    f"v{FROZEN_FINAL_VERSION} must close the historical ratchet at 0, "
                    f"got {actual_ceiling!r}"
                )

    if frozen_cumulative != FROZEN_MIGRATED_ENTITIES:
        errors.append(
            f"frozen v1-v{FROZEN_FINAL_VERSION} row count {frozen_cumulative!r} "
            f"!= expected {FROZEN_MIGRATED_ENTITIES}"
        )
    if len(seen) != cumulative:
        errors.append(
            f"unique migrated entity count {len(seen)} != migration row count {cumulative}"
        )
    if paths and load_json(paths[-1]).get("maxMissingDedicatedDossiers") != 0:
        errors.append("latest migration manifest must preserve a 0 missing-dossier ceiling")

    supersession_paths = sorted(
        MANIFEST_DIR.glob("entity-id-supersessions-v*.json"),
        key=version_from_path,
    )

    if args.base_ref:
        try:
            base_paths = git_manifest_paths(args.base_ref)
        except RuntimeError as exc:
            errors.append(str(exc))
            base_paths = []
        errors.extend(
            validate_base_versioned_history(
                base_ref=args.base_ref,
                current_paths=paths,
                base_paths=base_paths,
                prefix=MANIFEST_PREFIX,
                label="migration",
            )
        )

        try:
            base_supersession_paths = git_supersession_paths(args.base_ref)
        except RuntimeError as exc:
            errors.append(str(exc))
            base_supersession_paths = []
        errors.extend(
            validate_base_versioned_history(
                base_ref=args.base_ref,
                current_paths=supersession_paths,
                base_paths=base_supersession_paths,
                prefix=SUPERSESSION_PREFIX,
                label="identity supersession",
            )
        )
        try:
            curated_ids = git_curated_identity_ids(
                args.base_ref,
                base_paths,
                base_supersession_paths,
            )
        except RuntimeError as exc:
            errors.append(str(exc))
        else:
            errors.extend(
                validate_new_supersession_sources(
                    current_paths=supersession_paths,
                    base_paths=base_supersession_paths,
                    curated_ids=curated_ids,
                )
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    latest = versions[-1]
    base_note = (
        f"; base-ref migration + identity-supersession immutability/source-history checked against {args.base_ref}"
        if args.base_ref
        else ""
    )
    print(
        "canonical migration history: OK "
        f"(v1-v{latest}; {len(seen)} unique rows; frozen v1-v{FROZEN_FINAL_VERSION} "
        f"prefix={FROZEN_MIGRATED_ENTITIES}; post-closure ceiling=0{base_note})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
