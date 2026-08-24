#!/usr/bin/env python3
"""Independently fail closed on Schedule identities hidden by resolver heuristics.

This checker is deliberately separate from audit_schedule_reference_coverage.py. It
re-derives exact embedded ABox matches with stricter surface handling and verifies that
all such identities are present in the audit row's resolved_ids. It also checks every
scope row for cue-bound named people, including rows already resolved to another current
identity: each detected person must either be a current exact Person identity or be
explicitly named in a reviewed deferred/partial-deferred reason.

The result is a defense-in-depth gate: changing the primary resolver cannot silently
reintroduce longest-match, short-alias, context-only, reviewed-disposition or named-person
gaps. Identity coverage is not attribution and does not infer participation, control,
operation, supply, culpability or a governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
from entity_identity_resolution import build_name_index, eligible_in_state


PERSON_WORD = r"[^\W\d_]+(?:['’.-][^\W\d_]+)*"
PERSON_TOKEN_RE = re.compile(rf"\s*({PERSON_WORD})", re.UNICODE)
PERSON_CUE_RE = re.compile(
    r"(?:[—–/]|"
    r"\b(?:arrest|detention|prosecution|proceeding|proceedings|case|measures|measure|sentence|conviction|investigation|trial)"
    r"\s+(?:of|against|concerning)|"
    r"\b(?:concerning|against|named|involving))",
    re.I,
)
PERSON_PARTICLES = {"al", "bin", "bint", "da", "das", "de", "del", "do", "dos", "el", "ibn", "la", "le", "van", "von"}
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
    """Recognize short exact acronym surfaces, including mixed case and letter-digits.

    `ECtHR` and `DoD` qualify through multiple uppercase letters. `M23` qualifies through
    an uppercase letter plus a digit. Matching remains case-sensitive and is performed only
    against current State-safe ABox surfaces, so ordinary lowercase words do not enter the
    short-alias path.
    """
    if not text or any(ch.isspace() for ch in text) or len(text) > 16:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.-]+", text):
        return False
    letters = [ch for ch in text if ch.isalpha()]
    digits = [ch for ch in text if ch.isdigit()]
    uppercase = sum(ch.isupper() for ch in letters)
    return (len(letters) >= 2 and uppercase >= 2) or (uppercase >= 1 and bool(digits))


def named_person_mentions(raw: str) -> list[str]:
    """Extract high-precision person-name candidates after person-oriented scope cues.

    This is intentionally not generic NER. It consumes consecutive title-cased name tokens
    (with common lowercase surname particles) immediately after legal/custody cues or case
    separators. That keeps the detector narrow while allowing more than two-token names.
    """
    mentions: list[str] = []
    for cue in PERSON_CUE_RE.finditer(raw):
        segment = raw[cue.end(): cue.end() + 160]
        pos = 0
        tokens: list[str] = []
        capitalized_words = 0
        for _ in range(6):
            match = PERSON_TOKEN_RE.match(segment, pos)
            if not match:
                break
            token = match.group(1)
            lower = token.lower()
            if lower in PERSON_PARTICLES and tokens:
                tokens.append(token)
                pos = match.end()
                continue
            if not token[0].isupper() or lower in PERSON_STOPWORDS:
                break
            if len(token) > 1 and token.isupper():
                break
            tokens.append(token)
            capitalized_words += 1
            pos = match.end()
            if capitalized_words >= 4:
                break
        if capitalized_words < 2:
            continue
        mention = " ".join(tokens).strip()
        if mention and mention not in mentions:
            mentions.append(mention)
    return mentions


def named_person_signal(raw: str) -> bool:
    return bool(named_person_mentions(raw))


def independent_exact_matches(
    raw: str,
    entities: list[dict],
    identity_index,
    expected: str,
    state: str | None,
) -> list[str]:
    """Return every exact State-safe ABox surface embedded in raw.

    This intentionally does not use the audit's precomputed `acronym` flag, so mixed-case
    and letter-digit aliases cannot inherit a classification bug from the primary resolver.
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


def materialized_person_ids_for_mention(
    mention: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    """Return current State-safe Person IDs whose exact surface equals a detected mention."""
    mention_norm = schedule.norm(mention)
    matches: set[str] = set()
    for entity in entities:
        if entity.get("type") != "Person":
            continue
        if not eligible_in_state(identity_index, entity["id"], state):
            continue
        forms = entity.get("surface_forms") or [
            {"text": alias, "normalized": alias}
            for alias in entity.get("aliases", [])
        ]
        for form in forms:
            alias = form.get("normalized") or schedule.norm(form.get("text") or "")
            if alias and alias == mention_norm:
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


def explicitly_defers_person(row: dict, mention: str) -> bool:
    """Require a reviewed deferral to identify the unmatched person by name."""
    if row.get("resolution_source") != "reviewed-disposition":
        return False
    if row.get("status") not in {"deferred", "partial-deferred"}:
        return False
    reason = row.get("disposition_reason") or ""
    return schedule.norm(mention) in schedule.norm(reason)


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
            # Do not stop here: named-person completeness is checked below for every scope row.
        elif missing_ids:
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

        # Named-person debt must not disappear merely because another identity resolved the row.
        if row.get("kind") not in {"scope-reference", "scope-identity-reference"}:
            continue
        for mention in named_person_mentions(raw):
            person_ids = materialized_person_ids_for_mention(mention, entities, identity_index, state)
            if person_ids:
                missing_person_ids = sorted(set(person_ids) - set(resolved_ids))
                if missing_person_ids:
                    failures.append({
                        "reason": "scope row omits exact current named-person identity",
                        "state": state,
                        "field": row.get("field"),
                        "source": row.get("source"),
                        "raw": raw,
                        "person": mention,
                        "reported_ids": resolved_ids,
                        "missing_ids": missing_person_ids,
                        "resolution_source": row.get("resolution_source"),
                        "status": row.get("status"),
                    })
                continue
            if not explicitly_defers_person(row, mention):
                failures.append({
                    "reason": "scope row contains unmaterialized named person without explicit reviewed deferral",
                    "state": state,
                    "field": row.get("field"),
                    "source": row.get("source"),
                    "raw": raw,
                    "person": mention,
                    "reported_ids": resolved_ids,
                    "resolution_source": row.get("resolution_source"),
                    "status": row.get("status"),
                })
    return failures


def self_test() -> None:
    assert looks_like_acronym_surface("FACA")
    assert looks_like_acronym_surface("ECtHR")
    assert looks_like_acronym_surface("DoD")
    assert looks_like_acronym_surface("M23")
    assert not looks_like_acronym_surface("Media")
    assert not looks_like_acronym_surface("m23")

    assert named_person_mentions("TUR 6/2026 — Esra Işık / Halime Şaman enforcement project") == ["Esra Işık", "Halime Şaman"]
    assert named_person_signal("the prosecution of Esra Işık and measures concerning Halime Şaman")
    assert named_person_mentions("UNHCR measures concerning Jane Doe") == ["Jane Doe"]
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
        {
            "id": "ORG-AAA-M23",
            "type": "Organization",
            "aliases": ["m23"],
            "surface_forms": [{"text": "M23", "normalized": "m23"}],
        },
        {
            "id": "ORG-GLOBAL-UNHCR",
            "type": "Organization",
            "aliases": ["unhcr"],
            "surface_forms": [{"text": "UNHCR", "normalized": "unhcr"}],
        },
        {
            "id": "PERSON-AAA-ESRA-ISIK",
            "type": "Person",
            "aliases": ["esra i k"],
            "surface_forms": [{"text": "Esra Işık", "normalized": schedule.norm("Esra Işık")}],
        },
    ]
    raw_entities = [
        {"id": "INSTITUTION-AAA-COURT", "type": "Institution", "name": "State Security Court", "aliases": []},
        {"id": "AGENCY-AAA-MEDIA", "type": "Agency", "name": "Media Commission", "aliases": []},
        {"id": "INSTITUTION-AAA-ECHR", "type": "Institution", "name": "European Court", "aliases": ["ECtHR"]},
        {"id": "AGENCY-AAA-DOD", "type": "Agency", "name": "Defence Department", "aliases": ["DoD"]},
        {"id": "ORG-AAA-M23", "type": "Organization", "name": "March 23 Movement", "aliases": ["M23"]},
        {"id": "ORG-GLOBAL-UNHCR", "type": "Organization", "name": "UNHCR", "aliases": []},
        {"id": "PERSON-AAA-ESRA-ISIK", "type": "Person", "name": "Esra Işık", "aliases": []},
    ]
    idx = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)

    composite = independent_exact_matches(
        "State Security Court / Media Commission", synthetic, idx, "actor", "AAA"
    )
    assert composite == ["AGENCY-AAA-MEDIA", "INSTITUTION-AAA-COURT"]
    mixed = independent_exact_matches("ECtHR / DoD", synthetic, idx, "identity", "AAA")
    assert mixed == ["AGENCY-AAA-DOD", "INSTITUTION-AAA-ECHR"]
    letter_digit = independent_exact_matches("State Security Court / M23", synthetic, idx, "actor", "AAA")
    assert letter_digit == ["INSTITUTION-AAA-COURT", "ORG-AAA-M23"]
    assert materialized_person_ids_for_mention("Esra Işık", synthetic, idx, "AAA") == ["PERSON-AAA-ESRA-ISIK"]

    longest_match_report = {
        "references": [{
            "kind": "actor-reference",
            "state": "AAA",
            "field": "candidate_parties",
            "source": "x.yml",
            "raw": "State Security Court / M23",
            "status": "resolved",
            "resolution_source": "jurisdiction-safe-canonical-name-or-alias",
            "resolved_ids": ["INSTITUTION-AAA-COURT"],
        }]
    }
    failures = completeness_failures(longest_match_report, synthetic, idx)
    assert failures and failures[0]["missing_ids"] == ["ORG-AAA-M23"]

    resolved_person_bypass = {
        "references": [{
            "kind": "scope-identity-reference",
            "state": "AAA",
            "field": "project_boundary",
            "source": "x.yml",
            "raw": "UNHCR measures concerning Jane Doe",
            "status": "resolved",
            "resolution_source": "state-safe-exact-embedded-name-or-alias",
            "resolved_ids": ["ORG-GLOBAL-UNHCR"],
            "disposition_reason": None,
        }]
    }
    failures = completeness_failures(resolved_person_bypass, synthetic, idx)
    assert any(f.get("person") == "Jane Doe" and "unmaterialized" in f["reason"] for f in failures)

    reviewed_person_deferral = {
        "references": [{
            "kind": "scope-identity-reference",
            "state": "AAA",
            "field": "project_boundary",
            "source": "x.yml",
            "raw": "UNHCR measures concerning Jane Doe",
            "status": "partial-deferred",
            "resolution_source": "reviewed-disposition",
            "resolved_ids": ["ORG-GLOBAL-UNHCR"],
            "disposition_reason": "UNHCR is bound exactly; Jane Doe remains explicitly identity-deferred pending materialization.",
        }]
    }
    assert completeness_failures(reviewed_person_deferral, synthetic, idx) == []

    vague_person_deferral = {
        "references": [{
            **reviewed_person_deferral["references"][0],
            "disposition_reason": "UNHCR is bound exactly; remaining context is deferred.",
        }]
    }
    failures = completeness_failures(vague_person_deferral, synthetic, idx)
    assert any(f.get("person") == "Jane Doe" for f in failures)

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
