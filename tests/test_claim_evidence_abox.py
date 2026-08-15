import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate as shacl_validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
ECL = Namespace("urn:ecl:")

BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_knowledge_graph", ROOT / "tools" / "build_knowledge_graph.py"
)
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD_SPEC.loader.exec_module(BUILD)

EXPECTED_CLAIMS = {
    ECL["CLAIM-USA-TRACKS-OPERATION-EPIC-FURY-MINAB-TARGETING"],
    ECL["CLAIM-NLD-TRACKS-PROBATION-RISK-TOOLS"],
    ECL["CLAIM-NLD-PROBATION-RISK-TOOLS-RESPONSIBLE-USE-NOT-DEMONSTRATED"],
    ECL["CLAIM-LBY-TRACKS-MITIGA-DETENTION"],
    ECL["CLAIM-LBY-OPERATES-MITIGA-DETENTION"],
}
EXPECTED_EVIDENCE = {
    ECL["EVIDENCE-USA-CANONICAL-DOSSIER-2026-08-14"],
    ECL["EVIDENCE-NLD-CANONICAL-DOSSIER-2026-08-14"],
    ECL["EVIDENCE-NLD-INSPECTIE-JENV-RISK-ALGORITHMS-2026-02-12"],
    ECL["EVIDENCE-LBY-MITIGA-PROJECT-DOSSIER-2026-08-13"],
    ECL["EVIDENCE-LBY-STATE-DOSSIER-2026-08-11"],
    ECL["EVIDENCE-LBY-ICC-MITIGA-WARRANT-RECORD"],
}


class ClaimEvidenceABoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claim_schema = json.loads(
            (ROOT / "schemas" / "claim.schema.json").read_text(encoding="utf-8")
        )
        cls.evidence_schema = json.loads(
            (ROOT / "schemas" / "evidence-item.schema.json").read_text(encoding="utf-8")
        )
        cls.claim_validator = Draft202012Validator(
            cls.claim_schema, format_checker=FormatChecker()
        )
        cls.evidence_validator = Draft202012Validator(
            cls.evidence_schema, format_checker=FormatChecker()
        )
        cls.claim_files = sorted((ROOT / "knowledge" / "claims").glob("*.json"))
        cls.evidence_files = sorted((ROOT / "knowledge" / "evidence").glob("*.json"))
        cls.graph = Graph()
        for path in BUILD.iter_abox_files(ROOT / "knowledge"):
            cls.graph.parse(path, format="json-ld")
        cls.shapes = Graph().parse(ROOT / "ontology" / "ecl.shacl.ttl", format="turtle")
        cls.ontology = Graph().parse(ROOT / "ontology" / "ecl.owl.ttl", format="turtle")

    @staticmethod
    def integrity_query(name: str) -> str:
        return (ROOT / "sparql" / "integrity" / name).read_text(encoding="utf-8")

    def test_all_claim_and_evidence_sources_validate_against_json_schema(self):
        self.assertGreaterEqual(len(self.claim_files), 5)
        self.assertGreaterEqual(len(self.evidence_files), 6)
        for path in self.claim_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            errors = sorted(self.claim_validator.iter_errors(data), key=lambda e: list(e.path))
            self.assertEqual(errors, [], (path, [e.message for e in errors]))
        for path in self.evidence_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            errors = sorted(self.evidence_validator.iter_errors(data), key=lambda e: list(e.path))
            self.assertEqual(errors, [], (path, [e.message for e in errors]))

    def test_pilot_individuals_exist_as_first_class_rdf_nodes(self):
        claims = set(self.graph.subjects(RDF.type, ECL.Claim))
        evidence = set(self.graph.subjects(RDF.type, ECL.EvidenceItem))
        self.assertTrue(EXPECTED_CLAIMS <= claims)
        self.assertTrue(EXPECTED_EVIDENCE <= evidence)

    def test_accepted_claims_have_resolving_supporting_evidence(self):
        for claim in self.graph.subjects(RDF.type, ECL.Claim):
            statuses = {str(value) for value in self.graph.objects(claim, ECL.status)}
            if "accepted" not in statuses:
                continue
            supporting = list(self.graph.objects(claim, ECL.evidenceFor))
            self.assertTrue(supporting, claim)
            for evidence in supporting:
                self.assertIn((evidence, RDF.type, ECL.EvidenceItem), self.graph)
                self.assertTrue(any(self.graph.objects(evidence, ECL.stableId)), evidence)

    def test_lby_broad_operation_claim_preserves_live_dispute(self):
        claim = ECL["CLAIM-LBY-OPERATES-MITIGA-DETENTION"]
        self.assertEqual({str(v) for v in self.graph.objects(claim, ECL.status)}, {"disputed"})
        self.assertEqual({str(v) for v in self.graph.objects(claim, ECL.claimConfidence)}, {"disputed"})
        self.assertTrue(list(self.graph.objects(claim, ECL.evidenceFor)))
        self.assertTrue(list(self.graph.objects(claim, ECL.evidenceAgainst)))

    def test_evidence_grade_is_optional_and_only_curated_when_present(self):
        local = ECL["EVIDENCE-NLD-CANONICAL-DOSSIER-2026-08-14"]
        external = ECL["EVIDENCE-NLD-INSPECTIE-JENV-RISK-ALGORITHMS-2026-02-12"]
        self.assertEqual(list(self.graph.objects(local, ECL.evidenceGrade)), [])
        self.assertEqual({str(v) for v in self.graph.objects(external, ECL.evidenceGrade)}, {"E3"})

    def test_claim_internal_subjects_objects_and_evidence_links_resolve(self):
        for claim in self.graph.subjects(RDF.type, ECL.Claim):
            for predicate in (ECL.subject, ECL.object):
                for target in self.graph.objects(claim, predicate):
                    if isinstance(target, URIRef) and str(target).startswith("urn:ecl:"):
                        self.assertTrue(any(self.graph.objects(target, ECL.stableId)), (claim, target))
            for predicate in (ECL.evidenceFor, ECL.evidenceAgainst):
                for evidence in self.graph.objects(claim, predicate):
                    self.assertTrue(any(self.graph.objects(evidence, ECL.stableId)), (claim, evidence))

    def test_claims_do_not_assert_governance_outcome_predicates(self):
        forbidden_contains = (
            "currentgovernance",
            "governancestatus",
            "governanceoutcome",
            "restrictionstatus",
            "restrictedstatus",
            "provisionaloutcome",
        )
        for claim in self.graph.subjects(RDF.type, ECL.Claim):
            for predicate in self.graph.objects(claim, ECL.predicate):
                local_name = str(predicate).rsplit(":", 1)[-1].rsplit("/", 1)[-1].rsplit("#", 1)[-1]
                normalized = local_name.lower().replace("-", "").replace("_", "")
                forbidden = (
                    predicate == ECL.outcome
                    or any(token in normalized for token in forbidden_contains)
                    or normalized.startswith("tier")
                )
                self.assertFalse(forbidden, (claim, predicate))

    def test_conflict_guard_allows_multi_valued_relationships(self):
        graph = Graph()
        subject = ECL["STATE-TEST"]
        for suffix, target in (("A", ECL["PROJECT-A"]), ("B", ECL["PROJECT-B"])):
            claim = ECL[f"CLAIM-TEST-TRACKS-{suffix}"]
            graph.add((claim, RDF.type, ECL.Claim))
            graph.add((claim, ECL.subject, subject))
            graph.add((claim, ECL.predicate, ECL.tracks))
            graph.add((claim, ECL.status, Literal("accepted")))
            graph.add((claim, ECL.object, target))
        rows = list(graph.query(self.integrity_query("conflicting-accepted-claims.rq")))
        self.assertEqual(rows, [])

    def test_conflict_guard_preserves_literal_datatypes(self):
        graph = Graph()
        subject = ECL["PROJECT-TEST"]
        values = (Literal(1), Literal("1"))
        for index, value in enumerate(values):
            claim = ECL[f"CLAIM-TEST-STATUS-{index}"]
            graph.add((claim, RDF.type, ECL.Claim))
            graph.add((claim, ECL.subject, subject))
            graph.add((claim, ECL.predicate, ECL.status))
            graph.add((claim, ECL.status, Literal("accepted")))
            graph.add((claim, ECL.literalValue, value))
        rows = list(graph.query(self.integrity_query("conflicting-accepted-claims.rq")))
        self.assertEqual(len(rows), 1)

    def test_governance_guard_normalizes_separators_and_suffixes(self):
        graph = Graph()
        for index, predicate in enumerate(
            (ECL["governance__status"], ECL["governance-status-code"])
        ):
            claim = ECL[f"CLAIM-BAD-GOVERNANCE-{index}"]
            graph.add((claim, RDF.type, ECL.Claim))
            graph.add((claim, ECL.predicate, predicate))
        rows = list(graph.query(self.integrity_query("claim-governance-separation.rq")))
        self.assertEqual(len(rows), 2)

        data = Graph()
        claim = ECL["CLAIM-BAD-GOVERNANCE-SHACL"]
        data.add((claim, RDF.type, ECL.Claim))
        data.add((claim, ECL.stableId, Literal("CLAIM-BAD-GOVERNANCE-SHACL")))
        data.add((claim, ECL.subject, URIRef("https://example.invalid/subject")))
        data.add((claim, ECL.predicate, ECL["governance__status"]))
        data.add((claim, ECL.literalValue, Literal("x")))
        data.add((claim, ECL.status, Literal("rejected")))
        data.add((claim, ECL.provenance, Literal("adversarial test")))
        conforms, _, report = shacl_validate(
            data,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertFalse(conforms, report)

    def test_supersedes_must_resolve_to_same_record_kind(self):
        graph = Graph()
        claim = ECL["CLAIM-TEST-SUPERSESSION"]
        evidence_target = ECL["EVIDENCE-REAL-TARGET"]
        graph.add((claim, RDF.type, ECL.Claim))
        graph.add((claim, ECL.stableId, Literal("CLAIM-TEST-SUPERSESSION")))
        graph.add((claim, ECL.subject, URIRef("https://example.invalid/subject")))
        graph.add((claim, ECL.predicate, ECL.status))
        graph.add((claim, ECL.literalValue, Literal("x")))
        graph.add((claim, ECL.status, Literal("rejected")))
        graph.add((claim, ECL.provenance, Literal("adversarial test")))
        graph.add((claim, ECL.supersedes, evidence_target))

        graph.add((evidence_target, RDF.type, ECL.EvidenceItem))
        graph.add((evidence_target, ECL.stableId, Literal("EVIDENCE-REAL-TARGET")))
        graph.add((evidence_target, ECL.sourceLocator, Literal("https://example.invalid/evidence")))
        graph.add((evidence_target, ECL.provenance, Literal("adversarial test")))

        evidence = ECL["EVIDENCE-TEST-SUPERSESSION"]
        graph.add((evidence, RDF.type, ECL.EvidenceItem))
        graph.add((evidence, ECL.stableId, Literal("EVIDENCE-TEST-SUPERSESSION")))
        graph.add((evidence, ECL.sourceLocator, Literal("https://example.invalid/evidence-2")))
        graph.add((evidence, ECL.provenance, Literal("adversarial test")))
        graph.add((evidence, ECL.supersedes, ECL["EVIDENCE-MISSING"]))

        rows = list(graph.query(self.integrity_query("dangling-supersedes.rq")))
        self.assertEqual(len(rows), 2)

        conforms, _, report = shacl_validate(
            graph,
            shacl_graph=self.shapes,
            ont_graph=self.ontology,
            inference="none",
        )
        self.assertFalse(conforms, report)

    def test_repository_has_no_dangling_supersedes(self):
        self.assertEqual(
            list(self.graph.query(self.integrity_query("dangling-supersedes.rq"))), []
        )

    def test_schema_rejects_accepted_claim_without_support(self):
        sample = json.loads(self.claim_files[0].read_text(encoding="utf-8"))
        sample["status"] = "accepted"
        sample.pop("evidenceFor", None)
        sample.pop("evidenceAgainst", None)
        self.assertTrue(list(self.claim_validator.iter_errors(sample)))

    def test_builder_rejects_duplicate_source_iri_before_rdf_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = {"@context": {}, "iri": "ecl:DUPLICATE", "id": "DUPLICATE"}
            (root / "a.json").write_text(json.dumps(base), encoding="utf-8")
            other = dict(base)
            other["id"] = "OTHER-ID"
            (root / "b.json").write_text(json.dumps(other), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate ABox IRI"):
                BUILD.iter_abox_files(root)

    def test_builder_rejects_duplicate_source_stable_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.json").write_text(
                json.dumps({"@context": {}, "iri": "ecl:A", "id": "DUPLICATE-ID"}),
                encoding="utf-8",
            )
            (root / "b.json").write_text(
                json.dumps({"@context": {}, "iri": "ecl:B", "id": "DUPLICATE-ID"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate ABox stable id"):
                BUILD.iter_abox_files(root)


if __name__ == "__main__":
    unittest.main()
