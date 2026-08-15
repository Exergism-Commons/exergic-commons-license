import unittest
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

ROOT = Path(__file__).resolve().parents[1]
ECL = Namespace("urn:ecl:")


class GovernancePredicatePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query = (ROOT / "sparql" / "integrity" / "claim-governance-separation.rq").read_text(
            encoding="utf-8"
        )
        cls.shapes = Graph().parse(ROOT / "ontology" / "ecl.shacl.ttl", format="turtle")
        cls.ontology = Graph().parse(ROOT / "ontology" / "ecl.owl.ttl", format="turtle")

    @staticmethod
    def claim_graph(predicate: URIRef, stable_id: str) -> Graph:
        graph = Graph()
        claim = ECL[stable_id]
        graph.add((claim, RDF.type, ECL.Claim))
        graph.add((claim, ECL.stableId, Literal(stable_id)))
        graph.add((claim, ECL.subject, URIRef("https://example.invalid/subject")))
        graph.add((claim, ECL.predicate, predicate))
        graph.add((claim, ECL.literalValue, Literal("x")))
        graph.add((claim, ECL.status, Literal("rejected")))
        graph.add((claim, ECL.provenance, Literal("adversarial path-separator regression")))
        return graph

    def assert_claim_conforms(self, graph: Graph) -> None:
        conforms, _, report = shacl_validate(
            graph,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertTrue(conforms, report)

    def test_http_path_governance_predicate_is_rejected_by_sparql_and_shacl(self):
        graph = self.claim_graph(
            URIRef("https://example.invalid/governance/status"),
            "CLAIM-HTTP-PATH-GOVERNANCE",
        )
        rows = list(graph.query(self.query))
        self.assertEqual(len(rows), 1)

        conforms, _, report = shacl_validate(
            graph,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertFalse(conforms, report)
        self.assertIn("Claim nodes may not encode governance", report)

    def test_generic_http_status_predicate_remains_allowed_by_claim_guard(self):
        graph = self.claim_graph(
            URIRef("https://example.invalid/project/status"),
            "CLAIM-HTTP-PATH-STATUS",
        )
        self.assertEqual(list(graph.query(self.query)), [])
        self.assert_claim_conforms(graph)

    def test_frontier_token_does_not_trigger_tier_guard(self):
        graph = self.claim_graph(
            URIRef("https://example.invalid/project/frontier-status"),
            "CLAIM-HTTP-FRONTIER-STATUS",
        )
        self.assertEqual(list(graph.query(self.query)), [])
        self.assert_claim_conforms(graph)

    def test_governance_hostname_alone_does_not_trigger_guard(self):
        graph = self.claim_graph(
            URIRef("https://governancestatus.example.invalid/project/value"),
            "CLAIM-GOVERNANCE-HOSTNAME-ONLY",
        )
        self.assertEqual(list(graph.query(self.query)), [])
        self.assert_claim_conforms(graph)

    def test_state_guard_uses_the_same_full_iri_normalization(self):
        graph = Graph()
        state = ECL["STATE-TST"]
        graph.add((state, RDF.type, ECL.State))
        graph.add((state, ECL.stableId, Literal("STATE-TST")))
        graph.add((state, ECL.name, Literal("Test State")))
        graph.add((state, ECL.iso3, Literal("TST")))
        graph.add((state, ECL.dossier, Literal("../../dossiers/states/TST.md")))
        graph.add((state, ECL.publicReviewIssue, URIRef("https://example.invalid/review/1")))
        graph.add((state, ECL.lastSubstantiveReview, Literal("2026-08-15", datatype=XSD.date)))
        graph.add((state, ECL.reviewClass, Literal("manual")))
        graph.add((state, URIRef("https://example.invalid/governance/status"), Literal("x")))

        conforms, _, report = shacl_validate(
            graph,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertFalse(conforms, report)
        self.assertIn("Governance/tier/restriction status must never live directly", report)


if __name__ == "__main__":
    unittest.main()
