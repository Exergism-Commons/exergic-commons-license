import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RESOLVE = load_module("ecl_resolve_distribution_contract", ROOT / "tools" / "ecl_resolve.py")
DIST = load_module("ecl_distribution_contract", ROOT / "tools" / "ecl_distribution.py")
SCHEMA = json.loads((ROOT / "schemas" / "distribution.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
DRAFT_BUNDLE = "ECL-0.3-DRAFT@RP-EMPTY-1"
DRAFT_BUNDLE_PATH = ROOT / "releases" / "bundles" / f"{DRAFT_BUNDLE}.json"


class DistributionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)

    def _build(self, parent: Path):
        output = parent / DRAFT_BUNDLE
        descriptor = DIST.build_distribution(
            ROOT,
            bundle_ref=DRAFT_BUNDLE,
            output=output,
            allow_draft=True,
        )
        return output, descriptor

    def _draft_manifest(self):
        return RESOLVE.load_json(DRAFT_BUNDLE_PATH)

    def test_builder_descriptor_conforms_to_distribution_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, descriptor = self._build(Path(tmp))
            VALIDATOR.validate(descriptor)
            parsed = RESOLVE.parse_json_object(
                (output / DIST.DESCRIPTOR_NAME).read_text(encoding="utf-8"),
                label="generated descriptor",
            )
            VALIDATOR.validate(parsed)

    def test_schema_rejects_mutable_schedule_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, descriptor = self._build(Path(tmp))
            descriptor["schedule"]["ref"] = "ECL-latest"
            with self.assertRaises(jsonschema.ValidationError):
                VALIDATOR.validate(descriptor)

    def test_schema_rejects_descriptor_path_redirection(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, descriptor = self._build(Path(tmp))
            descriptor["schedule"]["path"] = "../ECL-SCHEDULE"
            with self.assertRaises(jsonschema.ValidationError):
                VALIDATOR.validate(descriptor)

    def test_strict_json_parser_rejects_duplicate_root_member(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object member: bundle"):
            RESOLVE.parse_json_object(
                '{"bundle":"ECL-1.0.0@RP-2026.08.18.1",'
                '"bundle":"ECL-1.0.1@RP-2026.08.18.1"}',
                label="duplicate test",
            )

    def test_strict_json_parser_rejects_duplicate_nested_member(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object member: ref"):
            RESOLVE.parse_json_object(
                '{"license":{"ref":"ECL-1.0.0","ref":"ECL-1.0.1"}}',
                label="nested duplicate test",
            )

    def test_verifier_rejects_duplicate_descriptor_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self._build(Path(tmp))
            (output / DIST.DESCRIPTOR_NAME).write_text(
                '{"bundle":"ECL-0.3-DRAFT@RP-EMPTY-1",'
                '"bundle":"ECL-1.0.0@RP-2026.08.18.1"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate JSON object member: bundle"):
                DIST.verify_distribution(output)

    def test_verifier_rejects_duplicate_bundle_manifest_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self._build(Path(tmp))
            manifest_bytes = (
                b'{"bundle":"ECL-0.3-DRAFT@RP-EMPTY-1",'
                b'"bundle":"ECL-1.0.0@RP-2026.08.18.1"}'
            )
            (output / DIST.BUNDLE_NAME).write_bytes(manifest_bytes)
            descriptor_path = output / DIST.DESCRIPTOR_NAME
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            descriptor["bundle_manifest"]["sha256"] = DIST.sha256_bytes(manifest_bytes)
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate JSON object member: bundle"):
                DIST.verify_distribution(output)

    def test_optional_bundle_metadata_accepts_schema_compatible_values(self):
        bundle = self._draft_manifest()
        bundle["knowledge_snapshot"] = "urn:ecl:knowledge:snapshot:test"
        bundle["released_at"] = "2026-08-18T00:00:00Z"
        self.assertIs(DIST._validate_bundle_manifest_shape(bundle), bundle)

    def test_optional_knowledge_snapshot_rejects_non_schema_type(self):
        bundle = self._draft_manifest()
        bundle["knowledge_snapshot"] = {"mutable": True}
        with self.assertRaisesRegex(ValueError, "knowledge_snapshot must be a string or null"):
            DIST._validate_bundle_manifest_shape(bundle)

    def test_optional_released_at_rejects_non_string(self):
        bundle = self._draft_manifest()
        bundle["released_at"] = 123
        with self.assertRaisesRegex(ValueError, "released_at must be an RFC3339"):
            DIST._validate_bundle_manifest_shape(bundle)

    def test_optional_released_at_rejects_invalid_string(self):
        bundle = self._draft_manifest()
        bundle["released_at"] = "not-a-date"
        with self.assertRaisesRegex(ValueError, "released_at must be an RFC3339"):
            DIST._validate_bundle_manifest_shape(bundle)

    def test_optional_released_at_rejects_impossible_calendar_date(self):
        bundle = self._draft_manifest()
        bundle["released_at"] = "2026-02-31T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "released_at must be an RFC3339"):
            DIST._validate_bundle_manifest_shape(bundle)


if __name__ == "__main__":
    unittest.main()
