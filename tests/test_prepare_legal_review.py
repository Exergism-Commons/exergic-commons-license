import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location("prepare_legal_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareLegalReviewTests(unittest.TestCase):
    def _write_repo(self, root: Path) -> Path:
        (root / "spec").mkdir(parents=True)
        (root / "schemas").mkdir(parents=True)
        (root / "versions" / "licenses").mkdir(parents=True)
        (root / "reviews" / "legal").mkdir(parents=True)

        (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_bytes(b"review-spec\n")
        (root / "spec" / "VERSIONING.md").write_bytes(b"versioning\n")
        (root / "schemas" / "bundle.schema.json").write_bytes(b'{"bundle": true}\n')
        license_path = root / "versions" / "licenses" / "ECL-1.0-RC1.md"
        license_path.write_bytes(b"candidate-license\n")
        return license_path

    def test_freezes_exact_inputs_without_creating_completed_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            license_path = self._write_repo(root)

            result = MODULE.prepare_review_inputs(
                root,
                review_id="ECL-1.0-RC1-review-a",
                license_path="versions/licenses/ECL-1.0-RC1.md",
            )

            self.assertEqual(result["status"], "prepared-not-reviewed")
            self.assertIn("NOT A LEGAL REVIEW RECORD", result["notice"])
            self.assertEqual(
                result["license"]["sha256"],
                hashlib.sha256(license_path.read_bytes()).hexdigest(),
            )

            input_dir = root / "reviews" / "legal" / "inputs" / "ECL-1.0-RC1-review-a"
            expected = {
                "LEGAL-ADVERSARIAL-REVIEW.md": b"review-spec\n",
                "VERSIONING.md": b"versioning\n",
                "bundle.schema.json": b'{"bundle": true}\n',
            }
            for filename, contents in expected.items():
                frozen = input_dir / filename
                self.assertEqual(frozen.read_bytes(), contents)

            self.assertFalse((root / "reviews" / "legal" / "records").exists())
            self.assertEqual(
                result["completed_record_path"],
                "reviews/legal/records/ECL-1.0-RC1-review-a.json",
            )

    def test_existing_review_id_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)
            kwargs = {
                "review_id": "ECL-1.0-RC1-review-a",
                "license_path": "versions/licenses/ECL-1.0-RC1.md",
            }
            MODULE.prepare_review_inputs(root, **kwargs)
            frozen = (
                root
                / "reviews"
                / "legal"
                / "inputs"
                / "ECL-1.0-RC1-review-a"
                / "VERSIONING.md"
            )
            original = frozen.read_bytes()
            (root / "spec" / "VERSIONING.md").write_bytes(b"changed-canonical\n")

            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.prepare_review_inputs(root, **kwargs)

            self.assertEqual(frozen.read_bytes(), original)

    def test_invalid_review_id_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)

            for review_id in ("", "../escape", "review/child", "-leading", "trailing-"):
                with self.subTest(review_id=review_id):
                    with self.assertRaisesRegex(ValueError, "safe identifier"):
                        MODULE.prepare_review_inputs(
                            root,
                            review_id=review_id,
                            license_path="versions/licenses/ECL-1.0-RC1.md",
                        )

            self.assertFalse((root / "reviews" / "legal" / "inputs").exists())

    def test_unsafe_candidate_license_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)

            for path in ("../LICENSE", "/tmp/LICENSE", "versions\\licenses\\ECL.md"):
                with self.subTest(path=path):
                    with self.assertRaisesRegex(ValueError, "repository-relative|unsafe"):
                        MODULE.prepare_review_inputs(
                            root,
                            review_id="review-a",
                            license_path=path,
                        )

    def test_missing_canonical_input_leaves_no_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)
            (root / "schemas" / "bundle.schema.json").unlink()

            with self.assertRaisesRegex(ValueError, "missing canonical bundle_schema"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                )

            self.assertFalse(
                (root / "reviews" / "legal" / "inputs" / "review-a").exists()
            )

    def test_candidate_license_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            license_path = self._write_repo(root)
            link = license_path.with_name("linked-license.md")
            try:
                link.symlink_to(license_path.name)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/linked-license.md",
                )

    def test_symlinked_input_namespace_is_rejected_without_external_write(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            self._write_repo(root)
            outside_root = Path(outside)
            inputs = root / "reviews" / "legal" / "inputs"
            try:
                inputs.symlink_to(outside_root, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                )

            self.assertEqual(list(outside_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
