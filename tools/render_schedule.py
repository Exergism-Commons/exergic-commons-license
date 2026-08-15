#!/usr/bin/env python3
"""Render a non-operative ECL Schedule candidate from frozen registries.

The renderer deliberately consumes only freeze/override records. Dossiers and
historical reviews are evidence sources, not Schedule inputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry"
TARGET_LICENSE = "ECL-0.3-DRAFT"

READY_PREFIX = "ready"
REFERENCE_STATUSES = {
    "ready-by-cross-entity-reference",
    "ready-narrowed-subset-via-direct-project",
    "ready-by-state-scope-reference",
    "ready-by-project-reference",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected mapping at document root")
    return value


def extract_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data.get("records"), list):
        return [r for r in data["records"] if isinstance(r, dict)]
    if "state" in data:
        return [data]
    return []


def state_outcomes() -> dict[str, str]:
    base = load_yaml(REG / "states.yml").get("outcomes", {})
    result: dict[str, str] = {}
    for outcome in ("R", "S", "U", "N"):
        for iso3 in base.get(outcome, []) or []:
            result[str(iso3)] = outcome

    # Outcome overlays are intentionally cumulative. Apply every matching
    # layer in lexical order so renderer semantics match the canonical
    # governance precedence documented by README/progress validation.
    for overlay_path in sorted(REG.glob("state-outcome-overrides*.yml")):
        overlay = load_yaml(overlay_path)
        for iso3, record in (overlay.get("overrides") or {}).items():
            if not isinstance(record, dict) or "to" not in record:
                raise ValueError(f"{overlay_path}: malformed override for {iso3}")
            result[str(iso3)] = str(record["to"])
    return result


def status_blocked_states() -> set[str]:
    path = REG / "schedule-status-overrides.yml"
    if not path.exists():
        return set()
    data = load_yaml(path)
    return {str(v) for v in (data.get("current_status_review") or [])}


def render_bullets(values: Iterable[Any], indent: str = "") -> list[str]:
    return [f"{indent}- {str(value)}" for value in values if str(value).strip()]


def first_identity(record: dict[str, Any]) -> str | None:
    value = record.get("schedule_identity")
    if value:
        return str(value)
    parties = record.get("candidate_parties") or []
    if parties:
        return str(parties[0])
    projects = record.get("candidate_projects") or []
    if projects:
        return str(projects[0])
    return None


def schedule_clause_source_paths() -> list[Path]:
    """Return every frozen source whose clauses may be emitted by this renderer."""

    fixed = [
        REG / "schedule-state-r-freeze.yml",
        REG / "schedule-organization-freezes.yml",
        REG / "schedule-armed-organization-freezes.yml",
        REG / "schedule-project-freezes.yml",
    ]
    paths = [path for path in fixed if path.exists()]
    paths.extend(sorted((REG / "schedule-state-s-freezes").glob("*.yml")))
    return paths


def compatibility_status(
    target_license: str = TARGET_LICENSE,
) -> tuple[set[str], list[Path]]:
    """Validate declared License compatibility for all rendered clause sources.

    Compatibility is evidence, not a label inferred from the working LICENSE.
    Every frozen clause source must declare its compatibility. A target License
    may be advertised only when every consumed source was explicitly validated
    for that exact target.
    """

    declarations: set[str] = set()
    incompatible: list[Path] = []
    sources = schedule_clause_source_paths()
    if not sources:
        raise ValueError("no frozen Schedule clause sources found")

    for path in sources:
        data = load_yaml(path)
        declared = data.get("compatible_license")
        if not isinstance(declared, str) or not declared.strip():
            raise ValueError(f"{path}: missing compatible_license declaration")
        declared = declared.strip()
        declarations.add(declared)
        if declared != target_license:
            incompatible.append(path)

    return declarations, incompatible


def collect_state_s_records(outcomes: dict[str, str]) -> list[dict[str, Any]]:
    blocked = status_blocked_states()
    records: list[dict[str, Any]] = []
    freeze_dir = REG / "schedule-state-s-freezes"
    for path in sorted(freeze_dir.glob("*.yml")):
        data = load_yaml(path)
        for record in extract_records(data):
            state = str(record.get("state", ""))
            status = str(record.get("schedule_status", ""))
            if not state or outcomes.get(state) != "S":
                continue
            if state in blocked:
                continue
            if not status.startswith(READY_PREFIX):
                continue
            if status in REFERENCE_STATUSES:
                # Direct project / synchronized entity will be rendered from its
                # canonical project or organization freeze instead.
                continue
            if not first_identity(record):
                raise ValueError(f"{path}: ready record for {state} has no identity")
            copied = dict(record)
            copied["_source"] = str(path.relative_to(ROOT))
            records.append(copied)
    return records


def collect_state_r_records(outcomes: dict[str, str]) -> list[dict[str, Any]]:
    data = load_yaml(REG / "schedule-state-r-freeze.yml")
    records = []
    for record in data.get("entries", []) or []:
        iso3 = str(record.get("iso3", ""))
        if outcomes.get(iso3) != "R":
            continue
        if not record.get("candidate_class"):
            raise ValueError(f"R freeze {iso3} has no candidate_class")
        records.append(record)
    return records


def collect_organizations() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for filename in (
        "schedule-organization-freezes.yml",
        "schedule-armed-organization-freezes.yml",
    ):
        path = REG / filename
        if not path.exists():
            continue
        data = load_yaml(path)
        for record in data.get("organizations", []) or []:
            status = str(record.get("schedule_status", ""))
            if not status.startswith(READY_PREFIX) or status in REFERENCE_STATUSES:
                continue
            if not record.get("schedule_identity") and not record.get(
                "schedule_entities"
            ):
                raise ValueError(
                    f"{path}: ready organization {record.get('id')} has no identity"
                )
            records.append(record)
    return records


def collect_projects() -> list[dict[str, Any]]:
    data = load_yaml(REG / "schedule-project-freezes.yml")
    records = []
    for record in data.get("projects", []) or []:
        status = str(record.get("schedule_status", ""))
        if not status.startswith(READY_PREFIX):
            continue
        if not record.get("schedule_identity"):
            raise ValueError(f"ready project {record.get('id')} has no schedule_identity")
        records.append(record)
    return records


def validate_unique(records: Iterable[dict[str, Any]], key: str, label: str) -> None:
    seen: set[str] = set()
    for record in records:
        value = str(record.get(key, "")).strip()
        if not value:
            continue
        if value in seen:
            raise ValueError(f"duplicate {label}: {value}")
        seen.add(value)


def render() -> tuple[str, dict[str, int]]:
    declared_licenses, incompatible_sources = compatibility_status()
    outcomes = state_outcomes()
    r_states = collect_state_r_records(outcomes)
    s_records = collect_state_s_records(outcomes)
    organizations = collect_organizations()
    projects = collect_projects()

    validate_unique(r_states, "iso3", "R State ISO3")
    validate_unique(organizations, "id", "organization ID")
    validate_unique(projects, "id", "project ID")

    if len(r_states) != sum(1 for v in outcomes.values() if v == "R"):
        raise ValueError("not every active R State has a frozen Schedule identity")

    if incompatible_sources:
        declared_text = ", ".join(sorted(declared_licenses))
        compatibility_lines = [
            f"> Target working License: **{TARGET_LICENSE}**.",
            ">",
            f"> Compatibility status: **NOT YET VALIDATED for {TARGET_LICENSE}**.",
            ">",
            f"> Frozen clause inputs currently declare compatibility with: **{declared_text}**.",
            ">",
            "> This candidate MUST NOT be labelled compatible with the target License until every consumed frozen clause source is explicitly revalidated for that exact License.",
        ]
    else:
        compatibility_lines = [
            f"> Intended compatibility: **{TARGET_LICENSE} only**.",
        ]

    lines: list[str] = [
        "# ECL Restricted Parties / Projects Schedule — 0.5 GENERATED DRAFT",
        "",
        "> **NON-OPERATIVE GENERATED CANDIDATE. DO NOT ADOPT OR INCORPORATE INTO A RELEASE.**",
        ">",
        *compatibility_lines,
        "",
        "This file is deterministically rendered from frozen registry records. It omits U/N outcomes, unresolved factual/status records, unfrozen residual dossier scope and cross-entity references whose canonical project/organization is rendered separately.",
        "",
        "## Global interpretation",
        "",
        "- State entries concern only the stated apparatus/project capacity, never population or nationality.",
        "- Independent remediation, legal defence, audit and rights-protective review remain excluded unless expressly designated.",
        "- Association, employment, residence or remote affiliation does not create status by itself.",
        "- Material Participation controls project/associate linkage under the operative ECL text.",
        "- No external sanctions/warrant list is dynamically incorporated.",
        "",
        "## State apparatus entries — R",
        "",
    ]

    for record in r_states:
        lines.append(
            f"- **{record['iso3']} — {record['entity']}:** {record['candidate_class']}"
        )

    lines += ["", "## Scoped State entries — S", ""]
    for record in sorted(
        s_records, key=lambda r: (str(r.get("state")), str(first_identity(r)))
    ):
        state = record.get("state")
        entity = record.get("entity") or state
        lines += [f"### {state} — {entity}", ""]
        if record.get("schedule_identity"):
            lines += [f"**Frozen identity/project:** {record['schedule_identity']}", ""]
        if record.get("candidate_parties"):
            lines += [
                "**Candidate parties:**",
                *render_bullets(record["candidate_parties"]),
                "",
            ]
        if record.get("candidate_projects"):
            lines += [
                "**Frozen projects/capacities:**",
                *render_bullets(record["candidate_projects"]),
                "",
            ]
        for key, title in (
            ("project_boundary", "Boundary"),
            ("capacity_limit", "Capacity limit"),
            ("scope_rule", "Scope rule"),
        ):
            if record.get(key):
                lines += [f"**{title}:** {record[key]}", ""]
        if record.get("exclusions"):
            lines += [
                "**Exclusions:**",
                *render_bullets(record["exclusions"]),
                "",
            ]
        lines += [f"_Freeze source: `{record['_source']}`._", ""]

    lines += ["## Non-State organization entries", ""]
    for record in organizations:
        lines += [f"### {record['id']} — {record['outcome']}", ""]
        if record.get("schedule_identity"):
            lines += [f"**Frozen identity:** {record['schedule_identity']}", ""]
        if record.get("schedule_entities"):
            lines += [
                "**Frozen exact entities:**",
                *render_bullets(record["schedule_entities"]),
                "",
            ]
        if record.get("frozen_aliases"):
            lines += [
                "**Frozen aliases:**",
                *render_bullets(record["frozen_aliases"]),
                "",
            ]
        for key, title in (
            ("scope_rule", "Scope rule"),
            ("capacity_limit", "Capacity limit"),
        ):
            if record.get(key):
                lines += [f"**{title}:** {record[key]}", ""]
        if record.get("exclusions"):
            lines += [
                "**Exclusions:**",
                *render_bullets(record["exclusions"]),
                "",
            ]

    lines += ["## Direct Restricted Projects", ""]
    for record in projects:
        lines += [
            f"### {record['id']} — {record['outcome']}",
            "",
            f"**Frozen project:** {record['schedule_identity']}",
            "",
        ]
        for key, title in (
            ("project_boundary", "Boundary"),
            ("operator_boundary", "Operator boundary"),
            ("prohibited_capacity", "Restricted capacity"),
        ):
            if record.get(key):
                lines += [f"**{title}:** {record[key]}", ""]
        if record.get("exclusions"):
            lines += [
                "**Exclusions:**",
                *render_bullets(record["exclusions"]),
                "",
            ]
        if record.get("continuation_rule"):
            lines += [f"**Continuation rule:** {record['continuation_rule']}", ""]

    lines += [
        "## Non-operative status",
        "",
        "This generated draft is a release-readiness artifact only. It has no licensing effect unless a future exact Schedule is intentionally reviewed, versioned and expressly incorporated with an exact ECL version.",
        "",
    ]

    counts = {
        "r_states": len(r_states),
        "s_state_entries": len(s_records),
        "organizations": len(organizations),
        "projects": len(projects),
        "compatibility_mismatches": len(incompatible_sources),
    }
    return "\n".join(lines), counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    text, counts = render()
    compatibility = (
        "ready"
        if counts["compatibility_mismatches"] == 0
        else f"pending ({counts['compatibility_mismatches']} source files require revalidation)"
    )
    print(
        "validated schedule inputs: "
        f"R states={counts['r_states']}, "
        f"S state entries={counts['s_state_entries']}, "
        f"organizations={counts['organizations']}, "
        f"projects={counts['projects']}, "
        f"target compatibility={compatibility}"
    )
    if args.validate_only:
        return
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
