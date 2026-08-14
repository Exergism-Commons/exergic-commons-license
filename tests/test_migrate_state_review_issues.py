import importlib.util
import sys
import tempfile
import unittest
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

    def test_frontmatter_parses_issue_mapping(self):
        meta = MODULE.parse_frontmatter(self.dossier_text())
        self.assertEqual(meta["issue"], "187")
        self.assertEqual(meta["iso3"], "USA")
        self.assertEqual(meta["entity"], "United States")

    def test_load_dossiers_uses_frontmatter_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "USA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(Path(tmp))[0]
            self.assertEqual(dossier.issue, 187)
            self.assertEqual(dossier.iso3, "USA")
            self.assertEqual(dossier.outcome, "S")

    def test_duplicate_issue_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AAA.md").write_text(self.dossier_text(issue=10, iso3="AAA", entity="A"), encoding="utf-8")
            (root / "BBB.md").write_text(self.dossier_text(issue=10, iso3="BBB", entity="B"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate issue mapping"):
                MODULE.load_dossiers(root)

    def test_render_preserves_historical_body_and_marks_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "USA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(Path(tmp))[0]
        historical = "Original evidence gathering body\nwith details."
        rendered = MODULE.render_review_body(dossier, "owner/repo", historical)
        self.assertIn(MODULE.MARKER, rendered)
        self.assertIn("Current provisional outcome: `S`", rendered)
        self.assertIn("Original evidence gathering body", rendered)
        self.assertIn("Reviews are **not votes**", rendered)
        self.assertIn("actively sought", rendered)

    def test_marker_makes_migration_idempotent(self):
        body = f"{MODULE.MARKER} iso3=USA issue=187 -->\nreview"
        self.assertTrue(MODULE.already_migrated(body))
        self.assertFalse(MODULE.already_migrated("historical body"))

    def test_title_is_review_not_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "USA.md"
            path.write_text(self.dossier_text(), encoding="utf-8")
            dossier = MODULE.load_dossiers(Path(tmp))[0]
        self.assertEqual(
            MODULE.review_title(dossier),
            "[STATE REVIEW] United States — adversarial review of canonical ECL dossier",
        )


if __name__ == "__main__":
    unittest.main()
