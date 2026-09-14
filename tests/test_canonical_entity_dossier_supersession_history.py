#!/usr/bin/env python3
"""Regressions for immutable canonical history after identity-ID supersession."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_canonical_entity_dossiers_extended as coverage  # noqa: E402
import check_canonical_entity_manifest_history as history  # noqa: E402
import check_canonical_entity_migration_preservation as preservation  # noqa: E402
import check_canonical_entity_migration_preservation_extended as preservation_extended  # noqa: E402


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

    def _write_supersession_manifest(self, root: Path, version: int, rows: list[dict], follows: str | None) -> Path:
        path = root / f"knowledge/generated/entity-id-supersessions-v{version}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": version, "follows": follows, "supersessions": rows}),
            encoding="utf-8",
        )
        return path

    def test_coverage_and_preservation_load_every_versioned_supersession_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self._write_supersession_manifest(
                root, 1, [{"from": "ORG-A", "to": "ORG-B", "reason": "canonical rename"}], None
            )
            self._write_supersession_manifest(
                root, 2, [{"from": "ORG-C", "to": "ORG-D", "reason": "canonical rename"}],
                str(v1.relative_to(root)),
            )
            with mock.patch.object(coverage.checker, "ROOT", root), mock.patch.object(
                coverage.checker, "SUPERSESSIONS_DIR", root / "knowledge/generated"
            ):
                mapping, errors = coverage.checker.load_supersessions()
            self.assertEqual(errors, [])
            self.assertEqual(mapping, {"ORG-A": "ORG-B", "ORG-C": "ORG-D"})
            self.assertEqual(preservation.current_supersession_map(root), mapping)

    def test_coverage_loader_rejects_self_supersession(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write_supersession_manifest(
                root, 1, [{"from": "ORG-A", "to": "ORG-A", "reason": "invalid"}], None
            )
            with mock.patch.object(coverage.checker, "ROOT", root):
                mapping, errors = coverage.checker.load_supersessions(path)
            self.assertEqual(mapping, {})
            self.assertTrue(any("self-supersession" in error for error in errors), errors)

    def test_preservation_loader_rejects_supersession_chains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_supersession_manifest(
                root, 1, [
                    {"from": "ORG-A", "to": "ORG-B", "reason": "first"},
                    {"from": "ORG-B", "to": "ORG-C", "reason": "second"},
                ], None
            )
            with self.assertRaisesRegex(RuntimeError, "chains are forbidden"):
                preservation.current_supersession_map(root)

    def test_supersession_history_rejects_rewrite_of_published_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self._write_supersession_manifest(
                root, 1, [{"from": "ORG-A", "to": "ORG-C", "reason": "retargeted"}], None
            )
            base_rel = "knowledge/generated/entity-id-supersessions-v1.json"
            with mock.patch.object(history, "ROOT", root), mock.patch.object(
                history, "git_bytes", return_value=b'{"version":1,"follows":null,"supersessions":[{"from":"ORG-A","to":"ORG-B","reason":"published"}]}'
            ):
                errors = history.validate_base_versioned_history(
                    base_ref="BASE",
                    current_paths=[v1],
                    base_paths=[base_rel],
                    prefix=history.SUPERSESSION_PREFIX,
                    label="identity supersession",
                )
        self.assertTrue(any("immutable once present in the PR base" in error for error in errors), errors)
        self.assertTrue(any("append a new version instead" in error for error in errors), errors)

    def test_supersession_history_allows_new_contiguous_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self._write_supersession_manifest(
                root, 1, [{"from": "ORG-A", "to": "ORG-B", "reason": "published"}], None
            )
            v2 = self._write_supersession_manifest(
                root,
                2,
                [{"from": "ORG-C", "to": "ORG-D", "reason": "new normalization"}],
                str(v1.relative_to(root)),
            )
            base_rel = "knowledge/generated/entity-id-supersessions-v1.json"
            with mock.patch.object(history, "ROOT", root), mock.patch.object(
                history, "git_bytes", return_value=v1.read_bytes()
            ):
                errors = history.validate_base_versioned_history(
                    base_ref="BASE",
                    current_paths=[v1, v2],
                    base_paths=[base_rel],
                    prefix=history.SUPERSESSION_PREFIX,
                    label="identity supersession",
                )
        self.assertEqual(errors, [])

    def test_canonical_checker_reports_missing_supersession_target_without_nameerror(self) -> None:
        mapping, errors = coverage.checker.load_supersessions()
        self.assertEqual(errors, [])
        invalid_mapping = dict(mapping)
        invalid_mapping["ORG-TEST-MISSING-SOURCE"] = "ORG-TEST-MISSING-TARGET"
        with mock.patch.object(
            coverage.checker, "load_supersessions", return_value=(invalid_mapping, [])
        ), mock.patch.object(
            sys, "argv", ["check_canonical_entity_dossiers.py"]
        ), mock.patch("builtins.print") as output:
            return_code = coverage.checker.main()
        self.assertEqual(return_code, 1)
        rendered = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
        self.assertIn(
            "knowledge/generated/entity-id-supersessions-v*.json: supersession target is not a current ABox identity: "
            "ORG-TEST-MISSING-SOURCE -> ORG-TEST-MISSING-TARGET",
            rendered,
        )

    def test_baseline_preservation_accepts_authoritative_source_removal(self) -> None:
        before = {"id": "ORG-OLD", "iri": "ecl:ORG-OLD", "type": "Organization"}
        target = {"id": "ORG-NEW", "iri": "ecl:ORG-NEW", "type": "Organization"}
        with mock.patch.object(
            preservation_extended, "_supported_base_records", return_value={"ORG-OLD": before}
        ), mock.patch.object(
            preservation, "current_entity_index", return_value={"ORG-NEW": (target, "knowledge/entities/ORG-NEW.json")}
        ), mock.patch.object(
            preservation, "current_supersession_map", return_value={"ORG-OLD": "ORG-NEW"}
        ):
            self.assertEqual(preservation_extended.validate_baseline_identity_preservation("BASE", REPO_ROOT), [])

    def test_baseline_preservation_rejects_unmapped_deletion(self) -> None:
        before = {"id": "ORG-OLD", "iri": "ecl:ORG-OLD", "type": "Organization"}
        with mock.patch.object(
            preservation_extended, "_supported_base_records", return_value={"ORG-OLD": before}
        ), mock.patch.object(
            preservation, "current_entity_index", return_value={}
        ), mock.patch.object(
            preservation, "current_supersession_map", return_value={}
        ):
            errors = preservation_extended.validate_baseline_identity_preservation("BASE", REPO_ROOT)
        self.assertTrue(any("deleted without an authoritative identity supersession" in error for error in errors), errors)

    def test_baseline_preservation_rejects_materialized_supersession_source(self) -> None:
        before = {"id": "ORG-OLD", "iri": "ecl:ORG-OLD", "type": "Organization"}
        target = {"id": "ORG-NEW", "iri": "ecl:ORG-NEW", "type": "Organization"}
        current = {
            "ORG-OLD": (before, "knowledge/entities/ORG-OLD.json"),
            "ORG-NEW": (target, "knowledge/entities/ORG-NEW.json"),
        }
        with mock.patch.object(
            preservation_extended, "_supported_base_records", return_value={"ORG-OLD": before}
        ), mock.patch.object(
            preservation, "current_entity_index", return_value=current
        ), mock.patch.object(
            preservation, "current_supersession_map", return_value={"ORG-OLD": "ORG-NEW"}
        ):
            errors = preservation_extended.validate_baseline_identity_preservation("BASE", REPO_ROOT)
        self.assertTrue(any("superseded source remains materialized" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
