#!/usr/bin/env python3
"""Fail closed on high-confidence named people hidden from the broad State-dossier audit.

The broad discovery audit is intentionally organization/project oriented. This companion
checker covers concrete personal names in legal/custody/remediation and explicit human-role
prose without turning a victim, defendant, journalist, activist, lawyer, writer or other
case subject into a culpable actor. Identity coverage is neutral.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict

import audit_private_org_mentions as rendered
import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


ROLE_RE = re.compile(
    r"(?i)\b(?:journalist|reporter|activist|lawyer|attorney|writer|blogger|defender|"
    r"human[- ]rights defender|rights defender|peace activist|opposition leader|politician|"
    r"academic|researcher|student|unionist|trade unionist|cleric|pastor|imam|priest|doctor|physician)\s+"
)
ACTION_OF_RE = re.compile(
    r"(?i)\b(?:arrest|detention|prosecution|conviction|sentencing|sentence|trial|imprisonment|"
    r"incarceration|abduction|disappearance|release|pardon|clemency|killing|execution)\s+of\s+"
    r"(?:(?:journalist|reporter|activist|lawyer|attorney|writer|blogger|defender|"
    r"human[- ]rights defender|rights defender|peace activist|opposition leader|politician|"
    r"academic|researcher|student|unionist|trade unionist|cleric|pastor|imam|priest|doctor|physician)\s+)?"
)
PASSIVE_ACTION_RE = re.compile(
    r"\b(?P<name>[^\n,;:()]{2,100}?)\s+(?i:was|were|is|remains|remain)\s+"
    r"(?i:arrested|detained|prosecuted|convicted|sentenced|imprisoned|incarcerated|abducted|"
    r"disappeared|released|pardoned|executed|killed)\b"
)
FRONTMATTER_PERSON_KEYS = {"provisional_scope", "adversarial_result"}
LOCAL_STOP = {
    "current evidence", "current reporting", "the evidence", "the dossier", "the state",
    "the government", "this review", "the review", "the law", "the court", "the regime",
}


def add_name(out: list[str], candidate: str | None) -> None:
    if not candidate:
        return
    value = " ".join(candidate.split()).strip(" ,;:()[]{}\"'“”‘’*_`")
    if not value or value.casefold() in LOCAL_STOP:
        return
    if strict.valid_name(value, allow_all_caps=True) and value not in out:
        out.append(value)


def names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    # Reuse the hardened Schedule parser for cue-before-name and prefix-name legal forms.
    for name in strict.strict_named_mentions(prose, "scope-reference"):
        add_name(names, name)

    for match in ROLE_RE.finditer(prose):
        add_name(names, strict.leading_name_phrase(prose[match.end():], allow_all_caps=True))

    for match in ACTION_OF_RE.finditer(prose):
        add_name(names, strict.leading_name_phrase(prose[match.end():], allow_all_caps=True))

    for match in PASSIVE_ACTION_RE.finditer(prose):
        fragment = match.group("name")
        # Only the trailing name-shaped phrase before the passive verb is relevant. Walk
        # backwards over at most eight tokens and choose the longest valid suffix.
        tokens = strict.NAME_TOKEN_RE.findall(fragment)
        for width in range(min(8, len(tokens)), 1, -1):
            candidate = " ".join(tokens[-width:])
            if strict.valid_name(candidate, allow_all_caps=True):
                add_name(names, candidate)
                break
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_prose(prose):
            if exact.materialized_person_ids_for_mention(name, entities, identity_index, state):
                continue
            # A title-cased institution following a human-looking cue must not manufacture a
            # Person debt when an exact current non-Person identity owns that surface.
            if exact.materialized_non_person_ids_for_mention(name, entities, identity_index, state):
                continue
            key = (state, schedule.norm(name))
            row = failures_by_key.setdefault(key, {
                "state": state,
                "name": name,
                "normalized": schedule.norm(name),
                "reason": "high-confidence named person lacks neutral ABox identity",
                "occurrences": [],
            })
            row["occurrences"].append({"source": source, "location": location, "snippet": snippet[:420]})

    for path, front, body_offset in dossiers:
        state = front["iso3"]
        source = str(path.relative_to(base.ROOT))
        for field in FRONTMATTER_PERSON_KEYS:
            value = front.get(field)
            if isinstance(value, str) and value.strip():
                inspect(state=state, source=source, location=f"frontmatter:{field}", prose=value, snippet=value)

        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        for rel_line, snippet, prose in rendered.rendered_prose_segments(text[body_offset:]):
            inspect(
                state=state, source=source, location=f"line:{line_offset + rel_line}",
                prose=prose, snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    assert "Hassan Bouras" in names_from_prose("arbitrary detention of journalist Hassan Bouras continued")
    assert "Boualem Sansal" in names_from_prose("the November 2025 pardon of writer Boualem Sansal")
    assert "Jane Doe" in names_from_prose("journalist Jane Doe reported the detention")
    assert "Jane Doe" in names_from_prose("Jane Doe was detained pending trial")
    assert names_from_prose("the Human Rights Commission was established") == []
    assert names_from_prose("current evidence was reviewed") == []
    print("State dossier named-person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_PEOPLE=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("State dossier named-person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
