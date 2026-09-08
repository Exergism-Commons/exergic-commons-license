#!/usr/bin/env python3
"""Reject duplicate mapping keys in every curated State Schedule-freeze YAML file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "registry" / "schedule-state-s-freezes"


class UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that fails instead of silently overwriting mapping keys."""

    def construct_mapping(self, node: MappingNode, deep: bool = False):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None, f"expected a mapping node, got {node.id}", node.start_mark)
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found unhashable mapping key {key!r}",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate mapping key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def checked_files() -> list[Path]:
    return sorted({*FREEZE_DIR.glob("*.yml"), *FREEZE_DIR.glob("*.yaml")})


def strict_load(text: str):
    return yaml.load(text, Loader=UniqueKeySafeLoader)


def validate() -> list[dict]:
    failures: list[dict] = []
    for path in checked_files():
        try:
            strict_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            failures.append({"file": str(path.relative_to(ROOT)), "reason": str(exc)})
    return failures


def self_test() -> None:
    assert strict_load("state: AAA\noutcome: S\n") == {"state": "AAA", "outcome": "S"}
    for text in (
        "state: AAA\nstate: BBB\n",
        "record:\n  actor: Alpha\n  actor: Beta\n",
        "records:\n  - state: AAA\n    candidate_party: Alpha\n    candidate_party: Beta\n",
    ):
        try:
            strict_load(text)
        except ConstructorError:
            pass
        else:
            raise AssertionError(f"duplicate YAML key was not rejected: {text!r}")
    print("Schedule YAML duplicate-key integrity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = validate()
    if failures:
        print("SCHEDULE_YAML_DUPLICATE_KEY_ERRORS=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print(f"Schedule YAML duplicate-key integrity: OK ({len(checked_files())} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
