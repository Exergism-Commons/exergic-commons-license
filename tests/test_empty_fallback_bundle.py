import copy
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

    def _manifest(self):
        return json.loads(
            (ROOT / "releases" / "bundles" / f"{self.BUNDLE_REF}.json").read_text(
                encoding="utf-8"
            )
        )

    def _validator(self):
        schema = json.loads(
            (ROOT / "schemas" / "bundle.schema.json").read_text(encoding="utf-8")
        )
        return jsonschema.Draft202012Validator(schema)

    def test_canonical_fallback_manifest_validates_against_bundle_schema(self):
        self._validator().validate(self._manifest())

    def test_schema_rejects_empty_suffix_or_component_substitution(self):
        manifest = self._manifest()
        attacks = [
            ("unsupported suffix", lambda value: value.__setitem__("bundle", "ECL-0.3-DRAFT@RP-EMPTY-999")),
            ("license ref", lambda value: value["license"].__setitem__("ref", "ECL-9.9-DRAFT")),
            (
                "license path",
                lambda value: value["license"].__setitem__(
                    "path", "versions/licenses/ECL-9.9-DRAFT.md"
                ),
            ),
            ("license hash", lambda value: value["license"].__setitem__("sha256", "0" * 64)),
            ("schedule ref", lambda value: value["schedule"].__setitem__("ref", "ECL-RP-EMPTY-999")),
            (
                "schedule path",
                lambda value: value["schedule"].__setitem__(
                    "path", "schedules/ECL-RP-EMPTY-999.md"
                ),
            ),
            ("schedule hash", lambda value: value["schedule"].__setitem__("sha256", "0" * 64)),
            ("operative escalation", lambda value: value.__setitem__("operative", True)),
        ]
        validator = self._validator()
        for label, mutate in attacks:
            with self.subTest(label=label):
                candidate = copy.deepcopy(manifest)
                mutate(candidate)
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(candidate)

    def test_runtime_rejects_empty_bundle_component_substitution(self):
        manifest = self._manifest()
        attacks = [
            (
                "license ref",
                "mismatched license identity",
                lambda value: value["license"].__setitem__("ref", "ECL-9.9-DRAFT"),
            ),
            (
                "license path",
                "mismatched license identity",
                lambda value: value["license"].__setitem__(
                    "path", "versions/licenses/ECL-9.9-DRAFT.md"
                ),
            ),
            (
                "license hash",
                "mismatched license identity",
                lambda value: value["license"].__setitem__("sha256", "0" * 64),
            ),
            (
                "schedule ref",
                "mismatched schedule identity",
                lambda value: value["schedule"].__setitem__("ref", "ECL-RP-EMPTY-999"),
            ),
            (
                "schedule path",
                "mismatched schedule identity",
                lambda value: value["schedule"].__setitem__(
                    "path", "schedules/ECL-RP-EMPTY-999.md"
                ),
            ),
            (
                "schedule hash",
                "mismatched schedule identity",
                lambda value: value["schedule"].__setitem__("sha256", "0" * 64),
            ),
            (
                "operative escalation",
                "invalid operative state",
                lambda value: value.__setitem__("operative", True),
            ),
        ]
        for label, error, mutate in attacks:
            with self.subTest(label=label):
                candidate = copy.deepcopy(manifest)
                mutate(candidate)
                with self.assertRaisesRegex(ValueError, error):
                    MODULE.validate_bundle_components(ROOT, candidate)

    def test_runtime_rejects_unregistered_empty_bundle_identifier(self):
        candidate = self._manifest()
        candidate["bundle"] = "ECL-0.3-DRAFT@RP-EMPTY-999"
        candidate["schedule"]["ref"] = "ECL-RP-EMPTY-999"
        with self.assertRaisesRegex(ValueError, "unsupported canonical empty fallback bundle"):
            MODULE.validate_bundle_components(ROOT, candidate)

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
