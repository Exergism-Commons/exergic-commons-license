import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from tools.build_knowledge_graph import iter_abox_files


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
ENTITIES = KNOWLEDGE / "entities"
MANIFEST = KNOWLEDGE / "generated" / "agency-hierarchy-scaleout-v5.json"
ONTOLOGY = ROOT / "ontology" / "ecl.owl.ttl"
ENTITY_SCHEMA = ROOT / "schemas" / "entity.schema.json"
ECL = Namespace("https://id.exergism.org/ecl#")

EX = Namespace("https://id.exergism.org/exergism#")
EC = Namespace("https://id.exergism.org/commons#")
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

ACTOR_IDENTITY_TYPES = {
    EX.State,
    EC.Organization,
    EC.Person,
    EX.Agency,
    ECL.Institution,
}

FORBIDDEN_PROPAGATION_PREDICATES = {
    ECL.tracks,
    ECL.controls,
    ECL.controlledBy,
    ECL.participatesIn,
    ECL.operates,
    ECL.deploys,
    ECL.materiallyBenefits,
    ECL.targetsOrAffects,
    ECL.remediates,
    ECL.reviews,
    ECL.hasAssessment,
    ECL.hasDecision,
    ECL.outcome,
    ECL.basedOnAssessment,
    ECL.affectedVariable,
    ECL.affectedCriterion,
    ECL.triggersReviewOf,
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
    return URIRef(f"https://id.exergism.org/ecl#{stable_id}")


def with_owlrl(ontology: Graph, data: Graph) -> Graph:
    graph = Graph()
    for triple in ontology:
        graph.add(triple)
    for triple in data:
        graph.add(triple)
    DeductiveClosure(OWLRL_Semantics).expand(graph)
    return graph


class AgencyHierarchyScaleoutV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abox = build_abox()
        cls.ontology = Graph().parse(ONTOLOGY, format="turtle")
        cls.inferred = with_owlrl(cls.ontology, cls.abox)

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
                self.assertIn((agency, RDF.type, EX.Agency), self.abox)
                self.assertIn((agency, ECL.partOf, parent), self.abox)
                self.assertTrue(
                    any(self.abox.objects(parent, EC.stableId)),
                    f"{agency_id}: unresolved direct parent {parent_id}",
                )

    def test_schema_allows_partof_only_on_actor_source_records(self):
        validator = Draft202012Validator(load_json(ENTITY_SCHEMA))
        common = {
            "@context": "../../ontology/ecl-context.jsonld",
            "name": "Synthetic",
            "dossier": "../../dossiers/synthetic.md",
            "lastSubstantiveReview": "2026-08-15",
            "reviewClass": "manual",
            "partOf": ["ex:STATE-USA"],
        }
        agency = {
            **common,
            "iri": "ex:AGENCY-SYNTHETIC",
            "id": "AGENCY-SYNTHETIC",
            "type": "Agency",
        }
        project = {
            **common,
            "iri": "ex:PROJECT-SYNTHETIC",
            "id": "PROJECT-SYNTHETIC",
            "type": "Project",
        }
        self.assertEqual(list(validator.iter_errors(agency)), [])
        self.assertTrue(list(validator.iter_errors(project)))

    def test_every_partof_endpoint_is_a_resolved_actor_identity_in_raw_abox(self):
        for child, parent in self.abox.subject_objects(ECL.partOf):
            with self.subTest(child=str(child), parent=str(parent)):
                self.assertTrue(list(self.abox.objects(child, EC.stableId)), child)
                self.assertTrue(list(self.abox.objects(parent, EC.stableId)), parent)
                child_types = set(self.abox.objects(child, RDF.type))
                parent_types = set(self.abox.objects(parent, RDF.type))
                self.assertTrue(child_types.intersection(ACTOR_IDENTITY_TYPES), child_types)
                self.assertTrue(parent_types.intersection(ACTOR_IDENTITY_TYPES), parent_types)

    def test_partof_is_direct_and_non_propagating_even_after_owlrl(self):
        self.assertIn((ECL.partOf, RDF.type, OWL.ObjectProperty), self.ontology)
        self.assertNotIn((ECL.partOf, RDF.type, OWL.TransitiveProperty), self.ontology)
        self.assertEqual(list(self.ontology.triples((None, OWL.propertyChainAxiom, None))), [])

        for forbidden in FORBIDDEN_PROPAGATION_PREDICATES:
            with self.subTest(forbidden=str(forbidden)):
                self.assertNotIn((ECL.partOf, RDFS.subPropertyOf, forbidden), self.ontology)
                self.assertNotIn((forbidden, RDFS.subPropertyOf, ECL.partOf), self.ontology)
                self.assertNotIn((ECL.partOf, OWL.equivalentProperty, forbidden), self.ontology)
                self.assertNotIn((forbidden, OWL.equivalentProperty, ECL.partOf), self.ontology)
                self.assertNotIn((ECL.partOf, OWL.inverseOf, forbidden), self.ontology)
                self.assertNotIn((forbidden, OWL.inverseOf, ECL.partOf), self.ontology)

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

        fixture = Graph()
        root = iri("SYNTHETIC-ROOT")
        parent = iri("SYNTHETIC-PARENT")
        child = iri("SYNTHETIC-CHILD")
        sibling = iri("SYNTHETIC-SIBLING")
        for node in (root, parent, child, sibling):
            fixture.add((node, RDF.type, EX.Agency))
        fixture.add((child, ECL.partOf, parent))
        fixture.add((sibling, ECL.partOf, parent))
        fixture.add((parent, ECL.partOf, root))
        closure = with_owlrl(self.ontology, fixture)

        hierarchy_nodes = {root, parent, child, sibling}
        for subject in hierarchy_nodes:
            for predicate in FORBIDDEN_PROPAGATION_PREDICATES:
                leaked = [obj for obj in closure.objects(subject, predicate) if obj in hierarchy_nodes]
                with self.subTest(subject=str(subject), predicate=str(predicate)):
                    self.assertEqual(leaked, [])

    def test_functional_claims_are_narrow_evidence_backed_propositions(self):
        for claim_id, (subject_id, predicate, object_id, evidence_id) in EXPECTED_CLAIMS.items():
            claim = iri(claim_id)
            with self.subTest(claim=claim_id):
                self.assertIn((claim, RDF.type, EX.Claim), self.abox)
                self.assertIn((claim, ECL.subject, iri(subject_id)), self.abox)
                self.assertIn((claim, ECL.predicate, predicate), self.abox)
                self.assertIn((claim, ECL.object, iri(object_id)), self.abox)
                self.assertEqual(
                    {str(value) for value in self.abox.objects(claim, EC.status)},
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
