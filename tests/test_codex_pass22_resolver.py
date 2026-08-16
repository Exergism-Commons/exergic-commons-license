from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve_pass22", MODULE_PATH)
RESOLVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RESOLVER)


class CodexPass22ResolverTests(unittest.TestCase):
    def ordinary_bundle(self):
        return {
            "bundle": "ECL-0.3.0@RP-2026.08.15",
            "operative": False,
            "license": {
                "ref": "ECL-0.3.0",
                "path": "versions/licenses/ECL-0.3.0.md",
                "sha256": "1" * 64,
            },
            "schedule": {
                "ref": "ECL-RP-2026.08.15",
                "path": "schedules/ECL-RP-2026.08.15.md",
                "sha256": "2" * 64,
            },
        }

    def test_non_string_reserved_identity_dimensions_are_validation_errors(self):
        probes = [
            ("license", "ref", []),
            ("license", "path", {}),
            ("license", "sha256", []),
            ("schedule", "ref", {}),
            ("schedule", "path", []),
            ("schedule", "sha256", {}),
        ]
        for component, key, malformed in probes:
            with self.subTest(component=component, key=key, malformed=malformed):
                bundle = copy.deepcopy(self.ordinary_bundle())
                bundle[component][key] = malformed
                with self.assertRaisesRegex(
                    ValueError, rf"bundle component {key} must be a non-empty string"
                ):
                    RESOLVER.validate_bundle_identity(bundle)

    def test_non_string_identity_dimensions_never_escape_as_typeerror(self):
        bundle = self.ordinary_bundle()
        bundle["license"]["ref"] = []
        try:
            RESOLVER.validate_bundle_identity(bundle)
        except TypeError as exc:  # pragma: no cover - this is the bypass regression
            self.fail(f"malformed Bundle identity escaped as TypeError: {exc}")
        except ValueError:
            pass
        else:
            self.fail("malformed Bundle identity was accepted")


if __name__ == "__main__":
    unittest.main()
