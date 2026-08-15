import json
import unittest
from pathlib import Path

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF

from tools.build_knowledge_graph import iter_abox_files


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
ENTITIES = KNOWLEDGE / "entities"
MANIFEST = KNOWLEDGE / "generated" / "agency-hierarchy-scaleout-v5.json"
ONTOLOGY = ROOT / "ontology" / "ecl.owl.ttl"
ECL = Namespace("urn:ecl:")

EXPECTED_AGENCIES = {
    "AGENCY-USA-DHS": "STATE-USA",
    "AGENCY-USA-ICE": "AGENCY-USA-DHS",
    "AGENCY-USA-HSI": "AGENCY-USA-ICE",
    "AGENCY-USA-DOD": "STATE-USA",
    "AGENCY-USA-ARMY": "AGENCY-USA-DOD",
    "AGENCY-USA-CENTCOM": "AGENCY-USA-DOD",
}

EXPECTED_CLAIMS = {
    "CLAIM-HSI-PARTICIPATES-IN-ICE-ICM-IA": (
        "AGENCY-USA-HSI",
        ECL.participatesIn,
        "PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS",
        "EVIDENCE-ICE-ICM-CANONICAL-DOSSIER-2026-08-13",
    ),
    "CLAIM-USA-ARMY-PARTICIPATES-IN-MAVEN-SMART-SYSTEM": (
        "AGENCY-USA-ARMY",
        ECL.participatesIn,
        "PROJECT-MAVEN-SMART-SYSTEM",
        "EVIDENCE-MAVEN-CANONICAL-DOSSIER-2026-08-13",
    ),
    "CLAIM-USA-CENTCOM-OPERATES-EPIC-FURY-MINAB-TARGETING": (
        "AGENCY-USA-CENTCOM",
        ECL.operates,
        "PROJECT-OPERATION-EPIC-FURY-MINAB-TARGETING",
        "EVIDENCE-MINAB-CANONICAL-DOSSIER-2026-08-13",
    ),
}

FORBIDDEN_GOVERNANCE_KEYS = {
    "outcome",
    "status",
    "tier",
    "restrictionStatus",
    "restricted",
    "inheritedRestriction",
    "currentGovernance",
    "governanceStatus",
    "governanceOutcome",
    "provisional_outcome",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_abox() -> Graph:
    graph = Graph()
    for path in iter_abox_files(KNOWLEDGE):
        graph.parse(path, format="json-ld")
    return graph


def iri(stable_id: str) -> URIRef:
    return URIRef(f"urn:ecl:{stable_id}")


class AgencyHierarchyScaleoutV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abox = build_abox()
        cls.ontology = Graph().parse(ONTOLOGY, format="turtle")
        cls.inferred = Graph()
        for triple in cls.ontology:
            cls.inferred.add(triple)
        for triple in cls.abox:
            cls.inferred.add(triple)
        DeductiveClosure(OWLRL_Semantics).expand(cls.inferred)

    def test_expected_agencies_are_identity_only_and_resolve_direct_parents(self):
        for agency_id, parent_id in EXPECTED_AGENCIES.items():
            path = ENTITIES / f"{agency_id}.json"
            self.assertTrue(path.is_file(), path)
            record = load_json(path)
            with self.subTest(agency=agency_id):
                self.assertEqual(record["type"], "Agency")
                self.assertEqual(record["iri"], f"ecl:{agency_id}")
                self.assertEqual(record["id"], agency_id)
                self.assertEqual(record["partOf"], [f"ecl:{parent_id}"])
                self.assertFalse(
                    FORBIDDEN_GOVERNANCE_KEYS.intersection(record),
                    f"{path}: Agency identity must not carry governance fields",
                )
                dossier = (path.parent / record["dossier"]).resolve()
                self.assertTrue(dossier.is_file(), dossier)

                agency = iri(agency_id)
                parent = iri(parent_id)
                self.assertIn((agency, RDF.type, ECL.Agency), self.abox)
                self.assertIn((agency, ECL.partOf, parent), self.abox)
                self.assertTrue(
                    any(self.abox.objects(parent, ECL.stableId)),
                    f"{agency_id}: unresolved direct parent {parent_id}",
                )

    def test_partof_is_direct_and_non_propagating_even_after_owlrl(self):
        self.assertIn((ECL.partOf, RDF.type, OWL.ObjectProperty), self.ontology)
        self.assertNotIn((ECL.partOf, RDF.type, OWL.TransitiveProperty), self.ontology)
        self.assertEqual(list(self.ontology.triples((None, OWL.propertyChainAxiom, None))), [])

        non_edges = {
            ("AGENCY-USA-HSI", "AGENCY-USA-DHS"),
            ("AGENCY-USA-HSI", "STATE-USA"),
            ("AGENCY-USA-ICE", "STATE-USA"),
            ("AGENCY-USA-ARMY", "STATE-USA"),
            ("AGENCY-USA-CENTCOM", "STATE-USA"),
        }
        for child_id, ancestor_id in non_edges:
            edge = (iri(child_id), ECL.partOf, iri(ancestor_id))
            with self.subTest(child=child_id, ancestor=ancestor_id):
                self.assertNotIn(edge, self.abox)
                self.assertNotIn(edge, self.inferred)

    def test_functional_claims_are_narrow_evidence_backed_propositions(self):
        for claim_id, (subject_id, predicate, object_id, evidence_id) in EXPECTED_CLAIMS.items():
            claim = iri(claim_id)
            with self.subTest(claim=claim_id):
                self.assertIn((claim, RDF.type, ECL.Claim), self.abox)
                self.assertIn((claim, ECL.subject, iri(subject_id)), self.abox)
                self.assertIn((claim, ECL.predicate, predicate), self.abox)
                self.assertIn((claim, ECL.object, iri(object_id)), self.abox)
                self.assertIn((claim, ECL.status, None), self.abox)
                self.assertEqual(
                    {str(value) for value in self.abox.objects(claim, ECL.status)},
                    {"accepted"},
                )
                self.assertIn((claim, ECL.evidenceFor, iri(evidence_id)), self.abox)
                self.assertIn((iri(evidence_id), RDF.type, ECL.EvidenceItem), self.abox)

    def test_claim_predicates_do_not_execute_or_inherit_through_parents(self):
        forbidden_direct_relations = {
            ("AGENCY-USA-HSI", ECL.participatesIn, "PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS"),
            ("AGENCY-USA-ICE", ECL.participatesIn, "PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS"),
            ("AGENCY-USA-DHS", ECL.participatesIn, "PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS"),
            ("AGENCY-USA-ARMY", ECL.participatesIn, "PROJECT-MAVEN-SMART-SYSTEM"),
            ("AGENCY-USA-DOD", ECL.participatesIn, "PROJECT-MAVEN-SMART-SYSTEM"),
            ("AGENCY-USA-CENTCOM", ECL.operates, "PROJECT-OPERATION-EPIC-FURY-MINAB-TARGETING"),
            ("AGENCY-USA-DOD", ECL.operates, "PROJECT-OPERATION-EPIC-FURY-MINAB-TARGETING"),
            ("STATE-USA", ECL.operates, "PROJECT-OPERATION-EPIC-FURY-MINAB-TARGETING"),
        }
        for subject_id, predicate, object_id in forbidden_direct_relations:
            triple = (iri(subject_id), predicate, iri(object_id))
            with self.subTest(subject=subject_id, predicate=str(predicate), object=object_id):
                self.assertNotIn(triple, self.abox)
                self.assertNotIn(triple, self.inferred)

    def test_tranche_5_manifest_is_a_bounded_audit_snapshot(self):
        manifest = load_json(MANIFEST)
        self.assertEqual(manifest["version"], 5)
        self.assertEqual(manifest["globalTranche"], 5)
        self.assertEqual(manifest["issue"], 224)
        self.assertEqual(manifest["baseMainCommit"], "d56aa690b19115cd275043c2f49ea8cbcc8f5cc2")
        self.assertEqual(set(manifest["agencies"]), set(EXPECTED_AGENCIES))
        self.assertEqual(set(manifest["functionalClaims"]), set(EXPECTED_CLAIMS))
        self.assertFalse(manifest["semantics"]["transitive"])
        self.assertFalse(manifest["semantics"]["propagatesFunctionalAttribution"])
        self.assertFalse(manifest["semantics"]["propagatesGovernance"])
        self.assertFalse(manifest["semantics"]["claimsExecutePredicates"])

        edges = {(edge["child"], edge["parent"]) for edge in manifest["partOfEdges"]}
        self.assertEqual(edges, set(EXPECTED_AGENCIES.items()))


if __name__ == "__main__":
    unittest.main()
