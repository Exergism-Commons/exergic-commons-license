#!/usr/bin/env python3
"""Build and verify a self-contained ECL redistribution identity envelope.

This tool implements one strict, machine-verifiable way to satisfy the identity
side of ECL Section 4(c)-(d): ship exact License and Schedule bytes together
with an exact Bundle manifest and a local descriptor that binds all of them.

It is packaging/integrity tooling, not a legal-compliance oracle and not a legal
review. Section 4 also permits a demonstrably retrievable immutable
content-addressed Schedule reference in circumstances described by the License;
this tool intentionally does not attempt network retrieval or adjudicate that
alternative route.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import ecl_resolve  # noqa: E402

PROFILE = "ecl-self-contained-redistribution-v1"
DESCRIPTOR_NAME = "ECL-DISTRIBUTION.json"
BUNDLE_NAME = "ECL-BUNDLE.json"
LICENSE_NAME = "LICENSE"
SCHEDULE_NAME = "ECL-SCHEDULE"
NOTICE = (
    "PACKAGING INTEGRITY ONLY. Verification of this envelope does not constitute "
    "legal advice, a qualified legal review, or a determination of ECL compliance."
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)
BUNDLE_REF_RE = re.compile(
    r"^(?:ECL-[0-9]+\.[0-9]+\.[0-9]+@RP-[0-9]{4}\.[0-9]{2}\.[0-9]{2}"
    r"(?:\.[0-9]+)?|ECL-0\.3-DRAFT@RP-EMPTY-1)$"
)
LICENSE_REF_RE = re.compile(r"^(?:ECL-[0-9]+\.[0-9]+\.[0-9]+|ECL-0\.3-DRAFT)$")
SCHEDULE_REF_RE = re.compile(
    r"^ECL-RP-(?:[0-9]{4}\.[0-9]{2}\.[0-9]{2}(?:\.[0-9]+)?|EMPTY-1)$"
)
DESCRIPTOR_KEYS = {
    "schema_version",
    "profile",
    "bundle",
    "operative",
    "bundle_manifest",
    "license",
    "schedule",
    "notice",
}
BUNDLE_KEYS = {
    "schema_version",
    "bundle",
    "operative",
    "license",
    "schedule",
    "legal_review",
    "knowledge_snapshot",
    "released_at",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_existing_root(root: Path, *, label: str) -> Path:
    absolute = Path(os.path.abspath(root))
    try:
        resolved = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"missing {label}: {root}") from exc
    if absolute != resolved:
        raise ValueError(f"{label} must not traverse symbolic links: {root}")
    if not resolved.is_dir():
        raise ValueError(f"{label} must be a real directory: {root}")
    return resolved


def _require_schema_version_one(value: Any, *, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        raise ValueError(f"unsupported {label} schema_version")


def _validate_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _validate_rfc3339(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be an RFC3339 date-time string")
    normalized = value.replace("t", "T")
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} must be an RFC3339 date-time string") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include an RFC3339 timezone")
    return value


def _validate_local_component(
    value: Any,
    *,
    label: str,
    expected_path: str,
    ref_pattern: re.Pattern[str] | None = None,
) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"ref", "path", "sha256"}:
        raise ValueError(f"{label} must contain exactly ref, path and sha256")
    ref = value.get("ref")
    if not isinstance(ref, str) or not ref:
        raise ValueError(f"{label} ref must be a non-empty string")
    if ref_pattern is not None and ref_pattern.fullmatch(ref) is None:
        raise ValueError(f"{label} ref is not an immutable ECL release identifier: {ref}")
    if value.get("path") != expected_path:
        raise ValueError(f"{label} path must be exactly {expected_path}")
    _validate_sha256(value.get("sha256"), label=f"{label} sha256")
    return value


def _validate_manifest_locator(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise ValueError("bundle_manifest must contain exactly path and sha256")
    if value.get("path") != BUNDLE_NAME:
        raise ValueError(f"bundle_manifest path must be exactly {BUNDLE_NAME}")
    _validate_sha256(value.get("sha256"), label="bundle_manifest sha256")
    return value


def _validate_metadata_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} path must be a non-empty string")
    if "\\" in value or value.startswith("/"):
        raise ValueError(f"{label} path must be repository-relative POSIX metadata")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{label} path contains an unsafe segment")
    return value


def _validate_review_metadata(value: Any, *, required: bool) -> None:
    if value is None:
        if required:
            raise ValueError("operative bundle manifest requires immutable legal_review metadata")
        return
    if not isinstance(value, dict) or set(value) != {"ref", "path", "sha256"}:
        raise ValueError("bundle legal_review must contain exactly ref, path and sha256")
    review_ref = value.get("ref")
    if not isinstance(review_ref, str) or not ecl_resolve.valid_review_id(review_ref):
        raise ValueError("bundle legal_review ref must be a safe immutable review identifier")
    expected_path = f"reviews/legal/records/{review_ref}.json"
    if value.get("path") != expected_path:
        raise ValueError(f"bundle legal_review path must be exactly {expected_path}")
    _validate_sha256(value.get("sha256"), label="bundle legal_review sha256")


def _validate_optional_bundle_metadata(bundle: dict[str, Any]) -> None:
    if "knowledge_snapshot" in bundle:
        snapshot = bundle["knowledge_snapshot"]
        if snapshot is not None and not isinstance(snapshot, str):
            raise ValueError("bundle knowledge_snapshot must be a string or null")
    if "released_at" in bundle:
        _validate_rfc3339(bundle["released_at"], label="bundle released_at")


def _validate_bundle_manifest_shape(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise ValueError("ECL-BUNDLE.json must contain a JSON object")
    unknown = set(bundle) - BUNDLE_KEYS
    if unknown:
        raise ValueError(f"bundle manifest contains unsupported fields: {', '.join(sorted(unknown))}")
    for required in ("schema_version", "bundle", "operative", "license", "schedule"):
        if required not in bundle:
            raise ValueError(f"bundle manifest is missing {required}")
    _require_schema_version_one(bundle.get("schema_version"), label="bundle manifest")
    bundle_ref = bundle.get("bundle")
    if not isinstance(bundle_ref, str) or BUNDLE_REF_RE.fullmatch(bundle_ref) is None:
        raise ValueError("bundle manifest has invalid immutable bundle identifier")
    if not isinstance(bundle.get("operative"), bool):
        raise ValueError("bundle manifest operative must be boolean")

    for key, pattern in (("license", LICENSE_REF_RE), ("schedule", SCHEDULE_REF_RE)):
        component = bundle.get(key)
        if not isinstance(component, dict) or set(component) != {"ref", "path", "sha256"}:
            raise ValueError(f"bundle {key} must contain exactly ref, path and sha256")
        ref = component.get("ref")
        if not isinstance(ref, str) or pattern.fullmatch(ref) is None:
            raise ValueError(f"bundle {key} ref is not an immutable ECL release identifier")
        _validate_metadata_path(component.get("path"), label=f"bundle {key}")
        _validate_sha256(component.get("sha256"), label=f"bundle {key} sha256")

    _validate_review_metadata(bundle.get("legal_review"), required=bundle["operative"])
    _validate_optional_bundle_metadata(bundle)
    ecl_resolve.validate_bundle_identity(bundle)
    return bundle


def _read_static_file(root: Path, name: str, *, label: str) -> bytes:
    path = root / name
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link: {path}")
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} resolves outside distribution root: {path}")
    if not resolved.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")
    return resolved.read_bytes()


def _load_descriptor(root: Path) -> dict[str, Any]:
    raw = _read_static_file(root, DESCRIPTOR_NAME, label="distribution descriptor")
    data = ecl_resolve.parse_json_object(
        raw.decode("utf-8"), label="distribution descriptor"
    )
    if set(data) != DESCRIPTOR_KEYS:
        missing = sorted(DESCRIPTOR_KEYS - set(data))
        extra = sorted(set(data) - DESCRIPTOR_KEYS)
        detail = []
        if missing:
            detail.append(f"missing {', '.join(missing)}")
        if extra:
            detail.append(f"unsupported {', '.join(extra)}")
        raise ValueError(f"distribution descriptor fields invalid: {'; '.join(detail)}")
    _require_schema_version_one(data.get("schema_version"), label="distribution descriptor")
    if data.get("profile") != PROFILE:
        raise ValueError(f"distribution profile must be exactly {PROFILE}")
    if data.get("notice") != NOTICE:
        raise ValueError("distribution descriptor must preserve the packaging-only notice")
    bundle_ref = data.get("bundle")
    if not isinstance(bundle_ref, str) or BUNDLE_REF_RE.fullmatch(bundle_ref) is None:
        raise ValueError("distribution descriptor has invalid immutable bundle identifier")
    if not isinstance(data.get("operative"), bool):
        raise ValueError("distribution descriptor operative must be boolean")
    _validate_manifest_locator(data.get("bundle_manifest"))
    _validate_local_component(
        data.get("license"),
        label="distribution license",
        expected_path=LICENSE_NAME,
        ref_pattern=LICENSE_REF_RE,
    )
    _validate_local_component(
        data.get("schedule"),
        label="distribution schedule",
        expected_path=SCHEDULE_NAME,
        ref_pattern=SCHEDULE_REF_RE,
    )
    return data


def _verify_local_hash(root: Path, component: dict[str, str], *, label: str) -> bytes:
    path = ecl_resolve.validate_file_reference(root, component, label=label)
    data = path.read_bytes()
    if sha256_bytes(data) != component["sha256"]:
        raise ValueError(f"{label} changed while being verified: {path}")
    return data


def verify_distribution(root: Path) -> dict[str, Any]:
    """Verify one self-contained distribution envelope without repository state."""

    root = _canonical_existing_root(root, label="distribution root")
    descriptor = _load_descriptor(root)

    manifest_locator = descriptor["bundle_manifest"]
    manifest_bytes = _read_static_file(root, BUNDLE_NAME, label="bundle manifest")
    if sha256_bytes(manifest_bytes) != manifest_locator["sha256"]:
        raise ValueError("SHA-256 mismatch for ECL-BUNDLE.json")
    manifest = _validate_bundle_manifest_shape(
        ecl_resolve.parse_json_object(
            manifest_bytes.decode("utf-8"), label="ECL-BUNDLE.json"
        )
    )

    if manifest["bundle"] != descriptor["bundle"]:
        raise ValueError("distribution bundle identity does not match ECL-BUNDLE.json")
    if manifest["operative"] is not descriptor["operative"]:
        raise ValueError("distribution operative state does not match ECL-BUNDLE.json")

    for key in ("license", "schedule"):
        local_component = descriptor[key]
        source_component = manifest[key]
        if local_component["ref"] != source_component["ref"]:
            raise ValueError(f"distribution {key} ref does not match exact Bundle")
        if local_component["sha256"] != source_component["sha256"]:
            raise ValueError(f"distribution {key} SHA-256 does not match exact Bundle")
        _verify_local_hash(root, local_component, label=f"distributed {key}")

    return descriptor


def _safe_bundle_manifest_path(repo_root: Path, bundle_ref: str) -> Path:
    if BUNDLE_REF_RE.fullmatch(bundle_ref) is None:
        raise ValueError(f"invalid immutable ECL Bundle identifier: {bundle_ref}")
    path = repo_root
    for segment in ("releases", "bundles", f"{bundle_ref}.json"):
        path = path / segment
        if path.is_symlink():
            raise ValueError(f"Bundle manifest path must not traverse symbolic links: {path}")
    if not path.is_file():
        raise ValueError(f"missing immutable Bundle manifest: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(repo_root):
        raise ValueError(f"Bundle manifest resolves outside repository root: {path}")
    return resolved


def _prepare_output_root(output: Path) -> Path:
    if os.path.lexists(output):
        raise ValueError(f"distribution output already exists: {output}")
    parent = output.parent
    parent_resolved = _canonical_existing_root(parent, label="distribution output parent")
    name = output.name
    if name in {"", ".", ".."}:
        raise ValueError("distribution output must name a new directory")
    return parent_resolved / name


def _write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def build_distribution(
    repo_root: Path,
    *,
    bundle_ref: str,
    output: Path,
    allow_draft: bool = False,
) -> dict[str, Any]:
    """Materialize exact Bundle, License and Schedule bytes into a new envelope."""

    repo_root = _canonical_existing_root(repo_root, label="repository root")
    manifest_path = _safe_bundle_manifest_path(repo_root, bundle_ref)
    manifest_bytes = manifest_path.read_bytes()
    manifest = _validate_bundle_manifest_shape(
        ecl_resolve.parse_json_object(
            manifest_bytes.decode("utf-8"), label=str(manifest_path)
        )
    )
    if manifest["bundle"] != bundle_ref:
        raise ValueError("Bundle manifest identity does not match requested bundle")
    if not manifest["operative"] and not allow_draft:
        raise ValueError("refusing to package non-operative/draft Bundle without --allow-draft")

    # Source-repository validation includes exact component bytes and, for an
    # operative Bundle, the immutable completed legal-review gate record.
    ecl_resolve.validate_bundle_components(repo_root, manifest)
    license_path = ecl_resolve.validate_file_reference(
        repo_root, manifest["license"], label="source Bundle license"
    )
    schedule_path = ecl_resolve.validate_file_reference(
        repo_root, manifest["schedule"], label="source Bundle schedule"
    )
    license_bytes = license_path.read_bytes()
    schedule_bytes = schedule_path.read_bytes()
    if sha256_bytes(license_bytes) != manifest["license"]["sha256"]:
        raise ValueError("source License changed while preparing distribution")
    if sha256_bytes(schedule_bytes) != manifest["schedule"]["sha256"]:
        raise ValueError("source Schedule changed while preparing distribution")

    target = _prepare_output_root(output)
    descriptor: dict[str, Any] = {
        "schema_version": 1,
        "profile": PROFILE,
        "bundle": manifest["bundle"],
        "operative": manifest["operative"],
        "bundle_manifest": {
            "path": BUNDLE_NAME,
            "sha256": sha256_bytes(manifest_bytes),
        },
        "license": {
            "ref": manifest["license"]["ref"],
            "path": LICENSE_NAME,
            "sha256": manifest["license"]["sha256"],
        },
        "schedule": {
            "ref": manifest["schedule"]["ref"],
            "path": SCHEDULE_NAME,
            "sha256": manifest["schedule"]["sha256"],
        },
        "notice": NOTICE,
    }
    descriptor_bytes = (json.dumps(descriptor, indent=2, sort_keys=True) + "\n").encode("utf-8")

    target.mkdir(mode=0o755)
    try:
        _write_new(target / BUNDLE_NAME, manifest_bytes)
        _write_new(target / LICENSE_NAME, license_bytes)
        _write_new(target / SCHEDULE_NAME, schedule_bytes)
        # Publish the descriptor last: a crash before this point cannot look like
        # a complete self-contained profile to verify_distribution().
        _write_new(target / DESCRIPTOR_NAME, descriptor_bytes)
        verify_distribution(target)
    except Exception as primary:
        try:
            shutil.rmtree(target)
        except Exception as cleanup:
            raise OSError(
                "distribution build failed and cleanup also failed; "
                f"residual output may remain at {target}; "
                f"primary error: {primary!r}; cleanup error: {cleanup!r}"
            ) from cleanup
        raise
    return descriptor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="materialize a self-contained ECL envelope")
    build.add_argument("--repo-root", type=Path, default=Path("."))
    build.add_argument("--bundle", required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--allow-draft", action="store_true")

    verify = subparsers.add_parser("verify", help="verify a self-contained ECL envelope")
    verify.add_argument("--root", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "build":
            descriptor = build_distribution(
                args.repo_root,
                bundle_ref=args.bundle,
                output=args.output,
                allow_draft=args.allow_draft,
            )
            print(
                f"built {descriptor['bundle']} -> {args.output} "
                f"(operative={str(descriptor['operative']).lower()})"
            )
        else:
            descriptor = verify_distribution(args.root)
            print(
                f"verified self-contained ECL identity {descriptor['bundle']} "
                f"(operative={str(descriptor['operative']).lower()}); "
                "packaging integrity only, not legal compliance"
            )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
