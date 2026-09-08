#!/usr/bin/env python3
"""Regressions for identity-history, State lifecycle and recursive resolver contracts."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_canonical_entity_manifest_history as history  # noqa: E402
import entity_identity_resolution as resolver  # noqa: E402


class CodexP2IdentityContractTests(unittest.TestCase):
    def _write_supersession_manifest(
        self,
        root: Path,
        version: int,
        rows: list[dict],
        follows: str | None,
    ) -> Path:
        path = root / f"knowledge/generated/entity-id-supersessions-v{version}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": version, "follows": follows, "supersessions": rows}),
            encoding="utf-8",
        )
        return path

    def test_new_supersession_source_requires_curated_base_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self._write_supersession_manifest(root, 1, [], None)
            v2 = self._write_supersession_manifest(
                root,
                2,
                [{"from": "ORG-TYPO", "to": "ORG-LIVE", "reason": "mistyped historical id"}],
                str(v1.relative_to(root)),
            )
            with mock.patch.object(history, "ROOT", root):
                errors = history.validate_new_supersession_sources(
                    current_paths=[v1, v2],
                    base_paths=["knowledge/generated/entity-id-supersessions-v1.json"],
                    curated_ids={"ORG-LIVE", "ORG-KNOWN"},
                )
        self.assertTrue(any("ORG-TYPO" in error and "no curated identity history" in error for error in errors), errors)

    def test_new_supersession_source_accepts_previously_curated_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self._write_supersession_manifest(root, 1, [], None)
            v2 = self._write_supersession_manifest(
                root,
                2,
                [{"from": "ORG-KNOWN", "to": "ORG-LIVE", "reason": "canonical normalization"}],
                str(v1.relative_to(root)),
            )
            with mock.patch.object(history, "ROOT", root):
                errors = history.validate_new_supersession_sources(
                    current_paths=[v1, v2],
                    base_paths=["knowledge/generated/entity-id-supersessions-v1.json"],
                    curated_ids={"ORG-KNOWN", "ORG-LIVE"},
                )
        self.assertEqual(errors, [])

    def test_state_schema_rejects_identity_lifecycle_fields(self) -> None:
        schema = json.loads((REPO_ROOT / "schemas/entity.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        state = {
            "@context": "../../ontology/ecl-context.jsonld",
            "iri": "ecl:STATE-USA",
            "id": "STATE-USA",
            "type": "State",
            "name": "United States",
            "iso3": "USA",
            "aliases": ["United States of America"],
            "dossier": "../../dossiers/states/USA.md",
            "publicReviewIssue": "https://github.com/Papishushi/exergic-commons-license/issues/1",
            "lastSubstantiveReview": "2026-09-08",
            "reviewClass": "manual",
        }
        self.assertEqual(list(validator.iter_errors(state)), [])
        for field, value in (
            ("identityLifecycle", "active"),
            ("supersededBy", "ecl:STATE-CAN"),
        ):
            with self.subTest(field=field):
                mutated = dict(state)
                mutated[field] = value
                self.assertTrue(list(validator.iter_errors(mutated)))

    def test_non_state_schema_keeps_identity_lifecycle_contract(self) -> None:
        schema = json.loads((REPO_ROOT / "schemas/entity.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        organization = {
            "@context": "../../ontology/ecl-context.jsonld",
            "iri": "ecl:ORG-OLD",
            "id": "ORG-OLD",
            "type": "Organization",
            "name": "Old Organization",
            "dossier": "../../dossiers/organizations/ORG-OLD.md",
            "lastSubstantiveReview": "2026-09-08",
            "reviewClass": "manual",
            "identityLifecycle": "superseded",
            "supersededBy": "ecl:ORG-NEW",
        }
        self.assertEqual(list(validator.iter_errors(organization)), [])

    def test_repository_entity_loader_recurses_and_accepts_jsonld(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entity_dir = Path(tmp) / "knowledge/entities"
            nested = entity_dir / "nested"
            nested.mkdir(parents=True)
            (entity_dir / "ORG-TOP.json").write_text(json.dumps({"id": "ORG-TOP"}), encoding="utf-8")
            (nested / "ORG-NESTED.jsonld").write_text(json.dumps({"id": "ORG-NESTED"}), encoding="utf-8")
            (nested / "ORG-IGNORED.JSON").write_text(json.dumps({"id": "ORG-IGNORED"}), encoding="utf-8")
            entities, entity_ids = resolver.load_repository_entities(entity_dir)
        self.assertEqual(entity_ids, {"ORG-TOP", "ORG-NESTED"})
        self.assertEqual({record["id"] for record in entities}, entity_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
