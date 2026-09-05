import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "update_ticket_sweep.py"
SPEC = importlib.util.spec_from_file_location("update_ticket_sweep", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

REPO_ROOT = Path(__file__).resolve().parents[1]


class UpdateTicketSweepTests(unittest.TestCase):
    def entity(self, review_due="2026-09-01", review_class="hot"):
        entity = {
            "iri": "ex:STATE-TEST",
            "id": "STATE-TEST",
            "name": "Test State",
            "dossier": "../../dossiers/states/TST.md",
            "lastSubstantiveReview": "2026-08-14",
            "reviewClass": review_class,
            "reviewReason": "test",
        }
        if review_due is not None:
            entity["reviewDue"] = review_due
        return entity

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
        self.assertEqual(first["entityIri"], "ex:STATE-TEST")

    def test_stable_review_is_lower_priority(self):
        today = MODULE.dt.date(2026, 9, 1)
        signal = MODULE.build_signal(self.entity(review_class="stable"), today)
        self.assertEqual(signal["priority"], "P3")

    def test_manual_without_due_is_unscheduled_not_an_error(self):
        today = MODULE.dt.date(2026, 9, 1)
        self.assertIsNone(MODULE.build_signal(self.entity(review_due=None, review_class="manual"), today))

    def test_scheduled_class_without_due_is_invalid(self):
        today = MODULE.dt.date(2026, 9, 1)
        with self.assertRaisesRegex(ValueError, "reviewDue is required"):
            MODULE.build_signal(self.entity(review_due=None, review_class="hot"), today)

    def test_load_entities_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.json").write_text(json.dumps(self.entity()), encoding="utf-8")
            another = self.entity()
            another["id"] = "STATE-AAA"
            another["iri"] = "ex:STATE-AAA"
            (root / "a.jsonld").write_text(json.dumps(another), encoding="utf-8")
            loaded = MODULE.load_entities(root)
            self.assertEqual([Path(item["_path"]).name for item in loaded], ["a.jsonld", "b.json"])

    def test_pilot_signal_reads_governance_from_dossier(self):
        entity_path = REPO_ROOT / "knowledge" / "entities" / "STATE-JPN.json"
        entity = json.loads(entity_path.read_text(encoding="utf-8"))
        entity["_path"] = str(entity_path)
        signal = MODULE.build_signal(entity, MODULE.dt.date(2026, 9, 1))
        self.assertIsNotNone(signal)
        self.assertEqual(signal["currentGovernance"], "U")


if __name__ == "__main__":
    unittest.main()
