#!/usr/bin/env python3
"""Run base-relative migration preservation with the shared canonical type policy."""
import canonical_dossier_contract as contract
import check_canonical_entity_migration_preservation as checker

checker.TYPE_DIR = dict(contract.TYPE_DIR)
checker.ENTITY_SUFFIXES = set(contract.ENTITY_SUFFIXES)

if __name__ == "__main__":
    raise SystemExit(checker.main())
