#!/usr/bin/env python3
"""Require the State-dossier review ratchet to remain a zero-backlog contract."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATCHET = ROOT / "knowledge" / "generated" / "state-dossier-review-ratchet.json"
TREE_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_KEYS = {
    "version", "date", "min_review_priority", "reviewed_state_dossier_tree", "reason", "semantics"
}


def validate_data(data: object) -> list[str]:
    failures: list[str] = []
    if not isinstance(data, dict):
        return ["ratchet must be a JSON object"]
    unexpected = sorted(set(data) - ALLOWED_KEYS)
    if unexpected:
        failures.append(f"unexpected ratchet keys: {unexpected}")
    if not isinstance(data.get("version"), int) or data["version"] < 1:
        failures.append("version must be a positive integer")
    if not isinstance(data.get("date"), str) or not data["date"].strip():
        failures.append("date must be a non-empty string")
    if data.get("min_review_priority") != 0:
        failures.append(
            "min_review_priority must remain exactly 0; raising it would weaken the zero-unreviewed ratchet"
        )
    tree = data.get("reviewed_state_dossier_tree")
    if not isinstance(tree, str) or not TREE_RE.fullmatch(tree):
        failures.append("reviewed_state_dossier_tree must be an exact 40-hex Git tree id")
    if not isinstance(data.get("reason"), str) or not data["reason"].strip():
        failures.append("reason must be a non-empty string")
    semantics = data.get("semantics")
    if not isinstance(semantics, list) or not semantics or not all(
        isinstance(item, str) and item.strip() for item in semantics
    ):
        failures.append("semantics must be a non-empty string list")
    return failures


def self_test() -> None:
    valid = {
        "version": 1,
        "date": "2026-08-23",
        "min_review_priority": 0,
        "reviewed_state_dossier_tree": "a" * 40,
        "reason": "zero backlog",
        "semantics": ["all candidates reviewed"],
    }
    assert validate_data(valid) == []
    weakened = {**valid, "min_review_priority": 10}
    assert any("exactly 0" in item for item in validate_data(weakened))
    extra = {**valid, "allow_unreviewed": True}
    assert any("unexpected ratchet keys" in item for item in validate_data(extra))
    print("State dossier zero-backlog ratchet self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    data = json.loads(RATCHET.read_text(encoding="utf-8"))
    failures = validate_data(data)
    if failures:
        print("INVALID_STATE_DOSSIER_RATCHET=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("State dossier review ratchet integrity: OK (zero-backlog threshold fixed at 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
