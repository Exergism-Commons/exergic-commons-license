import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ecl_resolve.py"
SPEC = importlib.util.spec_from_file_location("ecl_resolve_identity", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ECLResolveIdentityTests(unittest.TestCase):
    def test_review_id_uses_ascii_non_dot_segment_grammar(self):
        rejected = [".", "..", "réview", ".hidden", "trailing."]
        accepted = ["ECL-1.0.0-legal-review-1", "r1", "A_B.C-2"]

        for value in rejected:
            with self.subTest(value=value):
                self.assertFalse(MODULE.valid_review_id(value))
        for value in accepted:
            with self.subTest(value=value):
                self.assertTrue(MODULE.valid_review_id(value))

    def test_runtime_review_id_grammar_matches_declared_schemas(self):
        bundle_schema = json.loads(
            (ROOT / "schemas" / "bundle.schema.json").read_text(encoding="utf-8")
        )
        review_schema = json.loads(
            (ROOT / "schemas" / "legal-review-record.schema.json").read_text(
                encoding="utf-8"
            )
        )
        bundle_pattern = bundle_schema["$defs"]["legalReviewComponent"]["properties"][
            "ref"
        ]["pattern"]
        review_pattern = review_schema["properties"]["review_id"]["pattern"]

        for value in [
            ".",
            "..",
            "réview",
            ".hidden",
            "trailing.",
            "ECL-1.0.0-legal-review-1",
            "r1",
            "A_B.C-2",
        ]:
            runtime = MODULE.valid_review_id(value)
            self.assertEqual(bool(re.fullmatch(bundle_pattern, value)), runtime)
            self.assertEqual(bool(re.fullmatch(review_pattern, value)), runtime)

    def test_file_reference_rejects_unsafe_segment_before_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            component = {"path": "reviews/../record.json", "sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "unsafe path segment"):
                MODULE.validate_file_reference(root, component, label="test artifact")

    def test_file_reference_has_explicit_symbolic_link_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}", encoding="utf-8")
            component = {"path": "artifact.json", "sha256": MODULE.sha256(artifact)}

            original = Path.is_symlink

            def report_only_artifact_as_link(path):
                if path == artifact:
                    return True
                return original(path)

            with patch.object(Path, "is_symlink", report_only_artifact_as_link):
                with self.assertRaisesRegex(ValueError, "symbolic links"):
                    MODULE.validate_file_reference(root, component, label="test artifact")


if __name__ == "__main__":
    unittest.main()
