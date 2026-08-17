import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVE_PATH = ROOT / "tools" / "ecl_resolve.py"
DIST_PATH = ROOT / "tools" / "ecl_distribution.py"

RESOLVE_SPEC = importlib.util.spec_from_file_location("ecl_resolve", RESOLVE_PATH)
RESOLVE = importlib.util.module_from_spec(RESOLVE_SPEC)
assert RESOLVE_SPEC.loader is not None
RESOLVE_SPEC.loader.exec_module(RESOLVE)

DIST_SPEC = importlib.util.spec_from_file_location("ecl_distribution", DIST_PATH)
DIST = importlib.util.module_from_spec(DIST_SPEC)
assert DIST_SPEC.loader is not None
DIST_SPEC.loader.exec_module(DIST)


class ECLDistributionTests(unittest.TestCase):
    def _write_source(self, root: Path):
        license_ref = "ECL-1.0.0"
        schedule_ref = "ECL-RP-2026.08.18.1"
        bundle_ref = "ECL-1.0.0@RP-2026.08.18.1"

        license_path = root / "versions" / "licenses" / f"{license_ref}.md"
        schedule_path = root / "schedules" / f"{schedule_ref}.md"
        bundle_path = root / "releases" / "bundles" / f"{bundle_ref}.json"
        license_path.parent.mkdir(parents=True)
        schedule_path.parent.mkdir(parents=True)
        bundle_path.parent.mkdir(parents=True)
        license_path.write_text("exact license bytes\n", encoding="utf-8")
        schedule_path.write_text("exact schedule bytes\n", encoding="utf-8")

        bundle = {
            "schema_version": 1,
            "bundle": bundle_ref,
            "operative": False,
            "license": {
                "ref": license_ref,
                "path": str(license_path.relative_to(root)),
                "sha256": RESOLVE.sha256(license_path),
            },
            "schedule": {
                "ref": schedule_ref,
                "path": str(schedule_path.relative_to(root)),
                "sha256": RESOLVE.sha256(schedule_path),
            },
        }
        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        return bundle, bundle_path

    def _build(self, source: Path, output: Path):
        bundle, _ = self._write_source(source)
        descriptor = DIST.build_distribution(
            source,
            bundle_ref=bundle["bundle"],
            output=output,
            allow_draft=True,
        )
        return bundle, descriptor

    def test_resolver_rejects_bundle_name_that_mismatches_license_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, bundle_path = self._write_source(root)
            bundle["license"]["ref"] = "ECL-1.0.1"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match license/schedule refs"):
                RESOLVE.resolve_pinned(
                    {"mode": "pinned", "bundle": "ECL-1.0.0@RP-2026.08.18.1"},
                    root,
                    True,
                )

    def test_resolver_rejects_bundle_name_that_mismatches_schedule_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, bundle_path = self._write_source(root)
            bundle["schedule"]["ref"] = "ECL-RP-2026.08.19.1"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match license/schedule refs"):
                RESOLVE.resolve_pinned(
                    {"mode": "pinned", "bundle": "ECL-1.0.0@RP-2026.08.18.1"},
                    root,
                    True,
                )

    def test_build_and_verify_self_contained_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            bundle, descriptor = self._build(source, output)

            verified = DIST.verify_distribution(output)
            self.assertEqual(bundle["bundle"], verified["bundle"])
            self.assertEqual(descriptor, verified)
            self.assertEqual((output / "LICENSE").read_text(), "exact license bytes\n")
            self.assertEqual((output / "ECL-SCHEDULE").read_text(), "exact schedule bytes\n")
            self.assertTrue((output / "ECL-BUNDLE.json").is_file())
            self.assertEqual(verified["notice"], DIST.NOTICE)
            self.assertFalse(verified["operative"])

    def test_build_refuses_nonoperative_bundle_without_explicit_draft_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            bundle, _ = self._write_source(source)

            with self.assertRaisesRegex(ValueError, "non-operative/draft"):
                DIST.build_distribution(
                    source,
                    bundle_ref=bundle["bundle"],
                    output=base / "dist",
                )

    def test_build_refuses_to_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            bundle, _ = self._write_source(source)
            output = base / "dist"
            output.mkdir()

            with self.assertRaisesRegex(ValueError, "output already exists"):
                DIST.build_distribution(
                    source,
                    bundle_ref=bundle["bundle"],
                    output=output,
                    allow_draft=True,
                )

    def test_missing_schedule_is_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            (output / "ECL-SCHEDULE").unlink()

            with self.assertRaisesRegex(ValueError, "missing distributed schedule"):
                DIST.verify_distribution(output)

    def test_tampered_schedule_is_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            (output / "ECL-SCHEDULE").write_text("later mutable schedule\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                DIST.verify_distribution(output)

    def test_schedule_symlink_cannot_satisfy_local_accompaniment(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            schedule = output / "ECL-SCHEDULE"
            original = schedule.read_bytes()
            schedule.unlink()
            outside = base / "outside-schedule"
            outside.write_bytes(original)
            schedule.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                DIST.verify_distribution(output)

    def test_tampered_bundle_manifest_is_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            (output / "ECL-BUNDLE.json").write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch for ECL-BUNDLE"):
                DIST.verify_distribution(output)

    def test_descriptor_cannot_redirect_schedule_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            descriptor_path = output / "ECL-DISTRIBUTION.json"
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["schedule"]["path"] = "../outside"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "path must be exactly ECL-SCHEDULE"):
                DIST.verify_distribution(output)

    def test_descriptor_bundle_must_match_frozen_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            descriptor_path = output / "ECL-DISTRIBUTION.json"
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["bundle"] = "ECL-1.0.1@RP-2026.08.18.1"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not match ECL-BUNDLE"):
                DIST.verify_distribution(output)

    def test_descriptor_must_preserve_non_attestation_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            descriptor_path = output / "ECL-DISTRIBUTION.json"
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["notice"] = "legally approved"
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "packaging-only notice"):
                DIST.verify_distribution(output)

    def test_operative_manifest_without_review_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            output = base / "dist"
            self._build(source, output)
            manifest_path = output / "ECL-BUNDLE.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["operative"] = True
            manifest_bytes = json.dumps(manifest).encode("utf-8")
            manifest_path.write_bytes(manifest_bytes)
            descriptor_path = output / "ECL-DISTRIBUTION.json"
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["operative"] = True
            descriptor["bundle_manifest"]["sha256"] = DIST.sha256_bytes(manifest_bytes)
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requires immutable legal_review"):
                DIST.verify_distribution(output)


if __name__ == "__main__":
    unittest.main()
