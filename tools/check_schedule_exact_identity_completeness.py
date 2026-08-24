#!/usr/bin/env python3
"""Independently fail closed on Schedule identities hidden by resolver heuristics.

This checker is deliberately separate from audit_schedule_reference_coverage.py. It
re-derives exact embedded ABox matches with stricter surface handling and verifies that
all such identities are present in the audit row's resolved_ids. It also checks every
scope row for high-confidence named people, including rows already resolved to another
current identity: each detected person must either be a current exact Person identity or
be explicitly named in a reviewed deferred/partial-deferred reason.

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
PERSON_PAIR_LABEL_RE = re.compile(
    rf"[—–]\s*({PERSON_WORD})\s+({PERSON_WORD})\s*/\s*({PERSON_WORD})\s+({PERSON_WORD})(?=\s|$)",
    re.UNICODE,
)
PERSON_CUE_RE = re.compile(
    r"(?:"
    r"\b(?:arrest|detention|prosecution|proceeding|proceedings|case|measures|measure|sentence|conviction|investigation|trial)"
    r"\s+(?:of|against|concerning)|"
    r"\b(?:concerning|against|named|involving))",
    re.I,
)
PERSON_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
PERSON_PREFIX_QUALIFIER = r"(?:[A-Z]{2,}(?:-[A-Za-z]+)+)"
PERSON_PREFIX_CUE_RE = re.compile(
    rf"(?:^|[—–/;:]\s*)"
    rf"({PERSON_WORD}(?:\s+{PERSON_WORD}){{1,4}}?)"
    rf"(?:\s+{PERSON_MONTH}\s+\d{{4}}|\s+\d{{4}})?"
    rf"(?:\s+{PERSON_PREFIX_QUALIFIER})?"
    rf"\s+(?:arrest|detention|prosecution|proceeding|proceedings|case|sentence|conviction|investigation|trial)\b",
    re.UNICODE | re.I,
)
PERSON_PARTICLES = {"al", "bin", "bint", "da", "das", "de", "del", "do", "dos", "el", "ibn", "la", "le", "van", "von"}
PERSON_STOPWORDS = {
    "act", "administration", "agency", "amendment", "article", "articles", "barracks", "border",
    "branch", "bureau", "centre", "center", "code", "commission", "committee", "constitutional",
    "council", "court", "criminal", "department", "digital", "directorate", "force", "forces",
    "government", "indigenous", "institution", "interior", "law", "media", "military", "ministry",
    "national", "nations", "office", "operation", "peoples", "police", "prison", "procedure", "project",
    "prosecution", "public", "secretariat", "security", "service", "state", "supreme", "tribunal", "united",
    "unit", "units", "university",
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


def _valid_name_word(token: str) -> bool:
    lower = token.lower()
    return (
        bool(token)
        and token[0].isupper()
        and lower not in PERSON_STOPWORDS
        and not (len(token) > 1 and token.isupper())
    )


def _add_mention(mentions: list[str], tokens: list[str]) -> None:
    capitalized = [token for token in tokens if token.lower() not in PERSON_PARTICLES]
    if len(capitalized) < 2 or any(not _valid_name_word(token) for token in capitalized):
        return
    mention = " ".join(tokens).strip()
    if mention and mention not in mentions:
        mentions.append(mention)


def named_person_mentions(raw: str) -> list[str]:
    """Extract high-precision named-person candidates from scope text.

    Names are accepted in three narrow forms: after a person-oriented legal/custody cue,
    in the paired case-label form `— First Last / First Last`, or at the start of a scope
    (and immediately after a strong separator) when the name itself precedes a legal cue,
    e.g. `Jane Doe June 2026 detention project`. Bare slash/dash separators are otherwise
    not person cues, avoiding place/facility false positives such as `El Haoud Prison`,
    `Yaoundé Military Tribunal` and `San Martin qualifying deployment`. A compact technical
    qualifier such as `EIT-law` may sit between the person and legal cue without being
    absorbed into the person's name.
    """
    mentions: list[str] = []

    for match in PERSON_PAIR_LABEL_RE.finditer(raw):
        first_a, first_b, second_a, second_b = match.groups()
        _add_mention(mentions, [first_a, first_b])
        _add_mention(mentions, [second_a, second_b])

    for match in PERSON_PREFIX_CUE_RE.finditer(raw):
        _add_mention(mentions, match.group(1).split())

    for cue in PERSON_CUE_RE.finditer(raw):
        segment = raw[cue.end(): cue.end() + 160]
        pos = 0
        tokens: list[str] = []
        capitalized_words = 0
        for _ in range(7):
            match = PERSON_TOKEN_RE.match(segment, pos)
            if not match:
                break
            token = match.group(1)
            lower = token.lower()
            if lower in PERSON_PARTICLES and tokens:
                tokens.append(token)
                pos = match.end()
                continue
            if not _valid_name_word(token):
                break
            tokens.append(token)
            capitalized_words += 1
            pos = match.end()
            if capitalized_words >= 4:
                break
        if capitalized_words >= 2:
            _add_mention(mentions, tokens)

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


def materialized_ids_for_mention(
    mention: str,
    entities: list[dict],
    identity_index,
    state: str | None,
    *,
    person: bool | None,
) -> list[str]:
    """Return current State-safe IDs whose exact surface equals a detected mention."""
    mention_norm = schedule.norm(mention)
    matches: set[str] = set()
    for entity in entities:
        is_person = entity.get("type") == "Person"
        if person is True and not is_person:
            continue
        if person is False and is_person:
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


def materialized_person_ids_for_mention(
    mention: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    return materialized_ids_for_mention(mention, entities, identity_index, state, person=True)


def materialized_non_person_ids_for_mention(
    mention: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    return materialized_ids_for_mention(mention, entities, identity_index, state, person=False)


def expected_kind(row: dict) -> str:
    kind = row.get("kind")
    if kind == "actor-reference":
        return "actor"
    if kind == "project-reference":
        return "project"
    return "identity"


def explicitly_defers_person(row: dict, mention: str) -> bool:
    """Require a reviewed deferral to identify the unmatched person by whole name."""
    if row.get("resolution_source") != "reviewed-disposition":
        return False
    if row.get("status") not in {"deferred", "partial-deferred"}:
        return False
    mention_norm = schedule.norm(mention)
    reason_norm = schedule.norm(row.get("disposition_reason") or "")
    if not mention_norm or not reason_norm:
        return False
    return f" {mention_norm} " in f" {reason_norm} "


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

            # A title-cased exact organization/institution/agency surface is not person debt.
            # Its coverage is already enforced above by the all-identity exact-match invariant.
            if materialized_non_person_ids_for_mention(mention, entities, identity_index, state):
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
    assert named_person_mentions("Jane Doe June 2026 detention project") == ["Jane Doe"]
    assert named_person_mentions("Khariq Anhar EIT-law prosecution project") == ["Khariq Anhar"]
    assert not named_person_signal("implementation of Law No. 32735 under the new rules")
    assert not named_person_signal("Queen Elizabeth Barracks, Nabua, Suva")
    assert named_person_mentions("Hassan Bouras detention project — DZA 3/2026 / El Haoud Prison, El Bayadh") == ["Hassan Bouras"]
    assert named_person_mentions("Abdu Karim Ali detention / Yaoundé Military Tribunal life-sentence project") == ["Abdu Karim Ali"]
    assert not named_person_signal("Polish Border Guard / Interior Belarus-border asylum-suspension and pushback project")
    assert not named_person_signal("Exterminio Total / San Martin qualifying deployment")

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
            "id": "ORG-HUMAN-RIGHTS-WATCH",
            "type": "Organization",
            "aliases": [schedule.norm("Human Rights Watch")],
            "surface_forms": [{"text": "Human Rights Watch", "normalized": schedule.norm("Human Rights Watch")}],
        },
        {
            "id": "PERSON-AAA-ESRA-ISIK",
            "type": "Person",
            "aliases": [schedule.norm("Esra Işık")],
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
        {"id": "ORG-HUMAN-RIGHTS-WATCH", "type": "Organization", "name": "Human Rights Watch", "aliases": []},
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
    assert materialized_non_person_ids_for_mention("Human Rights Watch", synthetic, idx, "AAA") == ["ORG-HUMAN-RIGHTS-WATCH"]

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

    prefix_person_bypass = {
        "references": [{
            **resolved_person_bypass["references"][0],
            "raw": "Jane Doe June 2026 detention project / UNHCR",
        }]
    }
    failures = completeness_failures(prefix_person_bypass, synthetic, idx)
    assert any(f.get("person") == "Jane Doe" and "unmaterialized" in f["reason"] for f in failures)

    exact_org_after_cue = {
        "references": [{
            "kind": "scope-identity-reference",
            "state": "AAA",
            "field": "project_boundary",
            "source": "x.yml",
            "raw": "case concerning Human Rights Watch",
            "status": "resolved",
            "resolution_source": "state-safe-exact-embedded-name-or-alias",
            "resolved_ids": ["ORG-HUMAN-RIGHTS-WATCH"],
            "disposition_reason": None,
        }]
    }
    assert completeness_failures(exact_org_after_cue, synthetic, idx) == []

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

    ann_row = {
        "resolution_source": "reviewed-disposition",
        "status": "partial-deferred",
        "disposition_reason": "Joann Lee is identity-deferred pending materialization.",
    }
    assert not explicitly_defers_person(ann_row, "Ann Lee")
    ann_row["disposition_reason"] = "Ann Lee is identity-deferred pending materialization."
    assert explicitly_defers_person(ann_row, "Ann Lee")

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