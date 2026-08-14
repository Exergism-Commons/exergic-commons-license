import importlib.util
import tempfile
import unittest
from pathlib import Path
import json

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "update_ticket_sweep.py"
SPEC = importlib.util.spec_from_file_location("update_ticket_sweep", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class UpdateTicketSweepTests(unittest.TestCase):
    def entity(self, next_review="2026-09-01", review_class="hot"):
        return {
            "id": "STATE-TEST",
            "name": "Test State",
            "dossier": "../../dossiers/states/TST.md",
            "currentGovernance": "U",
            "review": {
                "lastSubstantiveReview": "2026-08-14",
                "nextReview": next_review,
                "reviewClass": review_class,
                "reason": "test",
            },
        }

    def test_future_review_does_not_fire(self):
        today = MODULE.dt.date(2026, 8, 14)
        self.assertIsNone(MODULE.build_signal(self.entity(), today))

    def test_due_review_fires_deterministically(self):
        today = MODULE.dt.date(2026, 9, 1)
        first = MODULE.build_signal(self.entity(), today)
        second = MODULE.build_signal(self.entity(), today)
        self.assertIsNotNone(first)
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertEqual(first["priority"], "P1")
        self.assertEqual(first["type"], "review-due")

    def test_stable_review_is_lower_priority(self):
        today = MODULE.dt.date(2026, 9, 1)
        signal = MODULE.build_signal(self.entity(review_class="stable"), today)
        self.assertEqual(signal["priority"], "P3")

    def test_load_entities_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.json").write_text(json.dumps(self.entity()), encoding="utf-8")
            another = self.entity()
            another["id"] = "STATE-AAA"
            (root / "a.json").write_text(json.dumps(another), encoding="utf-8")
            loaded = MODULE.load_entities(root)
            self.assertEqual([Path(item["_path"]).name for item in loaded], ["a.json", "b.json"])


if __name__ == "__main__":
    unittest.main()
