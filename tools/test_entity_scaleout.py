#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from entity_identity_resolution import canonicalize_id, infer_domestic_state, load_id_supersessions

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "knowledge" / "generated"
ENTITY_DIR = ROOT / "knowledge" / "entities"
STATE_DOSSIER_DIR = (ROOT / "dossiers" / "states").resolve()
MANIFEST_RE = re.compile(r"^state-dossier-entity-scaleout-v([1-9][0-9]*)\.json$")
# Promoted nodes are identity records only. These allowlists are deliberately structural:
# adding any new manifest/row/entity key requires review instead of hoping a relation or
# governance blacklist happened to anticipate its spelling.
ALLOWED_MANIFEST_KEYS = {
    "version", "date", "purpose", "follows", "sourceAudit", "identityRule", "identities",
    "relationClaims", "formalAssessments", "governanceChanges", "explicitNonGoals",
    "explicitDeferrals",
}
ALLOWED_SOURCE_AUDITS = {
    "tools/audit_state_dossier_entities.py",
    "tools/audit_private_org_mentions.py",
    "tools/audit_schedule_reference_coverage.py",
    "tools/check_state_dossier_named_person_coverage.py",
}
ALLOWED_PROMOTION_ROW_KEYS = {"id", "type", "state", "source"}
ALLOWED_IDENTITY_KEYS = {
    "@context", "iri", "id", "type", "name", "aliases", "dossier", "provenance",
    "lastSubstantiveReview", "reviewDue", "reviewClass", "reviewReason", "publicReviewIssue",
}
ALLOWED_TYPES = {"Agency", "Organization", "Institution", "Person", "Project", "Deployment"}
STATE_RE = re.compile(r"^[A-Z]{3}$")


def manifests_by_version() -> list[tuple[int, Path]]:
    rows: list[tuple[int, Path]] = []
    for path in GENERATED.glob("state-dossier-entity-scaleout-v*.json"):
        match = MANIFEST_RE.fullmatch(path.name)
        assert match, f"malformed scale-out manifest filename: {path.name}"
        rows.append((int(match.group(1)), path))
    rows.sort()
    return rows


def validate_manifest_chain(manifests: list[tuple[int, Path]]) -> None:
    assert manifests, "no entity scale-out manifests"
    versions = [version for version, _ in manifests]
    assert versions == list(range(1, versions[-1] + 1)), f"non-contiguous scale-out manifest versions: {versions}"
    previous: Path | None = None
    for version, path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        unexpected = sorted(set(manifest) - ALLOWED_MANIFEST_KEYS)
        assert not unexpected, f"unexpected scale-out manifest keys in {path.relative_to(ROOT)}: {unexpected}"
        assert manifest.get("version") == version, (
            f"manifest version/file mismatch: {path.relative_to(ROOT)} -> {manifest.get('version')!r}"
        )
        assert isinstance(manifest.get("date"), str) and manifest["date"].strip(), path
        assert isinstance(manifest.get("purpose"), str) and manifest["purpose"].strip(), path
        if "sourceAudit" in manifest:
            source_audit = manifest.get("sourceAudit")
            assert source_audit in ALLOWED_SOURCE_AUDITS and (ROOT / source_audit).is_file(), (
                path, source_audit
            )
        assert isinstance(manifest.get("identityRule"), str) and manifest["identityRule"].strip(), path
        assert isinstance(manifest.get("identities"), list), path
        assert manifest.get("relationClaims") == [], path
        assert manifest.get("formalAssessments") == [], path
        assert manifest.get("governanceChanges") == [], path
        for optional in ("explicitNonGoals", "explicitDeferrals"):
            if optional in manifest:
                value = manifest[optional]
                assert isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value), (
                    path, optional, value
                )
        if previous is None:
            assert not manifest.get("follows"), f"v1 must not follow another manifest: {path.relative_to(ROOT)}"
        else:
            expected = str(previous.relative_to(ROOT))
            assert manifest.get("follows") == expected, (
                f"broken scale-out follows chain at {path.relative_to(ROOT)}: "
                f"expected {expected!r}, got {manifest.get('follows')!r}"
            )
        previous = path


def canonical_state_codes() -> set[str]:
    result: set[str] = set()
    for path in ENTITY_DIR.glob("STATE-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        entity_id = data.get("id")
        if data.get("type") == "State" and isinstance(entity_id, str) and entity_id.startswith("STATE-"):
            state = entity_id.removeprefix("STATE-")
            if STATE_RE.fullmatch(state):
                result.add(state)
    return result


def state_dossier_entities_without_promotion(promoted_ids: set[str]) -> list[dict[str, str]]:
    """Require the scale-out history to explain every non-State node sourced from a State dossier.

    This is the reverse half of the provenance invariant. Manifest rows already have to point
    to real identity files; here an identity file whose `dossier` provenance lands in the
    canonical State-dossier directory must also appear in the versioned promotion history.
    The check is based on provenance, not `reviewClass`, so changing metadata cannot hide an
    otherwise unreviewed State-dossier materialization.
    """
    missing: list[dict[str, str]] = []
    for path in sorted(ENTITY_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "State":
            continue
        entity_id = data.get("id")
        dossier_value = data.get("dossier")
        if not isinstance(entity_id, str) or not isinstance(dossier_value, str):
            continue
        target = (path.parent / dossier_value).resolve()
        if target.parent != STATE_DOSSIER_DIR or target.suffix != ".md":
            continue
        if entity_id not in promoted_ids:
            missing.append({
                "id": entity_id,
                "entity_file": str(path.relative_to(ROOT)),
                "dossier": str(target.relative_to(ROOT)),
            })
    return missing


def main() -> int:
    manifests = manifests_by_version()
    validate_manifest_chain(manifests)
    supersessions = load_id_supersessions()
    state_codes = canonical_state_codes()
    all_historical_ids: list[str] = []
    jurisdiction_errors: list[dict[str, object]] = []
    unexpected_key_errors: list[dict[str, object]] = []
    row_schema_errors: list[dict[str, object]] = []
    promotion_count = 0
    superseded_count = 0

    for version, manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest["identities"]
        for row_index, row in enumerate(rows):
            assert isinstance(row, dict), (manifest_path, row_index, row)
            unexpected_row_keys = sorted(set(row) - ALLOWED_PROMOTION_ROW_KEYS)
            missing_row_keys = sorted({"id", "type", "source"} - set(row))
            if unexpected_row_keys or missing_row_keys:
                row_schema_errors.append({
                    "version": version,
                    "row_index": row_index,
                    "id": row.get("id"),
                    "unexpected_keys": unexpected_row_keys,
                    "missing_required_keys": missing_row_keys,
                })
                continue

            promotion_count += 1
            historical_id = row["id"]
            all_historical_ids.append(historical_id)
            row_state = row.get("state")
            if row_state is not None:
                assert isinstance(row_state, str) and STATE_RE.fullmatch(row_state), (manifest_path, row)

            entity_id = canonicalize_id(historical_id, supersessions)
            domestic_state = infer_domestic_state(entity_id, state_codes)
            if domestic_state is not None and row_state != domestic_state:
                jurisdiction_errors.append({
                    "version": version,
                    "historical_id": historical_id,
                    "canonical_id": entity_id,
                    "expected_state": domestic_state,
                    "declared_state": row_state,
                    "source": row.get("source"),
                })

            if entity_id != historical_id:
                superseded_count += 1
                old_path = ENTITY_DIR / f"{historical_id}.json"
                assert not old_path.exists(), f"superseded identity source still materialized: {old_path}"

            path = ENTITY_DIR / f"{entity_id}.json"
            assert path.exists(), f"missing promoted/canonical identity: {path} (historical {historical_id})"
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["id"] == entity_id
            assert data["iri"] == f"ecl:{entity_id}"
            assert data["type"] == row["type"] in ALLOWED_TYPES
            assert isinstance(data.get("name"), str) and data["name"].strip()

            unexpected = sorted(set(data) - ALLOWED_IDENTITY_KEYS)
            if unexpected:
                unexpected_key_errors.append({
                    "version": version,
                    "historical_id": historical_id,
                    "canonical_id": entity_id,
                    "unexpected_keys": unexpected,
                })

            dossier_value = data.get("dossier")
            assert isinstance(dossier_value, str) and dossier_value, (entity_id, dossier_value)
            dossier = (path.parent / dossier_value).resolve()
            assert dossier.exists(), (entity_id, dossier)

            source_value = row.get("source")
            assert isinstance(source_value, str) and source_value, (historical_id, source_value)
            source = ROOT / source_value
            assert source.exists(), (historical_id, source)
            source_rel = Path(source_value)
            if source_rel.parts[:2] == ("dossiers", "states") and source_rel.suffix == ".md":
                assert source_rel.stem in state_codes, (
                    f"promotion source must be a canonical State dossier in v{version}: "
                    f"{historical_id} -> {source_rel}"
                )

    if row_schema_errors:
        print("PROMOTION_ROW_SCHEMA_ERRORS=" + json.dumps(row_schema_errors, ensure_ascii=False, sort_keys=True))
        return 4
    assert len(all_historical_ids) == len(set(all_historical_ids)), "duplicate promoted stable id across historical manifests"
    assert set(supersessions).issubset(set(all_historical_ids)), (
        "supersession sources must be historical promotion IDs", sorted(set(supersessions) - set(all_historical_ids))
    )
    if jurisdiction_errors:
        print("DOMESTIC_PROMOTION_STATE_ERRORS=" + json.dumps(jurisdiction_errors, ensure_ascii=False, sort_keys=True))
        return 2
    if unexpected_key_errors:
        print("PROMOTED_IDENTITY_UNEXPECTED_KEYS=" + json.dumps(unexpected_key_errors, ensure_ascii=False, sort_keys=True))
        return 3

    promoted_current_ids = {canonicalize_id(entity_id, supersessions) for entity_id in all_historical_ids}
    reverse_provenance_errors = state_dossier_entities_without_promotion(promoted_current_ids)
    if reverse_provenance_errors:
        print("STATE_DOSSIER_IDENTITIES_WITHOUT_PROMOTION=" + json.dumps(
            reverse_provenance_errors, ensure_ascii=False, sort_keys=True
        ))
        return 5

    print(
        f"identity scale-out tests: OK ({promotion_count} historical promotions across "
        f"{len(manifests)} manifests; {superseded_count} canonicalized IDs; "
        "manifest/row schema, reverse State-dossier provenance, and identity metadata allowlists enforced)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
