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

import audit_private_org_mentions as rendered
import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_schedule_named_identity_strictness as strict


ROLE = (
    r"human[- ]rights defender|rights defender|peace activist|opposition leader|"
    r"attorney general|public defender|prime minister|deputy minister|vice president|"
    r"member of parliament|trade unionist|"
    r"journalist|reporter|activist|lawyer|attorney|writer|blogger|defender|critic|dissident|"
    r"politician|academic|researcher|student|unionist|cleric|pastor|imam|priest|doctor|physician|"
    r"president|minister|governor|mayor|judge|justice|prosecutor|ombudsperson|commissioner|"
    r"general|colonel|major|captain|senator|representative|secretary|mp"
)
ROLE_RE = re.compile(rf"(?i)\b(?:{ROLE})\s+")
ACTION_OF_RE = re.compile(
    rf"(?i)\b(?:arrest|detention|prosecution|conviction|sentencing|sentence|trial|imprisonment|"
    rf"incarceration|abduction|disappearance|release|pardon|clemency|killing|execution)\s+of\s+"
    rf"(?:(?:{ROLE})(?:/(?:{ROLE}))?\s+)?"
)
ACTION_TARGET_RE = re.compile(r"(?i)\b(?:charges?|prosecution|proceedings?|case|appeal)\s+against\s+")
CASE_OF_RE = re.compile(r"(?i)\b(?:case|appeal|proceedings?)\s+of\s+")
REMEDIAL_TARGET_RE = re.compile(
    r"(?i)\b(?:dropped|dismissed|withdrew|withdrew charges against|granted bail to|freed|acquitted|cleared)\s+(?:the\s+)?"
)
NAME_WORD = r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’-]*|[A-Z]\.)"
NAME_PARTICLE = r"(?:de|del|da|dos|van|von|bin|binti|al|el)"
NAME_PHRASE = rf"{NAME_WORD}(?:\s+(?:{NAME_WORD}|{NAME_PARTICLE})){{1,7}}"
NAME_SEPARATOR = r"(?:\s*,\s*|\s+(?i:and)\s+|\s*&\s*)"
NAME_LIST = rf"{NAME_PHRASE}(?:{NAME_SEPARATOR}{NAME_PHRASE}){{0,4}}"
CUSTODY_STATE = (
    r"arrested|detained|prosecuted|convicted|sentenced|imprisoned|incarcerated|abducted|"
    r"disappeared|released|pardoned|executed|killed|incommunicado|missing|unaccounted\s+for"
)
PASSIVE_ACTION_RE = re.compile(
    rf"\b(?P<names>{NAME_LIST})\s+(?i:was|were|is|remains|remain|remained)\s+(?i:{CUSTODY_STATE})\b"
)
ACTIVE_ACTION_RE = re.compile(
    rf"\b(?i:arrested|detained|prosecuted|convicted|sentenced|imprisoned|incarcerated|abducted|"
    rf"released|pardoned|executed|killed|freed|acquitted|cleared)\s+"
    rf"(?:(?i:(?:{ROLE}))(?:/(?i:(?:{ROLE})))?\s+)?(?P<names>{NAME_LIST})"
)
FRONTMATTER_PERSON_KEYS = {"provisional_scope", "adversarial_result"}
LOCAL_STOP = {
    "current evidence", "current reporting", "the evidence", "the dossier", "the state",
    "the government", "this review", "the review", "the law", "the court", "the regime",
    "unlawful combatants",
}
NON_PERSON_TERMS = {
    "Administration", "Agency", "Army", "Assembly", "Authority", "Bank", "Brigade", "Bureau",
    "Command", "Commission", "Committee", "Council", "Court", "Department", "Directorate",
    "Force", "Forces", "Government", "Institute", "Law", "Ministry", "Navy", "Office",
    "Operation", "Parliament", "Platform", "Police", "Program", "Programme", "Project",
    "Service", "Services", "System", "Tribunal", "University",
}


def clean_candidate(candidate: str | None) -> str | None:
    if not candidate:
        return None
    value = " ".join(candidate.split()).strip(" ,;:()[]{}\"'“”‘’*_`")
    value = re.sub(r"(?:['’]s)$", "", value).strip()
    value = re.sub(rf"(?i)^(?:{ROLE})\s+", "", value).strip()
    return value or None


def add_name(out: list[str], candidate: str | None) -> None:
    value = clean_candidate(candidate)
    if not value or value.casefold() in LOCAL_STOP:
        return
    if set(value.replace("-", " ").split()) & NON_PERSON_TERMS:
        return
    if strict.valid_name(value, allow_all_caps=True) and value not in out:
        out.append(value)


def split_name_list(value: str) -> list[str]:
    return [part for part in re.split(r"\s*,\s*|\s+(?:and|&)\s+", value, flags=re.I) if part.strip()]


def leading_action_names(tail: str) -> list[str]:
    tail = tail.lstrip()
    if re.match(r"(?i)^(?:of\b|the\b)", tail):
        return []
    match = re.match(rf"(?P<names>{NAME_LIST})", tail)
    if not match:
        return []
    names = split_name_list(match.group("names"))
    remainder = tail[match.end():].lstrip()
    if re.match(r"(?i)^Law\b", remainder):
        return []
    cleaned: list[str] = []
    for name in names:
        value = clean_candidate(name)
        if value:
            cleaned.append(value)
    return cleaned


def names_from_prose(prose: str) -> list[str]:
    names: list[str] = []

    for match in ROLE_RE.finditer(prose):
        for name in leading_action_names(prose[match.end():]):
            add_name(names, name)

    for regex in (ACTION_OF_RE, ACTION_TARGET_RE, CASE_OF_RE, REMEDIAL_TARGET_RE):
        for match in regex.finditer(prose):
            for name in leading_action_names(prose[match.end():]):
                add_name(names, name)

    for regex in (PASSIVE_ACTION_RE, ACTIVE_ACTION_RE):
        for match in regex.finditer(prose):
            for name in split_name_list(match.group("names")):
                add_name(names, name)
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_prose(prose):
            if exact.materialized_person_ids_for_mention(name, entities, identity_index, state):
                continue
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
    assert "Hugues Comlan Sossoukpè" in names_from_prose("detention/prosecution of journalist/defender Hugues Comlan Sossoukpè after transfer")
    assert "Boualem Sansal" in names_from_prose("the November 2025 pardon of writer Boualem Sansal")
    assert names_from_prose("writer Boualem Sansal. Clemency does not itself dismantle the system") == ["Boualem Sansal"]
    assert names_from_prose("opposition leader Victoire Ingabire. UN reporting continued") == ["Victoire Ingabire"]
    assert names_from_prose("TRANSITIONAL-JUSTICE EXCLUSIONS. Current attributable abuse remains sufficient") == []
    assert "Jane Doe" in names_from_prose("journalist Jane Doe reported the detention")
    assert "Jane Doe" in names_from_prose("authorities arrested Jane Doe after the protest")
    assert set(names_from_prose("authorities detained Jane Doe and John Roe after the protest")) == {"Jane Doe", "John Roe"}
    assert "Jane Doe" in names_from_prose("Jane Doe was detained pending trial")
    assert "Jane Doe" in names_from_prose("Jane Doe remained incommunicado after transfer")
    assert "Jane Doe" in names_from_prose("Jane Doe remained unaccounted for after transfer")
    assert set(names_from_prose("Luis Pacheco and Héctor Chaclán remained imprisoned")) == {"Luis Pacheco", "Héctor Chaclán"}
    assert names_from_prose("Defender Joaquín Elo Ayeto remained unaccounted for after transfer") == ["Joaquín Elo Ayeto"]
    assert "Jane Doe" in names_from_prose("Prime Minister Jane Doe announced the measure")
    assert "Jane Doe" in names_from_prose("Attorney General Jane Doe announced the measure")
    assert "Paul Chambers" in names_from_prose("prosecutors dropped the Paul Chambers lèse-majesté case in 2025")
    assert "Jane Doe" in names_from_prose("the case of Jane Doe remains under review")
    assert "Jane Doe" in names_from_prose("the court acquitted Jane Doe after trial")
    assert "Kokila Annamalai" in names_from_prose("rights groups called for charges against Kokila Annamalai to be dropped")
    assert "Martinez Zogo" in names_from_prose("the trial concerning journalist Martinez Zogo's killing resumed")
    assert names_from_prose("the court dismissed the Constitutional Court challenge") == []
    assert names_from_prose("Minister of Interior announced the measure") == []
    assert names_from_prose("detention involving Hong Kong democracy/human-rights defenders") == []
    assert names_from_prose("investigation of North Sinai abuses") == []
    assert names_from_prose("Independent San Martín investigation and judicial review") == []
    assert names_from_prose("the Incarceration of Unlawful Combatants Law detention process") == []
    assert names_from_prose("UPHOLD / NARROW S. The detention basis remains current") == []
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
