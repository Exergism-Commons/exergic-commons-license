import json
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "knowledge" / "entities"
CLAIMS = ROOT / "knowledge" / "claims"
EVIDENCE = ROOT / "knowledge" / "evidence"
MANIFEST = ROOT / "knowledge" / "generated" / "state-project-relation-normalization-v4.json"
ACTIVE_STATUSES = {"candidate", "accepted", "disputed"}
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


def record_paths(root: Path, stem_glob: str = "*"):
    return sorted(
        [
            *root.glob(f"{stem_glob}.json"),
            *root.glob(f"{stem_glob}.jsonld"),
        ]
    )


def records_by_iri(root: Path):
    records = {}
    for path in record_paths(root):
        record = load_json(path)
        iri = record.get("iri")
        if iri:
            if iri in records:
                raise AssertionError(f"duplicate IRI {iri}: {records[iri][0]} and {path}")
            records[iri] = (path, record)
    return records


class StateProjectTrackClaimCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = records_by_iri(ENTITIES)
        cls.evidence = records_by_iri(EVIDENCE)
        cls.claim_paths = record_paths(CLAIMS)
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
                and claim.get("predicate") == "ecl:tracks"
                and claim.get("status") in ACTIVE_STATUSES
            ):
                cls.active_track_claims[(claim.get("subject"), claim.get("object"))].append((path, claim))

    def test_every_state_tracked_object_has_one_active_claim(self):
        for state_path in record_paths(ENTITIES, "STATE-*"):
            state = load_json(state_path)
            self.assertEqual(state.get("type"), "State", state_path)
            for target in state.get("trackedObjects", []):
                with self.subTest(state=state["id"], target=target):
                    self.assertIn(target, self.entities, f"{state_path}: unresolved tracked target {target}")
                    target_path, target_record = self.entities[target]
                    self.assertEqual(target_record.get("type"), "Project", target_path)

                    key = (state["iri"], target)
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
                    self.assertTrue(supporting, f"{claim_path}: active State tracking Claim needs supporting evidence")
                    for evidence_iri in supporting:
                        self.assertIn(evidence_iri, self.evidence, f"{claim_path}: dangling evidenceFor {evidence_iri}")
                        evidence_path, evidence = self.evidence[evidence_iri]
                        self.assertEqual(evidence.get("type"), "EvidenceItem", evidence_path)

                    dossier_rel = target_record.get("dossier")
                    self.assertTrue(dossier_rel, f"{target_path}: Project identity requires dossier")
                    dossier_path = (target_path.parent / dossier_rel).resolve()
                    self.assertTrue(dossier_path.is_file(), f"{target_path}: missing Project dossier {dossier_path}")

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
            self.assertEqual(claim["subject"], "ecl:STATE-USA", claim_path)
            self.assertEqual(claim["predicate"], "ecl:tracks", claim_path)
            self.assertEqual(claim["status"], "accepted", claim_path)
            self.assertEqual(
                claim["evidenceFor"],
                ["ecl:EVIDENCE-USA-CANONICAL-DOSSIER-2026-08-14"],
                claim_path,
            )


if __name__ == "__main__":
    unittest.main()
