#!/usr/bin/env python3
"""Regression coverage for Schedule compatibility evidence and rendering gates."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScheduleCompatibilityGateTests(unittest.TestCase):
    def setUp(self):
        self.renderer = load_module("render_schedule_pass19", "tools/render_schedule.py")
        self.checker = load_module(
            "check_schedule_compatibility_pass19",
            "tools/check_schedule_compatibility_output.py",
        )
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

    def with_review(self, review):
        temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yml", delete=False)
        with temp:
            yaml.safe_dump(review, temp, sort_keys=False)
        path = Path(temp.name)
        self.created.append(path)
        return path

    def write_evidence_raw(self, raw: str):
        evidence_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        directory = ROOT / "reviews" / "schedule-compatibility"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{evidence_id}.yml"
        path.write_text(raw, encoding="utf-8")
        self.created.append(path)
        return evidence_id, path

    def evidence_template(self, reviewed_at="REVIEWED_AT_PLACEHOLDER"):
        return {
            "schema_version": 1,
            "target_license": self.renderer.TARGET_LICENSE,
            "target_license_artifact": copy.deepcopy(
                self.review["target_license_artifact"]
            ),
            "reviewer": "compatibility-regression-test",
            "reviewed_at": reviewed_at,
            "conclusion": "compatible",
            "sources": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": self.renderer.sha256(path),
                }
                for path in self.sources
            ],
        }

    def create_evidence(self, target_binding=None, reviewed_at="2026-08-15T00:00:00Z"):
        evidence = self.evidence_template(reviewed_at=reviewed_at)
        if target_binding is not None:
            evidence["target_license_artifact"] = copy.deepcopy(target_binding)
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        return self.write_evidence_raw(raw)

    def create_evidence_with_unquoted_reviewed_at(self, reviewed_at_text: str):
        evidence = self.evidence_template()
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        marker = "reviewed_at: REVIEWED_AT_PLACEHOLDER\n"
        self.assertIn(marker, raw)
        raw = raw.replace(marker, f"reviewed_at: {reviewed_at_text}\n", 1)
        return self.write_evidence_raw(raw)

    def create_evidence_with_duplicate_reviewed_at(self, first: str, second: str):
        evidence = self.evidence_template()
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        marker = "reviewed_at: REVIEWED_AT_PLACEHOLDER\n"
        self.assertIn(marker, raw)
        raw = raw.replace(
            marker,
            f"reviewed_at: {first}\nreviewed_at: {second}\n",
            1,
        )
        return self.write_evidence_raw(raw)

    def create_evidence_with_nested_duplicate_target_path(self):
        evidence = self.evidence_template(reviewed_at="2026-08-15T00:00:00Z")
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        target_path = self.review["target_license_artifact"]["path"]
        marker = f"target_license_artifact:\n  path: {target_path}\n"
        self.assertIn(marker, raw)
        raw = raw.replace(
            marker,
            "target_license_artifact:\n"
            "  path: stale/or-misleading-license.md\n"
            f"  path: {target_path}\n",
            1,
        )
        return self.write_evidence_raw(raw)

    def create_evidence_with_nested_merge_key(self):
        evidence = self.evidence_template(reviewed_at="2026-08-15T00:00:00Z")
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        target_path = self.review["target_license_artifact"]["path"]
        marker = f"target_license_artifact:\n  path: {target_path}\n"
        self.assertIn(marker, raw)
        raw = raw.replace(
            marker,
            "target_license_artifact:\n"
            "  <<: &target_defaults\n"
            f"    path: {target_path}\n"
            f"  path: {target_path}\n",
            1,
        )
        return self.write_evidence_raw(raw)

    def create_evidence_with_alias(self):
        evidence = self.evidence_template(reviewed_at="2026-08-15T00:00:00Z")
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        marker = "reviewer: compatibility-regression-test\n"
        self.assertIn(marker, raw)
        raw = raw.replace(
            marker,
            "reviewer: &reviewer compatibility-regression-test\n"
            "alias_probe: *reviewer\n",
            1,
        )
        return self.write_evidence_raw(raw)

    def create_evidence_with_custom_tag(self):
        evidence = self.evidence_template(reviewed_at="2026-08-15T00:00:00Z")
        raw = yaml.safe_dump(evidence, sort_keys=False, allow_unicode=True)
        marker = "reviewer: compatibility-regression-test\n"
        self.assertIn(marker, raw)
        raw = raw.replace(marker, "reviewer: !custom compatibility-regression-test\n", 1)
        return self.write_evidence_raw(raw)

    def complete_pointer(self, evidence_id):
        review = copy.deepcopy(self.review)
        review["status"] = "complete"
        review["review_evidence"] = {
            "id": evidence_id,
            "path": f"reviews/schedule-compatibility/{evidence_id}.yml",
        }
        return review

    def validate_pointer(self, review):
        review_path = self.with_review(review)
        old = self.renderer.COMPATIBILITY_REVIEW
        try:
            self.renderer.COMPATIBILITY_REVIEW = review_path
            return self.renderer.validate_compatibility_review(
                self.sources, self.renderer.TARGET_LICENSE
            )
        finally:
            self.renderer.COMPATIBILITY_REVIEW = old

    def test_current_pending_gate_binds_exact_target_license(self):
        self.assertFalse(
            self.renderer.validate_compatibility_review(
                self.sources, self.renderer.TARGET_LICENSE
            )
        )
        binding = self.review["target_license_artifact"]
        self.assertEqual(binding["path"], "versions/licenses/ECL-0.3-DRAFT.md")
        self.assertEqual(
            binding["sha256"],
            self.renderer.sha256(self.renderer.TARGET_LICENSE_ARTIFACT),
        )
        self.assertIsNone(self.review["review_evidence"])

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

    def test_working_license_drift_is_rejected(self):
        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        drifted = build / "compatibility-drift-license.txt"
        drifted.write_bytes(b"different working license bytes\n")
        self.created.append(drifted)
        old = self.renderer.WORKING_LICENSE
        try:
            self.renderer.WORKING_LICENSE = drifted
            with self.assertRaisesRegex(ValueError, "working LICENSE differs"):
                self.renderer.validate_compatibility_review(
                    self.sources, self.renderer.TARGET_LICENSE
                )
        finally:
            self.renderer.WORKING_LICENSE = old

    def test_complete_pointer_requires_content_addressed_evidence(self):
        evidence_id, _ = self.create_evidence()
        self.assertTrue(self.validate_pointer(self.complete_pointer(evidence_id)))

    def test_tampered_evidence_cannot_reuse_review_id(self):
        evidence_id, evidence_path = self.create_evidence()
        review = self.complete_pointer(evidence_id)
        review_path = self.with_review(review)
        evidence_path.write_text(
            evidence_path.read_text(encoding="utf-8") + "# tampered\n",
            encoding="utf-8",
        )
        old = self.renderer.COMPATIBILITY_REVIEW
        try:
            self.renderer.COMPATIBILITY_REVIEW = review_path
            with self.assertRaisesRegex(ValueError, "content hash does not match review id"):
                self.renderer.validate_compatibility_review(
                    self.sources, self.renderer.TARGET_LICENSE
                )
        finally:
            self.renderer.COMPATIBILITY_REVIEW = old

    def test_old_evidence_cannot_be_reused_after_license_refresh(self):
        evidence_id, _ = self.create_evidence()
        review = self.complete_pointer(evidence_id)

        build = ROOT / "build"
        build.mkdir(exist_ok=True)
        frozen = build / "future-ECL-0.3-DRAFT.md"
        working = build / "future-LICENSE"
        new_bytes = b"future license bytes not reviewed by old evidence\n"
        frozen.write_bytes(new_bytes)
        working.write_bytes(new_bytes)
        self.created.extend([frozen, working])
        review["target_license_artifact"] = {
            "path": str(frozen.relative_to(ROOT)),
            "sha256": hashlib.sha256(new_bytes).hexdigest(),
        }
        review_path = self.with_review(review)

        old_review = self.renderer.COMPATIBILITY_REVIEW
        old_target = self.renderer.TARGET_LICENSE_ARTIFACT
        old_working = self.renderer.WORKING_LICENSE
        try:
            self.renderer.COMPATIBILITY_REVIEW = review_path
            self.renderer.TARGET_LICENSE_ARTIFACT = frozen
            self.renderer.WORKING_LICENSE = working
            with self.assertRaisesRegex(ValueError, "evidence target License binding does not match pointer"):
                self.renderer.validate_compatibility_review(
                    self.sources, self.renderer.TARGET_LICENSE
                )
        finally:
            self.renderer.COMPATIBILITY_REVIEW = old_review
            self.renderer.TARGET_LICENSE_ARTIFACT = old_target
            self.renderer.WORKING_LICENSE = old_working

    def test_reviewed_at_accepts_iso_date_rfc3339_and_yaml_scalar_types(self):
        accepted = [
            "2026-08-15",
            "2026-08-15T00:00:00Z",
            "2026-08-15T00:00:00.123456+02:00",
            date(2026, 8, 15),
            datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc),
        ]
        for value in accepted:
            with self.subTest(value=value):
                self.renderer.validate_reviewed_at(value)

    def test_reviewed_at_rejects_malformed_timezone_less_or_padded_values(self):
        rejected = [
            "not-a-date",
            "2026-02-30",
            "2026-08-15T00:00:00",
            "2026-08-15 00:00:00Z",
            "2026-08-15T24:00:00Z",
            "2026-08-15T00:60:00Z",
            "2026-08-15T00:00:60Z",
            "2026-08-15T12:34:60Z",
            "2026-08-15T00:00:61Z",
            "2026-08-15T00:00:00+01:60",
            "2026-08-15T00:00:00+00:99",
            "2026-08-15T00:00:00+24:00",
            " 2026-08-15T00:00:00Z",
            "2026-08-15T00:00:00Z ",
            " 2026-08-15 ",
            datetime(2026, 8, 15, 0, 0),
            20260815,
        ]
        for value in rejected:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.renderer.validate_reviewed_at(value)

    def test_complete_evidence_accepts_unquoted_yaml_date_scalar(self):
        evidence_id, _ = self.create_evidence(reviewed_at=date(2026, 8, 15))
        self.assertTrue(self.validate_pointer(self.complete_pointer(evidence_id)))

    def test_complete_evidence_rejects_malformed_review_timestamp(self):
        evidence_id, _ = self.create_evidence(reviewed_at="not-a-date")
        with self.assertRaisesRegex(ValueError, "valid ISO date or RFC 3339 timestamp"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_unquoted_yaml_timestamp_cannot_normalize_out_of_range_fields(self):
        malformed = [
            "2026-08-15T24:00:00Z",
            "2026-08-15T00:00:00+01:60",
            "2026-08-15T00:00:00+00:99",
        ]
        for reviewed_at in malformed:
            with self.subTest(reviewed_at=reviewed_at):
                evidence_id, _ = self.create_evidence_with_unquoted_reviewed_at(reviewed_at)
                with self.assertRaisesRegex(
                    ValueError, "valid ISO date or RFC 3339 timestamp"
                ):
                    self.validate_pointer(self.complete_pointer(evidence_id))

    def test_duplicate_reviewed_at_keys_are_rejected_before_safe_load(self):
        evidence_id, _ = self.create_evidence_with_duplicate_reviewed_at(
            "2026-08-15T00:00:00Z",
            "2026-08-15T00:00:00+01:60",
        )
        with self.assertRaisesRegex(
            ValueError, "duplicate Schedule compatibility evidence key: reviewed_at"
        ):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_nested_duplicate_keys_are_rejected_before_safe_load(self):
        evidence_id, _ = self.create_evidence_with_nested_duplicate_target_path()
        with self.assertRaisesRegex(
            ValueError, "duplicate Schedule compatibility evidence key: path"
        ):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_nested_merge_keys_are_rejected_before_safe_load(self):
        evidence_id, _ = self.create_evidence_with_nested_merge_key()
        with self.assertRaisesRegex(ValueError, "must not use YAML merge keys"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_yaml_aliases_are_rejected_before_safe_load(self):
        evidence_id, _ = self.create_evidence_with_alias()
        with self.assertRaisesRegex(ValueError, "must not use YAML aliases"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_custom_yaml_tags_are_rejected_before_safe_load(self):
        evidence_id, _ = self.create_evidence_with_custom_tag()
        with self.assertRaisesRegex(ValueError, "unsupported YAML tag"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_complete_evidence_rejects_impossible_leap_second(self):
        evidence_id, _ = self.create_evidence(reviewed_at="2026-08-15T12:34:60Z")
        with self.assertRaisesRegex(ValueError, "valid ISO date or RFC 3339 timestamp"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_complete_evidence_rejects_quoted_timestamp_whitespace(self):
        evidence_id, _ = self.create_evidence(reviewed_at=" 2026-08-15T00:00:00Z ")
        with self.assertRaisesRegex(ValueError, "valid ISO date or RFC 3339 timestamp"):
            self.validate_pointer(self.complete_pointer(evidence_id))

    def test_rendered_state_checker_accepts_pending_and_complete(self):
        pending_text, _ = self.renderer.render()
        self.checker.validate_rendered_state(pending_text, self.review)

        complete_registry = copy.deepcopy(self.review)
        complete_registry["status"] = "complete"
        binding = complete_registry["target_license_artifact"]
        complete_text = "\n".join(
            [
                f"> Intended compatibility: **{self.renderer.TARGET_LICENSE} only**.",
                f"> Exact target License artifact: **{binding['path']}** (`{binding['sha256']}`).",
                "> Exact target License artifact and frozen clause source set: **compatibility revalidation complete and SHA-256-bound by immutable evidence**.",
            ]
        )
        self.checker.validate_rendered_state(complete_text, complete_registry)

    def test_schedule_workflows_cover_evidence_and_use_semantic_checker(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "LICENSE"', text)
            self.assertIn('- "versions/licenses/**"', text)
            self.assertIn('- "reviews/schedule-compatibility/**"', text)
            self.assertIn("check_schedule_compatibility_output.py", text)
            self.assertNotIn("grep -q \"Compatibility status:", text)


if __name__ == "__main__":
    unittest.main()
