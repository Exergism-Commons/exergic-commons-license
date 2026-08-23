#!/usr/bin/env python3
"""Reject duplicate object keys in JSON surfaces used by the State entity audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DuplicateKeyError(ValueError):
    pass


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def checked_files() -> list[Path]:
    files = list((ROOT / "knowledge" / "entities").glob("*.json"))
    generated = ROOT / "knowledge" / "generated"
    patterns = (
        "state-dossier-entity-scaleout-v*.json",
        "state-dossier-prose-dispositions-v*.json",
        "state-dossier-review-ratchet.json",
        "entity-id-supersessions-v*.json",
        "schedule-reference-dispositions-v*.json",
    )
    for pattern in patterns:
        files.extend(generated.glob(pattern))
    return sorted(set(files))


def validate() -> list[dict]:
    failures: list[dict] = []
    for path in checked_files():
        try:
            json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
        except (json.JSONDecodeError, DuplicateKeyError) as exc:
            failures.append({"file": str(path.relative_to(ROOT)), "reason": str(exc)})
    return failures


def self_test() -> None:
    assert json.loads('{"a":1,"b":2}', object_pairs_hook=strict_pairs) == {"a": 1, "b": 2}
    try:
        json.loads('{"a":1,"a":2}', object_pairs_hook=strict_pairs)
    except DuplicateKeyError:
        pass
    else:
        raise AssertionError("duplicate JSON key was not rejected")
    print("JSON duplicate-key integrity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = validate()
    if failures:
        print("JSON_DUPLICATE_KEY_ERRORS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print(f"JSON duplicate-key integrity: OK ({len(checked_files())} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
