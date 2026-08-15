#!/usr/bin/env python3
"""Resolve an ECL publisher policy to an exact immutable bundle manifest.

This is release tooling, not a licensing oracle. It refuses non-operative
channels by default and never changes an already published lock automatically.
For an operative bundle it verifies the integrity and machine-readable state of
the immutable legal-review record; it does not evaluate legal competence or the
substantive correctness of that review.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_JURISDICTIONS = {
    "eu_software",
    "spain",
    "united_states",
    "united_kingdom",
    "cross_border",
}
REQUIRED_ATTACK_SURFACES = {f"LAR-{number:02d}" for number in range(1, 17)}
COMPLETE_DISPOSITIONS = {"resolved", "accepted-risk", "not-applicable"}
REVIEWED_MECHANISM_FILENAMES = {
    "review_spec": "LEGAL-ADVERSARIAL-REVIEW.md",
    "incorporation_spec": "VERSIONING.md",
    "bundle_schema": "bundle.schema.json",
}
REVIEW_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
CANONICAL_EMPTY_BUNDLES: dict[str, dict[str, Any]] = {
    "ECL-0.3-DRAFT@RP-EMPTY-1": {
        "operative": False,
        "license": {
            "ref": "ECL-0.3-DRAFT",
            "path": "versions/licenses/ECL-0.3-DRAFT.md",
            "sha256": "347a39d2e0b2a0df5bbe6c8b4bb0cc97b34f4866061d6be8522fe5f5578eb50d",
        },
        "schedule": {
            "ref": "ECL-RP-EMPTY-1",
            "path": "schedules/ECL-RP-EMPTY-1.md",
            "sha256": "e12a6ffc03aa0be24a9f61d0d325bc8c06bb9c870416a72fcac0bfd968025aa2",
        },
    }
}
RESERVED_FALLBACK_IDENTITIES: dict[str, set[str]] = {
    key: {
        registered[component_name][key]
        for registered in CANONICAL_EMPTY_BUNDLES.values()
        for component_name in ("license", "schedule")
    }
    for key in ("ref", "path", "sha256")
}


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError("policy must be a TOML table")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def major_from_constraint(value: str) -> int | None:
    if value == "latest":
        return None
    if value.endswith(".x") and value[:-2].isdigit():
        return int(value[:-2])
    return None


def valid_review_id(value: str) -> bool:
    return REVIEW_ID_RE.fullmatch(value) is not None


def _uses_reserved_fallback_identity(actual: Any) -> bool:
    if not isinstance(actual, dict):
        return False
    return any(
        actual.get(key) in RESERVED_FALLBACK_IDENTITIES[key]
        for key in ("ref", "path", "sha256")
    )


def validate_bundle_identity(bundle: dict[str, Any]) -> None:
    """Enforce semantic identity for canonical empty-Schedule fallback Bundles.

    Empty fallback identities are intentionally opt-in rather than generative.
    Their identifiers and every reserved component identity are a single
    indivisible namespace: no reserved ref, path, or hash may be borrowed in
    either the License or Schedule slot of an ordinary Bundle. A new fallback is
    invalid until its exact state is registered here and in the Bundle schema.
    """

    bundle_ref = bundle.get("bundle")
    if not isinstance(bundle_ref, str):
        raise ValueError("bundle manifest is missing string bundle identity")

    expected = CANONICAL_EMPTY_BUNDLES.get(bundle_ref)
    if expected is not None:
        if bundle.get("operative") is not expected["operative"]:
            raise ValueError(
                f"canonical empty fallback {bundle_ref} has invalid operative state"
            )
        for component_name in ("license", "schedule"):
            actual_component = bundle.get(component_name)
            expected_component = expected[component_name]
            if actual_component != expected_component:
                raise ValueError(
                    f"canonical empty fallback {bundle_ref} has mismatched "
                    f"{component_name} identity"
                )
        return

    if "@RP-EMPTY-" in bundle_ref:
        raise ValueError(f"unsupported canonical empty fallback bundle: {bundle_ref}")

    for component_name in ("license", "schedule"):
        if _uses_reserved_fallback_identity(bundle.get(component_name)):
            raise ValueError(
                f"bundle {bundle_ref} uses reserved canonical empty fallback "
                f"identity in {component_name} slot"
            )


def validate_file_reference(
    root: Path, component: dict[str, Any], *, label: str
) -> Path:
    raw_path = component.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{label} is missing path")
    if "\\" in raw_path or raw_path.startswith("/"):
        raise ValueError(f"{label} path must be a repository-relative POSIX path")

    segments = raw_path.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError(f"{label} path contains an unsafe path segment")

    try:
        resolved_root = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"repository root does not exist: {root}") from exc

    path = root
    for segment in segments:
        path = path / segment
        if path.is_symlink():
            raise ValueError(f"{label} must not traverse symbolic links: {path}")

    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")

    try:
        resolved_path = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"missing {label}: {path}") from exc
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError(f"{label} resolves outside repository root: {path}")
    if not resolved_path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")

    expected = component.get("sha256")
    if not isinstance(expected, str) or not expected:
        raise ValueError(f"{label} is missing sha256")
    if sha256(resolved_path) != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return resolved_path


def validate_component(root: Path, component: dict[str, Any]) -> None:
    validate_file_reference(root, component, label="bundle component")


def validate_frozen_review_input(
    root: Path,
    record: dict[str, Any],
    *,
    review_id: str,
    key: str,
    filename: str,
) -> None:
    component = record.get(key)
    if not isinstance(component, dict):
        raise ValueError(f"legal review record is missing immutable {key}")
    expected_path = f"reviews/legal/inputs/{review_id}/{filename}"
    if component.get("path") != expected_path:
        raise ValueError(
            f"legal review {key} must bind frozen review input {expected_path}"
        )
    validate_file_reference(root, component, label=f"frozen legal review {key}")


def validate_legal_review(root: Path, bundle: dict[str, Any]) -> None:
    """Validate the machine-verifiable release-gate attestation.

    This deliberately does not attempt to decide whether a reviewer is legally
    qualified or whether the recorded legal conclusions are correct. Those are
    human review obligations defined by spec/LEGAL-ADVERSARIAL-REVIEW.md.

    Review-spec/versioning/schema inputs are validated against frozen per-review
    snapshots, never against later mutable canonical files. This preserves the
    validity of historical Bundles when the project evolves after release.
    """

    if not bundle.get("operative"):
        return

    component = bundle.get("legal_review")
    if not isinstance(component, dict):
        raise ValueError("operative bundle requires immutable legal_review component")
    review_path = validate_file_reference(root, component, label="legal review record")
    record = load_json(review_path)

    if record.get("schema_version") != 1:
        raise ValueError("unsupported legal review record schema_version")
    if record.get("status") != "complete":
        raise ValueError("operative bundle requires completed legal review record")

    review_id = record.get("review_id")
    if not isinstance(review_id, str) or not valid_review_id(review_id):
        raise ValueError("legal review record has invalid review_id")
    if component.get("ref") != review_id:
        raise ValueError("bundle legal_review ref does not match legal review record review_id")
    expected_record_path = f"reviews/legal/records/{review_id}.json"
    if component.get("path") != expected_record_path:
        raise ValueError(
            f"bundle legal_review path must match immutable record path {expected_record_path}"
        )

    license_component = bundle.get("license")
    if not isinstance(license_component, dict):
        raise ValueError("bundle license component is invalid")
    expected_license_sha = license_component.get("sha256")
    if record.get("license_sha256") != expected_license_sha:
        raise ValueError("legal review record does not bind exact bundle license SHA-256")

    for key, filename in REVIEWED_MECHANISM_FILENAMES.items():
        validate_frozen_review_input(
            root, record, review_id=review_id, key=key, filename=filename
        )

    jurisdictions = record.get("jurisdictions")
    if not isinstance(jurisdictions, dict):
        raise ValueError("legal review record is missing jurisdiction matrix")
    missing_jurisdictions = REQUIRED_JURISDICTIONS - jurisdictions.keys()
    incomplete_jurisdictions = {
        name
        for name in REQUIRED_JURISDICTIONS
        if jurisdictions.get(name) != "complete"
    }
    if missing_jurisdictions or incomplete_jurisdictions:
        failed = sorted(missing_jurisdictions | incomplete_jurisdictions)
        raise ValueError(f"legal review jurisdiction coverage incomplete: {', '.join(failed)}")

    surfaces = record.get("attack_surfaces")
    if not isinstance(surfaces, dict):
        raise ValueError("legal review record is missing attack-surface dispositions")
    missing_surfaces = REQUIRED_ATTACK_SURFACES - surfaces.keys()
    incomplete_surfaces = {
        name
        for name in REQUIRED_ATTACK_SURFACES
        if surfaces.get(name) not in COMPLETE_DISPOSITIONS
    }
    if missing_surfaces or incomplete_surfaces:
        failed = sorted(missing_surfaces | incomplete_surfaces)
        raise ValueError(f"legal review attack surfaces incomplete: {', '.join(failed)}")

    independent = record.get("qualified_independent_reviews")
    adversarial = record.get("qualified_adversarial_reviews")
    if not isinstance(independent, int) or isinstance(independent, bool) or independent < 2:
        raise ValueError("legal review requires at least two qualified independent reviews")
    if not isinstance(adversarial, int) or isinstance(adversarial, bool) or adversarial < 1:
        raise ValueError("legal review requires at least one qualified adversarial review")
    if adversarial > independent:
        raise ValueError("qualified adversarial review count exceeds independent review count")

    for key, label in (
        ("unresolved_blockers", "unresolved BLOCKER findings"),
        ("unresolved_majors", "unresolved MAJOR findings"),
        ("undispositioned_material_findings", "undispositioned material findings"),
    ):
        if record.get(key) != 0:
            raise ValueError(f"legal review has {label}")

    if record.get("delta_review_complete") is not True:
        raise ValueError("required legal delta review is incomplete")


def validate_bundle_components(root: Path, bundle: dict[str, Any]) -> None:
    validate_bundle_identity(bundle)
    license_component = bundle.get("license")
    schedule_component = bundle.get("schedule")
    if not isinstance(license_component, dict) or not isinstance(schedule_component, dict):
        raise ValueError("bundle requires license and schedule components")
    validate_component(root, license_component)
    validate_component(root, schedule_component)
    validate_legal_review(root, bundle)


def resolve_follow(policy: dict[str, Any], root: Path, allow_draft: bool) -> dict[str, Any]:
    channel_name = policy.get("channel")
    if not isinstance(channel_name, str) or not channel_name:
        raise ValueError("follow mode requires channel")
    channel = load_json(root / "channels" / f"{channel_name}.json")
    if not channel.get("operative") and not allow_draft:
        raise ValueError(f"channel {channel_name!r} is non-operative/draft")
    bundle_ref = channel.get("bundle")
    if not isinstance(bundle_ref, str) or not bundle_ref:
        raise ValueError(f"channel {channel_name!r} does not resolve an immutable bundle")
    path = root / "releases" / "bundles" / f"{bundle_ref}.json"
    bundle = load_json(path)
    if bundle.get("bundle") != bundle_ref:
        raise ValueError(f"bundle manifest identity mismatch in {path}")
    if not bundle.get("operative") and not allow_draft:
        raise ValueError(f"bundle {bundle_ref!r} is non-operative/draft")

    requested = policy.get("license", "latest")
    requested_major = major_from_constraint(str(requested))
    actual_ref = str(bundle["license"]["ref"])
    actual_version = actual_ref.removeprefix("ECL-")
    try:
        actual_major = int(actual_version.split(".", 1)[0])
    except ValueError as exc:
        raise ValueError(f"invalid license ref in bundle: {actual_ref}") from exc
    if requested_major is not None and requested_major != actual_major:
        raise ValueError(
            f"channel resolves ECL major {actual_major}, policy requires {requested_major}.x"
        )
    validate_bundle_components(root, bundle)
    return bundle


def resolve_pinned(policy: dict[str, Any], root: Path, allow_draft: bool) -> dict[str, Any]:
    bundle_ref = policy.get("bundle")
    if not isinstance(bundle_ref, str) or not bundle_ref:
        raise ValueError("pinned mode requires bundle")
    path = root / "releases" / "bundles" / f"{bundle_ref}.json"
    bundle = load_json(path)
    if bundle.get("bundle") != bundle_ref:
        raise ValueError(f"bundle manifest identity mismatch in {path}")
    if not bundle.get("operative") and not allow_draft:
        raise ValueError(f"bundle {bundle_ref!r} is non-operative/draft")
    validate_bundle_components(root, bundle)
    return bundle


def render_lock(bundle: dict[str, Any]) -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    license_part = bundle["license"]
    schedule_part = bundle["schedule"]
    operative = bool(bundle.get("operative"))
    lines = [
        f'bundle = "{bundle["bundle"]}"',
        f"operative = {'true' if operative else 'false'}",
        f'license = "{license_part["ref"]}"',
        f'license_sha256 = "{license_part["sha256"]}"',
        f'schedule = "{schedule_part["ref"]}"',
        f'schedule_sha256 = "{schedule_part["sha256"]}"',
    ]
    legal_review = bundle.get("legal_review")
    if isinstance(legal_review, dict):
        lines.extend(
            [
                f'legal_review = "{legal_review["ref"]}"',
                f'legal_review_sha256 = "{legal_review["sha256"]}"',
            ]
        )
    lines.extend([f'resolved_at = "{now}"', ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("ecl.lock"))
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()

    try:
        policy = load_toml(args.policy)
        mode = policy.get("mode")
        if mode == "pinned":
            bundle = resolve_pinned(policy, args.repo_root, args.allow_draft)
        elif mode in {"follow-stable", "latest-stable"}:
            bundle = resolve_follow(policy, args.repo_root, args.allow_draft)
        else:
            raise ValueError("mode must be pinned, follow-stable or latest-stable")
        args.output.write_text(render_lock(bundle), encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"resolved {bundle['bundle']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())