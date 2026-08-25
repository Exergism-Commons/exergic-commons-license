#!/usr/bin/env python3
"""Fail closed on named Schedule identities that the heuristic audit can hide.

This is an independent companion to check_schedule_exact_identity_completeness.py.
It deliberately re-parses person/name-like surfaces so a bug in that checker's person
regex cannot silently discharge identity debt. It covers actor, project and scope rows,
preserves hyphenated surnames, independently re-derives every exact current Person
surface, and accepts reviewed deferral only when the exact complete name is followed by
explicit deferral language.

Identity coverage is not attribution and does not infer participation, control,
operation, supply, culpability, membership or a governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
from entity_identity_resolution import build_name_index


NAME_WORD = r"[^\W\d_]+(?:['’.-][^\W\d_]+)*"
NAME_TOKEN_RE = re.compile(NAME_WORD, re.UNICODE)
MONTH = r"(?i:January|February|March|April|May|June|July|August|September|October|November|December)"
LEGAL_CUE = r"(?i:arrest|detention|prosecution|proceeding|proceedings|case|sentence|conviction|investigation|trial)"
# Technical qualifiers are deliberately closed-world here. A shape-based uppercase/hyphen
# heuristic can consume legitimate surnames such as SMITH-Jones. Add a qualifier only when
# the repository actually uses it as non-name syntax and cover it with a regression test.
TECH_QUALIFIER = r"(?:EIT-law)"
PREFIX_CUE_RE = re.compile(
    rf"(?:^|[—–/;:]\s*)"
    rf"({NAME_WORD}(?:\s+{NAME_WORD}){{1,4}}?)"
    rf"(?:\s+{MONTH}\s+\d{{4}}|\s+\d{{4}})?"
    rf"(?:\s+{TECH_QUALIFIER})?"
    rf"\s+{LEGAL_CUE}\b"
    rf"(?=\s+(?i:project|activity|case|matter|proceeding)\b|\s*(?:$|[/;,—–]))",
    re.UNICODE,
)
CUE_BEFORE_RE = re.compile(
    rf"(?i:(?:arrest|detention|prosecution|proceeding|proceedings|case|measures|measure|sentence|conviction|investigation|trial)"
    rf"\s+(?:of|against|concerning)|(?:concerning|against|named|involving))"
    rf"\s+({NAME_WORD}(?:\s+{NAME_WORD}){{1,3}})",
    re.UNICODE,
)
PAIR_RE = re.compile(
    rf"[—–]\s*({NAME_WORD}\s+{NAME_WORD})\s*/\s*({NAME_WORD}\s+{NAME_WORD})(?=\s|$)",
    re.UNICODE,
)
MATTER_NAME_RE = re.compile(
    rf"(?:^|\b\d{{4}}\s+)({NAME_WORD}(?:\s+{NAME_WORD}){{1,3}})\s+(?i:matter)\b",
    re.UNICODE,
)
ACTOR_FRAGMENT_RE = re.compile(rf"^({NAME_WORD}(?:\s+{NAME_WORD}){{1,3}})$", re.UNICODE)
CAPACITY_TAIL_RE = re.compile(
    r"(?i)^(?:only\b|where\b|when\b|to\s+the\s+extent\b|subject\s+to\b|as\b|"
    r"in\s+(?:the|its|their|this|that)\b)"
)

PARTICLES = {"al", "bin", "bint", "da", "das", "de", "del", "do", "dos", "el", "ibn", "la", "le", "van", "von"}
STOPWORDS = {
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
DEFER_BRIDGE = {"is", "remains", "remain", "was", "were", "explicitly", "identity", "identity-deferred", "name", "named"}
DEFER_WORDS = {"deferred", "identity-deferred", "deferral"}


def valid_name(mention: str) -> bool:
    tokens = NAME_TOKEN_RE.findall(mention)
    semantic = [token for token in tokens if token.casefold() not in PARTICLES]
    if len(semantic) < 2:
        return False
    for token in semantic:
        lower = token.casefold()
        if not token[0].isupper() or lower in STOPWORDS:
            return False
        if len(token) > 1 and token.isupper():
            return False
    return True


def add_unique(out: list[str], mention: str) -> None:
    mention = " ".join(mention.split()).strip(" ,;:()[]")
    if mention and valid_name(mention) and mention not in out:
        out.append(mention)


def actor_component_name(fragment: str) -> str | None:
    """Return a complete leading actor name, allowing only recognized capacity prose.

    A bare full component remains valid. If the component has a comma, only an explicitly
    recognized capacity/conditional tail may be stripped. This catches e.g.
    `Jane Doe, only where participation is established` without turning arbitrary prose
    into a person candidate.
    """
    cleaned = fragment.strip(" ,;:()[]")
    match = ACTOR_FRAGMENT_RE.fullmatch(cleaned)
    if match:
        return match.group(1)
    if "," not in cleaned:
        return None
    head, tail = cleaned.split(",", 1)
    if not CAPACITY_TAIL_RE.match(tail.strip()):
        return None
    match = ACTOR_FRAGMENT_RE.fullmatch(head.strip())
    return match.group(1) if match else None


def strict_named_mentions(raw: str, kind: str) -> list[str]:
    """Extract full person/name-like identities without truncating surnames."""
    mentions: list[str] = []
    for match in PAIR_RE.finditer(raw):
        add_unique(mentions, match.group(1))
        add_unique(mentions, match.group(2))
    for match in PREFIX_CUE_RE.finditer(raw):
        add_unique(mentions, match.group(1))
    for match in CUE_BEFORE_RE.finditer(raw):
        add_unique(mentions, match.group(1))
    if kind == "project-reference":
        for match in MATTER_NAME_RE.finditer(raw):
            add_unique(mentions, match.group(1))

    # Actor fields are identity-bearing by definition. For list-like composites, inspect
    # slash/semicolon components. A recognized comma-delimited capacity tail may follow the
    # leading complete name; exact organizations are suppressed later, while an unknown
    # named component must be explicitly reviewed rather than disappearing in vague prose.
    if kind == "actor-reference":
        for fragment in re.split(r"\s*(?:/|;)\s*", raw):
            candidate = actor_component_name(fragment)
            if candidate:
                add_unique(mentions, candidate)
    return mentions


def reason_tokens(text: str) -> list[str]:
    return [token.casefold() for token in NAME_TOKEN_RE.findall(text)]


def explicitly_defers_complete_name(row: dict, mention: str) -> bool:
    """Require the exact complete name immediately followed by deferral grammar.

    This intentionally rejects prefixes such as `Ann Lee` in `Ann Lee Jones ...` and
    `Ann Lee-Smith ...`; the token after the exact name must begin the deferral phrase.
    """
    if row.get("resolution_source") != "reviewed-disposition":
        return False
    if row.get("status") not in {"deferred", "partial-deferred"}:
        return False
    mention_tokens = reason_tokens(mention)
    tokens = reason_tokens(row.get("disposition_reason") or "")
    if not mention_tokens or not tokens:
        return False
    n = len(mention_tokens)
    for i in range(0, len(tokens) - n + 1):
        if tokens[i:i + n] != mention_tokens:
            continue
        tail = tokens[i + n:i + n + 6]
        if not tail:
            continue
        if tail[0] not in DEFER_BRIDGE | DEFER_WORDS:
            continue
        for token in tail:
            if token in DEFER_WORDS or token.endswith("-deferred"):
                return True
            if token not in DEFER_BRIDGE:
                break
    return False


def checked_row_kind(kind: str) -> bool:
    return kind in {"actor-reference", "project-reference", "scope-reference", "scope-identity-reference"}


def failures(report: dict, entities: list[dict], identity_index) -> list[dict]:
    out: list[dict] = []
    person_entities = [entity for entity in entities if entity.get("type") == "Person"]
    for row in report.get("references", []):
        kind = row.get("kind") or ""
        if not checked_row_kind(kind):
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        resolved_ids = set(row.get("resolved_ids") or [])

        # Person coverage is independent of the row's role. A project reference can name a
        # materialized Person while correctly resolving its project identity; both identities
        # must remain visible in reviewed coverage.
        exact_person_ids = exact.independent_exact_matches(
            raw, person_entities, identity_index, "identity", state
        )
        missing_exact_people = sorted(set(exact_person_ids) - resolved_ids)
        if missing_exact_people:
            out.append({
                "reason": "Schedule row omits one or more exact current Person identities",
                "state": state,
                "kind": kind,
                "field": row.get("field"),
                "source": row.get("source"),
                "raw": raw,
                "missing_ids": missing_exact_people,
                "reported_ids": sorted(resolved_ids),
                "resolution_source": row.get("resolution_source"),
                "status": row.get("status"),
            })

        for mention in strict_named_mentions(raw, kind):
            person_ids = exact.materialized_person_ids_for_mention(mention, entities, identity_index, state)
            if person_ids:
                # Exact Person omissions were already reported above from an independent
                # surface scan; avoid duplicate diagnostics for the same debt.
                continue

            non_person_ids = exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state)
            if non_person_ids:
                # Exact non-Person coverage is enforced by the existing all-identity gate.
                continue

            if not explicitly_defers_complete_name(row, mention):
                out.append({
                    "reason": "named actor/project/scope identity lacks exact materialization or explicit complete-name deferral",
                    "state": state,
                    "kind": kind,
                    "field": row.get("field"),
                    "source": row.get("source"),
                    "raw": raw,
                    "name": mention,
                    "reported_ids": sorted(resolved_ids),
                    "resolution_source": row.get("resolution_source"),
                    "status": row.get("status"),
                })
    return out


def self_test() -> None:
    assert strict_named_mentions("Jane Doe June 2026 detention project", "scope-identity-reference") == ["Jane Doe"]
    assert strict_named_mentions("Khariq Anhar EIT-law prosecution project", "scope-identity-reference") == ["Khariq Anhar"]
    assert strict_named_mentions("Jane Doe Smith-Jones prosecution project", "scope-identity-reference") == ["Jane Doe Smith-Jones"]
    assert strict_named_mentions("Jane Doe SMITH-Jones prosecution project", "scope-identity-reference") == ["Jane Doe SMITH-Jones"]
    assert "Jane Doe" in strict_named_mentions("Human Rights Watch / Jane Doe", "actor-reference")
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / Jane Doe, only where participation is established", "actor-reference"
    )
    assert "MacPherson Mukuka" in strict_named_mentions(
        "Cyber Crimes Act enforcement, including the frozen 2026 MacPherson Mukuka matter", "project-reference"
    )
    assert "Counter Terrorist" not in strict_named_mentions(
        "Sri Lanka Police — Counter Terrorist Investigation Division (CTID), only in actual detention activity",
        "actor-reference",
    )

    ann = {
        "resolution_source": "reviewed-disposition",
        "status": "partial-deferred",
        "disposition_reason": "Ann Lee remains explicitly identity-deferred pending materialization.",
    }
    assert explicitly_defers_complete_name(ann, "Ann Lee")
    ann["disposition_reason"] = "Joann Lee is identity-deferred pending materialization."
    assert not explicitly_defers_complete_name(ann, "Ann Lee")
    ann["disposition_reason"] = "Ann Lee Jones is identity-deferred pending materialization."
    assert not explicitly_defers_complete_name(ann, "Ann Lee")
    ann["disposition_reason"] = "Ann Lee-Smith is identity-deferred pending materialization."
    assert not explicitly_defers_complete_name(ann, "Ann Lee")

    synthetic = [
        {"id": "ORG-HRW", "type": "Organization", "aliases": [schedule.norm("Human Rights Watch")],
         "surface_forms": [{"text": "Human Rights Watch", "normalized": schedule.norm("Human Rights Watch")}]},
        {"id": "PERSON-MACPHERSON", "type": "Person", "aliases": [schedule.norm("MacPherson Mukuka")],
         "surface_forms": [{"text": "MacPherson Mukuka", "normalized": schedule.norm("MacPherson Mukuka")}]},
    ]
    raw_entities = [
        {"id": "ORG-HRW", "type": "Organization", "name": "Human Rights Watch", "aliases": []},
        {"id": "PERSON-MACPHERSON", "type": "Person", "name": "MacPherson Mukuka", "aliases": []},
    ]
    idx = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)
    actor_bypass = {"references": [{
        "kind": "actor-reference", "state": "AAA", "field": "candidate_parties", "source": "x.yml",
        "raw": "Human Rights Watch / Jane Doe, only where participation is established", "status": "partial-deferred",
        "resolution_source": "reviewed-disposition", "resolved_ids": ["ORG-HRW"],
        "disposition_reason": "Human Rights Watch is bound exactly; remaining actor context is deferred.",
    }]}
    found = failures(actor_bypass, synthetic, idx)
    assert any(item.get("name") == "Jane Doe" for item in found)
    actor_bypass["references"][0]["disposition_reason"] = (
        "Human Rights Watch is bound exactly; Jane Doe remains explicitly identity-deferred pending materialization."
    )
    assert failures(actor_bypass, synthetic, idx) == []

    project_bypass = {"references": [{
        "kind": "project-reference", "state": "AAA", "field": "candidate_projects", "source": "x.yml",
        "raw": "Cyber Crimes Act enforcement, including the frozen 2026 MacPherson Mukuka matter",
        "status": "resolved", "resolution_source": "reviewed-disposition", "resolved_ids": ["PROJECT-AAA-X"],
        "disposition_reason": "Exact project bound.",
    }]}
    found = failures(project_bypass, synthetic, idx)
    assert any(item.get("missing_ids") == ["PERSON-MACPHERSON"] for item in found)
    project_bypass["references"][0]["resolved_ids"].append("PERSON-MACPHERSON")
    assert failures(project_bypass, synthetic, idx) == []
    print("Schedule strict named-identity self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    report = schedule.audit()
    entities, _, identity_index = schedule.load_entities()
    found = failures(report, entities, identity_index)
    if found:
        print("HIDDEN_SCHEDULE_NAMED_IDENTITIES=" + json.dumps(found, ensure_ascii=False, sort_keys=True))
        return 2
    print("Schedule strict named-identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
