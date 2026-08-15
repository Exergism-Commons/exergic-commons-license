import json
import unittest
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from tools.build_knowledge_graph import iter_abox_files


ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "knowledge" / "entities"
CLAIMS = ROOT / "knowledge" / "claims"
EVIDENCE = ROOT / "knowledge" / "evidence"
MANIFEST = ROOT / "knowledge" / "generated" / "state-project-relation-normalization-v4.json"
ACTIVE_STATUSES = {"candidate", "accepted", "disputed"}
ECL = Namespace("urn:ecl:")
FORBIDDEN_GOVERNANCE_PREDICATES = {
    URIRef(f"urn:ecl:{name}")
    for name in {
        "outcome",
        "governanceOutcome",
        "tier",
        "restrictionStatus",
        "restricted",
        "inheritedRestriction",
        "currentGovernance",
    }
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_graph(path: Path) -> Graph:
    return Graph().parse(path, format="json-ld")


def stable_ids(graph: Graph, node) -> list[str]:
    return sorted(str(value) for value in graph.objects(node, ECL.stableId))


def one_stable_id(graph: Graph, node, path: Path) -> str:
    values = stable_ids(graph, node)
    if len(values) != 1:
        raise AssertionError(f"{path}: {node} must have exactly one stable id; got {values}")
    return values[0]


def records_by_iri(root: Path):
    records = {}
    for path in iter_abox_files(root):
        record = load_json(path)
        graph = load_graph(path)
        for node in set(graph.subjects(RDF.type, None)):
            if not isinstance(node, URIRef):
                continue
            iri = str(node)
            if not iri.startswith("urn:ecl:"):
                continue
            if iri in records:
                raise AssertionError(
                    f"duplicate RDF identity {iri}: {records[iri][0]} and {path}"
                )
            records[iri] = (path, record, graph, node)
    return records


class StateProjectTrackClaimCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = records_by_iri(ENTITIES)
        cls.evidence = records_by_iri(EVIDENCE)
        cls.claims_by_id = {}
        cls.active_track_claims = defaultdict(list)

        for path in iter_abox_files(CLAIMS):
            record = load_json(path)
            graph = load_graph(path)
            for claim_node in set(graph.subjects(RDF.type, ECL.Claim)):
                claim_id = one_stable_id(graph, claim_node, path)
                if claim_id in cls.claims_by_id:
                    raise AssertionError(
                        f"duplicate Claim id {claim_id}: {cls.claims_by_id[claim_id][0]} and {path}"
                    )
                cls.claims_by_id[claim_id] = (path, record, graph, claim_node)

                statuses = {str(value) for value in graph.objects(claim_node, ECL.status)}
                if not statuses.intersection(ACTIVE_STATUSES):
                    continue
                if (claim_node, ECL.predicate, ECL.tracks) not in graph:
                    continue

                subjects = list(graph.objects(claim_node, ECL.subject))
                objects = list(graph.objects(claim_node, ECL.object))
                for subject in subjects:
                    for obj in objects:
                        cls.active_track_claims[(str(subject), str(obj))].append(
                            (path, record, graph, claim_node)
                        )

    def test_every_state_tracked_object_has_one_active_claim(self):
        for state_path in iter_abox_files(ENTITIES):
            state_record = load_json(state_path)
            state_graph = load_graph(state_path)
            for state_node in set(state_graph.subjects(RDF.type, ECL.State)):
                state_id = one_stable_id(state_graph, state_node, state_path)
                for target_node in state_graph.objects(state_node, ECL.tracks):
                    target_iri = str(target_node)
                    with self.subTest(state=state_id, target=target_iri):
                        self.assertIn(
                            target_iri,
                            self.entities,
                            f"{state_path}: unresolved tracked target {target_iri}",
                        )
                        target_path, _, target_graph, canonical_target = self.entities[
                            target_iri
                        ]
                        self.assertIn(
                            (canonical_target, RDF.type, ECL.Project),
                            target_graph,
                            f"{target_path}: tracked target must be a Project",
                        )

                        key = (str(state_node), target_iri)
                        matches = self.active_track_claims.get(key, [])
                        self.assertEqual(
                            len(matches),
                            1,
                            f"{state_id} -> {target_iri} must have exactly one active ecl:tracks Claim; got {[str(path) for path, *_ in matches]}",
                        )

                        claim_path, _, claim_graph, claim_node = matches[0]
                        forbidden = {
                            predicate
                            for predicate in FORBIDDEN_GOVERNANCE_PREDICATES
                            if any(claim_graph.objects(claim_node, predicate))
                        }
                        self.assertFalse(
                            forbidden,
                            f"{claim_path}: tracking Claim must not carry governance predicates {sorted(map(str, forbidden))}",
                        )

                        supporting = list(claim_graph.objects(claim_node, ECL.evidenceFor))
                        self.assertTrue(
                            supporting,
                            f"{claim_path}: active State tracking Claim needs supporting evidence",
                        )
                        for evidence_node in supporting:
                            evidence_iri = str(evidence_node)
                            self.assertIn(
                                evidence_iri,
                                self.evidence,
                                f"{claim_path}: dangling evidenceFor {evidence_iri}",
                            )
                            (
                                evidence_path,
                                _,
                                evidence_graph,
                                canonical_evidence,
                            ) = self.evidence[evidence_iri]
                            self.assertIn(
                                (canonical_evidence, RDF.type, ECL.EvidenceItem),
                                evidence_graph,
                                f"{evidence_path}: supporting evidence must be an EvidenceItem",
                            )

                        dossiers = list(target_graph.objects(canonical_target, ECL.dossier))
                        self.assertEqual(
                            len(dossiers),
                            1,
                            f"{target_path}: Project identity requires exactly one dossier",
                        )
                        dossier_path = (target_path.parent / str(dossiers[0])).resolve()
                        self.assertTrue(
                            dossier_path.is_file(),
                            f"{target_path}: missing Project dossier {dossier_path}",
                        )

    def test_expanded_jsonld_property_keys_have_the_same_rdf_semantics(self):
        expanded = {
            "@id": "urn:ecl:CLAIM-EXPANDED-TEST",
            "@type": ["urn:ecl:Claim"],
            "urn:ecl:stableId": [{"@value": "CLAIM-EXPANDED-TEST"}],
            "urn:ecl:subject": [{"@id": "urn:ecl:STATE-USA"}],
            "urn:ecl:predicate": [{"@id": "urn:ecl:tracks"}],
            "urn:ecl:object": [{"@id": "urn:ecl:PROJECT-MAVEN-SMART-SYSTEM"}],
            "urn:ecl:status": [{"@value": "accepted"}],
        }
        graph = Graph().parse(data=json.dumps(expanded), format="json-ld")
        claim = URIRef("urn:ecl:CLAIM-EXPANDED-TEST")
        self.assertIn((claim, RDF.type, ECL.Claim), graph)
        self.assertIn((claim, ECL.subject, ECL["STATE-USA"]), graph)
        self.assertIn((claim, ECL.predicate, ECL.tracks), graph)
        self.assertIn((claim, ECL.object, ECL["PROJECT-MAVEN-SMART-SYSTEM"]), graph)
        self.assertIn("accepted", {str(value) for value in graph.objects(claim, ECL.status)})

    def test_tranche_4_manifest_preserves_the_captured_snapshot(self):
        manifest = load_json(MANIFEST)
        self.assertEqual(manifest["version"], 4)
        self.assertEqual(manifest["globalTranche"], 4)
        self.assertEqual(manifest["issue"], 222)
        self.assertEqual(manifest["capturedLegacyEdgeCount"], 5)
        self.assertEqual(len(manifest["legacyEdges"]), 5)

        captured = {
            (edge["subject"], edge["object"], edge["claim"], edge["disposition"])
            for edge in manifest["legacyEdges"]
        }
        self.assertEqual(
            captured,
            {
                ("STATE-LBY", "PROJECT-MITIGA-DETENTION", "CLAIM-LBY-TRACKS-MITIGA-DETENTION", "already-normalized"),
                ("STATE-NLD", "PROJECT-NLD-PROBATION-RISK-TOOLS", "CLAIM-NLD-TRACKS-PROBATION-RISK-TOOLS", "already-normalized"),
                ("STATE-USA", "PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS", "CLAIM-USA-TRACKS-ICE-ICM-INVESTIGATIVE-ANALYTICS", "materialized-in-tranche-4"),
                ("STATE-USA", "PROJECT-MAVEN-SMART-SYSTEM", "CLAIM-USA-TRACKS-MAVEN-SMART-SYSTEM", "materialized-in-tranche-4"),
                ("STATE-USA", "PROJECT-OPERATION-EPIC-FURY-MINAB-TARGETING", "CLAIM-USA-TRACKS-OPERATION-EPIC-FURY-MINAB-TARGETING", "already-normalized"),
            },
        )

        new_claims = set(manifest["newClaims"])
        self.assertEqual(
            new_claims,
            {
                "CLAIM-USA-TRACKS-ICE-ICM-INVESTIGATIVE-ANALYTICS",
                "CLAIM-USA-TRACKS-MAVEN-SMART-SYSTEM",
            },
        )
        for claim_id in new_claims:
            self.assertIn(claim_id, self.claims_by_id, claim_id)
            claim_path, _, claim_graph, claim_node = self.claims_by_id[claim_id]
            self.assertIn((claim_node, RDF.type, ECL.Claim), claim_graph, claim_path)
            self.assertEqual(
                {str(value) for value in claim_graph.objects(claim_node, ECL.subject)},
                {"urn:ecl:STATE-USA"},
                claim_path,
            )
            self.assertEqual(
                {str(value) for value in claim_graph.objects(claim_node, ECL.predicate)},
                {"urn:ecl:tracks"},
                claim_path,
            )
            self.assertEqual(
                {str(value) for value in claim_graph.objects(claim_node, ECL.status)},
                {"accepted"},
                claim_path,
            )
            self.assertEqual(
                {str(value) for value in claim_graph.objects(claim_node, ECL.evidenceFor)},
                {"urn:ecl:EVIDENCE-USA-CANONICAL-DOSSIER-2026-08-14"},
                claim_path,
            )


if __name__ == "__main__":
    unittest.main()
