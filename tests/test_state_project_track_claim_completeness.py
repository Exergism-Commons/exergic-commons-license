import json
import unittest
from collections import defaultdict
from pathlib import Path

from tools.build_knowledge_graph import _canonical_source_iri, iter_abox_files


ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "knowledge" / "entities"
CLAIMS = ROOT / "knowledge" / "claims"
EVIDENCE = ROOT / "knowledge" / "evidence"
MANIFEST = ROOT / "knowledge" / "generated" / "state-project-relation-normalization-v4.json"
ACTIVE_STATUSES = {"candidate", "accepted", "disputed"}
TRACKS_IRI = "urn:ecl:tracks"
FORBIDDEN_GOVERNANCE_FIELDS = {
    "outcome",
    "governanceOutcome",
    "tier",
    "restrictionStatus",
    "restricted",
    "inheritedRestriction",
    "currentGovernance",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_iri(value):
    if not isinstance(value, str):
        return value
    return _canonical_source_iri(value)


def records_by_iri(root: Path):
    records = {}
    for path in iter_abox_files(root):
        record = load_json(path)
        iri = record.get("iri", record.get("@id"))
        if iri:
            canonical = canonical_iri(iri)
            if canonical in records:
                raise AssertionError(
                    f"duplicate IRI {canonical}: {records[canonical][0]} and {path}"
                )
            records[canonical] = (path, record)
    return records


class StateProjectTrackClaimCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = records_by_iri(ENTITIES)
        cls.evidence = records_by_iri(EVIDENCE)
        cls.claim_paths = iter_abox_files(CLAIMS)
        cls.claims = [load_json(path) for path in cls.claim_paths]
        cls.claims_by_id = {}

        cls.active_track_claims = defaultdict(list)
        for path, claim in zip(cls.claim_paths, cls.claims):
            claim_id = claim.get("id")
            if claim_id:
                if claim_id in cls.claims_by_id:
                    raise AssertionError(
                        f"duplicate Claim id {claim_id}: {cls.claims_by_id[claim_id][0]} and {path}"
                    )
                cls.claims_by_id[claim_id] = (path, claim)
            if (
                claim.get("type") == "Claim"
                and canonical_iri(claim.get("predicate")) == TRACKS_IRI
                and claim.get("status") in ACTIVE_STATUSES
            ):
                key = (
                    canonical_iri(claim.get("subject")),
                    canonical_iri(claim.get("object")),
                )
                cls.active_track_claims[key].append((path, claim))

    def test_every_state_tracked_object_has_one_active_claim(self):
        for state_path in iter_abox_files(ENTITIES):
            state = load_json(state_path)
            if state.get("type") != "State":
                continue
            for target in state.get("trackedObjects", []):
                target_iri = canonical_iri(target)
                with self.subTest(state=state["id"], target=target):
                    self.assertIn(
                        target_iri,
                        self.entities,
                        f"{state_path}: unresolved tracked target {target}",
                    )
                    target_path, target_record = self.entities[target_iri]
                    self.assertEqual(target_record.get("type"), "Project", target_path)

                    key = (canonical_iri(state["iri"]), target_iri)
                    matches = self.active_track_claims.get(key, [])
                    self.assertEqual(
                        len(matches),
                        1,
                        f"{state['id']} -> {target} must have exactly one active ecl:tracks Claim; got {[str(path) for path, _ in matches]}",
                    )

                    claim_path, claim = matches[0]
                    self.assertFalse(
                        FORBIDDEN_GOVERNANCE_FIELDS.intersection(claim),
                        f"{claim_path}: tracking Claim must not carry governance fields",
                    )
                    supporting = claim.get("evidenceFor", [])
                    self.assertTrue(
                        supporting,
                        f"{claim_path}: active State tracking Claim needs supporting evidence",
                    )
                    for evidence_iri in supporting:
                        canonical_evidence = canonical_iri(evidence_iri)
                        self.assertIn(
                            canonical_evidence,
                            self.evidence,
                            f"{claim_path}: dangling evidenceFor {evidence_iri}",
                        )
                        evidence_path, evidence = self.evidence[canonical_evidence]
                        self.assertEqual(evidence.get("type"), "EvidenceItem", evidence_path)

                    dossier_rel = target_record.get("dossier")
                    self.assertTrue(
                        dossier_rel, f"{target_path}: Project identity requires dossier"
                    )
                    dossier_path = (target_path.parent / dossier_rel).resolve()
                    self.assertTrue(
                        dossier_path.is_file(),
                        f"{target_path}: missing Project dossier {dossier_path}",
                    )

    def test_compact_and_full_tracking_iris_are_equivalent(self):
        self.assertEqual(canonical_iri("ecl:tracks"), TRACKS_IRI)
        self.assertEqual(canonical_iri("urn:ecl:tracks"), TRACKS_IRI)
        self.assertEqual(
            canonical_iri("ecl:PROJECT-MAVEN-SMART-SYSTEM"),
            canonical_iri("urn:ecl:PROJECT-MAVEN-SMART-SYSTEM"),
        )

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
            claim_path, claim = self.claims_by_id[claim_id]
            self.assertEqual(
                canonical_iri(claim["subject"]), "urn:ecl:STATE-USA", claim_path
            )
            self.assertEqual(canonical_iri(claim["predicate"]), TRACKS_IRI, claim_path)
            self.assertEqual(claim["status"], "accepted", claim_path)
            self.assertEqual(
                [canonical_iri(value) for value in claim["evidenceFor"]],
                ["urn:ecl:EVIDENCE-USA-CANONICAL-DOSSIER-2026-08-14"],
                claim_path,
            )


if __name__ == "__main__":
    unittest.main()
