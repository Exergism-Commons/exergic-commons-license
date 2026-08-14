#!/usr/bin/env python3
"""Resolve an ECL publisher policy to an exact immutable bundle manifest.

This is release tooling, not a licensing oracle. It refuses non-operative
channels by default and never changes an already published lock automatically.
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


def validate_component(root: Path, component: dict[str, Any]) -> None:
    path = root / str(component["path"])
    if not path.is_file():
        raise ValueError(f"missing bundle component: {path}")
    expected = component.get("sha256")
    if expected and sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")


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
    validate_component(root, bundle["license"])
    validate_component(root, bundle["schedule"])
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
    validate_component(root, bundle["license"])
    validate_component(root, bundle["schedule"])
    return bundle


def render_lock(bundle: dict[str, Any]) -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    license_part = bundle["license"]
    schedule_part = bundle["schedule"]
    return "\n".join(
        [
            f'bundle = "{bundle["bundle"]}"',
            f'license = "{license_part["ref"]}"',
            f'license_sha256 = "{license_part["sha256"]}"',
            f'schedule = "{schedule_part["ref"]}"',
            f'schedule_sha256 = "{schedule_part["sha256"]}"',
            f'resolved_at = "{now}"',
            "",
        ]
    )


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
    except (OSError, json.JSONDecodeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"resolved {bundle['bundle']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
