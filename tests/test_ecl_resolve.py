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
    def test_repo_draft_channel_refuses_to_pretend_stable(self):
        root = Path(__file__).resolve().parents[1]
        policy = {"mode": "follow-stable", "license": "1.x", "channel": "draft"}
        with self.assertRaisesRegex(ValueError, "non-operative/draft"):
            MODULE.resolve_follow(policy, root, allow_draft=False)

    def test_exact_bundle_validates_hashes_and_renders_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channels").mkdir()
            (root / "releases" / "bundles").mkdir(parents=True)
            (root / "versions" / "licenses").mkdir(parents=True)
            (root / "schedules").mkdir()
            license_path = root / "versions" / "licenses" / "ECL-1.0.0.md"
            schedule_path = root / "schedules" / "ECL-RP-2026.10.02.1.md"
            license_path.write_text("license", encoding="utf-8")
            schedule_path.write_text("schedule", encoding="utf-8")
            bundle_ref = "ECL-1.0.0@RP-2026.10.02.1"
            bundle = {
                "schema_version": 1,
                "bundle": bundle_ref,
                "operative": True,
                "license": {
                    "ref": "ECL-1.0.0",
                    "path": "versions/licenses/ECL-1.0.0.md",
                    "sha256": MODULE.sha256(license_path),
                },
                "schedule": {
                    "ref": "ECL-RP-2026.10.02.1",
                    "path": "schedules/ECL-RP-2026.10.02.1.md",
                    "sha256": MODULE.sha256(schedule_path),
                },
            }
            manifest = root / "releases" / "bundles" / f"{bundle_ref}.json"
            manifest.write_text(json.dumps(bundle), encoding="utf-8")
            resolved = MODULE.resolve_pinned({"mode": "pinned", "bundle": bundle_ref}, root, False)
            lock = MODULE.render_lock(resolved)
            self.assertIn(f'bundle = "{bundle_ref}"', lock)
            self.assertIn('license = "ECL-1.0.0"', lock)

    def test_follow_stable_does_not_cross_required_major(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channels").mkdir()
            (root / "releases" / "bundles").mkdir(parents=True)
            (root / "versions" / "licenses").mkdir(parents=True)
            (root / "schedules").mkdir()
            license_path = root / "versions" / "licenses" / "ECL-2.0.0.md"
            schedule_path = root / "schedules" / "ECL-RP-2027.01.01.1.md"
            license_path.write_text("license2", encoding="utf-8")
            schedule_path.write_text("schedule2", encoding="utf-8")
            ref = "ECL-2.0.0@RP-2027.01.01.1"
            bundle = {
                "schema_version": 1,
                "bundle": ref,
                "operative": True,
                "license": {"ref": "ECL-2.0.0", "path": str(license_path.relative_to(root)), "sha256": MODULE.sha256(license_path)},
                "schedule": {"ref": "ECL-RP-2027.01.01.1", "path": str(schedule_path.relative_to(root)), "sha256": MODULE.sha256(schedule_path)},
            }
            (root / "releases" / "bundles" / f"{ref}.json").write_text(json.dumps(bundle), encoding="utf-8")
            (root / "channels" / "stable-1.json").write_text(json.dumps({"operative": True, "bundle": ref}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires 1.x"):
                MODULE.resolve_follow({"mode": "follow-stable", "license": "1.x", "channel": "stable-1"}, root, False)


if __name__ == "__main__":
    unittest.main()
