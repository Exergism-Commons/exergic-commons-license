import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location(
    "prepare_legal_review_git_identity", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


class PrepareLegalReviewGitIdentityTests(unittest.TestCase):
    def _repo(self, root: Path) -> str:
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
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
        return git(root, "rev-parse", "HEAD")

    def test_post_clean_worktree_source_mutation_cannot_change_frozen_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            original_gate = MODULE._require_head_and_clean

            def mutate_after_gate(repo: Path, source: str) -> None:
                original_gate(repo, source)
                (root / "spec" / "VERSIONING.md").write_bytes(
                    b"attacker-versioning\n"
                )
                (root / "schemas" / "bundle.schema.json").write_bytes(
                    b"attacker-schema\n"
                )
                (
                    root / "versions" / "licenses" / "ECL-1.0-RC1.md"
                ).write_bytes(b"attacker-license\n")

            with mock.patch.object(
                MODULE, "_require_head_and_clean", side_effect=mutate_after_gate
            ):
                result = MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

            target = root / "reviews" / "legal" / "inputs" / "review-a"
            self.assertEqual(
                (target / "VERSIONING.md").read_bytes(), b"versioning\n"
            )
            self.assertEqual(
                (target / "bundle.schema.json").read_bytes(), b'{"bundle": true}\n'
            )
            self.assertNotEqual(
                result["license"]["sha256"], MODULE.sha256_bytes(b"attacker-license\n")
            )

    def test_post_clean_source_directory_replacement_cannot_rebind_git_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            original_gate = MODULE._require_head_and_clean

            def replace_versions_after_gate(repo: Path, source: str) -> None:
                original_gate(repo, source)
                (root / "versions").rename(root / "versions-old")
                (root / "versions" / "licenses").mkdir(parents=True)
                (
                    root / "versions" / "licenses" / "ECL-1.0-RC1.md"
                ).write_bytes(b"replacement\n")

            with mock.patch.object(
                MODULE, "_require_head_and_clean", side_effect=replace_versions_after_gate
            ):
                result = MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

            self.assertEqual(result["source_commit"], commit)
            self.assertEqual(
                result["license"]["sha256"],
                MODULE.sha256_bytes(b"candidate-license\n"),
            )

    def test_post_clean_canonical_directory_replacement_cannot_rebind_git_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = self._repo(root)
            original_gate = MODULE._require_head_and_clean

            def replace_spec_after_gate(repo: Path, source: str) -> None:
                original_gate(repo, source)
                (root / "spec").rename(root / "spec-old")
                (root / "spec").mkdir()
                (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_bytes(
                    b"replacement-review\n"
                )
                (root / "spec" / "VERSIONING.md").write_bytes(
                    b"replacement-versioning\n"
                )

            with mock.patch.object(
                MODULE, "_require_head_and_clean", side_effect=replace_spec_after_gate
            ):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )

            target = root / "reviews" / "legal" / "inputs" / "review-a"
            self.assertEqual(
                (target / "LEGAL-ADVERSARIAL-REVIEW.md").read_bytes(),
                b"review-spec\n",
            )
            self.assertEqual(
                (target / "VERSIONING.md").read_bytes(), b"versioning\n"
            )


if __name__ == "__main__":
    unittest.main()
