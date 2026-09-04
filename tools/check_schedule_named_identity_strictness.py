#!/usr/bin/env python3
"""Fail closed on named Schedule identities that heuristic resolution can hide.

This checker is independent from the primary Schedule resolver. It re-parses person/name
surfaces across actor, project, and scope rows; independently re-derives exact current
Person identities; and accepts reviewed deferral only when the complete name is stated.

For project-reference rows, role binding and identity coverage remain separate:
``resolved_ids`` stays Project/Deployment-only, while an optional reviewed
``identity_coverage_ids`` list may preserve exact Person identities without implying that
those people are projects or participants.

Identity coverage is not attribution and does not infer participation, control,
operation, supply, culpability, membership, or a governance outcome.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import check_schedule_exact_identity_completeness as exact
from entity_identity_resolution import build_name_index, eligible_in_state


NAME_WORD = r"(?:[^\W\d_]\.|[^\W\d_]+(?:['’.-][^\W\d_]+)*)"
NAME_TOKEN_RE = re.compile(NAME_WORD, re.UNICODE)
MONTH = r"(?i:January|February|March|April|May|June|July|August|September|October|November|December)"
LEGAL_CUE = r"(?i:arrest|detention|prosecution|proceeding|proceedings|case|sentence|conviction|investigation|trial)"
# Technical qualifiers are deliberately closed-world. Shape-based acronym heuristics can
# consume legitimate surnames (e.g. SMITH-Jones), so only syntax observed as non-name text
# in the repository belongs here.
TECH_QUALIFIER = r"(?:EIT-law)"
PREFIX_CUE_RE = re.compile(
    rf"(?:^|[—–/;:]\s*)"
    rf"({NAME_WORD}(?:\s+{NAME_WORD}){{1,7}}?)"
    rf"(?:\s+{MONTH}\s+\d{{4}}|\s+\d{{4}})?"
    rf"(?:\s+{TECH_QUALIFIER})?"
    rf"\s+{LEGAL_CUE}\b"
    rf"(?=\s+(?i:project|activity|case|matter|proceeding)\b|\s*(?:$|[/;,—–]))",
    re.UNICODE,
)
# Locate only the legal/name cue. The following name is parsed token-by-token so lowercase
# prose after a name terminates it rather than invalidating the whole candidate.
CUE_BEFORE_HEAD_RE = re.compile(
    rf"(?i:(?:arrest|detention|prosecution|proceeding|proceedings|case|measures|measure|sentence|conviction|investigation|trial)"
    rf"\s+(?:of|against|concerning)|(?:concerning|against|named|involving))\s+",
    re.UNICODE,
)
MATTER_NAME_RE = re.compile(
    rf"(?:^|\b\d{{4}}\s+)({NAME_WORD}(?:\s+{NAME_WORD}){{1,7}})\s+(?i:matter)\b",
    re.UNICODE,
)
ACTOR_LIST_SEPARATOR_RE = re.compile(r"\s+(?:and|&)\s+|,\s*", re.I)
CAPACITY_TAIL_RE = re.compile(
    r"(?i)^(?:only\b|where\b|when\b|acting\b|serving\b|appearing\b|"
    r"to\s+the\s+extent\b|subject\s+to\b|as\b|"
    r"in\s+(?:a|an|the|its|their|this|that)\b)"
)
OPENING_NAME_DELIMS = " \t\r\n\"'“‘([{*_`"

PARTICLES = {"al", "bin", "bint", "da", "das", "de", "del", "do", "dos", "el", "ibn", "la", "le", "van", "von"}
STOPWORDS = {
    "act", "administration", "agency", "amendment", "article", "articles", "barracks", "border",
    "branch", "bureau", "centre", "center", "code", "commission", "committee", "constitutional",
    "control", "council", "court", "criminal", "department", "digital", "directorate", "force", "forces",
    "government", "indigenous", "institution", "interior", "law", "media", "military", "ministry",
    "national", "nations", "office", "operation", "peoples", "police", "prison", "procedure", "project",
    "prosecution", "public", "secretariat", "security", "service", "state", "supreme", "tribunal", "united",
    "unit", "units", "university",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december",
}
DEFER_BRIDGE = {"is", "remains", "remain", "was", "were", "explicitly", "identity", "identity-deferred", "name", "named"}
DEFER_WORDS = {"deferred", "identity-deferred", "deferral"}


def semantic_name_token(token: str, *, allow_all_caps: bool = False) -> bool:
    """Return whether one non-particle token can belong to a person/name candidate."""
    lower = token.casefold()
    if not token or not token[0].isupper() or lower in STOPWORDS:
        return False
    # Hyphenated all-caps surnames are legitimate. Plain all-caps tokens are accepted only
    # in syntactically strong name contexts (legal cues, explicit actor components, etc.).
    if len(token) > 1 and token.isupper() and "-" not in token and not allow_all_caps:
        return False
    return True


def valid_name(mention: str, *, allow_all_caps: bool = False) -> bool:
    tokens = NAME_TOKEN_RE.findall(mention)
    semantic = [token for token in tokens if token.casefold() not in PARTICLES]
    if len(semantic) < 2:
        return False
    return all(semantic_name_token(token, allow_all_caps=allow_all_caps) for token in semantic)


def leading_name_phrase(
    text: str,
    max_tokens: int = 8,
    *,
    allow_all_caps: bool = False,
) -> str | None:
    """Parse a leading complete name, stopping at non-name prose or punctuation."""
    text = text.lstrip(OPENING_NAME_DELIMS)
    accepted: list[str] = []
    position = 0
    for match in NAME_TOKEN_RE.finditer(text):
        if len(accepted) >= max_tokens:
            break
        gap = text[position:match.start()]
        if gap and not gap.isspace():
            break
        token = match.group(0)
        lower = token.casefold()
        if lower in PARTICLES:
            if not accepted:
                break
            accepted.append(token)
        elif semantic_name_token(token, allow_all_caps=allow_all_caps):
            accepted.append(token)
        else:
            break
        position = match.end()
    while accepted and accepted[-1].casefold() in PARTICLES:
        accepted.pop()
    candidate = " ".join(accepted)
    return candidate if valid_name(candidate, allow_all_caps=allow_all_caps) else None


def full_name_phrase(text: str, *, allow_all_caps: bool = False) -> str | None:
    """Accept an entire 2–8-token name fragment and nothing else."""
    cleaned = text.strip(" \t\r\n\"'“”‘’()[]{}*_`,;:")
    if not re.fullmatch(rf"{NAME_WORD}(?:\s+{NAME_WORD}){{1,7}}", cleaned, re.UNICODE):
        return None
    return cleaned if valid_name(cleaned, allow_all_caps=allow_all_caps) else None


def add_unique(out: list[str], mention: str, *, allow_all_caps: bool = False) -> None:
    mention = " ".join(mention.split()).strip(" ,;:()[]{}\"'“”‘’*_`")
    if mention and valid_name(mention, allow_all_caps=allow_all_caps) and mention not in out:
        out.append(mention)


def actor_component_name(fragment: str) -> str | None:
    """Return a complete actor-name component, allowing recognized capacity prose."""
    cleaned = fragment.strip(" \t\r\n,;:[]{}")
    direct = full_name_phrase(cleaned, allow_all_caps=True)
    if direct:
        return direct

    # A trailing parenthesized capacity is equivalent to the already-supported comma tail,
    # but only when its inner text begins with the same closed-world capacity grammar.
    # Arbitrary parenthetical prose is deliberately not discarded.
    parenthesized = re.fullmatch(r"(.+?)\s*\(([^()]*)\)\s*", cleaned)
    if parenthesized and CAPACITY_TAIL_RE.match(parenthesized.group(2).strip()):
        candidate = full_name_phrase(parenthesized.group(1), allow_all_caps=True)
        if candidate:
            return candidate

    if "," not in cleaned:
        return None
    head, tail = cleaned.split(",", 1)
    if not CAPACITY_TAIL_RE.match(tail.strip()):
        return None
    return full_name_phrase(head, allow_all_caps=True)


def pair_label_mentions(raw: str) -> list[str]:
    """Parse `— Name / Name` labels with multi-token and all-caps names."""
    out: list[str] = []
    for marker in re.finditer(r"[—–]\s*", raw):
        tail = raw[marker.end(): marker.end() + 240]
        slash = tail.find("/")
        if slash <= 0:
            continue
        left = full_name_phrase(tail[:slash], allow_all_caps=True)
        right = leading_name_phrase(tail[slash + 1:], allow_all_caps=True)
        if left and right:
            add_unique(out, left, allow_all_caps=True)
            add_unique(out, right, allow_all_caps=True)
    return out


def strict_named_mentions(raw: str, kind: str) -> list[str]:
    """Extract high-precision complete person/name-like identities."""
    mentions: list[str] = []
    for mention in pair_label_mentions(raw):
        add_unique(mentions, mention, allow_all_caps=True)
    for match in PREFIX_CUE_RE.finditer(raw):
        add_unique(mentions, match.group(1), allow_all_caps=True)
    for match in CUE_BEFORE_HEAD_RE.finditer(raw):
        candidate = leading_name_phrase(raw[match.end():], allow_all_caps=True)
        if candidate:
            add_unique(mentions, candidate, allow_all_caps=True)
    if kind == "project-reference":
        for match in MATTER_NAME_RE.finditer(raw):
            add_unique(mentions, match.group(1), allow_all_caps=True)

    if kind == "actor-reference":
        # Slash/semicolon are strong actor separators and can be handled without corpus
        # context. `and`, `&`, and comma are handled separately with an exact-identity anchor.
        for fragment in re.split(r"\s*(?:/|;)\s*", raw):
            candidate = actor_component_name(fragment)
            if candidate:
                add_unique(mentions, candidate, allow_all_caps=True)
    return mentions


def exact_non_person_actor_spans(raw: str, entities: list[dict], identity_index, state: str | None) -> list[tuple[int, int]]:
    """Return spans of exact current non-Person actor identities in the original text."""
    spans: list[tuple[int, int]] = []
    for entity in entities:
        if entity.get("type") in {"Person", "Project", "Deployment"}:
            continue
        if not eligible_in_state(identity_index, entity["id"], state):
            continue
        forms = entity.get("surface_forms") or [
            {"text": alias, "normalized": alias} for alias in entity.get("aliases", [])
        ]
        for form in forms:
            text = form.get("text") or ""
            if not text:
                continue
            if exact.looks_like_acronym_surface(text):
                pattern = rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])"
                flags = 0
            else:
                # Mirror the repository normalizer: exact long surfaces may differ only in
                # punctuation/spacing (e.g. `Human-Rights Watch`). Keep span recovery
                # tolerant to that typography so anchored actor-list checks cannot be
                # bypassed by changing a space to punctuation.
                alias = form.get("normalized") or schedule.norm(text)
                tokens = alias.split()
                if not tokens:
                    continue
                pattern = r"(?<![A-Za-z0-9])" + r"[^A-Za-z0-9]+".join(map(re.escape, tokens)) + r"(?![A-Za-z0-9])"
                flags = re.I
            for match in re.finditer(pattern, raw, flags):
                spans.append(match.span())
    return sorted(set(spans))


def _inside_span(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < position < end for start, end in spans)


def anchored_actor_list_mentions(
    raw: str,
    entities: list[dict],
    identity_index,
    state: str | None,
) -> list[str]:
    """Extract unknown actor components separated by `and`, `&`, or comma.

    These separators are ambiguous inside organization names, so they are considered only
    when the same actor row contains an exact current non-Person actor identity. Separators
    falling *inside* that exact identity surface are ignored, preventing a name such as
    `Ministry of Interior and Narcotics Control` from being split into fake people.
    """
    anchor_spans = exact_non_person_actor_spans(raw, entities, identity_index, state)
    if not anchor_spans:
        return []

    separators: list[tuple[int, int]] = []
    for match in ACTOR_LIST_SEPARATOR_RE.finditer(raw):
        if _inside_span(match.start(), anchor_spans):
            continue
        token = match.group(0)
        if token.lstrip().startswith(",") and CAPACITY_TAIL_RE.match(raw[match.end():].lstrip()):
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

    anchored_segments = {
        index
        for index, (seg_start, seg_end, _) in enumerate(segments)
        if any(seg_start <= anchor_start and anchor_end <= seg_end for anchor_start, anchor_end in anchor_spans)
    }
    if not anchored_segments:
        return []

    out: list[str] = []
    for index, (_, _, segment) in enumerate(segments):
        if index in anchored_segments:
            continue
        candidate = actor_component_name(segment)
        if candidate:
            add_unique(out, candidate, allow_all_caps=True)
    return out


def reason_tokens(text: str) -> list[str]:
    return [token.casefold() for token in NAME_TOKEN_RE.findall(text)]


def explicitly_defers_complete_name(row: dict, mention: str) -> bool:
    """Require the exact complete name immediately followed by deferral grammar."""
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
        if not tail or tail[0] not in DEFER_BRIDGE | DEFER_WORDS:
            continue
        for token in tail:
            if token in DEFER_WORDS or token.endswith("-deferred"):
                return True
            if token not in DEFER_BRIDGE:
                break
    return False


def checked_row_kind(kind: str) -> bool:
    return kind in {"actor-reference", "project-reference", "scope-reference", "scope-identity-reference"}


def load_identity_coverage_entries(by_id: dict[str, dict], identity_index) -> list[dict]:
    """Load and validate supplemental Person identity coverage from reviewed manifests."""
    entries: list[dict] = []
    for path in sorted((schedule.ROOT / "knowledge" / "generated").glob("schedule-reference-dispositions-v*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for index, row in enumerate(data.get("entries", [])):
            ids = row.get("identity_coverage_ids")
            if ids is None:
                continue
            if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
                raise ValueError(f"invalid identity_coverage_ids at {path.relative_to(schedule.ROOT)}#{index}")
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate identity_coverage_ids at {path.relative_to(schedule.ROOT)}#{index}: {ids}")
            if row.get("field") not in schedule.PROJECT_FIELDS:
                raise ValueError(
                    f"identity_coverage_ids are only valid for project-role dispositions: "
                    f"{path.relative_to(schedule.ROOT)}#{index}"
                )
            if row.get("disposition") not in {"bound", "partial-deferred"}:
                raise ValueError(
                    f"identity_coverage_ids require bound/partial-deferred review: "
                    f"{path.relative_to(schedule.ROOT)}#{index}"
                )
            resolved = set(row.get("resolved_ids") or [])
            overlap = sorted(resolved & set(ids))
            if overlap:
                raise ValueError(f"identity_coverage_ids must stay separate from role-bound resolved_ids: {overlap}")
            state = row.get("state")
            for entity_id in ids:
                entity = by_id.get(entity_id)
                if entity is None:
                    raise ValueError(f"identity_coverage_ids target does not resolve: {entity_id}")
                if entity.get("type") != "Person":
                    raise ValueError(f"identity_coverage_ids target is not a Person: {entity_id}")
                if not eligible_in_state(identity_index, entity_id, state):
                    raise ValueError(f"identity_coverage_ids target is not State-safe for {state}: {entity_id}")
            entries.append({
                "source": row["source"],
                "state": row["state"],
                "field": row["field"],
                "match_prefix": row["match_prefix"],
                "identity_coverage_ids": list(ids),
            })
    return entries


def supplemental_ids_for_row(row: dict, raw: str, coverage_entries: list[dict]) -> tuple[set[str], tuple[str, str, str, str] | None]:
    matches = [
        entry for entry in coverage_entries
        if entry["source"] == row.get("source")
        and entry["state"] == row.get("state")
        and entry["field"] == row.get("field")
        and raw.startswith(entry["match_prefix"])
    ]
    if len(matches) > 1:
        raise ValueError(f"multiple supplemental identity-coverage entries match row: {row}")
    if not matches:
        return set(), None
    entry = matches[0]
    if row.get("resolution_source") != "reviewed-disposition":
        raise ValueError(f"supplemental identity coverage matched a non-reviewed row: {row}")
    key = (entry["source"], entry["state"], entry["field"], entry["match_prefix"])
    return set(entry["identity_coverage_ids"]), key


def failures(
    report: dict,
    entities: list[dict],
    identity_index,
    coverage_entries: list[dict] | None = None,
) -> list[dict]:
    out: list[dict] = []
    person_entities = [entity for entity in entities if entity.get("type") == "Person"]
    by_id = {entity["id"]: entity for entity in entities}
    if coverage_entries is None:
        coverage_entries = load_identity_coverage_entries(by_id, identity_index)
    used_coverage_keys: set[tuple[str, str, str, str]] = set()

    for row in report.get("references", []):
        kind = row.get("kind") or ""
        if not checked_row_kind(kind):
            continue
        raw = row.get("raw") or ""
        state = row.get("state")
        resolved_ids = set(row.get("resolved_ids") or [])
        supplemental_ids, coverage_key = supplemental_ids_for_row(row, raw, coverage_entries)
        if coverage_key is not None:
            used_coverage_keys.add(coverage_key)
        covered_ids = resolved_ids | supplemental_ids

        exact_person_ids = set(exact.independent_exact_matches(raw, person_entities, identity_index, "identity", state))
        extraneous_supplemental = sorted(supplemental_ids - exact_person_ids)
        if extraneous_supplemental:
            out.append({
                "reason": "reviewed supplemental Person coverage is not an exact embedded identity",
                "state": state, "kind": kind, "field": row.get("field"), "source": row.get("source"),
                "raw": raw, "extraneous_ids": extraneous_supplemental,
            })
        missing_exact_people = sorted(exact_person_ids - covered_ids)
        if missing_exact_people:
            out.append({
                "reason": "Schedule row omits one or more exact current Person identities",
                "state": state, "kind": kind, "field": row.get("field"), "source": row.get("source"),
                "raw": raw, "missing_ids": missing_exact_people,
                "role_bound_ids": sorted(resolved_ids), "identity_coverage_ids": sorted(supplemental_ids),
                "resolution_source": row.get("resolution_source"), "status": row.get("status"),
            })

        mentions = strict_named_mentions(raw, kind)
        if kind == "actor-reference":
            for mention in anchored_actor_list_mentions(raw, entities, identity_index, state):
                add_unique(mentions, mention, allow_all_caps=True)

        for mention in mentions:
            person_ids = exact.materialized_person_ids_for_mention(mention, entities, identity_index, state)
            if person_ids:
                continue
            non_person_ids = exact.materialized_non_person_ids_for_mention(mention, entities, identity_index, state)
            if non_person_ids:
                continue
            if not explicitly_defers_complete_name(row, mention):
                out.append({
                    "reason": "named actor/project/scope identity lacks exact materialization or explicit complete-name deferral",
                    "state": state, "kind": kind, "field": row.get("field"), "source": row.get("source"),
                    "raw": raw, "name": mention,
                    "role_bound_ids": sorted(resolved_ids), "identity_coverage_ids": sorted(supplemental_ids),
                    "resolution_source": row.get("resolution_source"), "status": row.get("status"),
                })

    all_coverage_keys = {
        (entry["source"], entry["state"], entry["field"], entry["match_prefix"])
        for entry in coverage_entries
    }
    for key in sorted(all_coverage_keys - used_coverage_keys):
        out.append({
            "reason": "unused reviewed supplemental Person identity coverage",
            "source": key[0], "state": key[1], "field": key[2], "match_prefix": key[3],
        })
    return out


def self_test() -> None:
    assert strict_named_mentions("Jane Doe June 2026 detention project", "scope-identity-reference") == ["Jane Doe"]
    assert strict_named_mentions("Khariq Anhar EIT-law prosecution project", "scope-identity-reference") == ["Khariq Anhar"]
    assert strict_named_mentions("Jane Doe Smith-Jones prosecution project", "scope-identity-reference") == ["Jane Doe Smith-Jones"]
    assert strict_named_mentions("Jane Doe SMITH-Jones prosecution project", "scope-identity-reference") == ["Jane Doe SMITH-Jones"]
    assert strict_named_mentions("Jane Doe SMITH-JONES prosecution project", "scope-identity-reference") == ["Jane Doe SMITH-JONES"]
    assert strict_named_mentions("Jane DOE prosecution project", "scope-identity-reference") == ["Jane DOE"]
    assert strict_named_mentions("JANE DOE prosecution project", "scope-identity-reference") == ["JANE DOE"]
    assert strict_named_mentions("Juan Carlos de la Cruz Gomez detention project", "scope-identity-reference") == ["Juan Carlos de la Cruz Gomez"]
    assert "Jane DOE" in strict_named_mentions("detention of Jane DOE pending trial", "actor-reference")
    assert "JANE DOE" in strict_named_mentions("detention of JANE DOE pending trial", "actor-reference")
    assert "J. Doe" in strict_named_mentions("detention of J. Doe pending trial", "actor-reference")
    assert "Jane A. Doe" in strict_named_mentions("detention of Jane A. Doe pending trial", "actor-reference")
    assert "Jane Doe" in strict_named_mentions('detention of "Jane Doe" pending trial', "actor-reference")
    assert "Jean Marie Michel Mokoko" in strict_named_mentions(
        "TUR 6/2026 — Jean Marie Michel Mokoko / Andre Okombi Salissa enforcement project",
        "scope-identity-reference",
    )
    assert "Andre Okombi Salissa" in strict_named_mentions(
        "TUR 6/2026 — Jean Marie Michel Mokoko / Andre Okombi Salissa enforcement project",
        "scope-identity-reference",
    )
    assert "Jane Doe" in strict_named_mentions("Human Rights Watch / Jane Doe", "actor-reference")
    assert "JANE DOE" in strict_named_mentions("Human Rights Watch / JANE DOE", "actor-reference")
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / Jane Doe, acting only where participation is established", "actor-reference"
    )
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / Jane Doe, in an advisory capacity", "actor-reference"
    )
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / Jane Doe (in an advisory capacity)", "actor-reference"
    )
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / Jane Doe (acting only where participation is established)", "actor-reference"
    )
    assert "Jane Doe" not in strict_named_mentions(
        "Human Rights Watch / Jane Doe (unreviewed arbitrary prose)", "actor-reference"
    )
    assert "Jane Doe" in strict_named_mentions(
        "Human Rights Watch / detention of Jane Doe pending trial", "actor-reference"
    )
    assert "MacPherson Mukuka" in strict_named_mentions(
        "Cyber Crimes Act enforcement, including the frozen 2026 MacPherson Mukuka matter", "project-reference"
    )
    assert "Counter Terrorist" not in strict_named_mentions(
        "Sri Lanka Police — Counter Terrorist Investigation Division (CTID), only in actual detention activity",
        "actor-reference",
    )

    ann = {
        "resolution_source": "reviewed-disposition", "status": "partial-deferred",
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
        {"id": "AGENCY-MOI-NARC", "type": "Agency", "aliases": [schedule.norm("Ministry of Interior and Narcotics Control")],
         "surface_forms": [{"text": "Ministry of Interior and Narcotics Control", "normalized": schedule.norm("Ministry of Interior and Narcotics Control")}]},
        {"id": "PERSON-MACPHERSON", "type": "Person", "aliases": [schedule.norm("MacPherson Mukuka")],
         "surface_forms": [{"text": "MacPherson Mukuka", "normalized": schedule.norm("MacPherson Mukuka")}]},
    ]
    raw_entities = [
        {"id": "ORG-HRW", "type": "Organization", "name": "Human Rights Watch", "aliases": []},
        {"id": "AGENCY-MOI-NARC", "type": "Agency", "name": "Ministry of Interior and Narcotics Control", "aliases": []},
        {"id": "PERSON-MACPHERSON", "type": "Person", "name": "MacPherson Mukuka", "aliases": []},
    ]
    idx = build_name_index(raw_entities, state_codes={"AAA"}, normalizer=schedule.norm)

    for raw in (
        "Human Rights Watch and Jane Doe, acting only where participation is established",
        "Human Rights Watch & Jane Doe, in an advisory capacity",
        "Human Rights Watch, Jane Doe, only where participation is established",
        "Human-Rights Watch and Jane Doe, acting only where participation is established",
        "Human Rights Watch and Jane Doe (in an advisory capacity)",
    ):
        assert anchored_actor_list_mentions(raw, synthetic, idx, "AAA") == ["Jane Doe"]
    assert anchored_actor_list_mentions(
        "Ministry of Interior and Narcotics Control", synthetic, idx, "AAA"
    ) == []

    actor_bypass = {"references": [{
        "kind": "actor-reference", "state": "AAA", "field": "candidate_parties", "source": "x.yml",
        "raw": "Human Rights Watch and Jane Doe, acting only where participation is established",
        "status": "partial-deferred", "resolution_source": "reviewed-disposition", "resolved_ids": ["ORG-HRW"],
        "disposition_reason": "Human Rights Watch is bound exactly; remaining actor context is deferred.",
    }]}
    found = failures(actor_bypass, synthetic, idx, [])
    assert any(item.get("name") == "Jane Doe" for item in found)
    actor_bypass["references"][0]["disposition_reason"] = (
        "Human Rights Watch is bound exactly; Jane Doe remains explicitly identity-deferred pending materialization."
    )
    assert failures(actor_bypass, synthetic, idx, []) == []

    parenthesized_actor_bypass = {"references": [{
        "kind": "actor-reference", "state": "AAA", "field": "candidate_parties", "source": "x.yml",
        "raw": "Human Rights Watch / Jane Doe (in an advisory capacity)",
        "status": "partial-deferred", "resolution_source": "reviewed-disposition", "resolved_ids": ["ORG-HRW"],
        "disposition_reason": "Human Rights Watch is bound exactly; remaining actor context is deferred.",
    }]}
    found = failures(parenthesized_actor_bypass, synthetic, idx, [])
    assert any(item.get("name") == "Jane Doe" for item in found)

    cue_bypass = {"references": [{
        "kind": "actor-reference", "state": "AAA", "field": "candidate_parties", "source": "x.yml",
        "raw": "Human Rights Watch / detention of JANE DOE pending trial", "status": "partial-deferred",
        "resolution_source": "reviewed-disposition", "resolved_ids": ["ORG-HRW"],
        "disposition_reason": "Human Rights Watch is bound exactly; remaining actor context is deferred.",
    }]}
    found = failures(cue_bypass, synthetic, idx, [])
    assert any(item.get("name") == "JANE DOE" for item in found)

    project_bypass = {"references": [{
        "kind": "project-reference", "state": "AAA", "field": "candidate_projects", "source": "x.yml",
        "raw": "Cyber Crimes Act enforcement, including the frozen 2026 MacPherson Mukuka matter",
        "status": "resolved", "resolution_source": "reviewed-disposition", "resolved_ids": ["PROJECT-AAA-X"],
        "disposition_reason": "Exact project bound.",
    }]}
    found = failures(project_bypass, synthetic, idx, [])
    assert any(item.get("missing_ids") == ["PERSON-MACPHERSON"] for item in found)
    supplemental = [{
        "source": "x.yml", "state": "AAA", "field": "candidate_projects",
        "match_prefix": "Cyber Crimes Act enforcement", "identity_coverage_ids": ["PERSON-MACPHERSON"],
    }]
    assert failures(project_bypass, synthetic, idx, supplemental) == []
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
