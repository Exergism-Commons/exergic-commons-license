import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "migrate_state_abox.py"
SPEC = importlib.util.spec_from_file_location("migrate_state_abox", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StateABoxMigrationTests(unittest.TestCase):
    def dossier_text(self, *, iso3="AAA", entity="Example", issue=999, outcome="S", last="2026-08-11"):
        return f'''---
id: ECL-STATE-{iso3}
entity: "{entity}"
iso3: {iso3}
issue: {issue}
provisional_outcome: {outcome}
provisional_scope: "must remain governance-only"
confidence: high
last_reviewed: {last}
---
# {entity}
'''

    def test_projection_never_materializes_governance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(Path(tmp), require_195=False)[0]
            record = MODULE.projection(dossier)
            self.assertEqual(record["iso3"], "AAA")
            self.assertEqual(record["name"], "Example")
            self.assertNotIn("provisional_outcome", record)
            self.assertNotIn("outcome", record)
            self.assertNotIn("provisional_scope", record)
            self.assertNotIn("tier", record)
            self.assertNotIn("status", record)

    def test_invalid_frontmatter_outcome_is_rejected_not_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAA.md"
            path.write_text(self.dossier_text(outcome="X"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid provisional_outcome"):
                MODULE.load_dossiers(Path(tmp), require_195=False)

    def test_new_manual_record_does_not_invent_review_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AAA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(Path(tmp), require_195=False)[0]
            record = MODULE.merge(dossier, None, None)
            self.assertEqual(record["reviewClass"], "manual")
            self.assertNotIn("reviewDue", record)

    def test_curated_fields_survive_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dossier_path = root / "AAA.md"
            dossier_path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(root, require_195=False)[0]
            existing = {
                **MODULE.projection(dossier),
                "aliases": ["AAA", "Curated alias"],
                "reviewDue": "2026-08-20",
                "reviewClass": "hot",
                "reviewReason": "human-reviewed reason",
                "trackedObjects": ["ecl:PROJECT-EXAMPLE"],
                "participatesIn": ["ecl:PROJECT-EXAMPLE"],
                "monitorIds": ["MONITOR-EXAMPLE"],
            }
            merged = MODULE.merge(dossier, existing, None)
            self.assertEqual(merged["reviewReason"], "human-reviewed reason")
            self.assertEqual(merged["trackedObjects"], ["ecl:PROJECT-EXAMPLE"])
            self.assertEqual(merged["participatesIn"], ["ecl:PROJECT-EXAMPLE"])
            self.assertEqual(merged["monitorIds"], ["MONITOR-EXAMPLE"])
            self.assertEqual(merged["reviewClass"], "hot")
            self.assertEqual(merged["reviewDue"], "2026-08-20")

    def test_manual_curated_due_survives_normal_v2_regeneration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AAA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(root, require_195=False)[0]
            existing = {
                **MODULE.projection(dossier),
                "aliases": ["AAA"],
                "reviewDue": "2026-12-31",
                "reviewClass": "manual",
            }
            merged = MODULE.merge(dossier, existing, None, cleanup_v1=False)
            self.assertEqual(merged["reviewDue"], "2026-12-31")

    def test_v1_synthetic_manual_due_is_removed_on_manifest_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AAA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(root, require_195=False)[0]
            existing = {
                **MODULE.projection(dossier),
                "aliases": ["AAA"],
                "reviewDue": MODULE.synthetic_v1_due(dossier),
                "reviewClass": "manual",
            }
            merged = MODULE.merge(dossier, existing, MODULE.phash(existing), cleanup_v1=True)
            self.assertNotIn("reviewDue", merged)
            self.assertEqual(merged["reviewClass"], "manual")

    def test_legacy_canonical_name_conflict_becomes_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "PRK.md"
            path.write_text(self.dossier_text(iso3="PRK", entity="North Korea", issue=135), encoding="utf-8")
            dossier = MODULE.load_dossiers(root, require_195=False)[0]
            existing = {
                **MODULE.projection(dossier),
                "name": "North Korea (DPRK)",
                "aliases": ["PRK", "DPRK"],
                "reviewDue": "2026-08-20",
                "reviewClass": "hot",
            }
            merged = MODULE.merge(dossier, existing, None)
            self.assertEqual(merged["name"], "North Korea")
            self.assertIn("North Korea (DPRK)", merged["aliases"])

    def test_manifest_detects_edits_to_generator_owned_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AAA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(root, require_195=False)[0]
            existing = {
                **MODULE.projection(dossier),
                "aliases": ["AAA"],
                "reviewClass": "manual",
            }
            recorded_hash = MODULE.phash(existing)
            existing["name"] = "Silent human edit"
            with self.assertRaisesRegex(ValueError, "generator-owned fields changed"):
                MODULE.merge(dossier, existing, recorded_hash)

    def test_guardrail_rejects_governance_and_inheritance_fields(self):
        base = {"type": "State"}
        for key in ("currentGovernance", "governanceStatus", "restrictionStatus", "tier", "outcome", "inheritedRestriction"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    MODULE.guard({**base, key: "x"}, key)


class StateABoxRepositoryTests(unittest.TestCase):
    def test_full_repository_has_exactly_195_dossiers(self):
        dossiers = MODULE.load_dossiers(ROOT / "dossiers" / "states")
        self.assertEqual(len(dossiers), 195)
        self.assertEqual(len({d.iso3 for d in dossiers}), 195)
        self.assertEqual(len({d.dossier_id for d in dossiers}), 195)
        self.assertEqual(len({d.issue for d in dossiers}), 195)

    def test_full_repository_has_exactly_195_state_actors(self):
        entity_root = ROOT / "knowledge" / "entities"
        files = sorted(entity_root.glob("STATE-*.json"))
        self.assertEqual(len(files), 195)
        records = [json.loads(path.read_text(encoding="utf-8")) for path in files]
        self.assertTrue(all(record["type"] == "State" for record in records))
        self.assertEqual(len({record["iso3"] for record in records}), 195)
        self.assertEqual(len({record["id"] for record in records}), 195)
        self.assertEqual(len({record["iri"] for record in records}), 195)
        self.assertEqual(len({record["dossier"] for record in records}), 195)
        for path, record in zip(files, records):
            iso = path.stem.removeprefix("STATE-")
            self.assertEqual(record["iso3"], iso)
            self.assertEqual(record["id"], f"STATE-{iso}")
            self.assertEqual(record["iri"], f"ecl:STATE-{iso}")
            self.assertEqual(record["dossier"], f"../../dossiers/states/{iso}.md")
            MODULE.guard(record, str(path))
            if record.get("reviewClass") == "manual" and "reviewReason" not in record:
                self.assertNotIn("reviewDue", record, path)

    def test_manifest_has_all_195_generator_hashes(self):
        manifest = json.loads((ROOT / "knowledge" / "generated" / "state-abox-manifest.json").read_text(encoding="utf-8"))
        hashes = manifest["generatedProjectionSha256"]
        self.assertEqual(manifest["version"], MODULE.VERSION)
        self.assertEqual(manifest["generator"], MODULE.GENERATOR)
        self.assertEqual(len(hashes), 195)
        self.assertEqual(set(hashes), {path.stem.removeprefix("STATE-") for path in (ROOT / "knowledge" / "entities").glob("STATE-*.json")})

    def test_checked_in_corpus_is_idempotent(self):
        summary, code = MODULE.migrate(
            ROOT / "dossiers" / "states",
            ROOT / "knowledge" / "entities",
            ROOT / "knowledge" / "generated" / "state-abox-manifest.json",
            check=True,
        )
        self.assertEqual(code, 0, summary.conflicts)
        self.assertEqual(summary.state_actor_count, 195)
        self.assertEqual(len(summary.unchanged), 195)
        self.assertFalse(summary.created)
        self.assertFalse(summary.updated)
        self.assertFalse(summary.conflicts)

    def test_single_iso_check_is_supported(self):
        summary, code = MODULE.migrate(
            ROOT / "dossiers" / "states",
            ROOT / "knowledge" / "entities",
            ROOT / "knowledge" / "generated" / "state-abox-manifest.json",
            iso3="USA",
            check=True,
        )
        self.assertEqual(code, 0)
        self.assertEqual(summary.selected, 1)
        self.assertEqual(summary.unchanged, ["USA"])


if __name__ == "__main__":
    unittest.main()
