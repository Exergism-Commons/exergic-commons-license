#!/usr/bin/env python3
"""Reject parser-ambiguous duplicate JSON members on canonical JSON surfaces."""
from __future__ import annotations

from pathlib import Path

import strict_json

ROOT = Path(__file__).resolve().parents[1]


def normative_paths(root: Path = ROOT) -> list[Path]:
    paths: set[Path] = set()
    for directory in ("knowledge", "schemas", "dossiers/evidence-images"):
        base = root / directory
        if base.exists():
            paths.update(
                path for path in base.rglob("*")
                if path.is_file() and path.suffix.lower() in {".json", ".jsonld"}
            )
    context = root / "ontology/ecl-context.jsonld"
    if context.is_file():
        paths.add(context)
    return sorted(paths)


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for path in normative_paths(root):
        try:
            strict_json.load(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"canonical strict JSON: FAILED ({len(errors)} error(s))")
        return 1
    print(f"canonical strict JSON: OK ({len(normative_paths())} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
