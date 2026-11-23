import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve_selector_boundary", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ResolverSelectorBoundaryTests(unittest.TestCase):
    def test_pinned_traversal_is_rejected_before_manifest_read(self):
        with mock.patch.object(MODULE, "load_json") as load_json:
            with self.assertRaisesRegex(ValueError, "immutable Bundle identifier"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": "../../outside"}, ROOT, True
                )
            load_json.assert_not_called()

    def test_pinned_latest_alias_is_rejected_before_manifest_read(self):
        with mock.patch.object(MODULE, "load_json") as load_json:
            with self.assertRaisesRegex(ValueError, "immutable Bundle identifier"):
                MODULE.resolve_pinned(
                    {"mode": "pinned", "bundle": "ECL-1.0.0@latest"}, ROOT, True
                )
            load_json.assert_not_called()

    def test_follow_channel_traversal_is_rejected_before_channel_read(self):
        with mock.patch.object(MODULE, "load_json") as load_json:
            with self.assertRaisesRegex(ValueError, "safe channel identifier"):
                MODULE.resolve_follow(
                    {"mode": "follow-stable", "channel": "../../outside"}, ROOT, True
                )
            load_json.assert_not_called()

    def test_follow_channel_bundle_traversal_is_rejected_before_manifest_read(self):
        channel = {"operative": True, "bundle": "../../outside"}
        with mock.patch.object(MODULE, "load_json", return_value=channel) as load_json:
            with self.assertRaisesRegex(ValueError, "does not resolve an immutable bundle"):
                MODULE.resolve_follow(
                    {"mode": "follow-stable", "channel": "stable"}, ROOT, True
                )
            self.assertEqual(load_json.call_count, 1)
            self.assertEqual(load_json.call_args.args[0], ROOT / "channels" / "stable.json")

    def test_follow_channel_latest_bundle_is_rejected_before_manifest_read(self):
        channel = {"operative": True, "bundle": "ECL-1.0.0@latest"}
        with mock.patch.object(MODULE, "load_json", return_value=channel) as load_json:
            with self.assertRaisesRegex(ValueError, "does not resolve an immutable bundle"):
                MODULE.resolve_follow(
                    {"mode": "follow-stable", "channel": "stable"}, ROOT, True
                )
            self.assertEqual(load_json.call_count, 1)


if __name__ == "__main__":
    unittest.main()
