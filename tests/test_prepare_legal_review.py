import hashlib
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location("prepare_legal_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class PrepareLegalReviewTests(unittest.TestCase):
    def _repo(
        self,
        root: Path,
        *,
        record_id: str | None = None,
        input_id: str | None = None,
    ) -> str:
        (root / "spec").mkdir(parents=True)
        (root / "schemas").mkdir(parents=True)
        (root / "versions" / "licenses").mkdir(parents=True)
        (root / "reviews" / "legal").mkdir(parents=True)
        (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_bytes(b"review-spec\n")
        (root / "spec" / "VERSIONING.md").write_bytes(b"versioning\n")
        (root / "schemas" / "bundle.schema.json").write_bytes(b'{"bundle": true}\n')
        (root / "versions" / "licenses" / "ECL-1.0-RC1.md").write_bytes(
            b"candidate-license\n"
        )
        (root / "reviews" / "legal" / "README.md").write_text(
            "workspace\n", encoding="utf-8"
        )
        if record_id:
            records = root / "reviews" / "legal" / "records"
            records.mkdir()
            (records / f"{record_id}.json").write_text(
                '{"status":"complete"}\n', encoding="utf-8"
            )
        if input_id:
            inputs = root / "reviews" / "legal" / "inputs" / input_id
            inputs.mkdir(parents=True)
            (inputs / "VERSIONING.md").write_text("old\n", encoding="utf-8")

        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
        return git(root, "rev-parse", "HEAD")

    def test_freezes_exact_commit_inputs_without_creating_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            result = MODULE.prepare_review_inputs(
                root,
                review_id="ECL-1.0-RC1-review-a",
                license_path="versions/licenses/ECL-1.0-RC1.md",
                source_commit=commit,
            )

            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["source_commit"], commit)
            self.assertEqual(result["status"], "prepared-not-reviewed")
            self.assertIn("NOT A LEGAL REVIEW RECORD", result["notice"])
            self.assertEqual(
                result["license"]["sha256"],
                hashlib.sha256(b"candidate-license\n").hexdigest(),
            )

            target = (
                root
                / "reviews"
                / "legal"
                / "inputs"
                / "ECL-1.0-RC1-review-a"
            )
            self.assertEqual(
                (target / "LEGAL-ADVERSARIAL-REVIEW.md").read_bytes(),
                b"review-spec\n",
            )
            self.assertEqual(
                (target / "VERSIONING.md").read_bytes(), b"versioning\n"
            )
            self.assertEqual(
                (target / "bundle.schema.json").read_bytes(), b'{"bundle": true}\n'
            )
            self.assertFalse((root / "reviews" / "legal" / "records").exists())

    def test_existing_snapshot_consumes_review_id_before_cleanliness_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            target = root / "reviews" / "legal" / "inputs" / "review-a"
            target.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

    def test_completed_record_in_source_commit_permanently_consumes_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root, record_id="review-a")
            with self.assertRaisesRegex(ValueError, "permanently consumed"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

    def test_input_snapshot_in_source_commit_consumes_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root, input_id="review-a")
            with self.assertRaisesRegex(ValueError, "already exists"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

    def test_source_commit_must_equal_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._repo(root)
            (root / "extra.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "extra.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "second"], cwd=root, check=True)
            with self.assertRaisesRegex(ValueError, "must equal current HEAD"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=first,
                )

    def test_dirty_worktree_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            (root / "spec" / "VERSIONING.md").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "working tree must be clean"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

    def test_source_commit_requires_full_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            with self.assertRaisesRegex(ValueError, "full 40-hex"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit[:12],
                )

    def test_missing_candidate_in_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            with self.assertRaisesRegex(ValueError, "missing candidate License"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/absent.md",
                    source_commit=commit,
                )

    def test_invalid_review_id_and_unsafe_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            with self.assertRaisesRegex(ValueError, "safe identifier"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="../escape",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )
            for path in (
                "../LICENSE",
                "/tmp/LICENSE",
                "versions\\licenses\\ECL.md",
                "bad:path",
            ):
                with self.subTest(path=path):
                    with self.assertRaisesRegex(ValueError, "repository-relative|unsafe"):
                        MODULE.prepare_review_inputs(
                            root,
                            review_id="review-a",
                            license_path=path,
                            source_commit=commit,
                        )

    def test_committed_candidate_symlink_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            link = root / "versions" / "licenses" / "linked.md"
            try:
                link.symlink_to("ECL-1.0-RC1.md")
            except OSError as exc:
                self.skipTest(str(exc))
            subprocess.run(
                ["git", "add", "versions/licenses/linked.md"], cwd=root, check=True
            )
            subprocess.run(["git", "commit", "-qm", "symlink"], cwd=root, check=True)
            commit = git(root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "regular tracked file"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/linked.md",
                    source_commit=commit,
                )

    def test_symlinked_output_namespace_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            self._repo(root)
            inputs = root / "reviews" / "legal" / "inputs"
            try:
                inputs.symlink_to(Path(outside), target_is_directory=True)
            except OSError as exc:
                self.skipTest(str(exc))
            subprocess.run(
                ["git", "add", "reviews/legal/inputs"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "commit", "-qm", "bad inputs symlink"], cwd=root, check=True
            )
            commit = git(root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "real directory, not a symlink"):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )
            self.assertEqual(list(Path(outside).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
