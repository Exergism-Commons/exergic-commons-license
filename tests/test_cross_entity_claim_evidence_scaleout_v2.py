import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge" / "generated" / "cross-entity-scaleout-v2.json"
V1_MANIFEST = ROOT / "knowledge" / "generated" / "cross-entity-scaleout-v1.json"

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
FORBIDDEN_RELATION_PREDICATES = {
    "ecl:controls",
    "ecl:controlledBy",
    "ecl:operates",
    "ecl:participatesIn",
    "ecl:deploys",
    "ecl:materiallyBenefits",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CrossEntityClaimEvidenceScaleoutV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_json(MANIFEST)
        cls.v1_manifest = load_json(V1_MANIFEST)
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

    def test_manifest_is_bounded_and_follows_v1(self):
        self.assertEqual(self.manifest["version"], 2)
        self.assertEqual(self.manifest["issue"], 220)
        self.assertEqual(
            self.manifest["followsManifest"],
            "knowledge/generated/cross-entity-scaleout-v1.json",
        )
        self.assertEqual(len(self.manifest["identities"]), 6)
        self.assertEqual(len(self.manifest["claims"]), 7)
        self.assertEqual(len(self.manifest["evidence"]), 8)
        self.assertTrue((ROOT / self.manifest["sourceReview"]).is_file())

        self.assertEqual(self.v1_manifest["version"], 1)
        self.assertEqual(self.v1_manifest["issue"], 214)
        self.assertEqual(len(self.v1_manifest["identities"]), 12)
        self.assertEqual(len(self.v1_manifest["claims"]), 6)
        self.assertEqual(len(self.v1_manifest["evidence"]), 5)

    def test_intellexa_legal_entity_identities_are_exact_and_governance_free(self):
        dossier_text = (
            ROOT / "dossiers" / "organizations" / "INTELLEXA-PREDATOR-NETWORK.md"
        ).read_text(encoding="utf-8")

        for item in self.manifest["identities"]:
            with self.subTest(identity=item["id"]):
                record = self.entity_records[item["id"]]
                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["type"], "Organization")
                self.assertEqual(record["name"], item["name"])
                self.assertEqual(record["dossier"], f"../../{item['dossier']}")
                self.assertIn(item["name"], dossier_text)
                self.assertTrue(FORBIDDEN_IDENTITY_KEYS.isdisjoint(record))
                self.assertNotIn("reviewDue", record)
                self.assertEqual(record["reviewClass"], "manual")

    def test_tranche_claims_are_tracks_only_and_resolve(self):
        curation_evidence_ids = {
            item["id"]
            for item in self.manifest["evidence"]
            if item["kind"] == "curation-anchor"
        }

        for item in self.manifest["claims"]:
            with self.subTest(claim=item["id"]):
                path = ROOT / "knowledge" / "claims" / f"{item['id']}.json"
                record = load_json(path)

                self.assertEqual(record["iri"], f"ecl:{item['id']}")
                self.assertEqual(record["status"], "accepted")
                self.assertEqual(record["predicate"], "ecl:tracks")
                self.assertEqual(record["predicate"], item["predicate"])
                self.assertNotIn(record["predicate"], FORBIDDEN_RELATION_PREDICATES)
                self.assertEqual(record["subject"], f"ecl:{item['subject']}")
                self.assertEqual(record["object"], f"ecl:{item['object']}")
                self.assertIn(item["subject"], self.entity_records)
                self.assertIn(item["object"], self.entity_records)

                evidence_for = {
                    iri.removeprefix("ecl:") for iri in record.get("evidenceFor", [])
                }
                self.assertTrue(evidence_for)
                self.assertTrue(evidence_for <= curation_evidence_ids)
                self.assertTrue(evidence_for <= set(self.evidence_records))

    def test_network_tracks_exactly_the_six_enumerated_legal_entities(self):
        expected = {item["id"] for item in self.manifest["identities"]}
        network_claims = [
            item
            for item in self.manifest["claims"]
            if item["subject"] == "ORG-INTELLEXA-PREDATOR-NETWORK"
        ]
        self.assertEqual(len(network_claims), 6)
        self.assertEqual({item["object"] for item in network_claims}, expected)

        hamas_claims = [
            item for item in self.manifest["claims"] if item["subject"] == "ORG-HAMAS"
        ]
        self.assertEqual(
            [(item["predicate"], item["object"]) for item in hamas_claims],
            [("ecl:tracks", "ORG-IZZ-AL-DIN-AL-QASSAM")],
        )

    def test_primary_source_anchors_are_reusable_and_conservative(self):
        primary_items = [
            item
            for item in self.manifest["evidence"]
            if item["kind"] == "primary-source-anchor"
        ]
        self.assertEqual(len(primary_items), 6)

        for item in primary_items:
            with self.subTest(evidence=item["id"]):
                record = self.evidence_records[item["id"]]
                self.assertEqual(record["type"], "EvidenceItem")
                self.assertEqual(record["sourceLocator"], item["sourceLocator"])
                self.assertTrue(record["sourceLocator"].startswith("https://"))
                self.assertNotEqual(record.get("sourceType"), "canonical-dossier")
                self.assertNotIn("evidenceGrade", record)
                self.assertNotIn("publicationDate", record)
                self.assertNotIn("retrievedAt", record)

                for dossier in item["dossiers"]:
                    dossier_text = (ROOT / dossier).read_text(encoding="utf-8")
                    self.assertIn(record["sourceLocator"], dossier_text)

    def test_curation_anchors_have_resolving_repository_provenance(self):
        curation_items = [
            item
            for item in self.manifest["evidence"]
            if item["kind"] == "curation-anchor"
        ]
        self.assertEqual(len(curation_items), 2)

        for item in curation_items:
            with self.subTest(evidence=item["id"]):
                record = self.evidence_records[item["id"]]
                self.assertEqual(record["sourceType"], "canonical-dossier")
                self.assertNotIn("evidenceGrade", record)
                self.assertNotIn("publicationDate", record)
                self.assertNotIn("retrievedAt", record)
                for provenance in record["provenance"]:
                    self.assertTrue(
                        (ROOT / "knowledge" / "evidence" / provenance).resolve().is_file()
                    )

    def test_tranche_does_not_create_project_or_governance_semantics(self):
        new_identity_ids = {item["id"] for item in self.manifest["identities"]}
        self.assertTrue(all(identity.startswith("ORG-") for identity in new_identity_ids))
        self.assertTrue(
            all(item["predicate"] == "ecl:tracks" for item in self.manifest["claims"])
        )
        self.assertTrue(
            all(
                not item["object"].startswith(("PROJECT-", "DEPLOYMENT-"))
                for item in self.manifest["claims"]
            )
        )


if __name__ == "__main__":
    unittest.main()
