#!/usr/bin/env python3
"""Render a non-operative ECL Schedule candidate from frozen registries.

The renderer deliberately consumes only freeze/override records. Dossiers and
historical reviews are evidence sources, not Schedule inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry"
TARGET_LICENSE = "ECL-0.3-DRAFT"
TARGET_LICENSE_ARTIFACT = ROOT / "versions" / "licenses" / "ECL-0.3-DRAFT.md"
WORKING_LICENSE = ROOT / "LICENSE"
COMPATIBILITY_REVIEW = REG / "schedule-license-compatibility.yml"
COMPATIBILITY_EVIDENCE_DIR = ROOT / "reviews" / "schedule-compatibility"
SCHEDULE_REQUIREMENTS = ROOT / "tools" / "schedule-requirements.txt"
PINNED_PYYAML_VERSION = "6.0.3"

READY_PREFIX = "ready"
REFERENCE_STATUSES = {
    "ready-by-cross-entity-reference",
    "ready-narrowed-subset-via-direct-project",
    "ready-by-state-scope-reference",
    "ready-by-project-reference",
}
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
RFC3339_RE = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<hour>[01][0-9]|2[0-3]):"
    r"(?P<minute>[0-5][0-9]):"
    r"(?P<second>[0-5][0-9])"
    r"(?:\.[0-9]+)?"
    r"(?P<zone>Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)
STANDARD_MAPPING_TAG = "tag:yaml.org,2002:map"
STANDARD_SEQUENCE_TAG = "tag:yaml.org,2002:seq"
STANDARD_STRING_TAG = "tag:yaml.org,2002:str"
ALLOWED_SCALAR_TAGS = {
    STANDARD_STRING_TAG,
    "tag:yaml.org,2002:int",
    "tag:yaml.org,2002:bool",
    "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:timestamp",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected mapping at document root")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_renderer_environment() -> None:
    """Require the parser release reviewed as part of Schedule compatibility."""

    expected_requirements = f"PyYAML=={PINNED_PYYAML_VERSION}\n"
    if not SCHEDULE_REQUIREMENTS.is_file():
        raise ValueError(f"missing Schedule renderer dependency pin: {SCHEDULE_REQUIREMENTS}")
    if SCHEDULE_REQUIREMENTS.read_text(encoding="utf-8") != expected_requirements:
        raise ValueError(
            "Schedule renderer dependency pin does not match the renderer's expected PyYAML version"
        )
    actual_version = getattr(yaml, "__version__", None)
    if actual_version != PINNED_PYYAML_VERSION:
        raise ValueError(
            f"Schedule renderer requires PyYAML {PINNED_PYYAML_VERSION}; found {actual_version!r}"
        )


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


def schedule_renderer_control_paths() -> list[Path]:
    """Return non-clause inputs that can change reviewed renderer semantics."""

    paths = [REG / "states.yml"]
    paths.extend(sorted(REG.glob("state-outcome-overrides*.yml")))
    status_override = REG / "schedule-status-overrides.yml"
    if status_override.exists():
        paths.append(status_override)

    # The parser release is a semantic input: SafeLoader/compose determine the
    # values and node graph consumed by the renderer. Bind its exact pin along
    # with the renderer implementation so old evidence cannot survive either a
    # dependency upgrade or an algorithm change.
    paths.append(SCHEDULE_REQUIREMENTS)
    paths.append(Path(__file__).resolve())
    return paths


def schedule_compatibility_input_paths() -> list[Path]:
    """Return the complete byte-exact input set a compatibility review must bind."""

    validate_renderer_environment()
    result: list[Path] = []
    seen: set[Path] = set()
    for path in schedule_clause_source_paths() + schedule_renderer_control_paths():
        resolved = path.resolve()
        if resolved in seen:
            continue
        if not path.is_file():
            raise ValueError(f"missing Schedule renderer compatibility input: {path}")
        seen.add(resolved)
        result.append(path)
    return result


def validate_target_license_artifact(review: dict[str, Any]) -> None:
    """Bind compatibility evidence to exact frozen and working License bytes."""

    binding = review.get("target_license_artifact")
    if not isinstance(binding, dict):
        raise ValueError("Schedule compatibility review requires target_license_artifact")

    path_text = binding.get("path")
    digest = binding.get("sha256")
    expected_path = str(TARGET_LICENSE_ARTIFACT.relative_to(ROOT))
    if path_text != expected_path:
        raise ValueError(
            "Schedule compatibility review target License path does not match renderer target artifact"
        )
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("Schedule compatibility review target License has invalid sha256")
    if not TARGET_LICENSE_ARTIFACT.is_file():
        raise ValueError(f"missing target License artifact: {TARGET_LICENSE_ARTIFACT}")
    if not WORKING_LICENSE.is_file():
        raise ValueError(f"missing working License artifact: {WORKING_LICENSE}")

    frozen_digest = sha256(TARGET_LICENSE_ARTIFACT)
    if digest != frozen_digest:
        raise ValueError("Schedule compatibility review target License SHA-256 is stale")
    working_digest = sha256(WORKING_LICENSE)
    if working_digest != frozen_digest:
        raise ValueError(
            "working LICENSE differs from the exact target License artifact bound by the Schedule compatibility review"
        )


def expected_source_bindings(sources: list[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): sha256(path) for path in sources}


def parse_source_bindings(bindings: Any, label: str) -> dict[str, str]:
    if not isinstance(bindings, list):
        raise ValueError(f"{label} requires source bindings")
    actual: dict[str, str] = {}
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError(f"{label} source binding must be a mapping")
        path = binding.get("path")
        digest = binding.get("sha256")
        if not isinstance(path, str) or not path:
            raise ValueError(f"{label} source binding is missing path")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"{label} source binding has invalid sha256")
        if path in actual:
            raise ValueError(f"duplicate {label} source binding: {path}")
        actual[path] = digest
    return actual


def assert_exact_source_bindings(
    bindings: Any, sources: list[Path], label: str
) -> None:
    actual = parse_source_bindings(bindings, label)
    expected = expected_source_bindings(sources)
    if actual != expected:
        missing = sorted(expected.keys() - actual.keys())
        extra = sorted(actual.keys() - expected.keys())
        stale = sorted(
            path for path in expected.keys() & actual.keys() if expected[path] != actual[path]
        )
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if extra:
            details.append(f"extra={','.join(extra)}")
        if stale:
            details.append(f"stale={','.join(stale)}")
        raise ValueError(
            f"{label} does not bind the exact renderer source set"
            + (f" ({'; '.join(details)})" if details else "")
        )


def validate_reviewed_at(value: Any) -> None:
    """Accept exact ISO dates or timezone-aware RFC 3339 review timestamps.

    PyYAML may materialize unquoted YAML date/timestamp scalars as ``date`` or
    ``datetime`` objects, so those semantic scalar types are accepted directly.
    String values are validated lexically and semantically without trimming or
    other normalization. RFC 3339 clock and offset fields are range-bound before
    any YAML timestamp constructor can normalize malformed input. Leap seconds
    are intentionally rejected rather than relying on a mutable table of
    historical UTC insertion instants.
    """

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Schedule compatibility evidence reviewed_at timestamp must include a timezone"
            )
        return
    if isinstance(value, date):
        return
    if not isinstance(value, str) or not value:
        raise ValueError("Schedule compatibility evidence requires reviewed_at")

    text = value
    if DATE_RE.fullmatch(text):
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(
                "Schedule compatibility evidence reviewed_at must be a valid ISO date or RFC 3339 timestamp"
            ) from exc
        return

    match = RFC3339_RE.fullmatch(text)
    if match is None:
        raise ValueError(
            "Schedule compatibility evidence reviewed_at must be a valid ISO date or RFC 3339 timestamp"
        )
    try:
        date.fromisoformat(match.group("date"))
    except ValueError as exc:
        raise ValueError(
            "Schedule compatibility evidence reviewed_at must be a valid ISO date or RFC 3339 timestamp"
        ) from exc


def validate_evidence_yaml_node(node: Node, seen_nodes: set[int] | None = None) -> None:
    """Require an unambiguous, alias-free standard YAML subset for evidence."""

    if seen_nodes is None:
        seen_nodes = set()
    node_id = id(node)
    if node_id in seen_nodes:
        raise ValueError("Schedule compatibility evidence must not use YAML aliases")
    seen_nodes.add(node_id)

    if isinstance(node, MappingNode):
        if node.tag != STANDARD_MAPPING_TAG:
            raise ValueError("Schedule compatibility evidence mapping uses an unsupported YAML tag")
        seen_keys: set[str] = set()
        for key_node, value_node in node.value:
            if not isinstance(key_node, ScalarNode):
                raise ValueError("Schedule compatibility evidence keys must be scalar strings")
            key = key_node.value
            if key == "<<" or key_node.tag == "tag:yaml.org,2002:merge":
                raise ValueError("Schedule compatibility evidence must not use YAML merge keys")
            if key_node.tag != STANDARD_STRING_TAG:
                raise ValueError("Schedule compatibility evidence keys must use the YAML string tag")

            # Key nodes participate in the same object-identity graph as values.
            # Visiting them closes aliases that reuse a previously anchored
            # scalar as a mapping key (or vice versa).
            validate_evidence_yaml_node(key_node, seen_nodes)

            if key in seen_keys:
                raise ValueError(f"duplicate Schedule compatibility evidence key: {key}")
            seen_keys.add(key)
            validate_evidence_yaml_node(value_node, seen_nodes)
        return

    if isinstance(node, SequenceNode):
        if node.tag != STANDARD_SEQUENCE_TAG:
            raise ValueError("Schedule compatibility evidence sequence uses an unsupported YAML tag")
        for item in node.value:
            validate_evidence_yaml_node(item, seen_nodes)
        return

    if isinstance(node, ScalarNode):
        if node.tag not in ALLOWED_SCALAR_TAGS:
            raise ValueError("Schedule compatibility evidence scalar uses an unsupported YAML tag")
        return

    raise ValueError("Schedule compatibility evidence contains an unsupported YAML node")


def reviewed_at_lexical_value(path: Path) -> str:
    """Validate the complete evidence tree and return the original reviewed_at scalar."""

    text = path.read_text(encoding="utf-8")
    document = yaml.compose(text)
    if not isinstance(document, MappingNode):
        raise ValueError(f"{path}: expected mapping at document root")
    validate_evidence_yaml_node(document)

    reviewed_at_node: ScalarNode | None = None
    for key_node, value_node in document.value:
        if key_node.value == "reviewed_at":
            if not isinstance(value_node, ScalarNode):
                raise ValueError("Schedule compatibility evidence requires scalar reviewed_at")
            reviewed_at_node = value_node
            break

    if reviewed_at_node is None:
        raise ValueError("Schedule compatibility evidence requires reviewed_at")
    return reviewed_at_node.value


def load_content_addressed_compatibility_evidence(
    pointer: dict[str, Any], sources: list[Path], target_license: str
) -> dict[str, Any]:
    """Resolve immutable compatibility evidence from a SHA-256-addressed file."""

    reference = pointer.get("review_evidence")
    if not isinstance(reference, dict):
        raise ValueError("complete Schedule compatibility review requires review_evidence")
    evidence_id = reference.get("id")
    evidence_path_text = reference.get("path")
    if (
        not isinstance(evidence_id, str)
        or len(evidence_id) != 64
        or any(c not in "0123456789abcdef" for c in evidence_id)
    ):
        raise ValueError("Schedule compatibility review evidence id must be lowercase SHA-256")

    expected_path_text = f"reviews/schedule-compatibility/{evidence_id}.yml"
    if evidence_path_text != expected_path_text:
        raise ValueError("Schedule compatibility evidence path must match its content hash id")
    evidence_path = ROOT / expected_path_text
    if not evidence_path.is_file():
        raise ValueError(f"missing Schedule compatibility evidence: {evidence_path}")
    if sha256(evidence_path) != evidence_id:
        raise ValueError("Schedule compatibility evidence content hash does not match review id")

    # Inspect the complete original YAML tree before safe_load can collapse
    # duplicate/merge keys, resolve aliases, or normalize timestamp fields.
    validate_reviewed_at(reviewed_at_lexical_value(evidence_path))
    evidence = load_yaml(evidence_path)
    if evidence.get("schema_version") != 1:
        raise ValueError("unsupported Schedule compatibility evidence schema_version")
    if evidence.get("target_license") != target_license:
        raise ValueError("Schedule compatibility evidence targets a different License")
    if evidence.get("target_license_artifact") != pointer.get("target_license_artifact"):
        raise ValueError("Schedule compatibility evidence target License binding does not match pointer")
    validate_target_license_artifact(evidence)

    reviewer = evidence.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Schedule compatibility evidence requires reviewer")
    validate_reviewed_at(evidence.get("reviewed_at"))
    if evidence.get("conclusion") != "compatible":
        raise ValueError("Schedule compatibility evidence conclusion must be compatible")

    assert_exact_source_bindings(
        evidence.get("sources"), sources, "Schedule compatibility evidence"
    )
    return evidence


def validate_compatibility_review(sources: list[Path], target_license: str) -> bool:
    """Require immutable evidence before compatibility may be marked complete.

    The mutable registry is only a pointer. A complete state is accepted only
    when it resolves to a content-addressed evidence record whose own bytes bind
    the exact target License artifact and complete renderer input set.
    """

    validate_renderer_environment()
    if not COMPATIBILITY_REVIEW.is_file():
        raise ValueError(f"missing compatibility review gate: {COMPATIBILITY_REVIEW}")
    review = load_yaml(COMPATIBILITY_REVIEW)
    if review.get("schema_version") != 3:
        raise ValueError("unsupported Schedule compatibility review schema_version")
    if review.get("target_license") != target_license:
        raise ValueError(
            "Schedule compatibility review target does not match renderer target License"
        )
    validate_target_license_artifact(review)

    status = review.get("status")
    if status == "pending":
        if review.get("review_evidence") not in (None, {}):
            raise ValueError("pending Schedule compatibility review must not claim review evidence")
        if review.get("review_id") is not None or review.get("sources") is not None:
            raise ValueError("pending Schedule compatibility review must not use legacy mutable claims")
        return False
    if status != "complete":
        raise ValueError("Schedule compatibility review status must be pending or complete")

    if review.get("review_id") is not None or review.get("sources") is not None:
        raise ValueError("complete Schedule compatibility review must use immutable review_evidence only")
    load_content_addressed_compatibility_evidence(review, sources, target_license)
    return True


def compatibility_status(
    target_license: str = TARGET_LICENSE,
) -> tuple[set[str], list[Path], bool]:
    """Validate clause declarations and exact-input revalidation for a target License."""

    declarations: set[str] = set()
    incompatible: list[Path] = []
    clause_sources = schedule_clause_source_paths()
    if not clause_sources:
        raise ValueError("no frozen Schedule clause sources found")

    for path in clause_sources:
        data = load_yaml(path)
        declared = data.get("compatible_license")
        if not isinstance(declared, str) or not declared.strip():
            raise ValueError(f"{path}: missing compatible_license declaration")
        declared = declared.strip()
        declarations.add(declared)
        if declared != target_license:
            incompatible.append(path)

    review_complete = validate_compatibility_review(
        schedule_compatibility_input_paths(), target_license
    )
    if review_complete and incompatible:
        raise ValueError(
            "complete Schedule compatibility review conflicts with source compatible_license declarations"
        )
    return declarations, incompatible, review_complete


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
    declared_licenses, incompatible_sources, compatibility_review_complete = (
        compatibility_status()
    )
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

    compatibility_ready = not incompatible_sources and compatibility_review_complete
    if not compatibility_ready:
        declared_text = ", ".join(sorted(declared_licenses))
        compatibility_lines = [
            f"> Target working License: **{TARGET_LICENSE}**.",
            ">",
            f"> Exact target License artifact: **{TARGET_LICENSE_ARTIFACT.relative_to(ROOT)}** (`{sha256(TARGET_LICENSE_ARTIFACT)}`).",
            ">",
            f"> Compatibility status: **NOT YET VALIDATED for {TARGET_LICENSE}**.",
            ">",
            f"> Frozen clause inputs currently declare compatibility with: **{declared_text}**.",
            ">",
            "> Explicit content-addressed License-and-renderer-input compatibility revalidation: **PENDING**.",
            ">",
            "> This candidate MUST NOT be labelled compatible with the target License until every consumed frozen clause source is explicitly revalidated for that exact License and a content-addressed evidence record binds the exact target License artifact plus the complete renderer clause/control/code/environment input set by SHA-256.",
        ]
    else:
        compatibility_lines = [
            f"> Intended compatibility: **{TARGET_LICENSE} only**.",
            ">",
            f"> Exact target License artifact: **{TARGET_LICENSE_ARTIFACT.relative_to(ROOT)}** (`{sha256(TARGET_LICENSE_ARTIFACT)}`).",
            ">",
            "> Exact target License artifact and complete renderer input set: **compatibility revalidation complete and SHA-256-bound by immutable evidence**.",
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
        "compatibility_review_complete": int(compatibility_review_complete),
    }
    return "\n".join(lines), counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    text, counts = render()
    compatibility_ready = (
        counts["compatibility_mismatches"] == 0
        and counts["compatibility_review_complete"] == 1
    )
    compatibility = (
        "ready"
        if compatibility_ready
        else f"pending ({counts['compatibility_mismatches']} source files require target revalidation; explicit review complete={bool(counts['compatibility_review_complete'])})"
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
