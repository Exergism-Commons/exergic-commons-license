#!/usr/bin/env python3
"""Fail closed when canonical dossier visuals lack meaningful Markdown alt text."""
from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "knowledge/generated"
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
GENERIC_ALT_TEXT = {"state context", "evidence boundary", "image", "visual", "diagram"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_relative_visual(dossier: str, visual: str) -> str:
    dossier_dir = posixpath.dirname(dossier)
    return posixpath.relpath(visual, dossier_dir)


def main() -> int:
    errors: list[str] = []
    checked = 0
    manifests = sorted(
        MANIFEST_DIR.glob("canonical-entity-dossier-migration-v*.json"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )

    for manifest_path in manifests:
        manifest = load_json(manifest_path)
        for row in manifest.get("entities", []):
            entity_id = row.get("id", "<missing-id>")
            entity_name = row.get("name")
            dossier = row.get("dossier")
            visuals = row.get("visuals")
            if not isinstance(entity_name, str) or not entity_name:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: missing name")
                continue
            if not isinstance(dossier, str) or not dossier:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: missing dossier")
                continue
            if not isinstance(visuals, list) or not visuals:
                errors.append(f"{manifest_path.relative_to(ROOT)}: {entity_id}: missing visuals")
                continue

            dossier_path = ROOT / dossier
            if not dossier_path.is_file():
                errors.append(f"{dossier}: dossier does not exist")
                continue
            text = dossier_path.read_text(encoding="utf-8")
            images = [(alt.strip(), target.strip()) for alt, target in IMAGE_RE.findall(text)]

            for visual in visuals:
                if not isinstance(visual, str) or not visual:
                    errors.append(f"{dossier}: {entity_id}: invalid visual path {visual!r}")
                    continue
                expected_target = expected_relative_visual(dossier, visual)
                matches = [(alt, target) for alt, target in images if target == expected_target]
                if len(matches) != 1:
                    errors.append(
                        f"{dossier}: {entity_id}: expected exactly one Markdown image for "
                        f"{expected_target!r}, found {len(matches)}"
                    )
                    continue
                alt = matches[0][0]
                checked += 1
                if not alt:
                    errors.append(f"{dossier}: {entity_id}: empty alt text for {expected_target}")
                    continue
                if alt.casefold() in GENERIC_ALT_TEXT:
                    errors.append(
                        f"{dossier}: {entity_id}: generic alt text {alt!r} for {expected_target}"
                    )
                if entity_name.casefold() not in alt.casefold():
                    errors.append(
                        f"{dossier}: {entity_id}: alt text {alt!r} does not contain canonical "
                        f"entity name {entity_name!r}"
                    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "canonical dossier accessibility: OK "
        f"({checked} visual references with entity-specific Markdown alt text)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
