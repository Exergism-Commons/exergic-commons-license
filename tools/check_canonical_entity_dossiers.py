#!/usr/bin/env python3
# Validate canonical per-entity dossier coverage and visual-evidence invariants.

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTITY_DIR = ROOT / "knowledge/entities"
DEFAULT_MANIFEST_DIR = ROOT / "knowledge/generated"
DEFAULT_PALETTE = ROOT / "knowledge/generated/dossier-visual-palette-v1.json"
EVIDENCE_IMAGE_DIR = ROOT / "dossiers/evidence-images"
TYPE_DIR = {"Agency":"agencies","Institution":"institutions","Organization":"organizations","Person":"persons","Project":"projects"}
EXPECTED_PALETTE = {"R":"#B42318","S":"#E67E22","U":"#D4A017","N":"#2E7D32","UNKNOWN":"#667085"}
VALID_ENTITY_STATE_CONTEXTS = {"R", "S", "U", "N"}
REQUIRED_SECTIONS = ("## Identity scope","## State governance context","## Evidence record","## Attribution and exclusions","## Visual evidence","## Evidence gaps","## Sources","## Governance boundary")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_paths(manifest_dir: Path) -> list[Path]:
    paths = list(manifest_dir.glob("canonical-entity-dossier-migration-v*.json"))
    paths.sort(key=lambda p: int(p.stem.rsplit("v", 1)[1]))
    return paths


def repo_path_from_entity_ref(entity_file: Path, dossier_ref: str) -> Path:
    absolute = (entity_file.parent / dossier_ref).resolve()
    try:
        return absolute.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"dossier path escapes repository: {entity_file}: {dossier_ref}") from exc


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def is_dedicated(entity: dict, entity_file: Path) -> tuple[bool, Path | None]:
    expected_dir = TYPE_DIR.get(entity.get("type"))
    dossier_ref = entity.get("dossier")
    if not expected_dir or not dossier_ref:
        return False, None
    try:
        rel = repo_path_from_entity_ref(entity_file, dossier_ref)
    except ValueError:
        return False, None
    parts = rel.parts
    good = len(parts) >= 3 and parts[0] == "dossiers" and parts[1] == expected_dir and rel.suffix == ".md" and (ROOT / rel).is_file()
    return good, rel


def validate_svg(path: Path, required_text: list[str] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        return [f"{path.relative_to(ROOT)}: invalid SVG/XML: {exc}"]
    ns = "{http://www.w3.org/2000/svg}"
    if root.find(f"{ns}title") is None:
        errors.append(f"{path.relative_to(ROOT)}: missing <title>")
    if root.find(f"{ns}desc") is None:
        errors.append(f"{path.relative_to(ROOT)}: missing <desc>")
    text = path.read_text(encoding="utf-8")
    for token in required_text or []:
        if token not in text:
            errors.append(f"{path.relative_to(ROOT)}: missing required token {token!r}")
    return errors


def validate_source_images() -> list[str]:
    errors: list[str] = []
    if not EVIDENCE_IMAGE_DIR.exists():
        return errors
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
    for asset in sorted(p for p in EVIDENCE_IMAGE_DIR.rglob("*") if p.is_file() and p.suffix.lower() in image_exts):
        sidecar = asset.with_suffix(".json")
        if not sidecar.is_file():
            errors.append(f"{asset.relative_to(ROOT)}: missing source-image metadata sidecar {sidecar.name}")
            continue
        meta = load_json(sidecar)
        required = ("version","asset","sourceUrl","capturedAt","contentSha256","licenseBasis","propositions","transformation")
        for key in required:
            if key not in meta:
                errors.append(f"{sidecar.relative_to(ROOT)}: missing metadata field {key}")
        if meta.get("version") != 1:
            errors.append(f"{sidecar.relative_to(ROOT)}: version must be 1")
        if meta.get("asset") != asset.name:
            errors.append(f"{sidecar.relative_to(ROOT)}: asset must equal {asset.name!r}")
        if not str(meta.get("sourceUrl", "")).startswith("https://"):
            errors.append(f"{sidecar.relative_to(ROOT)}: sourceUrl must be https")
        if meta.get("contentSha256") != hashlib.sha256(asset.read_bytes()).hexdigest():
            errors.append(f"{sidecar.relative_to(ROOT)}: contentSha256 mismatch")
        propositions = meta.get("propositions")
        if not isinstance(propositions, list) or not propositions or not all(isinstance(x, str) and x.strip() for x in propositions):
            errors.append(f"{sidecar.relative_to(ROOT)}: propositions must be a non-empty string array")
        if not str(meta.get("licenseBasis", "")).strip():
            errors.append(f"{sidecar.relative_to(ROOT)}: licenseBasis must be non-empty")
        if not str(meta.get("transformation", "")).strip():
            errors.append(f"{sidecar.relative_to(ROOT)}: transformation must be non-empty")
    for sidecar in sorted(EVIDENCE_IMAGE_DIR.rglob("*.json")):
        meta = load_json(sidecar)
        asset_name = meta.get("asset")
        if asset_name and not (sidecar.parent / asset_name).is_file():
            errors.append(f"{sidecar.relative_to(ROOT)}: referenced asset does not exist: {asset_name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--palette", type=Path, default=DEFAULT_PALETTE)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    errors = validate_source_images()
    palette = load_json(args.palette)
    for key, expected in EXPECTED_PALETTE.items():
        got = palette.get("states", {}).get(key, {}).get("hex")
        if got != expected:
            errors.append(f"palette {key}: expected {expected}, got {got}")
    paths = manifest_paths(args.manifest_dir)
    manifests = [load_json(path) for path in paths]
    if not paths:
        errors.append("no canonical entity dossier migration manifests found")
    ratchets: list[int] = []
    previous = None
    for path, manifest in zip(paths, manifests):
        value = int(manifest["maxMissingDedicatedDossiers"])
        ratchets.append(value)
        if previous is not None and value > previous:
            errors.append(f"{path.relative_to(ROOT)}: maxMissingDedicatedDossiers regressed {previous} -> {value}")
        previous = value
    max_missing = ratchets[-1] if ratchets else 10**9
    entities: dict[str, tuple[dict, Path]] = {}
    non_state = dedicated = 0
    missing: list[str] = []
    by_type: dict[str, dict[str, int]] = {}
    for entity_file in sorted(ENTITY_DIR.glob("*.json")):
        entity = load_json(entity_file)
        entity_id, entity_type = entity.get("id"), entity.get("type")
        if not entity_id or not entity_type:
            continue
        entities[entity_id] = (entity, entity_file)
        if entity_type == "State" or entity_type not in TYPE_DIR:
            continue
        non_state += 1
        stats = by_type.setdefault(entity_type, {"total":0,"dedicated":0,"missing":0})
        stats["total"] += 1
        good, _ = is_dedicated(entity, entity_file)
        if good:
            dedicated += 1
            stats["dedicated"] += 1
        else:
            missing.append(entity_id)
            stats["missing"] += 1
    if len(missing) > max_missing:
        errors.append(f"dedicated-dossier ratchet regressed: {len(missing)} missing > allowed {max_missing}")
    migrated_ids: set[str] = set()
    for path, manifest in zip(paths, manifests):
        for row in manifest["entities"]:
            entity_id = row["id"]
            if entity_id in migrated_ids:
                errors.append(f"{path.relative_to(ROOT)}: duplicate migrated entity across manifests: {entity_id}")
                continue
            migrated_ids.add(entity_id)
            if entity_id not in entities:
                errors.append(f"{path.relative_to(ROOT)}: manifest entity missing: {entity_id}")
                continue
            entity, entity_file = entities[entity_id]
            if entity.get("type") != row["type"]:
                errors.append(f"{entity_id}: type mismatch")
            if entity.get("name") != row["name"]:
                errors.append(f"{entity_id}: name mismatch")
            good, rel = is_dedicated(entity, entity_file)
            expected_rel = Path(row["dossier"])
            if not good:
                errors.append(f"{entity_id}: does not point to an existing dedicated dossier")
                continue
            if rel != expected_rel:
                errors.append(f"{entity_id}: dossier path {rel} != manifest {expected_rel}")
            text = (ROOT / expected_rel).read_text(encoding="utf-8")
            fm = frontmatter(text)
            if fm.get("id") != f"ECL-{entity_id}": errors.append(f"{expected_rel}: frontmatter id mismatch")
            if fm.get("entity") != row["name"]: errors.append(f"{expected_rel}: frontmatter entity mismatch")
            if fm.get("entity_type") != row["type"].lower(): errors.append(f"{expected_rel}: frontmatter entity_type mismatch")
            if "provisional_outcome" in fm: errors.append(f"{expected_rel}: non-State canonical dossier must not inherit provisional_outcome")
            for section in REQUIRED_SECTIONS:
                if section not in text: errors.append(f"{expected_rel}: missing section {section}")
            if re.search(r"!\[[^\]]*\]\(\s*https?://", text, flags=re.I):
                errors.append(f"{expected_rel}: remote Markdown image is forbidden; curate a provenance-safe asset")
            if len(row.get("visuals", [])) < 2:
                errors.append(f"{entity_id}: requires at least status + evidence visuals")
            state = row.get("stateContext")
            if state not in VALID_ENTITY_STATE_CONTEXTS:
                errors.append(f"{entity_id}: invalid stateContext {state!r}")
                continue
            color = EXPECTED_PALETTE[state]
            for rel_visual in row.get("visuals", []):
                visual_path = ROOT / rel_visual
                if not visual_path.is_file():
                    errors.append(f"{entity_id}: missing visual {rel_visual}")
                    continue
                required = []
                if rel_visual.endswith("-status.svg"): required += [color, f">{state} ·", "no entity-level governance inheritance"]
                if rel_visual.endswith("-evidence.svg"): required += ["DERIVED EVIDENCE DIAGRAM", "Identity ≠ participation / culpability"]
                errors.extend(validate_svg(visual_path, required))
    report = {"nonStateEntities":non_state,"dedicatedDossiers":dedicated,"missingDedicatedDossiers":len(missing),"maxMissingDedicatedDossiers":max_missing,"migratedAcrossManifests":len(migrated_ids),"byType":by_type,"errors":errors}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
