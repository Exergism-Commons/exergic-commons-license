import json
import unittest
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from tools.build_knowledge_graph import _canonical_source_iri, iter_abox_files


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
ENTITIES = KNOWLEDGE / "entities"
EVIDENCE = KNOWLEDGE / "evidence"
MANIFEST = KNOWLEDGE / "generated" / "state-project-relation-normalization-v4.json"
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


def build_union_graph(root: Path):
    graph = Graph()
    top_level_sources = {}
    node_sources = defaultdict(set)

    for path in iter_abox_files(root):
        record = load_json(path)
        source_graph = load_graph(path)
        for subject, predicate, obj in source_graph:
            graph.add((subject, predicate, obj))
            if isinstance(subject, URIRef):
                node_sources[str(subject)].add(path)

        raw_iri = record.get("iri", record.get("@id"))
        top_level_sources[_canonical_source_iri(raw_iri)] = path

    return graph, top_level_sources, node_sources


def stable_ids(graph: Graph, node) -> list[str]:
    return sorted(str(value) for value in graph.objects(node, ECL.stableId))


def one_stable_id(graph: Graph, node, source_label: str) -> str:
    values = stable_ids(graph, node)
    if len(values) != 1:
        raise AssertionError(
            f"{source_label}: {node} must have exactly one stable id; got {values}"
        )
    return values[0]


def sources_for(node_sources, node) -> str:
    paths = sorted(str(path) for path in node_sources.get(str(node), set()))
    return ", ".join(paths) if paths else str(node)


def active_track_claim_pairs(graph: Graph):
    pairs = defaultdict(list)
    for claim_node in set(graph.subjects(RDF.type, ECL.Claim)):
        statuses = {str(value) for value in graph.objects(claim_node, ECL.status)}
        if not statuses.intersection(ACTIVE_STATUSES):
            continue
        if (claim_node, ECL.predicate, ECL.tracks) not in graph:
            continue
        for subject in graph.objects(claim_node, ECL.subject):
            for obj in graph.objects(claim_node, ECL.object):
                pairs[(str(subject), str(obj))].append(claim_node)
    return pairs


class StateProjectTrackClaimCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.graph,
            cls.top_level_sources,
            cls.node_sources,
        ) = build_union_graph(KNOWLEDGE)

        cls.claims_by_id = {}
        for claim_node in set(cls.graph.subjects(RDF.type, ECL.Claim)):
            label = sources_for(cls.node_sources, claim_node)
            claim_id = one_stable_id(cls.graph, claim_node, label)
            if claim_id in cls.claims_by_id:
                other = cls.claims_by_id[claim_id]
                raise AssertionError(
                    f"duplicate Claim stable id {claim_id} on distinct nodes: {other} and {claim_node}"
                )
            cls.claims_by_id[claim_id] = claim_node

        cls.active_track_claims = active_track_claim_pairs(cls.graph)

    def test_every_state_tracked_object_has_one_active_claim(self):
        for state_node in set(self.graph.subjects(RDF.type, ECL.State)):
            state_label = sources_for(self.node_sources, state_node)
            state_id = one_stable_id(self.graph, state_node, state_label)

            for target_node in self.graph.objects(state_node, ECL.tracks):
                target_iri = str(target_node)
                with self.subTest(state=state_id, target=target_iri):
                    self.assertIn(
                        (target_node, RDF.type, ECL.Project),
                        self.graph,
                        f"{state_label}: tracked target {target_iri} must resolve to a Project",
                    )

                    target_path = self.top_level_sources.get(target_iri)
                    self.assertIsNotNone(
                        target_path,
                        f"{target_iri}: tracked Project requires a canonical top-level ABox identity",
                    )
                    self.assertIn(
                        ENTITIES,
                        target_path.parents,
                        f"{target_path}: tracked Project identity must live under knowledge/entities",
                    )

                    matches = self.active_track_claims.get(
                        (str(state_node), target_iri), []
                    )
                    self.assertEqual(
                        len(matches),
                        1,
                        f"{state_id} -> {target_iri} must have exactly one active ecl:tracks Claim; got {[str(node) for node in matches]}",
                    )

                    claim_node = matches[0]
                    claim_label = sources_for(self.node_sources, claim_node)
                    one_stable_id(self.graph, claim_node, claim_label)

                    forbidden = {
                        predicate
                        for predicate in FORBIDDEN_GOVERNANCE_PREDICATES
                        if any(self.graph.objects(claim_node, predicate))
                    }
                    self.assertFalse(
                        forbidden,
                        f"{claim_label}: tracking Claim must not carry governance predicates {sorted(map(str, forbidden))}",
                    )

                    supporting = list(self.graph.objects(claim_node, ECL.evidenceFor))
                    self.assertTrue(
                        supporting,
                        f"{claim_label}: active State tracking Claim needs supporting evidence",
                    )
                    for evidence_node in supporting:
                        evidence_iri = str(evidence_node)
                        self.assertIn(
                            (evidence_node, RDF.type, ECL.EvidenceItem),
                            self.graph,
                            f"{claim_label}: dangling/non-EvidenceItem evidenceFor {evidence_iri}",
                        )
                        evidence_path = self.top_level_sources.get(evidence_iri)
                        self.assertIsNotNone(
                            evidence_path,
                            f"{evidence_iri}: supporting evidence requires a canonical top-level ABox identity",
                        )
                        self.assertIn(
                            EVIDENCE,
                            evidence_path.parents,
                            f"{evidence_path}: supporting EvidenceItem must live under knowledge/evidence",
                        )

                    dossiers = list(self.graph.objects(target_node, ECL.dossier))
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
            "urn:ecl:object": [
                {"@id": "urn:ecl:PROJECT-MAVEN-SMART-SYSTEM"}
            ],
            "urn:ecl:status": [{"@value": "accepted"}],
        }
        graph = Graph().parse(data=json.dumps(expanded), format="json-ld")
        claim = URIRef("urn:ecl:CLAIM-EXPANDED-TEST")
        self.assertIn((claim, RDF.type, ECL.Claim), graph)
        self.assertIn((claim, ECL.subject, ECL["STATE-USA"]), graph)
        self.assertIn((claim, ECL.predicate, ECL.tracks), graph)
        self.assertIn(
            (claim, ECL.object, ECL["PROJECT-MAVEN-SMART-SYSTEM"]), graph
        )
        self.assertIn(
            "accepted", {str(value) for value in graph.objects(claim, ECL.status)}
        )

    def test_split_claim_descriptions_are_classified_after_rdf_union(self):
        claim = URIRef("urn:ecl:CLAIM-SPLIT-TEST")
        first = {
            "@id": str(claim),
            "@type": ["urn:ecl:Claim"],
            "urn:ecl:stableId": [{"@value": "CLAIM-SPLIT-TEST"}],
            "urn:ecl:subject": [{"@id": "urn:ecl:STATE-USA"}],
            "urn:ecl:predicate": [{"@id": "urn:ecl:tracks"}],
            "urn:ecl:object": [
                {"@id": "urn:ecl:PROJECT-MAVEN-SMART-SYSTEM"}
            ],
        }
        second = {
            "@id": "urn:ecl:SUPPORT-DOC-SPLIT-TEST",
            "@graph": [
                {
                    "@id": str(claim),
                    "urn:ecl:status": [{"@value": "accepted"}],
                }
            ],
        }
        union = Graph()
        for document in (first, second):
            parsed = Graph().parse(data=json.dumps(document), format="json-ld")
            for triple in parsed:
                union.add(triple)

        pairs = active_track_claim_pairs(union)
        self.assertEqual(
            pairs[
                (
                    "urn:ecl:STATE-USA",
                    "urn:ecl:PROJECT-MAVEN-SMART-SYSTEM",
                )
            ],
            [claim],
        )
        self.assertEqual(stable_ids(union, claim), ["CLAIM-SPLIT-TEST"])

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
            claim_node = self.claims_by_id[claim_id]
            claim_label = sources_for(self.node_sources, claim_node)
            self.assertIn((claim_node, RDF.type, ECL.Claim), self.graph, claim_label)
            self.assertEqual(
                {str(value) for value in self.graph.objects(claim_node, ECL.subject)},
                {"urn:ecl:STATE-USA"},
                claim_label,
            )
            self.assertEqual(
                {str(value) for value in self.graph.objects(claim_node, ECL.predicate)},
                {"urn:ecl:tracks"},
                claim_label,
            )
            self.assertEqual(
                {str(value) for value in self.graph.objects(claim_node, ECL.status)},
                {"accepted"},
                claim_label,
            )
            self.assertEqual(
                {
                    str(value)
                    for value in self.graph.objects(claim_node, ECL.evidenceFor)
                },
                {"urn:ecl:EVIDENCE-USA-CANONICAL-DOSSIER-2026-08-14"},
                claim_label,
            )


if __name__ == "__main__":
    unittest.main()
