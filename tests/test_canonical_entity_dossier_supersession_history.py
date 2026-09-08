#!/usr/bin/env python3
"""Regressions for immutable canonical history after identity-ID supersession."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_canonical_entity_dossiers_extended as coverage  # noqa: E402
import check_canonical_entity_migration_preservation as preservation  # noqa: E402


class CanonicalHistoricalSupersessionTests(unittest.TestCase):
    def test_repository_supersessions_are_direct_with_live_targets(self) -> None:
        mapping, errors = coverage.checker.load_supersessions()
        self.assertEqual(errors, [])
        self.assertTrue(mapping)

        entities: dict[str, dict] = {}
        for path in coverage.checker.entity_paths():
            record = json.loads(path.read_text(encoding="utf-8"))
            entity_id = record.get("id")
            if isinstance(entity_id, str):
                entities[entity_id] = record

        for source, target in mapping.items():
            with self.subTest(source=source, target=target):
                self.assertNotIn(target, mapping, "supersession chains must remain forbidden")
                self.assertNotIn(source, entities, "superseded source must not remain materialized")
                self.assertIn(target, entities, "supersession target must remain materialized")
                self.assertEqual(source.split("-", 1)[0], target.split("-", 1)[0])

    def test_v39_ssd_history_remains_bound_to_old_dossier_and_new_identity(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "knowledge/generated/canonical-entity-dossier-migration-v39.json").read_text(
                encoding="utf-8"
            )
        )
        row = next(item for item in manifest["entities"] if item["id"] == "AGENCY-SSD-NSS")
        mapping, errors = coverage.checker.load_supersessions()
        self.assertEqual(errors, [])
        self.assertEqual(mapping["AGENCY-SSD-NSS"], "AGENCY-SSD-NATIONAL-SECURITY-SERVICE")
        self.assertTrue((REPO_ROOT / row["dossier"]).is_file())
        target = json.loads(
            (REPO_ROOT / "knowledge/entities/AGENCY-SSD-NATIONAL-SECURITY-SERVICE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(target["type"], row["type"])
        self.assertFalse((REPO_ROOT / "knowledge/entities/AGENCY-SSD-NSS.json").exists())

    def test_coverage_loader_rejects_self_and_duplicate_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "supersessions.json"
            path.write_text(
                json.dumps(
                    {
                        "supersessions": [
                            {"from": "ORG-A", "to": "ORG-A"},
                            {"from": "ORG-B", "to": "ORG-C"},
                            {"from": "ORG-B", "to": "ORG-D"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            mapping, errors = coverage.checker.load_supersessions(path)
            self.assertEqual(mapping, {"ORG-B": "ORG-C"})
            self.assertTrue(any("self-supersession" in error for error in errors), errors)
            self.assertTrue(any("duplicate supersession source ORG-B" in error for error in errors), errors)

    def test_preservation_loader_rejects_supersession_chains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / preservation.SUPERSESSIONS_REL
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "supersessions": [
                            {"from": "ORG-A", "to": "ORG-B"},
                            {"from": "ORG-B", "to": "ORG-C"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "one hop"):
                preservation.current_supersession_map(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
