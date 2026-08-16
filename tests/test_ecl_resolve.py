import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ECLResolveTests(unittest.TestCase):
    def _write_components(self, root: Path, license_ref: str, schedule_ref: str):
        (root / "versions" / "licenses").mkdir(parents=True, exist_ok=True)
        (root / "schedules").mkdir(parents=True, exist_ok=True)
        license_path = root / "versions" / "licenses" / f"{license_ref}.md"
        schedule_path = root / "schedules" / f"{schedule_ref}.md"
        license_path.write_text("license", encoding="utf-8")
        schedule_path.write_text("schedule", encoding="utf-8")
        return license_path, schedule_path

    def _write_completed_legal_review(self, root: Path, license_path: Path):
        review_id = "ECL-1.0.0-legal-review-1"
        input_dir = root / "reviews" / "legal" / "inputs" / review_id
        record_dir = root / "reviews" / "legal" / "records"
        input_dir.mkdir(parents=True, exist_ok=True)
        record_dir.mkdir(parents=True, exist_ok=True)

        review_spec_path = input_dir / "LEGAL-ADVERSARIAL-REVIEW.md"
        incorporation_spec_path = input_dir / "VERSIONING.md"
        bundle_schema_path = input_dir / "bundle.schema.json"
        review_spec_path.write_text("frozen legal review specification", encoding="utf-8")
        incorporation_spec_path.write_text("frozen exact incorporation model", encoding="utf-8")
        bundle_schema_path.write_text('{"frozen": true}', encoding="utf-8")

        # Canonical files may evolve after release. They are intentionally not
        # the files against which historical review validation is performed.
        (root / "spec").mkdir(parents=True, exist_ok=True)
        (root / "schemas").mkdir(parents=True, exist_ok=True)
        (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_text(
            "current review spec", encoding="utf-8"
        )
        (root / "spec" / "VERSIONING.md").write_text(
            "current incorporation model", encoding="utf-8"
        )
        (root / "schemas" / "bundle.schema.json").write_text(
            '{"current": true}', encoding="utf-8"
        )

        review_path = record_dir / f"{review_id}.json"
        record = {
            "schema_version": 1,
            "review_id": review_id,
            "status": "complete",
            "license_sha256": MODULE.sha256(license_path),
            "review_spec": {
                "path": str(review_spec_path.relative_to(root)),
                "sha256": MODULE.sha256(review_spec_path),
            },
            "incorporation_spec": {
                "path": str(incorporation_spec_path.relative_to(root)),
                "sha256": MODULE.sha256(incorporation_spec_path),
            },
            "bundle_schema": {
                "path": str(bundle_schema_path.relative_to(root)),
                "sha256": MODULE.sha256(bundle_schema_path),
            },
            "jurisdictions": {
                "eu_software": "complete",
                "spain": "complete",
                "united_states": "complete",
                "united_kingdom": "complete",
                "cross_border": "complete",
            },
            "attack_surfaces": {
                f"LAR-{number:02d}": "resolved" for number in range(1, 17)
            },
            "qualified_independent_reviews": 2,
            "qualified_adversarial_reviews": 1,
            "unresolved_blockers": 0,
            "unresolved_majors": 0,
            "undispositioned_material_findings": 0,
            "delta_review_complete": True,
            "recorded_at": "2026-08-15T00:00:00Z",
        }
        review_path.write_text(json.dumps(record), encoding="utf-8")
        component = {
            "ref": review_id,
            "path": str(review_path.relative_to(root)),
            "sha256": MODULE.sha256(review_path),
        }
        return review_path, record, component, input_dir

    def _write_bundle(self, root: Path, bundle: dict):
        (root / "releases" / "bundles").mkdir(parents=True, exist_ok=True)
        manifest = root / "releases" / "bundles" / f"{bundle['bundle']}.json"
        manifest.write_text(json.dumps(bundle), encoding="utf-8")
        return manifest

    def _bundle(self, root: Path, *, operative: bool = True, legal_review=None):
        license_ref = "ECL-1.0.0"
        schedule_ref = "ECL-RP-2026.10.02.1"
        license_path, schedule_path = self._write_components(root, license_ref, schedule_ref)
        bundle_ref = "ECL-1.0.0@RP-2026.10.02.1"
        bundle = {
            "schema_version": 1,
            "bundle": bundle_ref,
            "operative": operative,
            "license": {
                "ref": license_ref,
                "path": str(license_path.relative_to(root)),
                "sha256": MODULE.sha256(license_path),
            },
            "schedule": {
                "ref": schedule_ref,
                "path": str(schedule_path.relative_to(root)),
                "sha256": MODULE.sha256(schedule_path),
            },
        }
        if legal_review is not None:
            bundle["legal_review"] = legal_review
        return bundle, license_path

    def test_repo_draft_channel_refuses_to_pretend_stable(self):
        root = Path(__file__).resolve().parents[1]
        policy = {"mode": "follow-stable", "license": "1.x", "channel": "draft"}
        with self.assertRaisesRegex(ValueError, "non-operative/draft"):
            MODULE.resolve_follow(policy, root, allow_draft=False)

    def test_exact_operational_bundle_requires_completed_review_and_renders_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channels").mkdir()
            bundle, license_path = self._bundle(root, operative=True)
            _, _, legal_review, _ = self._write_completed_legal_review(root, license_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            resolved = MODULE.resolve_pinned(
                {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
            )
            lock = MODULE.render_lock(resolved)
            self.assertIn(f'bundle = "{bundle["bundle"]}"', lock)
            self.assertIn("operative = true", lock)
            self.assertIn('license = "ECL-1.0.0"', lock)
            self.assertIn('legal_review = "ECL-1.0.0-legal-review-1"', lock)

    def test_operative_bundle_without_legal_review_is_rejected_even_when_drafts_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, _ = self._bundle(root, operative=True)
            self._write_bundle(root, bundle)

            for allow_draft in (False, True):
                with self.subTest(allow_draft=allow_draft):
                    with self.assertRaisesRegex(ValueError, "requires immutable legal_review"):
                        MODULE.resolve_pinned(
                            {"mode": "pinned", "bundle": bundle["bundle"]},
                            root,
                            allow_draft,
                        )

    def test_nonoperative_bundle_can_be_resolved_explicitly_without_legal_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, _ = self._bundle(root, operative=False)
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "non-operative/draft"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

            resolved = MODULE.resolve_pinned(
                {"mode": "pinned", "bundle": bundle["bundle"]}, root, True
            )
            self.assertFalse(resolved["operative"])
            self.assertNotIn("legal_review", resolved)
            self.assertIn("operative = false", MODULE.render_lock(resolved))

    def test_legal_review_reference_must_match_record_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            _, _, legal_review, _ = self._write_completed_legal_review(root, license_path)
            legal_review["ref"] = "different-review"
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "ref does not match"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_legal_review_record_path_must_match_review_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            review_path, _, legal_review, _ = self._write_completed_legal_review(
                root, license_path
            )
            alternate = review_path.parent / "alternate.json"
            alternate.write_bytes(review_path.read_bytes())
            legal_review["path"] = str(alternate.relative_to(root))
            legal_review["sha256"] = MODULE.sha256(alternate)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "path must match immutable record path"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_legal_review_must_bind_exact_bundle_license_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            review_path, record, legal_review, _ = self._write_completed_legal_review(
                root, license_path
            )
            record["license_sha256"] = "0" * 64
            review_path.write_text(json.dumps(record), encoding="utf-8")
            legal_review["sha256"] = MODULE.sha256(review_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "does not bind exact bundle license SHA-256"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_later_canonical_spec_change_does_not_invalidate_historical_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            _, _, legal_review, _ = self._write_completed_legal_review(root, license_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            (root / "spec" / "VERSIONING.md").write_text(
                "future canonical incorporation model", encoding="utf-8"
            )
            (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_text(
                "future canonical review spec", encoding="utf-8"
            )
            (root / "schemas" / "bundle.schema.json").write_text(
                '{"future": true}', encoding="utf-8"
            )

            resolved = MODULE.resolve_pinned(
                {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
            )
            self.assertTrue(resolved["operative"])

    def test_mutating_frozen_incorporation_snapshot_invalidates_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            _, _, legal_review, input_dir = self._write_completed_legal_review(
                root, license_path
            )
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            (input_dir / "VERSIONING.md").write_text(
                "tampered frozen incorporation model", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_review_cannot_point_to_wrong_frozen_input_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            review_path, record, legal_review, input_dir = self._write_completed_legal_review(
                root, license_path
            )
            alternate = input_dir / "ALTERNATE.md"
            alternate.write_text("alternate", encoding="utf-8")
            record["incorporation_spec"] = {
                "path": str(alternate.relative_to(root)),
                "sha256": MODULE.sha256(alternate),
            }
            review_path.write_text(json.dumps(record), encoding="utf-8")
            legal_review["sha256"] = MODULE.sha256(review_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "must bind frozen review input"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_incomplete_required_jurisdiction_blocks_operative_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            review_path, record, legal_review, _ = self._write_completed_legal_review(
                root, license_path
            )
            record["jurisdictions"]["united_kingdom"] = "open"
            review_path.write_text(json.dumps(record), encoding="utf-8")
            legal_review["sha256"] = MODULE.sha256(review_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "jurisdiction coverage incomplete"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_missing_attack_surface_disposition_blocks_operative_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, license_path = self._bundle(root, operative=True)
            review_path, record, legal_review, _ = self._write_completed_legal_review(
                root, license_path
            )
            del record["attack_surfaces"]["LAR-16"]
            review_path.write_text(json.dumps(record), encoding="utf-8")
            legal_review["sha256"] = MODULE.sha256(review_path)
            bundle["legal_review"] = legal_review
            self._write_bundle(root, bundle)

            with self.assertRaisesRegex(ValueError, "attack surfaces incomplete"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": bundle["bundle"]}, root, False
                )

    def test_follow_channel_bundle_ref_must_match_manifest_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channels").mkdir()
            (root / "releases" / "bundles").mkdir(parents=True)
            bundle, _ = self._bundle(root, operative=False)
            channel_ref = bundle["bundle"]
            bundle["bundle"] = "ECL-1.0.0@RP-2026.10.02.99"
            manifest = root / "releases" / "bundles" / f"{channel_ref}.json"
            manifest.write_text(json.dumps(bundle), encoding="utf-8")
            (root / "channels" / "stable-1.json").write_text(
                json.dumps({"operative": True, "bundle": channel_ref}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "bundle manifest identity mismatch"):
                MODULE.resolve_follow(
                    {"mode": "follow-stable", "license": "1.x", "channel": "stable-1"},
                    root,
                    True,
                )

    def test_follow_stable_does_not_cross_required_major(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channels").mkdir()
            (root / "releases" / "bundles").mkdir(parents=True)
            license_path, schedule_path = self._write_components(
                root, "ECL-2.0.0", "ECL-RP-2027.01.01.1"
            )
            ref = "ECL-2.0.0@RP-2027.01.01.1"
            bundle = {
                "schema_version": 1,
                "bundle": ref,
                "operative": True,
                "license": {
                    "ref": "ECL-2.0.0",
                    "path": str(license_path.relative_to(root)),
                    "sha256": MODULE.sha256(license_path),
                },
                "schedule": {
                    "ref": "ECL-RP-2027.01.01.1",
                    "path": str(schedule_path.relative_to(root)),
                    "sha256": MODULE.sha256(schedule_path),
                },
            }
            self._write_bundle(root, bundle)
            (root / "channels" / "stable-1.json").write_text(
                json.dumps({"operative": True, "bundle": ref}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "requires 1.x"):
                MODULE.resolve_follow(
                    {"mode": "follow-stable", "license": "1.x", "channel": "stable-1"},
                    root,
                    False,
                )


if __name__ == "__main__":
    unittest.main()
