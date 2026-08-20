#!/usr/bin/env python3
"""Run canonical dossier coverage with the full supported non-State type universe."""
import check_canonical_entity_dossiers as checker

checker.TYPE_DIR["Deployment"] = "projects"

if __name__ == "__main__":
    raise SystemExit(checker.main())
