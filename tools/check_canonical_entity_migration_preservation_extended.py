#!/usr/bin/env python3
"""Run base-relative migration preservation plus no-denominator-shrink identity preservation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import canonical_dossier_contract as contract
import check_canonical_entity_migration_preservation as checker

checker.TYPE_DIR = dict(contract.TYPE_DIR)
checker.ENTITY_SUFFIXES = set(contract.ENTITY_SUFFIXES)

ROOT = Path(__file__).resolve().parents[1]
ENTITY_REL_DIR = Path("knowledge/entities")


def _supported_base_ids(base_ref: str, root: Path) -> set[str]:
    result: set[str] = set()
    for rel in checker.git_paths(base_ref, ENTITY_REL_DIR.as_posix(), root):
        if Path(rel).suffix not in contract.ENTITY_SUFFIXES:
            continue
        content = checker.git_show(base_ref, rel, root)
        if content is None:
            raise RuntimeError(f"cannot read base entity {rel} at {base_ref}")
        record = json.loads(content)
        entity_id = record.get("id") if isinstance(record, dict) else None
        if record.get("type") in contract.TYPE_DIR and isinstance(entity_id, str) and entity_id:
            result.add(entity_id)
    return result


def validate_baseline_identity_preservation(base_ref: str, root: Path = ROOT) -> list[str]:
    """A supported identity may be superseded semantically, but not physically disappear."""
    try:
        base_ids = _supported_base_ids(base_ref, root)
        current = checker.current_entity_index(root)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return [str(exc)]

    errors: list[str] = []
    for entity_id in sorted(base_ids):
        current_entry = current.get(entity_id)
        if current_entry is None:
            errors.append(
                f"{entity_id}: supported non-State identity existed at comparison base {base_ref} "
                "but was deleted; preserve canonical identity records instead of shrinking the "
                "dossier-coverage denominator"
            )
            continue
        record, _rel = current_entry
        if record.get("type") not in contract.TYPE_DIR:
            errors.append(
                f"{entity_id}: supported non-State identity changed to unsupported type "
                f"{record.get('type')!r}; type changes must not shrink the canonical coverage denominator"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()

    migration_errors, stats = checker.validate(args.base_ref, ROOT)
    baseline_errors = validate_baseline_identity_preservation(args.base_ref, ROOT)
    errors = migration_errors + baseline_errors
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"canonical migration preservation: FAILED ({len(errors)} error(s))")
        return 1

    print(
        "canonical migration preservation: OK "
        f"({stats['newlyMigrated']} new ledger row(s); {stats['atomicNew']} atomic post-v49 identity addition(s); "
        "existing identities are non-dedicated -> dedicated, preserve base sourceDossier, and change only dossier; "
        "all new non-State identities are ledgered; base supported identity set cannot shrink)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
