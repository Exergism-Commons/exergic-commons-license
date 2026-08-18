#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge" / "generated" / "state-dossier-entity-scaleout-v1.json"
FORBIDDEN_GOVERNANCE = {
    "provisional_outcome", "outcome", "tier", "derived_outcome", "score_outcome",
    "governanceStatus", "governanceOutcome", "restrictionStatus"
}
FORBIDDEN_RELATIONS = {
    "controls", "controlledBy", "partOf", "operates", "participatesIn", "deploys",
    "materiallyBenefits", "tracks", "remediates", "reviews"
}
ALLOWED_TYPES = {"Agency", "Organization", "Institution", "Person", "Project", "Deployment"}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["identities"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids)), "duplicate promoted stable id"
    assert manifest["relationClaims"] == []
    assert manifest["formalAssessments"] == []
    assert manifest["governanceChanges"] == []

    for row in rows:
        entity_id = row["id"]
        path = ROOT / "knowledge" / "entities" / f"{entity_id}.json"
        assert path.exists(), f"missing promoted identity: {path}"
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
        assert source.exists(), (entity_id, source)

    print(f"identity scale-out tests: OK ({len(rows)} identity-only promotions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
