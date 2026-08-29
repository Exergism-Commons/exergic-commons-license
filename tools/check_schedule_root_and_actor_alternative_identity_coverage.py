#!/usr/bin/env python3
"""Fail closed on root metadata identities and actor alternative separators.

This companion guard covers two identity-completeness surfaces independently from the
primary Schedule resolver:

* multi-record document-root metadata must not carry either heuristic identity labels or
  exact current ABox identity surfaces, because root metadata has no State-scoped record;
* reviewed actor rows using ``or`` / ``and/or`` alternatives must not hide an
  unmaterialized named actor behind a generic partial deferral.

Alternative separators are considered only when the row contains an exact current actor
anchor, and separators inside that exact anchor are protected. This keeps identity coverage
separate from participation, control, operation, supply, culpability or governance.
"""
from __future__ import annotations

import argparse
import json
import re

import yaml

import audit_schedule_reference_coverage as schedule
import check_schedule_adversarial_identity_gaps as adversarial
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict
import check_schedule_parenthesized_actor_capacity as parenthesized
from entity_identity_resolution import build_name_index


ALTERNATIVE_SEPARATOR_RE = re.compile(r"\s+(?:and\s*/\s*or|and-or|or)\s+", re.I)
# Record-level ``dossier`` is ordinary schema metadata and remains excluded by the
# adversarial scanner. At a multi-record document root there is no State-scoped record,
# however, so a root ``dossier`` value must be inspected rather than skipped.
DOCUMENT_ROOT_SKIP_FIELDS = frozenset(adversarial.SKIP_EXTRA_FIELDS - {"dossier"})


def root_exact_identity_ids(raw: str, entities: list[dict]) -> list[str]:
    """Return exact current identity surfaces without applying State eligibility.

    A document root has no State, so jurisdiction filtering must not turn a domestic exact
    identity into an accepted root field. We only detect the surface here; we never resolve
    it into a State-scoped role binding. Every exact current non-acronym surface is eligible,
    including short single-token names; normalized token boundaries prevent substring hits.
    """
    raw_norm = schedule.norm(raw)
    padded_raw = f" {raw_norm} "
    matches: set[str] = set()
    for entity in entities:
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            continue
        forms = entity.get("surface_forms") or [
            {"text": alias, "normalized": alias}
            for alias in entity.get("aliases", [])
            if isinstance(alias, str)
        ]
        for form in forms:
            text = form.get("text") or ""
            alias = form.get("normalized") or schedule.norm(text)
            if not text or not alias:
                continue
            if exact.looks_like_acronym_surface(text):
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])", raw):
                    matches.add(entity_id)
                    break
            elif f" {alias} " in padded_raw:
                matches.add(entity_id)
                break
    return sorted(matches)


def document_root_rows() -> list[dict]:
    """Re-scan multi-record roots without applying record-only ``dossier`` exclusion."""
    rows: list[dict] = []
    files = sorted(schedule.FREEZE_DIR.glob("*.yml")) + sorted(schedule.FREEZE_DIR.glob("*.yaml"))
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            continue
        source = str(path.relative_to(schedule.ROOT))
        root = {key: value for key, value in data.items() if key != "records"}
        rows.extend(adversarial.extra_rows_from_mapping(
            root,
            source=source,
            state=None,
            record_index=None,
            skip_fields=set(DOCUMENT_ROOT_SKIP_FIELDS),
            document_root=True,
        ))
    return rows


def document_root_failures(entities: list[dict]) -> list[dict]:
    """Reject any identity-bearing multi-record document-root metadata."""
    found: list[dict] = []
    for row in document_root_rows():
        raw = row.get("raw") or ""
        labels = adversarial.contextual_labels(row)
        exact_ids = root_exact_identity_ids(raw, entities)
        if not labels and not exact_ids:
            continue
        found.append({
            "reason": "identity-bearing multi-record document-root metadata is outside State-scoped Schedule audit; move it into a record",
            "source": row.get("source"),
            "field": row.get("field"),
            "record_index": row.get("record_index"),
            "raw": raw,
            "identity_surfaces": labels,
            "exact_identity_ids": exact_ids,
        })
    return found


def _alternative_segments(raw: str, anchor_spans: list[tuple[int, int]]) -> list[str]:
    """Return non-anchor segments split on ``or`` / ``and/or`` outside exact anchors."""
    if not anchor_spans:
        return []
    separators: list[tuple[int, int]] = []
    for match in ALTERNATIVE_SEPARATOR_RE.finditer(raw):
        if strict._inside_span(match.start(), anchor_spans):
            continue
        separators.append(match.span())
    if not separators:
        return []

    segments: list[tuple[int, int, str]] = []
    start = 0
    for sep_start, sep_end in separators:
        segments.append((start, sep_start, raw[start:sep_start]))
        start = sep_end
    segments.append((start, len(raw), raw[start:]))

    anchored_indexes = {
        index
        for index, (seg_start, seg_end, _) in enumerate(segments)
        if any(seg_start <= anchor_start and anchor_end <= seg_end for anchor_start, anchor_end in anchor_spans)
    }
    if not anchored_indexes:
        return []
    return [segment for index, (_, _, segment) in enumerate(segments) if index not in anchored_indexes]


def actor_alternative_mentions(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    """Extract complete unknown actor alternatives while preserving exact anchor names."""
    anchor_spans = parenthesized.exact_actor_anchor_spans(raw, entities, identity_index, state)
    out: list[str] = []
    for segment in _alternative_segments(raw, anchor_spans):
        candidate = parenthesized.parenthesized_actor_component(segment)
        if candidate is None:
            candidate = strict.actor_component_name(parenthesized.normalized_component(segment))
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def actor_alternative_failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    """Require every detected actor alternative to materialize or be explicitly deferred."""
    found: list[dict] = []
    for row in report.get("references", []):
        if row.get("kind") != "actor-reference":
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        for mention in actor_alternative_mentions(raw, entities, identity_index, state):
            if exact.materialized_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state):
                continue
            if strict.explicitly_defers_complete_name(row, mention):
                continue
            found.append({
                "reason": "or/and-or actor alternative lacks exact materialization or explicit complete-name deferral",
                "state": state,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "name": mention,
                "status": row.get("status"),
                "resolution_source": row.get("resolution_source"),
            })
    return found


def _entity(entity_id: str, entity_type: str, name: str) -> dict:
    return {
        "id": entity_id,
        "type": entity_type,
        "name": name,
        "aliases": [schedule.norm(name)],
        "surface_forms": [{"text": name, "normalized": schedule.norm(name)}],
    }


def self_test() -> None:
    entities = [
        _entity("ORG-HRW", "Organization", "Human Rights Watch"),
        _entity("ORG-META", "Organization", "Meta"),
        _entity("ORG-TRUTH-OR-RECON", "Organization", "Truth or Reconciliation Institute"),
        _entity("AGENCY-AAA-COURT", "Agency", "Example Domestic Court"),
        _entity("PERSON-ESRA", "Person", "Esra Işık"),
    ]
    raw_entities = [
        {"id": row["id"], "type": row["type"], "name": row["name"], "aliases": []}
        for row in entities
    ]
    identity_index = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)

    assert "dossier" in adversarial.SKIP_EXTRA_FIELDS
    assert "dossier" not in DOCUMENT_ROOT_SKIP_FIELDS
    root_dossier_rows = adversarial.extra_rows_from_mapping(
        {"dossier": "Human Rights Watch"},
        source="x.yml",
        state=None,
        record_index=None,
        skip_fields=set(DOCUMENT_ROOT_SKIP_FIELDS),
        document_root=True,
    )
    assert any(row.get("field") == "dossier" and row.get("raw") == "Human Rights Watch" for row in root_dossier_rows)
    record_dossier_rows = adversarial.extra_rows_from_mapping(
        {"dossier": "Human Rights Watch"},
        source="x.yml",
        state="AAA",
        record_index=0,
        skip_fields=adversarial.SKIP_EXTRA_FIELDS,
        document_root=False,
    )
    assert record_dossier_rows == []
    assert root_exact_identity_ids("Source: Human Rights Watch", entities) == ["ORG-HRW"]
    assert root_exact_identity_ids("Source: Meta", entities) == ["ORG-META"]
    assert root_exact_identity_ids("Source: metadata only", entities) == []
    assert root_exact_identity_ids("Source: Example Domestic Court", entities) == ["AGENCY-AAA-COURT"]
    assert root_exact_identity_ids("ordinary neutral metadata", entities) == []
    assert root_exact_identity_ids(root_dossier_rows[-1]["raw"], entities) == ["ORG-HRW"]

    assert actor_alternative_mentions("Human Rights Watch or Jane Doe", entities, identity_index, "AAA") == ["Jane Doe"]
    assert actor_alternative_mentions("Human Rights Watch and/or Jane Doe", entities, identity_index, "AAA") == ["Jane Doe"]
    assert actor_alternative_mentions("Human Rights Watch and / or Jane Doe", entities, identity_index, "AAA") == ["Jane Doe"]
    assert actor_alternative_mentions("Human Rights Watch and-or Jane Doe", entities, identity_index, "AAA") == ["Jane Doe"]
    assert actor_alternative_mentions(
        "Human Rights Watch or Jane Doe (in an advisory capacity).", entities, identity_index, "AAA"
    ) == ["Jane Doe"]
    assert actor_alternative_mentions(
        "Truth or Reconciliation Institute or Jane Doe", entities, identity_index, "AAA"
    ) == ["Jane Doe"]
    assert actor_alternative_mentions("Esra Işık or Jane Doe", entities, identity_index, "AAA") == ["Jane Doe"]
    assert actor_alternative_mentions("Jane Doe or John Smith", entities, identity_index, "AAA") == []

    bypass = {"references": [{
        "kind": "actor-reference",
        "state": "AAA",
        "field": "candidate_parties",
        "source": "x.yml",
        "raw": "Human Rights Watch or Jane Doe",
        "status": "partial-deferred",
        "resolution_source": "reviewed-disposition",
        "resolved_ids": ["ORG-HRW"],
        "disposition_reason": "Human Rights Watch is bound exactly; remaining actor context is deferred.",
    }]}
    problems = actor_alternative_failures(bypass, entities, identity_index)
    assert any(item.get("name") == "Jane Doe" for item in problems)
    bypass["references"][0]["disposition_reason"] = (
        "Human Rights Watch is bound exactly; Jane Doe remains explicitly identity-deferred pending materialization."
    )
    assert actor_alternative_failures(bypass, entities, identity_index) == []
    print("Schedule root/actor-alternative identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    entities, _, identity_index = schedule.load_entities()
    problems = document_root_failures(entities)
    problems.extend(actor_alternative_failures(schedule.audit(), entities, identity_index))
    if problems:
        print("SCHEDULE_ROOT_OR_ALTERNATIVE_IDENTITY_GAPS=" + json.dumps(problems, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule root/actor-alternative identity coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())