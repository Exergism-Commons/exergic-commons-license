import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP_PATH = ROOT / "tools" / "update_ticket_sweep.py"
SPEC = importlib.util.spec_from_file_location("update_ticket_sweep", SWEEP_PATH)
SWEEP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SWEEP)

ENTITY_IDS = (
    "ORG-INTELLEXA-SA",
    "ORG-INTELLEXA-LIMITED",
    "ORG-CYTROX-AD",
    "ORG-CYTROX-HOLDINGS-ZRT",
    "ORG-THALESTRIS-LIMITED",
    "ORG-ALIADA-GROUP-INC",
)
NETWORK_DOSSIER = "../../dossiers/organizations/INTELLEXA-PREDATOR-NETWORK.md"


class IdentityOnlyDossierGovernanceBoundaryTests(unittest.TestCase):
    def test_shared_network_governance_cannot_leak_into_exact_entities(self):
        for entity_id in ENTITY_IDS:
            with self.subTest(entity=entity_id):
                entity_path = ROOT / "knowledge" / "entities" / f"{entity_id}.json"
                entity = json.loads(entity_path.read_text(encoding="utf-8"))

                self.assertIn(NETWORK_DOSSIER, entity["provenance"])
                self.assertNotEqual(entity["dossier"], NETWORK_DOSSIER)

                dossier_path = (entity_path.parent / entity["dossier"]).resolve()
                dossier_text = dossier_path.read_text(encoding="utf-8")
                frontmatter = "\n".join(dossier_text.splitlines()[:20])
                self.assertIn(f"id: ECL-{entity_id}", frontmatter)
                self.assertNotIn("provisional_outcome:", frontmatter)

                synthetic_due = dict(entity)
                synthetic_due["_path"] = str(entity_path)
                synthetic_due["reviewDue"] = "2026-08-13"
                synthetic_due["reviewClass"] = "manual"
                signal = SWEEP.build_signal(
                    synthetic_due, SWEEP.dt.date(2026, 8, 13)
                )
                self.assertIsNotNone(signal)
                self.assertEqual(signal["currentGovernance"], "unknown")


if __name__ == "__main__":
    unittest.main()
