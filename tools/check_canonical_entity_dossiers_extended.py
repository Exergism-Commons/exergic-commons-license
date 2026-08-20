#!/usr/bin/env python3
"""Run canonical dossier coverage with the shared supported non-State policy."""
import canonical_dossier_contract as contract
import check_canonical_entity_dossiers as checker

checker.TYPE_DIR = dict(contract.TYPE_DIR)
checker.ENTITY_SUFFIXES = set(contract.ENTITY_SUFFIXES)
checker.IMAGE_EXTENSIONS = set(contract.RASTER_FACSIMILE_EXTENSIONS)

if __name__ == "__main__":
    raise SystemExit(checker.main())
