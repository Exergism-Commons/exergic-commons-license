#!/usr/bin/env python3
"""Prepare immutable inputs for an external ECL legal review.

This helper is deliberately narrow. It materializes review inputs from an exact
Git commit into ``reviews/legal/inputs/<review_id>/`` and prints a deterministic
preparation descriptor. It does not perform legal review, attest reviewer
qualifications, create a completed legal-review record, or satisfy the qualified
review gate by itself.

Trust boundary: run this command in an isolated/trusted checkout with no
untrusted concurrent writer. Source identity is taken from Git objects, not from
mutable working-tree paths. The command requires the requested source commit to
be the current HEAD and requires a clean working tree before publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
FULL_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
CANONICAL_INPUTS = {
    "review_spec": (
        "spec/LEGAL-ADVERSARIAL-REVIEW.md",
        "LEGAL-ADVERSARIAL-REVIEW.md",
    ),
    "incorporation_spec": ("spec/VERSIONING.md", "VERSIONING.md"),
    "bundle_schema": ("schemas/bundle.schema.json", "bundle.schema.json"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_review_id(review_id: str) -> None:
    if REVIEW_ID_RE.fullmatch(review_id) is None:
        raise ValueError("review_id must be a non-empty safe identifier")


def _path_segments(raw_path: str, *, label: str) -> list[str]:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{label} path must be a non-empty string")
    if "\\" in raw_path or raw_path.startswith("/") or ":" in raw_path:
        raise ValueError(f"{label} path must be a repository-relative POSIX path")
    segments = raw_path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{label} path contains an unsafe path segment")
    return segments


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail or process.returncode}")
    return process


def _require_repository_root(root: Path) -> Path:
    resolved = root.resolve(strict=True)
    top = _git(resolved, "rev-parse", "--show-toplevel").stdout.decode().strip()
    if Path(top).resolve() != resolved:
        raise ValueError("root must be the Git repository top-level directory")
    return resolved


def _resolve_source_commit(root: Path, source_commit: str) -> str:
    if FULL_COMMIT_RE.fullmatch(source_commit) is None:
        raise ValueError("source_commit must be an explicit full 40-hex Git commit SHA")
    normalized = source_commit.lower()
    _git(root, "cat-file", "-e", f"{normalized}^{{commit}}")
    actual = _git(root, "rev-parse", f"{normalized}^{{commit}}").stdout.decode().strip()
    if actual != normalized:
        raise ValueError("source_commit must identify the exact commit object")
    return normalized


def _require_full_history(root: Path) -> None:
    shallow = _git(root, "rev-parse", "--is-shallow-repository").stdout.decode().strip()
    if shallow != "false":
        raise ValueError(
            "legal-review preparation requires complete Git history; "
            "fetch/unshallow the repository before preparing a review ID"
        )


def _require_head_and_clean(root: Path, source_commit: str) -> None:
    head = _git(root, "rev-parse", "HEAD").stdout.decode().strip()
    if head != source_commit:
        raise ValueError(
            f"source_commit must equal current HEAD; HEAD is {head}, requested {source_commit}"
        )
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    if status:
        raise ValueError(
            "working tree must be clean before legal-review preparation; "
            "commit/stash unrelated changes and retry"
        )


def _tree_entry(
    root: Path, commit: str, raw_path: str, *, label: str
) -> tuple[str, str, str] | None:
    _path_segments(raw_path, label=label)
    output = _git(root, "ls-tree", "-z", commit, "--", raw_path).stdout
    if not output:
        return None
    records = [record for record in output.split(b"\0") if record]
    if len(records) != 1:
        raise ValueError(f"{label} does not resolve to one Git tree entry: {raw_path}")
    metadata, path_bytes = records[0].split(b"\t", 1)
    mode, object_type, object_id = metadata.decode("ascii").split()
    path = path_bytes.decode("utf-8")
    if path != raw_path:
        raise ValueError(f"{label} resolved to unexpected Git path: {path}")
    return mode, object_type, object_id


def _read_blob(root: Path, commit: str, raw_path: str, *, label: str) -> bytes:
    entry = _tree_entry(root, commit, raw_path, label=label)
    if entry is None:
        raise ValueError(f"missing {label} in source commit: {raw_path}")
    mode, object_type, object_id = entry
    if object_type != "blob" or mode not in {"100644", "100755"}:
        raise ValueError(
            f"{label} must be a regular tracked file, not mode/type "
            f"{mode}/{object_type}: {raw_path}"
        )
    return _git(root, "cat-file", "blob", object_id).stdout


def _history_path_exists(root: Path, raw_path: str) -> bool:
    _path_segments(raw_path, label="consumed review path")
    output = _git(root, "log", "--all", "--format=%H", "--", raw_path).stdout
    return bool(output.strip())


def _lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _assert_real_directory(path: Path, *, label: str) -> None:
    if not _lexists(path):
        raise ValueError(f"missing {label}: {path}")
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be a real directory, not a symlink: {path}")


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_snapshot(target: Path, frozen: dict[str, tuple[str, bytes]]) -> None:
    target.mkdir(mode=0o755)
    try:
        for filename, data in frozen.values():
            path = target / filename
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if path.read_bytes() != data:
                raise OSError(f"snapshot verification failed for {filename}")
        _fsync_directory(target)
        _fsync_directory(target.parent)
    except Exception as primary:
        try:
            shutil.rmtree(target)
            _fsync_directory(target.parent)
        except Exception as cleanup:
            raise OSError(
                "legal-review preparation failed and cleanup also failed; "
                f"residual snapshot may remain at {target}; "
                f"primary error: {primary!r}; cleanup error: {cleanup!r}"
            ) from cleanup
        raise


def prepare_review_inputs(
    root: Path,
    *,
    review_id: str,
    license_path: str,
    source_commit: str,
) -> dict[str, Any]:
    """Materialize exact review inputs from one immutable Git commit."""

    _validate_review_id(review_id)
    _path_segments(license_path, label="candidate License")
    root = _require_repository_root(root)
    source_commit = _resolve_source_commit(root, source_commit)
    _require_full_history(root)

    legal = root / "reviews" / "legal"
    _assert_real_directory(root / "reviews", label="reviews namespace")
    _assert_real_directory(legal, label="legal review workspace")

    target_rel = f"reviews/legal/inputs/{review_id}"
    record_rel = f"reviews/legal/records/{review_id}.json"
    target = root / target_rel
    record = root / record_rel

    # A review ID is permanently consumed by either historical Git state or the
    # current workspace. Check this before the cleanliness gate so rerunning an
    # already-prepared ID produces the more useful consumed-ID error.
    if _history_path_exists(root, target_rel) or _lexists(target):
        raise ValueError(f"legal review input snapshot already exists: {target_rel}")
    if _history_path_exists(root, record_rel) or _lexists(record):
        raise ValueError(
            "review_id is permanently consumed by an existing completed-record "
            f"path: {record_rel}"
        )

    _require_head_and_clean(root, source_commit)

    license_bytes = _read_blob(
        root, source_commit, license_path, label="candidate License"
    )
    frozen: dict[str, tuple[str, bytes]] = {}
    for key, (source_path, filename) in CANONICAL_INPUTS.items():
        frozen[key] = (
            filename,
            _read_blob(
                root,
                source_commit,
                source_path,
                label=f"canonical {key}",
            ),
        )

    inputs = legal / "inputs"
    if _lexists(inputs):
        _assert_real_directory(inputs, label="legal review input namespace")
    else:
        inputs.mkdir(mode=0o755)
        _fsync_directory(legal)

    # The checkout is a trusted isolated workspace by contract, but still fail
    # closed if a cooperative process created either namespace after our first
    # check.
    if _lexists(target) or _lexists(record):
        raise ValueError(f"review_id became consumed during preparation: {review_id}")

    _write_snapshot(target, frozen)

    if _lexists(record):
        try:
            shutil.rmtree(target)
            _fsync_directory(inputs)
        except Exception as cleanup:
            raise OSError(
                "completed record appeared during preparation and rollback failed; "
                f"residual snapshot may remain at {target}: {cleanup!r}"
            ) from cleanup
        raise ValueError(f"review_id became consumed by completed record: {record_rel}")

    try:
        for _, (filename, data) in frozen.items():
            if (target / filename).read_bytes() != data:
                raise OSError(
                    f"published frozen input changed before completion: {filename}"
                )
    except Exception as primary:
        try:
            shutil.rmtree(target)
            _fsync_directory(inputs)
        except Exception as cleanup:
            raise OSError(
                "final frozen-input verification failed and rollback also failed; "
                f"residual snapshot may remain at {target}; "
                f"primary error: {primary!r}; cleanup error: {cleanup!r}"
            ) from cleanup
        raise

    descriptor: dict[str, Any] = {
        "schema_version": 2,
        "kind": "ecl-legal-review-input-preparation",
        "status": "prepared-not-reviewed",
        "review_id": review_id,
        "source_commit": source_commit,
        "notice": (
            "NOT A LEGAL REVIEW RECORD. This snapshot does not count as a "
            "qualified, independent, or adversarial legal review."
        ),
        "license": {
            "path": license_path,
            "sha256": sha256_bytes(license_bytes),
        },
        "completed_record_path": record_rel,
        "completed_record_schema": "schemas/legal-review-record.schema.json",
    }
    for key, (filename, data) in frozen.items():
        descriptor[key] = {
            "path": f"{target_rel}/{filename}",
            "sha256": sha256_bytes(data),
        }
    return descriptor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_id")
    parser.add_argument("--license", required=True, dest="license_path")
    parser.add_argument(
        "--source-commit",
        required=True,
        help="exact full Git commit SHA whose blobs are the review inputs",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to this script's repository)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        descriptor = prepare_review_inputs(
            args.root,
            review_id=args.review_id,
            license_path=args.license_path,
            source_commit=args.source_commit,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps(descriptor, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
