#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one replacement site, found {count}")
    return text.replace(old, new, 1)


def patch_coverage() -> None:
    path = ROOT / "tools/check_canonical_entity_dossiers.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'EVIDENCE_IMAGE_DIR = ROOT / "dossiers/evidence-images"\n',
        'EVIDENCE_IMAGE_DIR = ROOT / "dossiers/evidence-images"\nSUPERSESSIONS_PATH = ROOT / "knowledge/generated/entity-id-supersessions-v1.json"\n',
        "coverage supersessions constant",
    )
    helper = '''\n\ndef load_supersessions(path: Path = SUPERSESSIONS_PATH) -> tuple[dict[str, str], list[str]]:\n    """Load direct identity supersessions used to reconcile immutable historical manifests."""\n    if not path.is_file():\n        return {}, []\n    try:\n        payload = load_json(path)\n    except (OSError, json.JSONDecodeError) as exc:\n        return {}, [f"{path.relative_to(ROOT)}: cannot load supersessions: {exc}"]\n    rows = payload.get("supersessions")\n    if not isinstance(rows, list):\n        return {}, [f"{path.relative_to(ROOT)}: supersessions must be a list"]\n    mapping: dict[str, str] = {}\n    errors: list[str] = []\n    for index, row in enumerate(rows):\n        if not isinstance(row, dict):\n            errors.append(f"{path.relative_to(ROOT)}: supersession row {index} must be an object")\n            continue\n        source, target = row.get("from"), row.get("to")\n        if not isinstance(source, str) or not source or not isinstance(target, str) or not target:\n            errors.append(f"{path.relative_to(ROOT)}: supersession row {index} requires non-empty from/to ids")\n            continue\n        if source == target:\n            errors.append(f"{path.relative_to(ROOT)}: self-supersession is forbidden for {source}")\n            continue\n        if source in mapping:\n            errors.append(f"{path.relative_to(ROOT)}: duplicate supersession source {source}")\n            continue\n        mapping[source] = target\n    return mapping, errors\n'''
    text = replace_once(
        text,
        'def manifest_paths(manifest_dir: Path) -> list[Path]:\n',
        helper + '\n\ndef manifest_paths(manifest_dir: Path) -> list[Path]:\n',
        "coverage helper insertion",
    )
    text = replace_once(
        text,
        '    if len(missing) > max_missing:\n        errors.append(f"dedicated-dossier ratchet regressed: {len(missing)} missing > allowed {max_missing}")\n    migrated_ids: set[str] = set()\n',
        '    if len(missing) > max_missing:\n        errors.append(f"dedicated-dossier ratchet regressed: {len(missing)} missing > allowed {max_missing}")\n    supersessions, supersession_errors = load_supersessions()\n    errors.extend(supersession_errors)\n    for source, target in sorted(supersessions.items()):\n        if target in supersessions:\n            errors.append(f"{SUPERSESSIONS_PATH.relative_to(ROOT)}: supersession must resolve in one hop: {source} -> {target}")\n        if target not in entities:\n            errors.append(f"{SUPERSESSIONS_PATH.relative_to(ROOT)}: supersession target is not a current ABox identity: {source} -> {target}")\n    migrated_ids: set[str] = set()\n',
        "coverage supersession validation",
    )
    old = '''            if entity_id not in entities:\n                errors.append(f"{path.relative_to(ROOT)}: manifest entity missing: {entity_id}")\n                continue\n            entity, entity_file = entities[entity_id]\n            if entity.get("type") != row["type"]:\n                errors.append(f"{entity_id}: type mismatch")\n            if entity.get("name") != row["name"]:\n                errors.append(f"{entity_id}: name mismatch")\n            good, rel = is_dedicated(entity, entity_file)\n            expected_rel = Path(row["dossier"])\n            if not good:\n                errors.append(f"{entity_id}: does not point to an existing dedicated dossier")\n                continue\n            if rel != expected_rel:\n                errors.append(f"{entity_id}: dossier path {rel} != manifest {expected_rel}")\n            dossier_path = ROOT / expected_rel\n            text = dossier_path.read_text(encoding="utf-8")\n'''
    new = '''            expected_rel = Path(row["dossier"])\n            entity_entry = entities.get(entity_id)\n            if entity_entry is None:\n                target_id = supersessions.get(entity_id)\n                if target_id is None:\n                    errors.append(f"{path.relative_to(ROOT)}: manifest entity missing: {entity_id}")\n                    continue\n                target_entry = entities.get(target_id)\n                if target_entry is None:\n                    errors.append(f"{path.relative_to(ROOT)}: superseded manifest entity {entity_id} has missing target {target_id}")\n                    continue\n                target_entity, _target_file = target_entry\n                if target_entity.get("type") != row["type"]:\n                    errors.append(f"{entity_id}: supersession target {target_id} type mismatch")\n                expected_dir = TYPE_DIR.get(row["type"])\n                parts = expected_rel.parts\n                if (\n                    expected_dir is None\n                    or len(parts) < 3\n                    or parts[0] != "dossiers"\n                    or parts[1] != expected_dir\n                    or expected_rel.suffix != ".md"\n                    or not (ROOT / expected_rel).is_file()\n                ):\n                    errors.append(\n                        f"{path.relative_to(ROOT)}: superseded historical row {entity_id} does not retain an existing type-appropriate dossier"\n                    )\n                    continue\n            else:\n                entity, entity_file = entity_entry\n                if entity.get("type") != row["type"]:\n                    errors.append(f"{entity_id}: type mismatch")\n                if entity.get("name") != row["name"]:\n                    errors.append(f"{entity_id}: name mismatch")\n                good, rel = is_dedicated(entity, entity_file)\n                if not good:\n                    errors.append(f"{entity_id}: does not point to an existing dedicated dossier")\n                    continue\n                if rel != expected_rel:\n                    errors.append(f"{entity_id}: dossier path {rel} != manifest {expected_rel}")\n            dossier_path = ROOT / expected_rel\n            if not dossier_path.is_file():\n                errors.append(f"{entity_id}: manifest dossier does not exist: {expected_rel}")\n                continue\n            text = dossier_path.read_text(encoding="utf-8")\n'''
    text = replace_once(text, old, new, "coverage manifest binding")
    path.write_text(text, encoding="utf-8")


def patch_preservation() -> None:
    path = ROOT / "tools/check_canonical_entity_migration_preservation.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'ENTITY_REL_DIR = Path("knowledge/entities")\n',
        'ENTITY_REL_DIR = Path("knowledge/entities")\nSUPERSESSIONS_REL = Path("knowledge/generated/entity-id-supersessions-v1.json")\n',
        "preservation supersessions constant",
    )
    helper = '''\n\ndef current_supersession_map(root: Path = ROOT) -> dict[str, str]:\n    """Return direct current supersessions; chains/dangling targets fail closed in callers."""\n    path = root / SUPERSESSIONS_REL\n    if not path.is_file():\n        return {}\n    payload = load_json(path)\n    rows = payload.get("supersessions")\n    if not isinstance(rows, list):\n        raise RuntimeError(f"{SUPERSESSIONS_REL}: supersessions must be a list")\n    mapping: dict[str, str] = {}\n    for index, row in enumerate(rows):\n        if not isinstance(row, dict):\n            raise RuntimeError(f"{SUPERSESSIONS_REL}: supersession row {index} must be an object")\n        source, target = row.get("from"), row.get("to")\n        if not isinstance(source, str) or not source or not isinstance(target, str) or not target:\n            raise RuntimeError(f"{SUPERSESSIONS_REL}: supersession row {index} requires non-empty from/to ids")\n        if source == target or source in mapping:\n            raise RuntimeError(f"{SUPERSESSIONS_REL}: invalid/duplicate supersession source {source!r}")\n        mapping[source] = target\n    for source, target in mapping.items():\n        if target in mapping:\n            raise RuntimeError(f"{SUPERSESSIONS_REL}: supersession must resolve in one hop: {source} -> {target}")\n    return mapping\n'''
    text = replace_once(
        text,
        'def git_show(ref: str, rel: str, root: Path = ROOT) -> str | None:\n',
        helper + '\n\ndef git_show(ref: str, rel: str, root: Path = ROOT) -> str | None:\n',
        "preservation helper insertion",
    )
    text = replace_once(
        text,
        '        historical_ids = base_migrated_ids(base_ref, root)\n        current_entities = current_entity_index(root)\n        base_entities = base_entity_index(base_ref, root)\n',
        '        historical_ids = base_migrated_ids(base_ref, root)\n        current_entities = current_entity_index(root)\n        base_entities = base_entity_index(base_ref, root)\n        supersessions = current_supersession_map(root)\n',
        "preservation load supersessions",
    )
    old = '''            newly_migrated.add(entity_id)\n            current_entry = current_entities.get(entity_id)\n            if current_entry is None:\n                errors.append(f"{entity_id}: current ABox entity file is missing (.json/.jsonld)")\n                continue\n            after, after_rel = current_entry\n            before_entry = base_entities.get(entity_id)\n'''
    new = '''            current_entry = current_entities.get(entity_id)\n            if current_entry is None:\n                target_id = supersessions.get(entity_id)\n                if version <= FROZEN_FINAL_VERSION and target_id is not None:\n                    current_target = current_entities.get(target_id)\n                    base_target = base_entities.get(target_id)\n                    if current_target is None:\n                        errors.append(f"{entity_id}: supersession target {target_id} is missing from current ABox")\n                    elif base_target is None:\n                        errors.append(\n                            f"{entity_id}: historical supersession target {target_id} did not exist at comparison base {base_ref}"\n                        )\n                    elif current_target[0].get("type") != row.get("type") or base_target[0].get("type") != row.get("type"):\n                        errors.append(f"{entity_id}: supersession target {target_id} does not preserve manifest type {row.get('type')!r}")\n                    continue\n                newly_migrated.add(entity_id)\n                errors.append(f"{entity_id}: current ABox entity file is missing (.json/.jsonld)")\n                continue\n            newly_migrated.add(entity_id)\n            after, after_rel = current_entry\n            before_entry = base_entities.get(entity_id)\n'''
    text = replace_once(text, old, new, "preservation superseded historical row")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_coverage()
    patch_preservation()
    print("patched canonical coverage and migration preservation for direct historical supersessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
