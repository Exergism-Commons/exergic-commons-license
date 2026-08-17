#!/usr/bin/env python3
"""Prepare immutable inputs for an external ECL legal review.

This tool performs repository/mechanism preparation only. It does not create a
completed legal-review record, assess reviewer qualifications, make legal
findings, or satisfy any part of the qualified-review minimum by itself.

The completed record remains a separate human-reviewed artifact at
``reviews/legal/records/<review_id>.json`` and is validated by ``ecl_resolve``.

The preparation boundary is intentionally fail-closed. Secure preparation
requires POSIX directory file-descriptor operations, ``O_NOFOLLOW`` and an
atomic no-replace directory publication primitive (Linux ``renameat2``).
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import stat
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
RENAME_NOREPLACE = 1
READ_CHUNK = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_secure_runtime() -> None:
    missing: list[str] = []
    for name in ("O_DIRECTORY", "O_NOFOLLOW"):
        if not hasattr(os, name):
            missing.append(name)
    for function in (os.open, os.mkdir, os.stat, os.unlink, os.rmdir):
        if function not in os.supports_dir_fd:
            missing.append(f"dir_fd:{function.__name__}")
    if os.stat not in os.supports_follow_symlinks:
        missing.append("stat:follow_symlinks")

    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError:
        missing.append("renameat2")
    else:
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int

    if missing:
        raise OSError(
            "secure legal-review preparation is unavailable on this runtime; "
            "missing: " + ", ".join(sorted(set(missing)))
        )


def _validate_review_id(review_id: str) -> None:
    if REVIEW_ID_RE.fullmatch(review_id) is None:
        raise ValueError("review_id must be a non-empty safe identifier")


def _path_segments(raw_path: str, *, label: str) -> list[str]:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{label} path must be a non-empty string")
    if "\\" in raw_path or raw_path.startswith("/"):
        raise ValueError(f"{label} path must be a repository-relative POSIX path")

    segments = raw_path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{label} path contains an unsafe path segment")
    return segments


def _directory_flags() -> int:
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _file_read_flags() -> int:
    return os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _file_write_flags() -> int:
    return (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_directory_at(
    parent_fd: int, name: str, *, label: str, missing_ok: bool = False
) -> int | None:
    try:
        fd = os.open(name, _directory_flags(), dir_fd=parent_fd)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise ValueError(f"missing {label}: {name}") from None
    except OSError as exc:
        raise ValueError(
            f"{label} must be a real directory without symbolic-link traversal: {name}"
        ) from exc

    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError(f"{label} must be a directory: {name}")
    return fd


def _open_directory_chain(root_fd: int, segments: list[str], *, label: str) -> int:
    current_fd = os.dup(root_fd)
    try:
        for segment in segments:
            next_fd = _open_directory_at(current_fd, segment, label=label)
            assert next_fd is not None
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _stat_fingerprint(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_all(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, READ_CHUNK)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _read_repository_file(root_fd: int, raw_path: str, *, label: str) -> bytes:
    segments = _path_segments(raw_path, label=label)
    parent_fd = _open_directory_chain(root_fd, segments[:-1], label=label)
    file_fd: int | None = None
    try:
        try:
            file_fd = os.open(segments[-1], _file_read_flags(), dir_fd=parent_fd)
        except FileNotFoundError:
            raise ValueError(f"missing {label}: {raw_path}") from None
        except OSError as exc:
            raise ValueError(
                f"{label} must be a regular file without symbolic-link traversal: "
                f"{raw_path}"
            ) from exc

        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"{label} must be a regular file: {raw_path}")
        data = _read_all(file_fd)
        after = os.fstat(file_fd)
        if _stat_fingerprint(before) != _stat_fingerprint(after):
            raise OSError(f"{label} changed while it was being read: {raw_path}")
        return data
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)


def _entry_exists(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _record_consumes_id(legal_fd: int, review_id: str) -> bool:
    records_fd = _open_directory_at(
        legal_fd,
        "records",
        label="legal review records namespace",
        missing_ok=True,
    )
    if records_fd is None:
        return False
    try:
        return _entry_exists(records_fd, f"{review_id}.json")
    finally:
        os.close(records_fd)


def _open_or_create_inputs(legal_fd: int) -> int:
    inputs_fd = _open_directory_at(
        legal_fd,
        "inputs",
        label="legal review input namespace",
        missing_ok=True,
    )
    if inputs_fd is not None:
        return inputs_fd

    try:
        os.mkdir("inputs", mode=0o755, dir_fd=legal_fd)
    except FileExistsError:
        pass
    inputs_fd = _open_directory_at(
        legal_fd,
        "inputs",
        label="legal review input namespace",
    )
    assert inputs_fd is not None
    return inputs_fd


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError("short write while freezing legal-review input")
        offset += written


def _write_frozen_file(directory_fd: int, filename: str, data: bytes) -> int:
    fd = os.open(filename, _file_write_flags(), 0o600, dir_fd=directory_fd)
    try:
        _write_all(fd, data)
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        if _read_all(fd) != data:
            raise OSError(f"snapshot verification failed for {filename}")
        os.fchmod(fd, 0o644)
        os.fsync(fd)
        return fd
    except Exception:
        os.close(fd)
        raise


def _rename_noreplace(parent_fd: int, source: str, destination: str) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise OSError("secure atomic no-replace publication is unavailable") from exc

    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        os.fsencode(source),
        parent_fd,
        os.fsencode(destination),
        RENAME_NOREPLACE,
    )
    if result == 0:
        return

    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise ValueError(
            f"legal review input snapshot already exists: reviews/legal/inputs/{destination}"
        )
    raise OSError(error, os.strerror(error))


def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _remove_owned_snapshot(
    inputs_fd: int,
    name: str,
    expected: os.stat_result,
    filenames: tuple[str, ...],
) -> None:
    directory_fd = _open_directory_at(
        inputs_fd,
        name,
        label="legal review cleanup directory",
        missing_ok=True,
    )
    if directory_fd is None:
        return
    try:
        if not _same_inode(os.fstat(directory_fd), expected):
            raise OSError(
                f"rollback could not verify ownership of reviews/legal/inputs/{name}"
            )
        for filename in filenames:
            try:
                os.unlink(filename, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

    try:
        current = os.stat(name, dir_fd=inputs_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not _same_inode(current, expected) or not stat.S_ISDIR(current.st_mode):
        raise OSError(
            f"rollback lost ownership of reviews/legal/inputs/{name}; residual namespace may remain"
        )

    os.rmdir(name, dir_fd=inputs_fd)
    os.fsync(inputs_fd)
    if _entry_exists(inputs_fd, name):
        raise OSError(
            f"rollback left a residual namespace at reviews/legal/inputs/{name}"
        )


def prepare_review_inputs(
    root: Path, *, review_id: str, license_path: str
) -> dict[str, Any]:
    """Freeze canonical mechanism inputs and return a non-review descriptor."""

    _require_secure_runtime()
    _validate_review_id(review_id)
    _path_segments(license_path, label="candidate License")

    root = root.resolve(strict=True)
    root_fd = os.open(root, _directory_flags())
    legal_fd: int | None = None
    inputs_fd: int | None = None
    snapshot_fd: int | None = None
    frozen_file_fds: list[int] = []
    published_name: str | None = None
    snapshot_identity: os.stat_result | None = None

    try:
        license_bytes = _read_repository_file(
            root_fd, license_path, label="candidate License"
        )
        frozen: dict[str, tuple[str, bytes]] = {}
        for key, (source_path, filename) in CANONICAL_INPUTS.items():
            frozen[key] = (
                filename,
                _read_repository_file(root_fd, source_path, label=f"canonical {key}"),
            )

        legal_fd = _open_directory_chain(
            root_fd, ["reviews", "legal"], label="legal review workspace"
        )
        if _record_consumes_id(legal_fd, review_id):
            raise ValueError(
                f"review_id is permanently consumed by an existing completed-record "
                f"path: reviews/legal/records/{review_id}.json"
            )

        inputs_fd = _open_or_create_inputs(legal_fd)
        if _entry_exists(inputs_fd, review_id):
            raise ValueError(
                f"legal review input snapshot already exists: "
                f"reviews/legal/inputs/{review_id}"
            )

        temp_name = ""
        for _ in range(32):
            candidate = f".{review_id}.prepare-{secrets.token_hex(16)}"
            try:
                os.mkdir(candidate, mode=0o700, dir_fd=inputs_fd)
            except FileExistsError:
                continue
            temp_name = candidate
            break
        if not temp_name:
            raise OSError("unable to allocate a private legal-review snapshot directory")

        snapshot_fd = _open_directory_at(
            inputs_fd,
            temp_name,
            label="private legal review preparation directory",
        )
        assert snapshot_fd is not None
        snapshot_identity = os.fstat(snapshot_fd)

        for filename, data in frozen.values():
            frozen_file_fds.append(_write_frozen_file(snapshot_fd, filename, data))
        os.fsync(snapshot_fd)

        if _record_consumes_id(legal_fd, review_id):
            raise ValueError(
                f"review_id became consumed by records/{review_id}.json during preparation"
            )
        if _entry_exists(inputs_fd, review_id):
            raise ValueError(
                f"legal review input snapshot appeared during preparation: {review_id}"
            )

        _rename_noreplace(inputs_fd, temp_name, review_id)
        published_name = review_id
        os.fsync(inputs_fd)

        published_fd = _open_directory_at(
            inputs_fd,
            review_id,
            label="published legal review input snapshot",
        )
        assert published_fd is not None
        try:
            if not _same_inode(os.fstat(published_fd), snapshot_identity):
                raise OSError("published legal-review snapshot identity changed")
        finally:
            os.close(published_fd)

        if _record_consumes_id(legal_fd, review_id):
            raise ValueError(
                f"review_id became consumed by records/{review_id}.json during publication"
            )

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
                "path": license_path,
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
    except Exception as primary_error:
        cleanup_error: Exception | None = None
        cleanup_name: str | None = None
        if inputs_fd is not None and snapshot_identity is not None:
            cleanup_name = published_name
            if cleanup_name is None and "temp_name" in locals() and temp_name:
                cleanup_name = temp_name
            if cleanup_name is not None:
                try:
                    _remove_owned_snapshot(
                        inputs_fd,
                        cleanup_name,
                        snapshot_identity,
                        tuple(filename for filename, _ in frozen.values())
                        if "frozen" in locals()
                        else (),
                    )
                except (OSError, ValueError) as exc:
                    cleanup_error = exc

        if cleanup_error is not None:
            raise OSError(
                "legal-review preparation failed and rollback could not verify cleanup; "
                f"a residual snapshot may remain at reviews/legal/inputs/{cleanup_name}. "
                f"primary error: {primary_error!r}; rollback error: {cleanup_error!r}"
            ) from cleanup_error
        raise
    finally:
        for fd in frozen_file_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        if snapshot_fd is not None:
            os.close(snapshot_fd)
        if inputs_fd is not None:
            os.close(inputs_fd)
        if legal_fd is not None:
            os.close(legal_fd)
        os.close(root_fd)


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
