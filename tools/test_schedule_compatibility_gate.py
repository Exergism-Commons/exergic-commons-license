#!/usr/bin/env python3
"""Regression coverage for CODEX-0.3-025 exact License compatibility binding."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_renderer():
    path = ROOT / "tools" / "render_schedule.py"
    spec = importlib.util.spec_from_file_location("render_schedule_pass14", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExactLicenseCompatibilityGateTests(unittest.TestCase):
    def setUp(self):
        self.renderer = load_renderer()
        self.sources = self.renderer.schedule_clause_source_paths()
        self.review = yaml.safe_load(
            (ROOT / "registry" / "schedule-license-compatibility.yml").read_text(
                encoding="utf-8"
            )
        )

    def with_review(self, review):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yml", delete=False)
        with temp:
            yaml.safe_dump(review, temp, sort_keys=False)
        return Path(temp.name)

    def test_current_pending_gate_binds_exact_target_license(self):
        self.assertFalse(
            self.renderer.validate_compatibility_review(
                self.sources, self.renderer.TARGET_LICENSE
            )
        )
        binding = self.review["target_license_artifact"]
        self.assertEqual(
            binding["path"], "versions/licenses/ECL-0.3-DRAFT.md"
        )
        self.assertEqual(
            binding["sha256"],
            self.renderer.sha256(self.renderer.TARGET_LICENSE_ARTIFACT),
        )
        self.assertEqual(
            self.renderer.sha256(self.renderer.WORKING_LICENSE),
            self.renderer.sha256(self.renderer.TARGET_LICENSE_ARTIFACT),
        )

    def test_stale_target_license_sha_is_rejected(self):
        review = copy.deepcopy(self.review)
        review["target_license_artifact"]["sha256"] = "0" * 64
        review_path = self.with_review(review)
        old = self.renderer.COMPATIBILITY_REVIEW
        try:
            self.renderer.COMPATIBILITY_REVIEW = review_path
            with self.assertRaisesRegex(ValueError, "target License SHA-256 is stale"):
                self.renderer.validate_compatibility_review(
                    self.sources, self.renderer.TARGET_LICENSE
                )
        finally:
            self.renderer.COMPATIBILITY_REVIEW = old
            review_path.unlink(missing_ok=True)

    def test_working_license_drift_is_rejected(self):
        with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
            handle.write(b"different working license bytes\n")
            drifted = Path(handle.name)
        old = self.renderer.WORKING_LICENSE
        try:
            self.renderer.WORKING_LICENSE = drifted
            with self.assertRaisesRegex(ValueError, "working LICENSE differs"):
                self.renderer.validate_compatibility_review(
                    self.sources, self.renderer.TARGET_LICENSE
                )
        finally:
            self.renderer.WORKING_LICENSE = old
            drifted.unlink(missing_ok=True)

    def test_schedule_workflows_trigger_on_both_license_artifacts(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "LICENSE"', text)
            self.assertIn('- "versions/licenses/**"', text)


if __name__ == "__main__":
    unittest.main()
