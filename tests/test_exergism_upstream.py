import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "exergism" / "upstream.json"

EXPECTED_REPOSITORY = "Exergism-Commons/exergism"
EXPECTED_RELEASE = "v0.1.0"
EXPECTED_COMMIT = "4ca5207244f30060c486ca342f2f0af0d2a80fa2"
EXPECTED_RELEASE_MANIFEST_SHA256 = "41fcd650ead5b568f384656009e3152f3b0b9fc4bca7aab7ee32b716e9386e67"
EXPECTED_SOURCE_ARCHIVE_SHA256 = "722b4654482e4405a78a279a0dfc041dcfbf8c19da8e5ad91e3c7102cb1beddb"


class ExergismUpstreamPinTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(PIN.read_text(encoding="utf-8"))

    def test_pin_uses_exact_immutable_release_identity(self):
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(self.payload["relationship"], "conceptual-formal-upstream")

        upstream = self.payload["upstream"]
        self.assertEqual(upstream["repository"], EXPECTED_REPOSITORY)
        self.assertEqual(upstream["release"], EXPECTED_RELEASE)
        self.assertEqual(upstream["git_commit"], EXPECTED_COMMIT)
        self.assertRegex(upstream["git_commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(upstream["release_manifest"]["sha256"], EXPECTED_RELEASE_MANIFEST_SHA256)
        self.assertEqual(upstream["source_archive"]["sha256"], EXPECTED_SOURCE_ARCHIVE_SHA256)
        self.assertRegex(upstream["release_manifest"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(upstream["source_archive"]["sha256"], r"^[0-9a-f]{64}$")

    def test_pin_has_no_mutable_or_automatic_normative_binding(self):
        serialized = json.dumps(self.payload, sort_keys=True).lower()
        for forbidden in ("/main", "latest", "master"):
            self.assertNotIn(forbidden, serialized)

        binding = self.payload["ecl_binding"]
        self.assertFalse(binding["legal_effect"])
        self.assertFalse(binding["schedule_effect"])
        self.assertFalse(binding["governance_outcome_effect"])
        self.assertFalse(binding["ontology_import"])
        self.assertIn("explicit ecl repository change", binding["adoption_rule"].lower())

    def test_ecl_docs_expose_the_pin_and_application_boundary(self):
        readme = (ROOT / "exergism" / "README.md").read_text(encoding="utf-8")
        spec = (ROOT / "spec" / "EXERGIC-ANALYSIS.md").read_text(encoding="utf-8")
        for text in (readme, spec):
            self.assertIn("exergism/upstream.json", text)
            self.assertIn(EXPECTED_RELEASE, text)
            self.assertIn(EXPECTED_COMMIT, text)
        self.assertIn("does not create licensing restrictions", spec)
        self.assertIn("does not import the upstream OWL ontology", spec)


if __name__ == "__main__":
    unittest.main()
