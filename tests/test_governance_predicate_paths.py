import unittest
from pathlib import Path

from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

ROOT = Path(__file__).resolve().parents[1]
ECL = Namespace("https://id.exergism.org/ecl#")


EX = Namespace("https://id.exergism.org/exergism#")
EC = Namespace("https://id.exergism.org/commons#")
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
        graph.add((claim, RDF.type, EX.Claim))
        graph.add((claim, EC.stableId, Literal(stable_id)))
        graph.add((claim, ECL.subject, URIRef("https://example.invalid/subject")))
        graph.add((claim, ECL.predicate, predicate))
        graph.add((claim, ECL.literalValue, Literal("x")))
        graph.add((claim, EC.status, Literal("rejected")))
        graph.add((claim, EC.provenance, Literal("adversarial IRI-separator regression")))
        return graph

    @staticmethod
    def state_graph(predicate: URIRef) -> Graph:
        graph = Graph()
        state = ECL["STATE-TST"]
        graph.add((state, RDF.type, EX.State))
        graph.add((state, EC.stableId, Literal("STATE-TST")))
        graph.add((state, ECL.name, Literal("Test State")))
        graph.add((state, ECL.iso3, Literal("TST")))
        graph.add((state, ECL.dossier, Literal("../../dossiers/states/TST.md")))
        graph.add((state, ECL.publicReviewIssue, URIRef("https://example.invalid/review/1")))
        graph.add((state, ECL.lastSubstantiveReview, Literal("2026-08-15", datatype=XSD.date)))
        graph.add((state, ECL.reviewClass, Literal("manual")))
        graph.add((state, predicate, Literal("x")))
        return graph

    def assert_claim_conforms(self, graph: Graph) -> None:
        conforms, _, report = shacl_validate(
            graph,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertTrue(conforms, report)

    def assert_claim_rejected(self, predicate: str, stable_id: str) -> None:
        graph = self.claim_graph(URIRef(predicate), stable_id)
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

    def test_http_path_governance_predicate_is_rejected_by_sparql_and_shacl(self):
        self.assert_claim_rejected(
            "https://example.invalid/governance/status",
            "CLAIM-HTTP-PATH-GOVERNANCE",
        )

    def test_http_fragment_governance_predicate_is_rejected_by_sparql_and_shacl(self):
        self.assert_claim_rejected(
            "https://example.invalid#governance-status",
            "CLAIM-HTTP-FRAGMENT-GOVERNANCE",
        )

    def test_http_query_governance_predicate_is_rejected_by_sparql_and_shacl(self):
        self.assert_claim_rejected(
            "https://example.invalid?kind=governance/status",
            "CLAIM-HTTP-QUERY-GOVERNANCE",
        )

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

    def test_state_guard_preserves_path_query_and_fragment_semantics(self):
        predicates = (
            "https://example.invalid/governance/status",
            "https://example.invalid#governance-status",
            "https://example.invalid?kind=governance/status",
        )
        for predicate in predicates:
            with self.subTest(predicate=predicate):
                graph = self.state_graph(URIRef(predicate))
                conforms, _, report = shacl_validate(
                    graph,
                    shacl_graph=self.shapes,
                    ont_graph=self.ontology,
                    inference="none",
                )
                self.assertFalse(conforms, report)
                self.assertIn(
                    "Governance/tier/restriction status must never live directly",
                    report,
                )


if __name__ == "__main__":
    unittest.main()
