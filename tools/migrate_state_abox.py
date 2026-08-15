#!/usr/bin/env python3
"""Deterministically materialize State identity records from canonical dossiers.

Governance remains in dossiers/decisions/Schedules. This migration only manages a
small, explicitly owned projection of State identity/provenance fields and never
writes provisional_outcome, scope, tier or restriction status to State actors.

Curated fields (aliases beyond the ISO3 seed, review clocks/reasons, tracked
objects, monitors and semantic relations) are preserved verbatim. A generated
projection hash manifest detects human edits to generator-owned fields instead
of overwriting them silently.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

STATE_FILE = re.compile(r"^[A-Z]{3}\.md$")
ISO3 = re.compile(r"^[A-Z]{3}$")
OUTCOMES = {"R", "S", "U", "N"}
MANIFEST_VERSION = 1
GENERATOR_ID = "tools/migrate_state_abox.py:v1"
GENERATED_FIELDS = (
    "@context", "iri", "id", "type", "name", "iso3", "dossier",
    "publicReviewIssue", "lastSubstantiveReview",
)
FORBIDDEN_STATE_KEYS = re.compile(
    r"(?:^|[_-])(?:current[-_]?governance|governance[-_]?(?:status|outcome)|"
    r"restriction[-_]?status|restricted[-_]?status|tier|provisional[-_]?outcome|outcome)"
    r"(?:$|[_-])",
    re.IGNORECASE,
)
INHERITANCE_KEY = re.compile(r"(?:inherit.*restrict|restrict.*inherit)", re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class Dossier:
    path: Path
    iso3: str
    dossier_id: str
    entity: str
    issue: int
    provisional_outcome: str
    last_reviewed: str


@dataclasses.dataclass
class MigrationSummary:
    dossiers_seen: int = 0
    selected: int = 0
    created: list[str] = dataclasses.field(default_factory=list)
    updated: list[str] = dataclasses.field(default_factory=list)
    unchanged: list[str] = dataclasses.field(default_factory=list)
    conflicts: list[str] = dataclasses.field(default_factory=list)
    state_actor_count: int = 0
    unique_iso3: int = 0
    unique_ids: int = 0
    unique_dossiers: int = 0
    generated_manifest_entries: int = 0

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter opener")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing YAML frontmatter closer") from exc
    result: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty frontmatter key: {line!r}")
        result[key] = _unquote(value)
    return result


def _parse_date(value: str, label: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an ISO date, got {value!r}") from exc


def load_dossiers(root: Path, *, require_195: bool = True) -> list[Dossier]:
    paths = [p for p in sorted(root.glob("*.md")) if STATE_FILE.fullmatch(p.name)]
    if require_195 and len(paths) != 195:
        raise ValueError(f"expected exactly 195 State dossiers, found {len(paths)} under {root}")
    dossiers: list[Dossier] = []
    seen_iso: set[str] = set()
    seen_ids: set[str] = set()
    seen_issues: set[int] = set()
    for path in paths:
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        required = ("id", "entity", "iso3", "issue", "provisional_outcome", "last_reviewed")
        missing = [key for key in required if not meta.get(key)]
        if missing:
            raise ValueError(f"{path}: missing required frontmatter {missing}")
        iso = meta["iso3"].strip().upper()
        if not ISO3.fullmatch(iso) or iso != path.stem:
            raise ValueError(f"{path}: iso3={meta['iso3']!r} does not match filename")
        dossier_id = meta["id"].strip()
        if dossier_id != f"ECL-STATE-{iso}":
            raise ValueError(f"{path}: expected id ECL-STATE-{iso}, got {dossier_id!r}")
        try:
            issue = int(meta["issue"])
        except ValueError as exc:
            raise ValueError(f"{path}: issue must be a positive integer") from exc
        if issue <= 0:
            raise ValueError(f"{path}: issue must be a positive integer")
        outcome = meta["provisional_outcome"].strip()
        if outcome not in OUTCOMES:
            raise ValueError(f"{path}: invalid provisional_outcome {outcome!r}")
        last_reviewed = meta["last_reviewed"].strip()
        _parse_date(last_reviewed, f"{path}: last_reviewed")
        entity = meta["entity"].strip()
        if not entity:
            raise ValueError(f"{path}: entity must not be empty")
        if iso in seen_iso or dossier_id in seen_ids or issue in seen_issues:
            raise ValueError(f"{path}: duplicate ISO3, dossier id or public review issue")
        seen_iso.add(iso)
        seen_ids.add(dossier_id)
        seen_issues.add(issue)
        dossiers.append(Dossier(path, iso, dossier_id, entity, issue, outcome, last_reviewed))
    return dossiers


def add_days(date_text: str, days: int) -> str:
    return (_parse_date(date_text, "date") + dt.timedelta(days=days)).isoformat()


def generated_projection(dossier: Dossier) -> dict[str, Any]:
    return {
        "@context": "../../ontology/ecl-context.jsonld",
        "iri": f"ecl:STATE-{dossier.iso3}",
        "id": f"STATE-{dossier.iso3}",
        "type": "State",
        "name": dossier.entity,
        "iso3": dossier.iso3,
        "dossier": f"../../dossiers/states/{dossier.iso3}.md",
        "publicReviewIssue": f"https://github.com/Papishushi/exergic-commons-license/issues/{dossier.issue}",
        "lastSubstantiveReview": dossier.last_reviewed,
    }


def projection_hash(record: dict[str, Any]) -> str:
    projection = {field: record.get(field) for field in GENERATED_FIELDS}
    payload = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": MANIFEST_VERSION, "generator": GENERATOR_ID, "generatedProjectionSha256": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a JSON object")
    if data.get("version") != MANIFEST_VERSION or data.get("generator") != GENERATOR_ID:
        raise ValueError(f"{path}: unsupported migration manifest version/generator")
    if not isinstance(data.get("generatedProjectionSha256"), dict):
        raise ValueError(f"{path}: generatedProjectionSha256 must be an object")
    return data


def render_manifest(hashes: dict[str, str]) -> str:
    data = {
        "version": MANIFEST_VERSION,
        "generator": GENERATOR_ID,
        "note": "Derived conflict-detection hashes only; not ABox data and not a governance source.",
        "generatedProjectionSha256": dict(sorted(hashes.items())),
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def validate_state_guardrail(record: dict[str, Any], *, label: str) -> None:
    for key in record:
        if FORBIDDEN_STATE_KEYS.search(key) or INHERITANCE_KEY.search(key):
            raise ValueError(f"{label}: forbidden governance/inheritance field on State: {key}")
    if record.get("type") == "State" and "status" in record:
        raise ValueError(f"{label}: generic status is forbidden on State identity records")


def _ordered_record(record: dict[str, Any]) -> dict[str, Any]:
    preferred = [
        "@context", "iri", "id", "type", "name", "iso3", "aliases", "dossier",
        "publicReviewIssue", "lastSubstantiveReview", "reviewDue", "reviewClass",
        "reviewReason", "trackedObjects", "monitorIds", "controls", "participatesIn",
        "operates", "deploys", "materiallyBenefits", "targetsOrAffects", "remediates", "reviews",
    ]
    out: dict[str, Any] = {}
    for key in preferred:
        if key in record:
            out[key] = record[key]
    for key in sorted(record):
        if key not in out:
            out[key] = record[key]
    return out


def render_record(record: dict[str, Any]) -> str:
    return json.dumps(_ordered_record(record), ensure_ascii=False, indent=2) + "\n"


def default_curated_fields(dossier: Dossier) -> dict[str, Any]:
    return {"aliases": [dossier.iso3], "reviewDue": add_days(dossier.last_reviewed, 90), "reviewClass": "manual"}


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def merge_record(dossier: Dossier, existing: dict[str, Any] | None, previous_hash: str | None) -> tuple[dict[str, Any], bool]:
    expected = generated_projection(dossier)
    if existing is None:
        merged = {**expected, **default_curated_fields(dossier)}
        validate_state_guardrail(merged, label=dossier.iso3)
        return merged, True
    validate_state_guardrail(existing, label=dossier.iso3)
    if previous_hash is not None:
        if projection_hash(existing) != previous_hash:
            raise ValueError(f"{dossier.iso3}: generator-owned fields changed since the last manifest; resolve the conflict explicitly")
    else:
        for field, value in expected.items():
            if field in existing and existing[field] != value:
                raise ValueError(f"{dossier.iso3}: legacy {field}={existing[field]!r} conflicts with dossier-derived value {value!r}")
    merged = dict(existing)
    merged.update(expected)
    for key, value in default_curated_fields(dossier).items():
        merged.setdefault(key, value)
    if not isinstance(merged.get("aliases"), list) or not merged["aliases"]:
        raise ValueError(f"{dossier.iso3}: aliases must be a non-empty array")
    if dossier.iso3 not in merged["aliases"]:
        merged["aliases"] = [dossier.iso3, *merged["aliases"]]
    review_due = _parse_date(str(merged["reviewDue"]), f"{dossier.iso3}.reviewDue")
    last = _parse_date(dossier.last_reviewed, f"{dossier.iso3}.last_reviewed")
    if review_due < last:
        raise ValueError(f"{dossier.iso3}: curated reviewDue predates lastSubstantiveReview")
    if merged.get("reviewClass") not in {"hot", "active", "stable", "manual"}:
        raise ValueError(f"{dossier.iso3}: invalid reviewClass {merged.get('reviewClass')!r}")
    validate_state_guardrail(merged, label=dossier.iso3)
    return merged, merged != existing


def scan_state_corpus(entity_root: Path) -> tuple[int, int, int, int]:
    records: list[dict[str, Any]] = []
    for path in sorted(entity_root.glob("STATE-*.json")):
        data = read_json_object(path)
        if data.get("type") == "State":
            validate_state_guardrail(data, label=str(path))
            records.append(data)
    return len(records), len({r.get("iso3") for r in records}), len({r.get("id") for r in records}), len({r.get("dossier") for r in records})


def migrate(dossier_root: Path, entity_root: Path, manifest_path: Path, *, iso3: str | None = None, check: bool = False, dry_run: bool = False) -> tuple[MigrationSummary, int]:
    dossiers = load_dossiers(dossier_root, require_195=True)
    if iso3 is not None:
        iso3 = iso3.upper()
        if not ISO3.fullmatch(iso3):
            raise ValueError(f"invalid --iso3 {iso3!r}")
        selected = [d for d in dossiers if d.iso3 == iso3]
        if not selected:
            raise ValueError(f"no dossier found for {iso3}")
    else:
        selected = dossiers
    manifest = load_manifest(manifest_path)
    previous_hashes: dict[str, str] = dict(manifest["generatedProjectionSha256"])
    next_hashes = dict(previous_hashes)
    summary = MigrationSummary(dossiers_seen=len(dossiers), selected=len(selected))
    planned: list[tuple[Path, str]] = []
    for dossier in selected:
        path = entity_root / f"STATE-{dossier.iso3}.json"
        existing = read_json_object(path) if path.exists() else None
        try:
            merged, _ = merge_record(dossier, existing, previous_hashes.get(dossier.iso3))
        except ValueError as exc:
            summary.conflicts.append(str(exc))
            continue
        next_hashes[dossier.iso3] = projection_hash(merged)
        desired = render_record(merged)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == desired:
            summary.unchanged.append(dossier.iso3)
        elif path.exists():
            summary.updated.append(dossier.iso3)
            planned.append((path, desired))
        else:
            summary.created.append(dossier.iso3)
            planned.append((path, desired))
    if not summary.conflicts:
        desired_manifest = render_manifest(next_hashes)
        current_manifest = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else None
        if current_manifest != desired_manifest:
            planned.append((manifest_path, desired_manifest))
    if not check and not dry_run and not summary.conflicts:
        entity_root.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        for path, content in planned:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    count, uiso, uids, udossiers = scan_state_corpus(entity_root)
    summary.state_actor_count = count
    summary.unique_iso3 = uiso
    summary.unique_ids = uids
    summary.unique_dossiers = udossiers
    summary.generated_manifest_entries = len(next_hashes)
    if summary.conflicts:
        return summary, 2
    if check and planned:
        return summary, 1
    return summary, 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dossier-root", type=Path, default=Path("dossiers/states"))
    parser.add_argument("--entity-root", type=Path, default=Path("knowledge/entities"))
    parser.add_argument("--manifest", type=Path, default=Path("knowledge/generated/state-abox-manifest.json"))
    parser.add_argument("--iso3", help="migrate/check one ISO3 while validating the full dossier set")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if migration would change files")
    mode.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    try:
        summary, code = migrate(args.dossier_root, args.entity_root, args.manifest, iso3=args.iso3, check=args.check, dry_run=args.dry_run)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(summary.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(payload)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(payload, encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
