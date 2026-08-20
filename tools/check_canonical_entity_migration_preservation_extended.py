#!/usr/bin/env python3
"""Run base-relative migration preservation with Deployment mapped to project dossiers."""
import check_canonical_entity_migration_preservation as checker

checker.TYPE_DIR["Deployment"] = "projects"

if __name__ == "__main__":
    raise SystemExit(checker.main())
