import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location("prepare_legal_review_grafts", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareLegalReviewGraftTests(unittest.TestCase):
    def test_local_grafts_are_rejected_before_history_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
            )
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "tracked.txt").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "one"], cwd=root, check=True)
            first = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            (root / "tracked.txt").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "two"], cwd=root, check=True)
            second = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            grafts = root / ".git" / "info" / "grafts"
            grafts.write_text(f"{second}\n", encoding="ascii")

            # The fixture is a real history rewrite: ordinary Git now hides the
            # original parent even though the commit object itself is unchanged.
            parents = subprocess.check_output(
                ["git", "show", "-s", "--format=%P", second], cwd=root, text=True
            ).strip()
            self.assertEqual(parents, "")
            self.assertNotEqual(first, second)

            with self.assertRaisesRegex(ValueError, "Git grafts are not permitted"):
                MODULE._require_no_grafts(root)


if __name__ == "__main__":
    unittest.main()
