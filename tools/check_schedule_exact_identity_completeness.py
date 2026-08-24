#!/usr/bin/env python3
"""Independently fail closed on Schedule identities hidden by resolver heuristics.

This checker is deliberately separate from audit_schedule_reference_coverage.py.  It
re-derives exact embedded ABox matches with stricter surface handling and verifies that
all such identities are present in the audit row's resolved_ids.  It also rejects
scope values that the audit marked context-only when they contain a high-confidence
named-person pattern.  The result is a defense-in-depth gate: changing the primary
resolver cannot silently reintroduce longest-match, short-alias or named-person gaps.

Identity coverage is not attribution.  Matching an identity here does not infer
participation, control, operation, supply, culpability or a governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
from entity_identity_resolution import build_name_index, eligible_in_state


PERSON_WORD = r"[^\W\d_]+(?:['’.-][^\W\d_]+)*"
PERSON_NAME_AFTER_CUE_RE = re.compile(
    rf"^\s*({PERSON_WORD})(?:\s+(?:de|del|da|das|do|dos|van|von|bin|bint|ibn|al|el|la|le))?\s+({PERSON_WORD})",
    re.UNICODE | re.I,
)
PERSON_CUE_RE = re.compile(
    r"(?:[—–/]|"
    r"\b(?:arrest|detention|prosecution|proceeding|proceedings|case|measures|measure|sentence|conviction|investigation|trial)"
    r"\s+(?:of|against|concerning)|"
    r"\b(?:concerning|against|named|involving))",
    re.I,
)
PERSON_STOPWORDS = {
    "act", "administration", "agency", "amendment", "article", "articles", "barracks", "border",
    "branch", "bureau", "centre", "center", "code", "commission", "committee", "constitutional",
    "council", "court", "criminal", "department", "digital", "directorate", "force", "forces",
    "government", "indigenous", "institution", "law", "media", "ministry", "national", "nations",
    "office", "operation", "peoples", "police", "prison", "procedure", "project", "prosecution",
    "public", "secretariat", "security", "service", "state", "supreme", "tribunal", "united", "unit",
    "units", "university",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
}


def looks_like_acronym_surface(text: str) -> bool:
    """Recognize conventional all- or mixed-case acronym surfaces.

    ECtHR and DoD are intentionally accepted.  Requiring two uppercase letters keeps
    ordinary one-word aliases from being promoted into the short case-sensitive path.
    """
    if not text or any(ch.isspace() for ch in text) or len(text) > 16:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.-]+", text):
        return False
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 2 and sum(ch.isupper() for ch in letters) >= 2


def named_person_signal(raw: str) -> bool:
    """High-precision signal for a named person embedded in free-form scope text.

    The detector is intentionally cue-bound rather than generic NER: it catches names
    after person-oriented legal/custody phrases and em-dash/slash case labels while
    avoiding laws, institutions, dates and locations such as `Law No. 32735` or
    `Queen Elizabeth Barracks`.
    """
    for cue in PERSON_CUE_RE.finditer(raw):
        match = PERSON_NAME_AFTER_CUE_RE.match(raw[cue.end(): cue.end() + 120])
        if not match:
            continue
        first, second = match.groups()
        if not first[0].isupper() or not second[0].isupper():
            continue
        if first.lower() in PERSON_STOPWORDS or second.lower() in PERSON_STOPWORDS:
            continue
        if (len(first) > 1 and first.isupper()) or (len(second) > 1 and second.isupper()):
            continue
        return True
    return False


def independent_exact_matches(
    raw: str,
    entities: list[dict],
    identity_index,
    expected: str,
    state: str | None,
) -> list[str]:
    """Return every exact State-safe ABox surface embedded in raw.

    This intentionally does not use the audit's precomputed `acronym` flag so mixed-case
    aliases cannot inherit a classification bug from the primary resolver.
    """
    raw_norm = schedule.norm(raw)
    padded_raw = f" {raw_norm} "
    matches: set[str] = set()
    for entity in entities:
        if not eligible_in_state(identity_index, entity["id"], state):
            continue
        is_project = entity["type"] in {"Project", "Deployment"}
        if expected == "actor" and is_project:
            continue
        if expected == "project" and not is_project:
            continue

        forms = entity.get("surface_forms") or [
            {"text": alias, "normalized": alias}
            for alias in entity.get("aliases", [])
        ]
        for form in forms:
            text = form.get("text") or ""
            alias = form.get("normalized") or schedule.norm(text)
            if not alias:
                continue
            if looks_like_acronym_surface(text):
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])", raw):
                    matches.add(entity["id"])
                    break
            elif len(alias) >= 6 and f" {alias} " in padded_raw:
                matches.add(entity["id"])
                break
    return sorted(matches)


def expected_kind(row: dict) -> str:
    kind = row.get("kind")
    if kind == "actor-reference":
        return "actor"
    if kind == "project-reference":
        return "project"
    return "identity"


def completeness_failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    failures: list[dict] = []
    for row in report.get("references", []):
        raw = row.get("raw") or ""
        state = row.get("state")
        expected = expected_kind(row)
        exact_ids = independent_exact_matches(raw, entities, identity_index, expected, state)
        resolved_ids = sorted(set(row.get("resolved_ids") or []))
        missing_ids = sorted(set(exact_ids) - set(resolved_ids))

        if row.get("status") == "context-only":
            if exact_ids:
                failures.append({
                    "reason": "context-only scope contains exact current ABox identity",
                    "state": state,
                    "field": row.get("field"),
                    "source": row.get("source"),
                    "raw": raw,
                    "missing_ids": exact_ids,
                })
            elif named_person_signal(raw):
                failures.append({
                    "reason": "context-only scope contains high-confidence named-person identity",
                    "state": state,
                    "field": row.get("field"),
                    "source": row.get("source"),
                    "raw": raw,
                    "missing_ids": [],
                })
            continue

        if missing_ids:
            failures.append({
                "reason": "Schedule row omits one or more exact current ABox identities",
                "state": state,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "reported_ids": resolved_ids,
                "missing_ids": missing_ids,
                "resolution_source": row.get("resolution_source"),
                "status": row.get("status"),
            })
    return failures


def self_test() -> None:
    assert looks_like_acronym_surface("FACA")
    assert looks_like_acronym_surface("ECtHR")
    assert looks_like_acronym_surface("DoD")
    assert not looks_like_acronym_surface("Media")
    assert named_person_signal("TUR 6/2026 — Esra Işık / Halime Şaman enforcement project")
    assert named_person_signal("the prosecution of Esra Işık and measures concerning Halime Şaman")
    assert not named_person_signal("implementation of Law No. 32735 under the new rules")
    assert not named_person_signal("Queen Elizabeth Barracks, Nabua, Suva")

    synthetic = [
        {
            "id": "INSTITUTION-AAA-COURT",
            "type": "Institution",
            "aliases": ["state security court"],
            "surface_forms": [{"text": "State Security Court", "normalized": "state security court"}],
        },
        {
            "id": "AGENCY-AAA-MEDIA",
            "type": "Agency",
            "aliases": ["media commission"],
            "surface_forms": [{"text": "Media Commission", "normalized": "media commission"}],
        },
        {
            "id": "INSTITUTION-AAA-ECHR",
            "type": "Institution",
            "aliases": ["ecthr"],
            "surface_forms": [{"text": "ECtHR", "normalized": "ecthr"}],
        },
        {
            "id": "AGENCY-AAA-DOD",
            "type": "Agency",
            "aliases": ["dod"],
            "surface_forms": [{"text": "DoD", "normalized": "dod"}],
        },
    ]
    raw_entities = [
        {"id": "INSTITUTION-AAA-COURT", "type": "Institution", "name": "State Security Court", "aliases": []},
        {"id": "AGENCY-AAA-MEDIA", "type": "Agency", "name": "Media Commission", "aliases": []},
        {"id": "INSTITUTION-AAA-ECHR", "type": "Institution", "name": "European Court", "aliases": ["ECtHR"]},
        {"id": "AGENCY-AAA-DOD", "type": "Agency", "name": "Defence Department", "aliases": ["DoD"]},
    ]
    idx = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    composite = independent_exact_matches(
        "State Security Court / Media Commission", synthetic, idx, "actor", "AAA"
    )
    assert composite == ["AGENCY-AAA-MEDIA", "INSTITUTION-AAA-COURT"]
    mixed = independent_exact_matches("ECtHR / DoD", synthetic, idx, "identity", "AAA")
    assert mixed == ["AGENCY-AAA-DOD", "INSTITUTION-AAA-ECHR"]

    report = {
        "references": [{
            "kind": "actor-reference",
            "state": "AAA",
            "field": "candidate_parties",
            "source": "x.yml",
            "raw": "State Security Court / Media Commission",
            "status": "resolved",
            "resolution_source": "jurisdiction-safe-canonical-name-or-alias",
            "resolved_ids": ["INSTITUTION-AAA-COURT"],
        }]
    }
    failures = completeness_failures(report, synthetic, idx)
    assert failures and failures[0]["missing_ids"] == ["AGENCY-AAA-MEDIA"]
    print("Schedule exact-identity completeness self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    report = schedule.audit()
    entities, _, identity_index = schedule.load_entities()
    failures = completeness_failures(report, entities, identity_index)
    if failures:
        print("HIDDEN_SCHEDULE_IDENTITIES=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule exact-identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
