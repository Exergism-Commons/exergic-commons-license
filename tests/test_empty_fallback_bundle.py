import importlib.util
import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EmptyScheduleFallbackBundleTests(unittest.TestCase):
    BUNDLE_REF = "ECL-0.3-DRAFT@RP-EMPTY-1"

    def test_canonical_fallback_manifest_validates_against_bundle_schema(self):
        schema = json.loads((ROOT / "schemas" / "bundle.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (ROOT / "releases" / "bundles" / f"{self.BUNDLE_REF}.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.Draft202012Validator(schema).validate(manifest)

    def test_resolver_pins_exact_fallback_components(self):
        with self.assertRaisesRegex(ValueError, "non-operative/draft"):
            MODULE.resolve_pinned(
                {"mode": "pinned", "bundle": self.BUNDLE_REF}, ROOT, allow_draft=False
            )

        resolved = MODULE.resolve_pinned(
            {"mode": "pinned", "bundle": self.BUNDLE_REF}, ROOT, allow_draft=True
        )
        self.assertEqual(
            resolved["license"]["sha256"],
            MODULE.sha256(ROOT / "versions" / "licenses" / "ECL-0.3-DRAFT.md"),
        )
        self.assertEqual(
            resolved["schedule"]["sha256"],
            MODULE.sha256(ROOT / "schedules" / "ECL-RP-EMPTY-1.md"),
        )
        lock = MODULE.render_lock(resolved)
        self.assertIn(f'bundle = "{self.BUNDLE_REF}"', lock)
        self.assertIn('license = "ECL-0.3-DRAFT"', lock)
        self.assertIn('schedule = "ECL-RP-EMPTY-1"', lock)
        self.assertIn("operative = false", lock)


if __name__ == "__main__":
    unittest.main()
