import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from rdflib import Graph, Namespace, RDF, URIRef

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
        forbidden_suffixes = (
            "currentgovernance", "governancestatus", "governanceoutcome",
            "restrictionstatus", "restrictedstatus", "tier", "provisionaloutcome", "outcome",
        )
        for claim in self.graph.subjects(RDF.type, ECL.Claim):
            for predicate in self.graph.objects(claim, ECL.predicate):
                normalized = str(predicate).lower().replace("-", "").replace("_", "")
                self.assertFalse(normalized.endswith(forbidden_suffixes), (claim, predicate))

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
