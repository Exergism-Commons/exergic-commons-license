#!/usr/bin/env python3
"""Assert that rendered Schedule compatibility text matches the registry state."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "schedule-license-compatibility.yml"
TARGET_LICENSE_ARTIFACT = ROOT / "versions" / "licenses" / "ECL-0.3-DRAFT.md"


def load_registry() -> dict[str, Any]:
    value = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError("Schedule compatibility registry must be a mapping")
    return value


def validate_rendered_state(text: str, registry: dict[str, Any]) -> None:
    target = registry.get("target_license")
    status = registry.get("status")
    if not isinstance(target, str) or not target:
        raise ValueError("Schedule compatibility registry requires target_license")
    artifact = registry.get("target_license_artifact")
    if not isinstance(artifact, dict):
        raise ValueError("Schedule compatibility registry requires target_license_artifact")
    artifact_path = artifact.get("path")
    artifact_sha = artifact.get("sha256")
    if not isinstance(artifact_path, str) or not artifact_path:
        raise ValueError("Schedule compatibility registry target artifact requires path")
    if not isinstance(artifact_sha, str) or len(artifact_sha) != 64:
        raise ValueError("Schedule compatibility registry target artifact requires sha256")

    exact_artifact_line = f"Exact target License artifact: **{artifact_path}** (`{artifact_sha}`)."
    if exact_artifact_line not in text:
        raise ValueError("rendered Schedule does not identify the exact target License artifact")

    pending_marker = f"Compatibility status: **NOT YET VALIDATED for {target}**."
    ready_marker = f"Intended compatibility: **{target} only**."

    if status == "pending":
        if f"Target working License: **{target}**." not in text:
            raise ValueError("pending rendered Schedule omits target working License")
        if pending_marker not in text:
            raise ValueError("pending rendered Schedule omits NOT YET VALIDATED marker")
        if ready_marker in text:
            raise ValueError("pending rendered Schedule falsely advertises completed compatibility")
        if "compatibility revalidation: **PENDING**" not in text:
            raise ValueError("pending rendered Schedule omits compatibility-review state")
        return

    if status == "complete":
        if ready_marker not in text:
            raise ValueError("complete rendered Schedule omits intended compatibility marker")
        if pending_marker in text or "compatibility revalidation: **PENDING**" in text:
            raise ValueError("complete rendered Schedule still advertises pending compatibility")
        if "compatibility revalidation complete and SHA-256-bound" not in text:
            raise ValueError("complete rendered Schedule omits immutable evidence marker")
        return

    raise ValueError("Schedule compatibility registry status must be pending or complete")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    text = args.artifact.read_text(encoding="utf-8")
    validate_rendered_state(text, load_registry())
    print("rendered Schedule compatibility state matches registry semantics")


if __name__ == "__main__":
    main()
