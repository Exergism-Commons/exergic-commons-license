import copy
import importlib.util
import json
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RESOLVER = load_module("ecl_resolve_pass12", ROOT / "tools" / "ecl_resolve.py")
RENDERER = load_module("render_schedule_pass12", ROOT / "tools" / "render_schedule.py")


class CrossSlotFallbackIdentityTests(unittest.TestCase):
    FALLBACK = "ECL-0.3-DRAFT@RP-EMPTY-1"
    ORDINARY = "ECL-0.3.0@RP-2026.08.15"

    def setUp(self):
        self.manifest = json.loads(
            (ROOT / "releases" / "bundles" / f"{self.FALLBACK}.json").read_text(
                encoding="utf-8"
            )
        )
        schema = json.loads(
            (ROOT / "schemas" / "bundle.schema.json").read_text(encoding="utf-8")
        )
        self.validator = jsonschema.Draft202012Validator(schema)

    @staticmethod
    def ordinary_component(ref: str, path: str) -> dict[str, str]:
        return {"ref": ref, "path": path, "sha256": "0" * 64}

    def assert_rejected_by_both(self, candidate):
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(candidate)
        with self.assertRaisesRegex(ValueError, "reserved canonical empty fallback identity"):
            RESOLVER.validate_bundle_components(ROOT, candidate)

    def test_reserved_schedule_identity_cannot_move_into_license_slot(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["bundle"] = self.ORDINARY
        candidate["operative"] = False
        candidate["license"] = copy.deepcopy(self.manifest["schedule"])
        candidate["schedule"] = self.ordinary_component(
            "ECL-RP-2026.08.15", "schedules/ECL-RP-2026.08.15.md"
        )
        self.assert_rejected_by_both(candidate)

    def test_reserved_license_identity_cannot_move_into_schedule_slot(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["bundle"] = self.ORDINARY
        candidate["operative"] = False
        candidate["license"] = self.ordinary_component(
            "ECL-0.3.0", "versions/licenses/ECL-0.3.0.md"
        )
        candidate["schedule"] = copy.deepcopy(self.manifest["license"])
        self.assert_rejected_by_both(candidate)

    def test_partial_cross_slot_reserved_ref_is_rejected(self):
        candidate = copy.deepcopy(self.manifest)
        candidate["bundle"] = self.ORDINARY
        candidate["operative"] = False
        candidate["license"] = self.ordinary_component(
            "ECL-RP-EMPTY-1", "versions/licenses/not-the-fallback.md"
        )
        candidate["schedule"] = self.ordinary_component(
            "ECL-RP-2026.08.15", "schedules/ECL-RP-2026.08.15.md"
        )
        self.assert_rejected_by_both(candidate)


class DraftVersionAlignmentTests(unittest.TestCase):
    def test_draft_channel_renderer_and_stored_schedule_agree_on_03(self):
        channel = json.loads(
            (ROOT / "channels" / "draft.json").read_text(encoding="utf-8")
        )
        self.assertFalse(channel["operative"])
        self.assertIsNone(channel["bundle"])
        self.assertEqual(channel["license"]["ref"], "ECL-0.3-DRAFT")
        self.assertEqual(channel["license"]["path"], "LICENSE")

        working_license = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("0.3-DRAFT", working_license[:300])

        rendered, _ = RENDERER.render()
        self.assertIn("Intended compatibility: **ECL 0.3-DRAFT only**.", rendered)
        self.assertNotIn("ECL 0.2-DRAFT only", rendered)

        stored_schedule = (
            ROOT / "schedules" / "ECL-RP-0.5-PARTIAL-DRAFT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Intended compatibility: **ECL 0.3-DRAFT only**.", stored_schedule)
        self.assertNotIn("ECL 0.2-DRAFT", stored_schedule)


if __name__ == "__main__":
    unittest.main()
