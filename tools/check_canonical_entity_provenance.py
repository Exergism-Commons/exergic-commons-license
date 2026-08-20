#!/usr/bin/env python3
"""Fail closed on canonical migration State-provenance mismatches."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def main() -> int:
    errors: list[str] = []
    manifests = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )
    if not manifests:
        errors.append("no canonical entity dossier migration manifests found")

    for path in manifests:
        manifest = load_json(path)
        for row in manifest.get("entities", []):
            entity_id = row.get("id", "<missing-id>")
            state = row.get("state")
            source = row.get("sourceDossier")
            if not isinstance(state, str) or not state:
                errors.append(f"{path.relative_to(ROOT)}: {entity_id}: missing state")
                continue
            expected = Path("dossiers/states") / f"{state}.md"
            if source != expected.as_posix():
                errors.append(
                    f"{path.relative_to(ROOT)}: {entity_id}: sourceDossier {source!r} "
                    f"!= State provenance {expected.as_posix()!r}"
                )
                continue
            source_path = ROOT / expected
            if not source_path.is_file():
                errors.append(f"{path.relative_to(ROOT)}: {entity_id}: missing sourceDossier {expected}")
                continue
            fm = frontmatter(source_path.read_text(encoding="utf-8"))
            if fm.get("iso3") != state:
                errors.append(
                    f"{path.relative_to(ROOT)}: {entity_id}: source dossier iso3 "
                    f"{fm.get('iso3')!r} != manifest state {state!r}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"canonical entity provenance: OK ({len(manifests)} manifests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
