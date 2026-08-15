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
REVIEWED_MECHANISM_ARTIFACTS = {
    "review_spec": "spec/LEGAL-ADVERSARIAL-REVIEW.md",
    "incorporation_spec": "spec/VERSIONING.md",
    "bundle_schema": "schemas/bundle.schema.json",
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


def validate_file_reference(
    root: Path, component: dict[str, Any], *, label: str
) -> Path:
    raw_path = component.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError(f"{label} is missing path")
    path = root / raw_path
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    expected = component.get("sha256")
    if not isinstance(expected, str) or not expected:
        raise ValueError(f"{label} is missing sha256")
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return path


def validate_component(root: Path, component: dict[str, Any]) -> None:
    validate_file_reference(root, component, label="bundle component")


def validate_reviewed_mechanism_artifact(
    root: Path, record: dict[str, Any], key: str, expected_path: str
) -> None:
    component = record.get(key)
    if not isinstance(component, dict):
        raise ValueError(f"legal review record is missing immutable {key}")
    if component.get("path") != expected_path:
        raise ValueError(
            f"legal review {key} must bind exact repository artifact {expected_path}"
        )
    validate_file_reference(root, component, label=f"legal review {key}")


def validate_legal_review(root: Path, bundle: dict[str, Any]) -> None:
    """Validate the machine-verifiable release-gate attestation.

    This deliberately does not attempt to decide whether a reviewer is legally
    qualified or whether the recorded legal conclusions are correct. Those are
    human review obligations defined by spec/LEGAL-ADVERSARIAL-REVIEW.md.
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
    if not isinstance(review_id, str) or not review_id:
        raise ValueError("legal review record is missing review_id")
    if component.get("ref") != review_id:
        raise ValueError("bundle legal_review ref does not match legal review record review_id")

    license_component = bundle.get("license")
    if not isinstance(license_component, dict):
        raise ValueError("bundle license component is invalid")
    expected_license_sha = license_component.get("sha256")
    if record.get("license_sha256") != expected_license_sha:
        raise ValueError("legal review record does not bind exact bundle license SHA-256")

    for key, expected_path in REVIEWED_MECHANISM_ARTIFACTS.items():
        validate_reviewed_mechanism_artifact(root, record, key, expected_path)

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
    bundle = load_json(root / "releases" / "bundles" / f"{bundle_ref}.json")
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
