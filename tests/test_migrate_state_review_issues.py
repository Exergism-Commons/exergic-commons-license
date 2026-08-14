import importlib.util
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "migrate_state_review_issues.py"
SPEC = importlib.util.spec_from_file_location("migrate_state_review_issues", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class StateReviewMigrationTests(unittest.TestCase):
    def dossier_text(self, issue=187, iso3="USA", entity="United States", outcome="S"):
        return f'''---
id: ECL-STATE-{iso3}
entity: "{entity}"
iso3: {iso3}
issue: {issue}
provisional_outcome: {outcome}
provisional_scope: "narrow reviewed scope"
evidence_cutoff: 2026-08-11
review_stage: formal-exergism-pilot
exergism_status: scorable
exergism_assessment: ../../exergism/assessments/{iso3}.json
---
# {entity}
'''

    def load_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "USA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            return MODULE.load_dossiers(Path(tmp))[0]

    def test_frontmatter_parses_issue_mapping(self):
        meta = MODULE.parse_frontmatter(self.dossier_text())
        self.assertEqual(meta["issue"], "187")
        self.assertEqual(meta["iso3"], "USA")
        self.assertEqual(meta["entity"], "United States")

    def test_load_dossiers_uses_frontmatter_mapping(self):
        dossier = self.load_one()
        self.assertEqual(dossier.issue, 187)
        self.assertEqual(dossier.iso3, "USA")
        self.assertEqual(dossier.outcome, "S")

    def test_duplicate_issue_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AAA.md").write_text(
                self.dossier_text(issue=10, iso3="AAA", entity="A"),
                encoding="utf-8",
            )
            (root / "BBB.md").write_text(
                self.dossier_text(issue=10, iso3="BBB", entity="B"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate issue mapping"):
                MODULE.load_dossiers(root)

    def test_render_preserves_historical_body_and_marks_surface(self):
        dossier = self.load_one()
        historical = "Original evidence gathering body\nwith details."
        rendered = MODULE.render_review_body(dossier, "owner/repo", historical)
        self.assertIn(MODULE.MARKER, rendered)
        self.assertIn(MODULE.METADATA_START, rendered)
        self.assertIn("Provisional outcome (derived): `S`", rendered)
        self.assertIn("the dossier controls", rendered)
        self.assertIn("Original evidence gathering body", rendered)
        self.assertIn("Reviews are **not votes**", rendered)
        self.assertIn("actively sought", rendered)

    def test_historical_body_can_be_recovered(self):
        dossier = self.load_one()
        historical = "Original body\nwith immutable context."
        rendered = MODULE.render_review_body(dossier, "owner/repo", historical)
        self.assertEqual(MODULE.extract_historical_body(rendered), historical)

    def test_metadata_sync_preserves_review_edits_outside_generated_block(self):
        dossier = self.load_one()
        rendered = MODULE.render_review_body(dossier, "owner/repo", "historical")
        edited = rendered.replace(
            "- [ ] Exact actor / institutional identity",
            "- [x] Exact actor / institutional identity",
        )
        changed = replace(
            dossier,
            outcome="N",
            scope="new canonical scope",
            evidence_cutoff="2026-08-15",
        )
        synchronized = MODULE.synchronize_review_body(changed, "owner/repo", edited)
        self.assertIn("Provisional outcome (derived): `N`", synchronized)
        self.assertIn("Provisional scope (derived): new canonical scope", synchronized)
        self.assertIn("Evidence cutoff (derived): `2026-08-15`", synchronized)
        self.assertIn("- [x] Exact actor / institutional identity", synchronized)
        self.assertEqual(MODULE.extract_historical_body(synchronized), "historical")

    def test_legacy_migrated_surface_upgrades_without_losing_history(self):
        dossier = self.load_one()
        legacy = f"""{MODULE.MARKER} iso3=USA issue=187 -->
legacy generated content
{MODULE.HISTORY_OPEN}old evidence body{MODULE.HISTORY_CLOSE}
"""
        upgraded = MODULE.synchronize_review_body(dossier, "owner/repo", legacy)
        self.assertIn(MODULE.METADATA_START, upgraded)
        self.assertEqual(MODULE.extract_historical_body(upgraded), "old evidence body")

    def test_marker_identifies_review_surface(self):
        body = f"{MODULE.MARKER} iso3=USA issue=187 -->\nreview"
        self.assertTrue(MODULE.already_migrated(body))
        self.assertFalse(MODULE.already_migrated("historical body"))

    def test_title_is_review_not_dossier(self):
        dossier = self.load_one()
        self.assertEqual(
            MODULE.review_title(dossier),
            "[STATE REVIEW] United States — adversarial review of canonical ECL dossier",
        )


if __name__ == "__main__":
    unittest.main()
