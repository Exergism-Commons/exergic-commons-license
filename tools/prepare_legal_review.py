#!/usr/bin/env python3
"""Prepare immutable inputs for an external ECL legal review.

This tool performs repository/mechanism preparation only. It does not create a
completed legal-review record, assess reviewer qualifications, make legal
findings, or satisfy any part of the qualified-review minimum by itself.

The completed record remains a separate human-reviewed artifact at
``reviews/legal/records/<review_id>.json`` and is validated by ``ecl_resolve``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
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


def _repository_file(root: Path, raw_path: str, *, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{label} path must be a non-empty string")
    if "\\" in raw_path or raw_path.startswith("/"):
        raise ValueError(f"{label} path must be a repository-relative POSIX path")

    segments = raw_path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{label} path contains an unsafe path segment")

    resolved_root = root.resolve(strict=True)
    path = root
    for segment in segments:
        path = path / segment
        if path.is_symlink():
            raise ValueError(f"{label} must not traverse symbolic links: {path}")

    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")

    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"{label} resolves outside repository root: {path}")
    if not resolved.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")
    return resolved


def _safe_directory(root: Path, relative_path: str, *, label: str) -> Path:
    """Return a repository directory path without traversing symlink parents."""

    path = root
    for segment in relative_path.split("/"):
        path = path / segment
        if path.is_symlink():
            raise ValueError(f"{label} must not traverse symbolic links: {path}")
    return path


def prepare_review_inputs(
    root: Path, *, review_id: str, license_path: str
) -> dict[str, Any]:
    """Freeze canonical mechanism inputs and return a non-review descriptor.

    All source bytes are read and hashed before the destination directory is
    created. Existing review IDs are never overwritten, even when their bytes
    are identical. On a write failure, a newly-created partial snapshot is
    removed.
    """

    _validate_review_id(review_id)
    root = root.resolve(strict=True)

    candidate_license = _repository_file(root, license_path, label="candidate License")
    license_bytes = candidate_license.read_bytes()

    frozen: dict[str, tuple[str, bytes]] = {}
    for key, (source_path, filename) in CANONICAL_INPUTS.items():
        source = _repository_file(root, source_path, label=f"canonical {key}")
        frozen[key] = (filename, source.read_bytes())

    inputs_root = _safe_directory(
        root, "reviews/legal/inputs", label="legal review input namespace"
    )
    review_dir = inputs_root / review_id
    if review_dir.exists() or review_dir.is_symlink():
        raise ValueError(f"legal review input snapshot already exists: {review_dir}")

    inputs_root.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        review_dir.mkdir(exist_ok=False)
        created = True
        for filename, data in frozen.values():
            destination = review_dir / filename
            with destination.open("xb") as handle:
                handle.write(data)
            if hashlib.sha256(destination.read_bytes()).digest() != hashlib.sha256(data).digest():
                raise OSError(f"snapshot verification failed for {destination}")
    except Exception:
        if created:
            shutil.rmtree(review_dir, ignore_errors=True)
        raise

    descriptor: dict[str, Any] = {
        "schema_version": 1,
        "kind": "ecl-legal-review-input-preparation",
        "status": "prepared-not-reviewed",
        "review_id": review_id,
        "notice": (
            "NOT A LEGAL REVIEW RECORD. This snapshot does not count as a "
            "qualified, independent, or adversarial legal review."
        ),
        "license": {
            "path": str(candidate_license.relative_to(root)),
            "sha256": sha256_bytes(license_bytes),
        },
        "completed_record_path": f"reviews/legal/records/{review_id}.json",
        "completed_record_schema": "schemas/legal-review-record.schema.json",
    }

    for key, (filename, data) in frozen.items():
        descriptor[key] = {
            "path": f"reviews/legal/inputs/{review_id}/{filename}",
            "sha256": sha256_bytes(data),
        }

    return descriptor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze the exact non-License inputs for a qualified ECL legal review. "
            "This command never creates a completed legal-review record."
        )
    )
    parser.add_argument("review_id", help="immutable review identifier")
    parser.add_argument(
        "--license",
        required=True,
        dest="license_path",
        help="repository-relative path to the exact candidate License",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        descriptor = prepare_review_inputs(
            root, review_id=args.review_id, license_path=args.license_path
        )
    except (OSError, ValueError) as exc:
        print(f"legal-review preparation failed: {exc}")
        return 1

    print(json.dumps(descriptor, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
