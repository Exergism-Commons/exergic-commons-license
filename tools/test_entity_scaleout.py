#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from entity_identity_resolution import canonicalize_id, infer_domestic_state, load_id_supersessions

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "knowledge" / "generated"
ENTITY_DIR = ROOT / "knowledge" / "entities"
MANIFEST_RE = re.compile(r"^state-dossier-entity-scaleout-v([1-9][0-9]*)\.json$")
FORBIDDEN_GOVERNANCE = {
    "provisional_outcome", "outcome", "tier", "derived_outcome", "score_outcome",
    "governanceStatus", "governanceOutcome", "restrictionStatus"
}
FORBIDDEN_RELATIONS = {
    "controls", "controlledBy", "partOf", "operates", "participatesIn", "deploys",
    "materiallyBenefits", "tracks", "remediates", "reviews"
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
        assert manifest.get("version") == version, (
            f"manifest version/file mismatch: {path.relative_to(ROOT)} -> {manifest.get('version')!r}"
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


def main() -> int:
    manifests = manifests_by_version()
    validate_manifest_chain(manifests)
    supersessions = load_id_supersessions()
    state_codes = canonical_state_codes()
    all_historical_ids: list[str] = []
    promotion_count = 0
    superseded_count = 0
    for version, manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest["identities"]
        assert isinstance(rows, list), manifest_path
        assert manifest["relationClaims"] == []
        assert manifest["formalAssessments"] == []
        assert manifest["governanceChanges"] == []
        for row in rows:
            promotion_count += 1
            historical_id = row["id"]
            all_historical_ids.append(historical_id)
            row_state = row.get("state")
            if row_state is not None:
                assert isinstance(row_state, str) and STATE_RE.fullmatch(row_state), (manifest_path, row)
            entity_id = canonicalize_id(historical_id, supersessions)
            domestic_state = infer_domestic_state(entity_id, state_codes)
            if domestic_state is not None:
                assert row_state == domestic_state, (
                    f"domestic promotion must declare its canonical State in v{version}: "
                    f"{historical_id} canonicalizes to {entity_id} ({domestic_state}), row state={row_state!r}"
                )
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
            assert not (FORBIDDEN_GOVERNANCE & set(data)), (entity_id, FORBIDDEN_GOVERNANCE & set(data))
            assert not (FORBIDDEN_RELATIONS & set(data)), (entity_id, FORBIDDEN_RELATIONS & set(data))
            dossier = (path.parent / data["dossier"]).resolve()
            assert dossier.exists(), (entity_id, dossier)
            source = ROOT / row["source"]
            assert source.exists(), (historical_id, source)
            source_rel = Path(row["source"])
            if row_state is not None and source_rel.parts[:2] == ("dossiers", "states") and source_rel.suffix == ".md":
                assert source_rel.stem == row_state, (
                    f"manifest State/source mismatch in v{version}: {historical_id} -> "
                    f"state {row_state}, source {source_rel}"
                )
    assert len(all_historical_ids) == len(set(all_historical_ids)), "duplicate promoted stable id across historical manifests"
    assert set(supersessions).issubset(set(all_historical_ids)), (
        "supersession sources must be historical promotion IDs", sorted(set(supersessions) - set(all_historical_ids))
    )
    print(
        f"identity scale-out tests: OK ({promotion_count} historical promotions across "
        f"{len(manifests)} manifests; {superseded_count} canonicalized IDs; manifest chain contiguous)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
