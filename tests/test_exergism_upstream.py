import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "exergism" / "upstream.json"

EXPECTED_REPOSITORY = "Exergism-Commons/exergism"
EXPECTED_RELEASE = "v0.1.0"
EXPECTED_COMMIT = "4ca5207244f30060c486ca342f2f0af0d2a80fa2"
EXPECTED_RELEASE_MANIFEST_SHA256 = "41fcd650ead5b568f384656009e3152f3b0b9fc4bca7aab7ee32b716e9386e67"
EXPECTED_SOURCE_ARCHIVE_SHA256 = "722b4654482e4405a78a279a0dfc041dcfbf8c19da8e5ad91e3c7102cb1beddb"
EXPECTED_FORMAL_PATH = "formal/sistema_analitico_exergico.json"

PINNED_PROFILES = (
    "upstream-transition-v0.1.0.json",
    "upstream-liberated-society-v0.1.0.json",
    "upstream-mundane-interaction-v0.1.0.json",
)


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
        self.assertEqual(upstream["formal_model"]["path"], EXPECTED_FORMAL_PATH)
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

    def test_pinned_profiles_are_upstream_profiles_not_local_balanced_defaults(self):
        profiles_dir = ROOT / "exergism" / "profiles"
        contexts = set()
        for filename in PINNED_PROFILES:
            profile = json.loads((profiles_dir / filename).read_text(encoding="utf-8"))
            self.assertEqual(profile["status"], "pinned-upstream-context-profile")
            self.assertEqual(profile["upstream_release"], EXPECTED_RELEASE)
            self.assertEqual(profile["upstream_commit"], EXPECTED_COMMIT)
            self.assertEqual(profile["upstream_path"], EXPECTED_FORMAL_PATH)
            self.assertEqual(profile["qC"], 2.0)
            self.assertEqual(profile["qS"], 2.0)
            self.assertEqual(profile["S_crit"], 0.85)
            self.assertEqual(profile["C_crit"], 0.80)
            contexts.add(profile["context"])
        self.assertEqual(contexts, {"transicion", "sociedad_liberada", "interaccion_mundana"})

        legacy = json.loads((profiles_dir / "reference-balanced-v2.json").read_text(encoding="utf-8"))
        self.assertIn("deprecated", legacy["status"])

    def test_transition_ambiguity_is_preserved(self):
        profile = json.loads(
            (ROOT / "exergism" / "profiles" / "upstream-transition-v0.1.0.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(sum(profile[f"a{i}"] for i in range(1, 6)), 0.90)
        self.assertTrue(profile.get("known_ambiguities"))

    def test_docs_expose_upstream_and_application_boundary(self):
        readme = (ROOT / "exergism" / "README.md").read_text(encoding="utf-8")
        spec = (ROOT / "spec" / "EXERGIC-ANALYSIS.md").read_text(encoding="utf-8")
        for text in (readme, spec):
            self.assertIn(EXPECTED_RELEASE, text)
            self.assertIn(EXPECTED_COMMIT, text)
            self.assertIn(EXPECTED_FORMAL_PATH, text)
        self.assertIn("no licensing effect", readme.lower())
        self.assertIn("does not create licensing restrictions", spec)
        self.assertIn("does not `owl:imports`", spec)
        self.assertIn("P_atr", spec)
        self.assertIn("E_i_adj", spec)
        self.assertIn("M_f", spec)


if __name__ == "__main__":
    unittest.main()
