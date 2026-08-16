#!/usr/bin/env python3
"""Regression coverage for YAML key-identity collisions in compatibility evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_renderer():
    path = ROOT / "tools" / "render_schedule.py"
    spec = importlib.util.spec_from_file_location("render_schedule_pass20_keys", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScheduleYamlKeySecurityTests(unittest.TestCase):
    def setUp(self):
        self.renderer = load_renderer()
        self.sources = self.renderer.schedule_clause_source_paths()
        self.review = yaml.safe_load(
            (ROOT / "registry" / "schedule-license-compatibility.yml").read_text(
                encoding="utf-8"
            )
        )
        self.created: list[Path] = []

    def tearDown(self):
        for path in self.created:
            path.unlink(missing_ok=True)

    def evidence_body(self) -> str:
        evidence = {
            "schema_version": 1,
            "target_license": self.renderer.TARGET_LICENSE,
            "target_license_artifact": copy.deepcopy(
                self.review["target_license_artifact"]
            ),
            "reviewer": "yaml-key-regression-test",
            "reviewed_at": "2026-08-15T00:00:00Z",
            "conclusion": "compatible",
            "sources": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": self.renderer.sha256(path),
                }
                for path in self.sources
            ],
        }
        return yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)

    def write_evidence(self, prefix: str) -> str:
        raw = prefix + self.evidence_body()
        evidence_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        directory = ROOT / "reviews" / "schedule-compatibility"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{evidence_id}.yml"
        path.write_text(raw, encoding="utf-8")
        self.created.append(path)
        return evidence_id

    def validate_complete(self, evidence_id: str) -> bool:
        pointer = copy.deepcopy(self.review)
        pointer["status"] = "complete"
        pointer["review_evidence"] = {
            "id": evidence_id,
            "path": f"reviews/schedule-compatibility/{evidence_id}.yml",
        }
        temp = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".yml", delete=False
        )
        with temp:
            yaml.safe_dump(pointer, temp, sort_keys=False)
        pointer_path = Path(temp.name)
        self.created.append(pointer_path)

        old = self.renderer.COMPATIBILITY_REVIEW
        try:
            self.renderer.COMPATIBILITY_REVIEW = pointer_path
            return self.renderer.validate_compatibility_review(
                self.sources, self.renderer.TARGET_LICENSE
            )
        finally:
            self.renderer.COMPATIBILITY_REVIEW = old

    def test_safe_loader_equal_non_string_keys_are_rejected_before_construction(self):
        collision_prefixes = [
            "1: first\ntrue: second\n",
            "01: first\n1: second\n",
            "null: first\n~: second\n",
        ]
        for prefix in collision_prefixes:
            with self.subTest(prefix=prefix):
                evidence_id = self.write_evidence(prefix)
                with self.assertRaisesRegex(
                    ValueError, "keys must use the YAML string tag"
                ):
                    self.validate_complete(evidence_id)

    def test_quoted_extra_key_remains_a_string_key(self):
        evidence_id = self.write_evidence('"1": harmless-extra-field\n')
        self.assertTrue(self.validate_complete(evidence_id))


if __name__ == "__main__":
    unittest.main()
