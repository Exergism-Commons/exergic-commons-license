import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve_identity", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BundleReleaseIdentityTests(unittest.TestCase):
    def _bundle(self):
        return {
            "schema_version": 1,
            "bundle": "ECL-1.0.0@RP-2026.08.18.1",
            "operative": False,
            "license": {
                "ref": "ECL-1.0.0",
                "path": "versions/licenses/ECL-1.0.0.md",
                "sha256": "1" * 64,
            },
            "schedule": {
                "ref": "ECL-RP-2026.08.18.1",
                "path": "schedules/ECL-RP-2026.08.18.1.md",
                "sha256": "2" * 64,
            },
        }

    def test_bundle_cannot_use_latest_identity(self):
        bundle = self._bundle()
        bundle["bundle"] = "ECL-1.0.0@latest"
        bundle["schedule"]["ref"] = "ECL-latest"
        bundle["schedule"]["path"] = "schedules/ECL-latest.md"
        with self.assertRaisesRegex(ValueError, "invalid immutable bundle identity"):
            MODULE.validate_bundle_identity(bundle)

    def test_license_ref_must_be_immutable_release_identifier(self):
        bundle = self._bundle()
        bundle["license"]["ref"] = "ECL-latest"
        with self.assertRaisesRegex(ValueError, "license ref is not an immutable"):
            MODULE.validate_bundle_identity(bundle)

    def test_license_path_cannot_use_mutable_channel_namespace(self):
        bundle = self._bundle()
        bundle["license"]["path"] = "channels/stable-license.md"
        with self.assertRaisesRegex(ValueError, "license path must use immutable release namespace"):
            MODULE.validate_bundle_identity(bundle)

    def test_schedule_path_cannot_use_mutable_channel_namespace(self):
        bundle = self._bundle()
        bundle["schedule"]["path"] = "channels/latest-schedule.md"
        with self.assertRaisesRegex(ValueError, "schedule path must use immutable release namespace"):
            MODULE.validate_bundle_identity(bundle)


if __name__ == "__main__":
    unittest.main()
