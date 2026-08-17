import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location(
    "prepare_legal_review_tree_ancestors", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def configure_origin(root: Path) -> None:
    origin = root / ".git" / "authoritative-origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=root, check=True)
    subprocess.run(
        ["git", "push", "-q", "-u", "origin", "HEAD:refs/heads/main"],
        cwd=root,
        check=True,
    )


class PrepareLegalReviewTreeAncestorTests(unittest.TestCase):
    def test_hidden_non_tree_legal_ancestor_is_rejected_from_source_commit(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "spec").mkdir(parents=True)
            (root / "schemas").mkdir(parents=True)
            (root / "versions" / "licenses").mkdir(parents=True)
            (root / "reviews").mkdir(parents=True)

            (root / "spec" / "LEGAL-ADVERSARIAL-REVIEW.md").write_bytes(
                b"review-spec\n"
            )
            (root / "spec" / "VERSIONING.md").write_bytes(b"versioning\n")
            (root / "schemas" / "bundle.schema.json").write_bytes(
                b'{"bundle": true}\n'
            )
            (root / "versions" / "licenses" / "ECL-1.0-RC1.md").write_bytes(
                b"candidate-license\n"
            )

            legal = root / "reviews" / "legal"
            try:
                legal.symlink_to("elsewhere", target_is_directory=True)
            except OSError as exc:
                self.skipTest(str(exc))

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=root, check=True
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            configure_origin(root)
            commit = git(root, "rev-parse", "HEAD")

            # Simulate a sparse/skip-worktree checkout that locally materializes
            # a benign-looking directory while the immutable source commit still
            # contains a symlink at reviews/legal.
            legal.unlink()
            legal.mkdir()
            (legal / "README.md").write_text("local workspace\n", encoding="utf-8")
            subprocess.run(
                ["git", "update-index", "--skip-worktree", "reviews/legal"],
                cwd=root,
                check=True,
            )
            self.assertEqual(git(root, "status", "--porcelain=v1"), "")

            with self.assertRaisesRegex(
                ValueError, "legal review workspace in source_commit must be a directory"
            ):
                MODULE.prepare_review_inputs(
                    root,
                    review_id="review-a",
                    license_path="versions/licenses/ECL-1.0-RC1.md",
                    source_commit=commit,
                )


if __name__ == "__main__":
    unittest.main()
