import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge" / "generated" / "scoped-system-project-scaleout-v2.json"

FORBIDDEN_IDENTITY_KEYS = {
    "outcome",
    "provisionalOutcome",
    "provisional_outcome",
    "tier",
    "restrictionStatus",
    "restrictedStatus",
    "governanceStatus",
    "currentGovernance",
    "operative",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ScopedSystemProjectScaleoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_json(MANIFEST)
        cls.entities = {
            record["id"]: record
            for path in (ROOT / "knowledge" / "entities").glob("*.json")
            for record in [load_json(path)]
        }
        cls.evidence = {
            record["id"]: record
            for path in (ROOT / "knowledge" / "evidence").glob("*.json")
            for record in [load_json(path)]
        }

    def test_manifest_is_bounded_and_records_the_deferred_france_vsa(self):
        self.assertEqual(self.manifest["version"], 2)
        self.assertEqual(self.manifest["issue"], 217)
        self.assertEqual(len(self.manifest["projectDossiers"]), 3)
        self.assertEqual(len(self.manifest["identities"]), 3)
        self.assertEqual(len(self.manifest["claims"]), 4)
        self.assertEqual(len(self.manifest["evidence"]), 4)
        self.assertTrue((ROOT / self.manifest["sourceReview"]).is_file())

        self.assertEqual(len(self.manifest["deferred"]), 1)
        deferred = self.manifest["deferred"][0]
        self.assertEqual(deferred["candidateId"], "PROJECT-FRA-NATIONAL-LAW-ENFORCEMENT-VSA")
        self.assertIn("insufficient exact deployment boundary", deferred["reason"])
        self.assertNotIn(deferred["candidateId"], self.entities)

    def test_project_dossiers_and_identity_nodes_are_separate_governance_layers(self):
        dossier_ids = {item["dossierId"]: item for item in self.manifest["projectDossiers"]}
        for item in self.manifest["identities"]:
            with self.subTest(identity=item["id"]):
                record = self.entities[item["id"]]
                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["type"], "Project")
                self.assertEqual(record["dossier"], f"../../{item['dossier']}")
                self.assertEqual(record["reviewClass"], "manual")
                self.assertNotIn("reviewDue", record)
                self.assertTrue(FORBIDDEN_IDENTITY_KEYS.isdisjoint(record))

                dossier = (ROOT / item["dossier"]).read_text(encoding="utf-8")
                expected_dossier_id = f"ECL-{item['id']}"
                self.assertIn(expected_dossier_id, dossier_ids)
                self.assertIn(f"id: {expected_dossier_id}", dossier)
                self.assertIn("operative: false", dossier)
                self.assertIn("Governance record only", dossier)

    def test_claims_resolve_and_preserve_review_dependency_boundary(self):
        for item in self.manifest["claims"]:
            with self.subTest(claim=item["id"]):
                record = load_json(ROOT / "knowledge" / "claims" / f"{item['id']}.json")
                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["status"], "accepted")
                self.assertEqual(record["predicate"], item["predicate"])
                self.assertEqual(record["subject"], f"ecl:{item['subject']}")
                self.assertIn(item["subject"], self.entities)
                self.assertTrue(record.get("evidenceFor"))
                for evidence_iri in record["evidenceFor"]:
                    self.assertIn(evidence_iri.removeprefix("ecl:"), self.evidence)

                if item["predicate"] == "ecl:tracks":
                    self.assertEqual(record["object"], f"ecl:{item['object']}")
                    self.assertIn(item["object"], self.entities)
                    self.assertNotIn("literalValue", record)
                else:
                    self.assertEqual(item["predicate"], "ec:status")
                    self.assertNotIn("object", record)
                    self.assertEqual(record["literalValue"], item["literalValue"])

                self.assertNotEqual(record["predicate"], "ecl:outcome")

    def test_nice_status_is_narrow_judicial_remediation_fact(self):
        claim = load_json(
            ROOT
            / "knowledge"
            / "claims"
            / "CLAIM-FRA-NICE-ALGORITHMIC-CCTV-JUDICIALLY-BLOCKED.json"
        )
        self.assertEqual(claim["predicate"], "ec:status")
        self.assertEqual(claim["literalValue"], "judicially-blocked-not-authorized")
        self.assertEqual(claim["claimConfidence"], "established")
        self.assertEqual(claim["asOf"], "2026-01-30")
        self.assertNotIn("validFrom", claim)
        self.assertNotIn("validTo", claim)

        evidence = self.evidence["EVIDENCE-FRA-CONSEIL-ETAT-NICE-CCTV-2026-01-30"]
        self.assertEqual(evidence["sourceType"], "judicial-decision")
        self.assertEqual(evidence["evidenceGrade"], "E3")
        self.assertNotIn("publicationDate", evidence)
        self.assertNotIn("retrievedAt", evidence)
        self.assertIn("proposition-specific", evidence["notes"])

    def test_new_canonical_dossier_evidence_does_not_invent_grades_or_dates(self):
        canonical_ids = {
            item["id"]
            for item in self.manifest["evidence"]
            if item["kind"] == "canonical-dossier"
        }
        self.assertEqual(len(canonical_ids), 3)
        for evidence_id in canonical_ids:
            with self.subTest(evidence=evidence_id):
                record = self.evidence[evidence_id]
                self.assertEqual(record["sourceType"], "canonical-dossier")
                self.assertNotIn("evidenceGrade", record)
                self.assertNotIn("publicationDate", record)
                self.assertNotIn("retrievedAt", record)


if __name__ == "__main__":
    unittest.main()
