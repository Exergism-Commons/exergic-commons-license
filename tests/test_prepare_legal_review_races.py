import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "prepare_legal_review.py"
SPEC = importlib.util.spec_from_file_location("prepare_legal_review_races", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareLegalReviewRaceTests(unittest.TestCase):
    def setUp(self):
        try:
            MODULE._require_secure_runtime()
        except OSError as exc:
            self.skipTest(f"secure legal-review preparation unavailable: {exc}")

    def _write_repo(self, root: Path) -> None:
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

    def test_source_ancestor_move_cannot_rebind_candidate_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)
            original_read_all = MODULE._read_all
            raced = False

            def move_versions_after_open(fd: int) -> bytes:
                nonlocal raced
                if not raced:
                    (root / "versions").rename(root / "versions-old")
                    (root / "versions").mkdir()
                    raced = True
                return original_read_all(fd)

            with mock.patch.object(
                MODULE, "_read_all", side_effect=move_versions_after_open
            ):
                with self.assertRaisesRegex(
                    OSError, "candidate License source directory changed"
                ):
                    MODULE.prepare_review_inputs(
                        root,
                        review_id="review-a",
                        license_path="versions/licenses/ECL-1.0-RC1.md",
                    )

            self.assertFalse((root / "reviews" / "legal" / "inputs").exists())

    def test_replaced_frozen_entry_after_precheck_is_rejected_post_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)
            original_rename = MODULE._rename_noreplace

            def replace_versioning_then_publish(
                parent_fd: int, source: str, destination: str
            ) -> None:
                temp_fd = os.open(source, MODULE._directory_flags(), dir_fd=parent_fd)
                try:
                    os.unlink("VERSIONING.md", dir_fd=temp_fd)
                    attacker_fd = os.open(
                        "VERSIONING.md",
                        MODULE._file_write_flags(),
                        0o600,
                        dir_fd=temp_fd,
                    )
                    try:
                        MODULE._write_all(attacker_fd, b"attacker-bytes\n")
                        os.fsync(attacker_fd)
                    finally:
                        os.close(attacker_fd)
                    os.fsync(temp_fd)
                finally:
                    os.close(temp_fd)
                original_rename(parent_fd, source, destination)

            with mock.patch.object(
                MODULE,
                "_rename_noreplace",
                side_effect=replace_versioning_then_publish,
            ):
                with self.assertRaisesRegex(OSError, "frozen input entry changed"):
                    MODULE.prepare_review_inputs(
                        root,
                        review_id="review-a",
                        license_path="versions/licenses/ECL-1.0-RC1.md",
                    )

            self.assertFalse(
                (root / "reviews" / "legal" / "inputs" / "review-a").exists()
            )

    def test_snapshot_renamed_before_cleanup_is_reported_as_residual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_repo(root)
            original_remove = MODULE._remove_owned_snapshot
            moved_names: list[str] = []

            def move_snapshot_then_cleanup(
                inputs_fd: int,
                name: str,
                expected: os.stat_result,
                filenames: tuple[str, ...],
            ) -> None:
                moved = f"{name}-moved"
                os.rename(
                    name,
                    moved,
                    src_dir_fd=inputs_fd,
                    dst_dir_fd=inputs_fd,
                )
                moved_names.append(moved)
                original_remove(inputs_fd, name, expected, filenames)

            with mock.patch.object(
                MODULE, "_record_consumes_id", side_effect=[False, True]
            ), mock.patch.object(
                MODULE,
                "_remove_owned_snapshot",
                side_effect=move_snapshot_then_cleanup,
            ):
                with self.assertRaisesRegex(
                    OSError, "rollback could not verify cleanup.*residual snapshot"
                ):
                    MODULE.prepare_review_inputs(
                        root,
                        review_id="review-a",
                        license_path="versions/licenses/ECL-1.0-RC1.md",
                    )

            self.assertEqual(len(moved_names), 1)
            self.assertTrue(
                (root / "reviews" / "legal" / "inputs" / moved_names[0]).is_dir()
            )


if __name__ == "__main__":
    unittest.main()
