#!/usr/bin/env python3
"""Round-eight regression for pre-ledger CommonMark resource enforcement."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import canonical_dossier_contract as contract  # noqa: E402


class CanonicalRoundEightTests(unittest.TestCase):
    def test_preledger_dossier_cannot_hide_remote_image_with_escaped_alt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entity_id = "ORG-PRELEDGER"
            entity_dir = root / "knowledge/entities"
            dossier_dir = root / "dossiers/organizations"
            entity_dir.mkdir(parents=True, exist_ok=True)
            dossier_dir.mkdir(parents=True, exist_ok=True)

            entity = {
                "@context": "../../ontology/ecl-context.jsonld",
                "iri": f"ecl:{entity_id}",
                "id": entity_id,
                "type": "Organization",
                "name": "Pre-ledger Organization",
                "dossier": f"../../dossiers/organizations/{entity_id}.md",
            }
            (entity_dir / f"{entity_id}.json").write_text(
                json.dumps(entity),
                encoding="utf-8",
            )

            remote = "https://example.invalid/preledger.png"
            markdown = rf"""---
id: ECL-{entity_id}
entity: Pre-ledger Organization
entity_type: organization
---
# Pre-ledger Organization

![x\]y]({remote})
"""
            (dossier_dir / f"{entity_id}.md").write_text(markdown, encoding="utf-8")

            # This fixture deliberately has no migration manifest: it represents the
            # dedicated baseline that predates the canonical dossier ledger.
            self.assertFalse((root / "knowledge/generated").exists())
            self.assertIn(remote, contract.commonmark_image_targets(markdown))

            errors = contract.validate_universe(root)
            self.assertTrue(
                any(remote in error and "non-local embedded resource" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
