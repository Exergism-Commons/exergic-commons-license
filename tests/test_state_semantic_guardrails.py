import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, RDF
from rdflib.namespace import OWL

ROOT = Path(__file__).resolve().parents[1]
ECL = Namespace("urn:ecl:")

BUILD_SPEC = importlib.util.spec_from_file_location("build_knowledge_graph", ROOT / "tools" / "build_knowledge_graph.py")
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD_SPEC.loader.exec_module(BUILD)


class StateSemanticGuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abox = Graph()
        cls.state_files = sorted((ROOT / "knowledge" / "entities").glob("STATE-*.json"))
        for path in cls.state_files:
            cls.abox.parse(path, format="json-ld")
        cls.tbox = Graph().parse(ROOT / "ontology" / "ecl.owl.ttl", format="turtle")

    def test_all_195_jsonld_state_records_parse_as_rdf(self):
        states = set(self.abox.subjects(RDF.type, ECL.State))
        self.assertEqual(len(self.state_files), 195)
        self.assertEqual(len(states), 195)

    def test_each_state_has_exactly_one_iso_and_mapping(self):
        for state in self.abox.subjects(RDF.type, ECL.State):
            iso = list(self.abox.objects(state, ECL.iso3))
            ids = list(self.abox.objects(state, ECL.stableId))
            dossiers = list(self.abox.objects(state, ECL.dossier))
            issues = list(self.abox.objects(state, ECL.publicReviewIssue))
            self.assertEqual(len(iso), 1, state)
            self.assertEqual(len(ids), 1, state)
            self.assertEqual(len(dossiers), 1, state)
            self.assertEqual(len(issues), 1, state)
            code = str(iso[0])
            self.assertEqual(str(state), f"urn:ecl:STATE-{code}")
            self.assertEqual(str(ids[0]), f"STATE-{code}")
            self.assertTrue(str(dossiers[0]).endswith(f"/{code}.md"))
            self.assertTrue(str(issues[0]).startswith("https://github.com/Papishushi/exergic-commons-license/issues/"))

    def test_state_actors_do_not_contain_governance_outcomes(self):
        forbidden_suffixes = (
            "currentgovernance", "governancestatus", "governanceoutcome",
            "restrictionstatus", "restrictedstatus", "tier", "provisionaloutcome", "outcome",
        )
        outcomes = {ECL.OutcomeR, ECL.OutcomeS, ECL.OutcomeU, ECL.OutcomeN}
        outcomes.update(self.tbox.subjects(RDF.type, ECL.GovernanceOutcome))
        for state in self.abox.subjects(RDF.type, ECL.State):
            for predicate, value in self.abox.predicate_objects(state):
                normalized = str(predicate).lower().replace("-", "").replace("_", "")
                self.assertFalse(normalized.endswith(forbidden_suffixes), (state, predicate))
                self.assertNotIn(value, outcomes, (state, predicate, value))

    def test_ontology_has_no_property_chain_axioms(self):
        chains = list(self.tbox.triples((None, OWL.propertyChainAxiom, None)))
        self.assertEqual(chains, [])

    def test_relationships_are_not_subproperties_of_governance_outcome(self):
        relation_names = (
            "controls", "controlledBy", "participatesIn", "operates", "deploys",
            "materiallyBenefits", "targetsOrAffects", "tracks", "remediates", "reviews",
        )
        for name in relation_names:
            relation = ECL[name]
            for _, predicate, target in self.tbox.triples((relation, None, None)):
                self.assertNotEqual(predicate, OWL.propertyChainAxiom)
                self.assertNotEqual(target, ECL.outcome)

    def test_deterministic_canonical_rdf_build(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            meta_a = BUILD.build(ROOT / "knowledge", ROOT / "ontology" / "ecl.owl.ttl", Path(a))
            meta_b = BUILD.build(ROOT / "knowledge", ROOT / "ontology" / "ecl.owl.ttl", Path(b))
            self.assertEqual((Path(a) / "ecl-abox.nt").read_bytes(), (Path(b) / "ecl-abox.nt").read_bytes())
            self.assertEqual((Path(a) / "ecl-knowledge.nt").read_bytes(), (Path(b) / "ecl-knowledge.nt").read_bytes())
            self.assertEqual(meta_a["abox_rdf_sha256"], meta_b["abox_rdf_sha256"])
            self.assertEqual(meta_a["combined_rdf_sha256"], meta_b["combined_rdf_sha256"])

    def test_generated_manifest_is_not_an_abox_record(self):
        manifest = json.loads((ROOT / "knowledge" / "generated" / "state-abox-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("@context", manifest)
        self.assertNotIn("outcome", json.dumps(manifest).lower())


if __name__ == "__main__":
    unittest.main()
