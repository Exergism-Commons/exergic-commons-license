import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge" / "generated" / "cross-entity-scaleout-v1.json"

FORBIDDEN_IDENTITY_KEYS = {
    "outcome",
    "provisionalOutcome",
    "provisional_outcome",
    "tier",
    "restrictionStatus",
    "restrictedStatus",
    "governanceStatus",
    "currentGovernance",
}
ALLOWED_RELATION_PREDICATES = {"ecl:tracks", "ecl:participatesIn", "ecl:operates"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CrossEntityClaimEvidenceScaleoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_json(MANIFEST)
        cls.entity_records = {
            record["id"]: record
            for path in (ROOT / "knowledge" / "entities").glob("*.json")
            for record in [load_json(path)]
        }
        cls.evidence_records = {
            record["id"]: record
            for path in (ROOT / "knowledge" / "evidence").glob("*.json")
            for record in [load_json(path)]
        }

    def test_manifest_is_bounded_and_auditable(self):
        self.assertEqual(self.manifest["version"], 1)
        self.assertEqual(self.manifest["issue"], 214)
        self.assertEqual(len(self.manifest["identities"]), 12)
        self.assertEqual(len(self.manifest["claims"]), 6)
        self.assertEqual(len(self.manifest["evidence"]), 5)
        self.assertTrue((ROOT / self.manifest["sourceReview"]).is_file())

    def test_non_state_identities_match_canonical_dossiers_without_governance(self):
        for item in self.manifest["identities"]:
            with self.subTest(identity=item["id"]):
                record = self.entity_records[item["id"]]
                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["type"], item["type"])
                self.assertEqual(record["dossier"], f"../../{item['dossier']}")
                self.assertTrue(FORBIDDEN_IDENTITY_KEYS.isdisjoint(record))
                self.assertNotIn("reviewDue", record)
                self.assertEqual(record["reviewClass"], "manual")

                dossier = (ROOT / item["dossier"]).read_text(encoding="utf-8")
                self.assertIn(f"id: {item['dossierId']}", dossier)
                self.assertIn("last_reviewed: 2026-08-13", dossier)

    def test_scaleout_claims_are_explicit_relations_with_resolving_references(self):
        new_evidence_ids = {item["id"] for item in self.manifest["evidence"]}
        all_evidence_ids = set(self.evidence_records)
        self.assertTrue(new_evidence_ids <= all_evidence_ids)

        for item in self.manifest["claims"]:
            with self.subTest(claim=item["id"]):
                path = ROOT / "knowledge" / "claims" / f"{item['id']}.json"
                record = load_json(path)
                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["status"], "accepted")
                self.assertEqual(record["predicate"], item["predicate"])
                self.assertIn(record["predicate"], ALLOWED_RELATION_PREDICATES)
                self.assertEqual(record["subject"], f"ecl:{item['subject']}")
                self.assertEqual(record["object"], f"ecl:{item['object']}")
                self.assertIn(item["subject"], self.entity_records)
                self.assertIn(item["object"], self.entity_records)
                self.assertTrue(record.get("evidenceFor"))
                for evidence_iri in record["evidenceFor"]:
                    self.assertTrue(evidence_iri.startswith("ecl:EVIDENCE-"))
                    self.assertIn(evidence_iri.removeprefix("ecl:"), all_evidence_ids)
                self.assertNotEqual(record["predicate"], "ecl:outcome")

    def test_new_dossier_evidence_does_not_invent_grade_or_dates(self):
        for item in self.manifest["evidence"]:
            with self.subTest(evidence=item["id"]):
                record = self.evidence_records[item["id"]]
                self.assertEqual(record["type"], "EvidenceItem")
                self.assertEqual(record["sourceType"], "canonical-dossier")
                self.assertNotIn("evidenceGrade", record)
                self.assertNotIn("publicationDate", record)
                self.assertNotIn("retrievedAt", record)

    def test_this_tranche_does_not_materialize_njeem_warrant_allegations_as_claims(self):
        person_id = "PERSON-OSAMA-ELMASRY-NJEEM"
        tranche_subjects = {item["subject"] for item in self.manifest["claims"]}
        self.assertNotIn(person_id, tranche_subjects)


if __name__ == "__main__":
    unittest.main()
