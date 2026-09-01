#!/usr/bin/env python3
"""Fail closed on State-dossier title identities hidden by standalone ampersands.

The broad State-dossier TITLE_RE deliberately recognizes title-like organization/project
surfaces. Historically it treated ``&`` only as an in-token character, so a visible name
such as ``Research & Development Agency`` was split into smaller fragments. This companion
guard independently reconstructs standalone-ampersand title surfaces from rendered prose and
requires the complete surface to be a current State-safe ABox identity, unless every
ampersand-delimited member is already an exact current identity (the unambiguous list case).

Identity coverage is neutral: this checker never infers attribution, participation, control,
operation, supply, membership, culpability, or governance.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_private_org_mentions as rendered
import audit_state_dossier_entities as base
from entity_identity_resolution import build_name_index


TITLE_WORD = r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9.'’/-]*|[A-ZÀ-ÖØ-Þ]{2,})"
TITLE_CONNECTOR = r"(?:of|the|and|for|de|del|la|le|des|da|di|van|von)"
TITLE_SIDE = rf"{TITLE_WORD}(?:\s+(?:{TITLE_CONNECTOR}|{TITLE_WORD})){{0,8}}"
AMPERSAND = r"(?:&|＆)"

# A comma/dash immediately before a closed-world legal/institutional suffix is part of the
# identity surface, not sentence punctuation. Keep this deliberately narrower than arbitrary
# title-case prose so ``Research & Development, Inc.`` is covered without turning every
# post-comma phrase into a candidate.
PUNCTUATED_ACTOR_SUFFIX = (
    r"(?:Administration|Agency|Army|Authority|Bank|Brigade|Brigades|Bureau|Command|"
    r"Commission|Committee|Council|Court|Department|Directorate|Division|Forces|Force|"
    r"Group|Guard|Institute|Intelligence|Laboratories|Ministry|Network|Office|Police|"
    r"Service|Services|Technologies|Technology|University|"
    r"Ltd\.?|Limited|Inc\.?|Corp\.?|Corporation|Company|LLC|LLP|PLC|"
    r"S\.A\.|S\.p\.A\.|GmbH|AG|SE|B\.V\.|N\.V\.|AD|ZRT|"
    r"Pty(?:\.?\s+Ltd\.?)?|Pte(?:\.?\s+Ltd\.?)?)"
)
PUNCTUATED_PROJECT_SUFFIX = (
    r"(?:Campaign|CCTV|Database|Deployment|Model|Operation|Platform|Program|Programme|"
    r"Project|System|Systems|Tool|Tools|VSA)"
)
PUNCTUATED_SUFFIX = (
    rf"(?:\s*(?:,|[–—-])\s*(?:{PUNCTUATED_ACTOR_SUFFIX}|{PUNCTUATED_PROJECT_SUFFIX}))?"
)
TITLE_MEMBER = rf"{TITLE_SIDE}{PUNCTUATED_SUFFIX}"
AMPERSAND_TITLE_RE = re.compile(
    rf"\b(?P<surface>{TITLE_MEMBER}(?:\s+{AMPERSAND}\s+{TITLE_MEMBER})+)"
    rf"(?=$|[\s.,;:!?()\[\]{{}}\"'“”‘’])"
)
AMPERSAND_SPLIT_RE = re.compile(rf"\s+{AMPERSAND}\s+")
LEADING_DETERMINER_RE = re.compile(r"^(?:the|a|an)\s+", re.I)
PUNCTUATED_ACTOR_SUFFIX_RE = re.compile(
    rf"(?:,|[–—-])\s*{PUNCTUATED_ACTOR_SUFFIX}$"
)
PUNCTUATED_PROJECT_SUFFIX_RE = re.compile(
    rf"(?:,|[–—-])\s*{PUNCTUATED_PROJECT_SUFFIX}$"
)


def classify_ampersand_surface(text: str) -> str | None:
    """Classify with the broad vocabulary plus closed punctuated legal suffixes."""
    kind = base.classify(text)
    if kind is not None:
        return kind
    if PUNCTUATED_PROJECT_SUFFIX_RE.search(text):
        return "project-or-deployment"
    if PUNCTUATED_ACTOR_SUFFIX_RE.search(text):
        return "actor-or-institution"
    return None


def ampersand_title_surfaces(prose: str) -> list[tuple[str, str]]:
    """Return complete classified title surfaces containing standalone ampersands."""
    text = " ".join(prose.split())
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in AMPERSAND_TITLE_RE.finditer(text):
        value = base.clean_candidate(match.group("surface"))
        kind = classify_ampersand_surface(value)
        if kind is None or not base.plausible(value):
            continue
        marker = (base.norm(value), kind)
        if marker in seen:
            continue
        seen.add(marker)
        out.append((value, kind))
    return out


def inline_code_ampersand_titles(raw: str) -> list[tuple[str, str]]:
    """Preserve the broad audit's explicit inline-code identity surface."""
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in base.INLINE_CODE_RE.finditer(raw):
        for value, kind in ampersand_title_surfaces(match.group(1)):
            marker = (base.norm(value), kind)
            if marker not in seen:
                seen.add(marker)
                out.append((value, kind))
    return out


def exact_id(index, state: str, value: str) -> str | None:
    return base.resolve_name(index, state, value)


def canonical_review_surface(index, state: str, value: str) -> str:
    """Treat a narrow prose article as syntax only when the literal identity is absent.

    Literal exact resolution is deliberately attempted first. This preserves identities whose
    actual reviewed name begins with ``The``, ``A`` or ``An``. Only when the literal surface is
    not a current State-safe identity do we remove one leading determiner for review/resolution.
    """
    if exact_id(index, state, value) is not None:
        return value
    return LEADING_DETERMINER_RE.sub("", value, count=1)


def uncovered_surface(index, state: str, value: str) -> tuple[list[str], list[str]] | None:
    """Return unresolved member diagnostics, or None when the complete surface is covered.

    Exact materialization of the complete ``A & B`` surface is authoritative. Otherwise the
    ampersand is accepted as a list separator only when *every* complete member independently
    resolves to a current State-safe identity. Narrow leading articles are syntax only after
    literal exact resolution has failed; the same rule is applied independently to list
    members. This is intentionally stricter than guessing from capitalization: if any member
    is not exact, the complete surface remains review debt and cannot disappear behind the
    dossier-tree ratchet.
    """
    value = canonical_review_surface(index, state, value)
    if exact_id(index, state, value) is not None:
        return None
    members = [base.clean_candidate(part) for part in AMPERSAND_SPLIT_RE.split(value)]
    members = [canonical_review_surface(index, state, member) for member in members if member]
    if len(members) < 2:
        return (members, members)
    unresolved = [member for member in members if exact_id(index, state, member) is None]
    if not unresolved:
        return None
    return members, unresolved


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(
        *,
        state: str,
        source: str,
        location: str,
        raw: str,
        prose: str,
        snippet: str,
    ) -> None:
        candidates = ampersand_title_surfaces(prose)
        candidates += inline_code_ampersand_titles(raw)
        seen_local: set[tuple[str, str]] = set()
        for raw_value, raw_kind in candidates:
            value = canonical_review_surface(identity_index, state, raw_value)
            kind = classify_ampersand_surface(value) or raw_kind
            marker = (base.norm(value), kind)
            if marker in seen_local:
                continue
            seen_local.add(marker)
            uncovered = uncovered_surface(identity_index, state, value)
            if uncovered is None:
                continue
            members, unresolved = uncovered
            key = (state, marker[0], source, location)
            failures_by_key[key] = {
                "state": state,
                "candidate": value,
                "normalized": marker[0],
                "kind": kind,
                "reason": "standalone-ampersand title surface lacks complete exact identity coverage",
                "members": members,
                "unresolved_members": unresolved,
                "source": source,
                "location": location,
                "snippet": snippet[:420],
            }

    for path, front, body_offset in dossiers:
        state = front["iso3"]
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))
        text = path.read_text(encoding="utf-8")

        for field, line_no, raw in base.frontmatter_identity_values(text, front):
            prose = rendered.visible_prose(" ".join(raw.splitlines()))
            inspect(
                state=state,
                source=source,
                location=f"frontmatter:{field}:{line_no}",
                raw=raw,
                prose=prose,
                snippet=f"{field}: {raw}",
            )

        line_offset = text[:body_offset].count("\n")
        body = text[body_offset:]
        for rel_line, snippet, prose in rendered.rendered_prose_segments(body):
            # The H1 is structurally constrained by check_state_dossier_identity_sets.py to be
            # the canonical State title. Keep this non-State guard aligned with that contract.
            if snippet.lstrip().startswith("# "):
                continue
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                raw=snippet,
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    plain = ampersand_title_surfaces("Research & Development Agency reported findings")
    assert ("Research & Development Agency", "actor-or-institution") in plain, plain
    multi = ampersand_title_surfaces("Research & Development & Innovation Agency")
    assert ("Research & Development & Innovation Agency", "actor-or-institution") in multi, multi
    softwrap = ampersand_title_surfaces("Research &\nDevelopment Agency")
    assert ("Research & Development Agency", "actor-or-institution") in softwrap, softwrap
    fullwidth = ampersand_title_surfaces("Research ＆ Development Agency")
    assert ("Research ＆ Development Agency", "actor-or-institution") in fullwidth, fullwidth
    html_amp = ampersand_title_surfaces(rendered.visible_prose("Research &amp; Development Agency"))
    assert any(value == "Research & Development Agency" for value, _ in html_amp), html_amp
    emphasized = ampersand_title_surfaces(rendered.visible_prose("Research **&** Development Agency"))
    assert any(value == "Research & Development Agency" for value, _ in emphasized), emphasized
    code = inline_code_ampersand_titles("`Research & Development Agency` is named")
    assert any(value == "Research & Development Agency" for value, _ in code), code

    punctuated = ampersand_title_surfaces("Research & Development, Inc. reported findings")
    assert any(value == "Research & Development, Inc" for value, _ in punctuated), punctuated
    punctuated_llc = ampersand_title_surfaces("Research & Development, LLC reported findings")
    assert ("Research & Development, LLC", "actor-or-institution") in punctuated_llc, punctuated_llc
    punctuated_institution = ampersand_title_surfaces("Research & Development — Agency reported findings")
    assert (
        "Research & Development — Agency",
        "actor-or-institution",
    ) in punctuated_institution, punctuated_institution
    internal_suffix = ampersand_title_surfaces("Research & Development, Inc. & Project Aurora")
    assert any(
        value == "Research & Development, Inc. & Project Aurora" or value == "Research & Development, Inc & Project Aurora"
        for value, _ in internal_suffix
    ), internal_suffix

    assert ampersand_title_surfaces("Alpha & Beta") == []
    assert ampersand_title_surfaces("research & development agency") == []

    empty = build_name_index([], state_codes={"AAA"}, normalizer=base.norm)
    debt = uncovered_surface(empty, "AAA", "Research & Development Agency")
    assert debt == (["Research", "Development Agency"], ["Research", "Development Agency"]), debt
    article_debt = uncovered_surface(empty, "AAA", "The Research & Development Agency")
    assert article_debt == (["Research", "Development Agency"], ["Research", "Development Agency"]), article_debt

    exact_full = build_name_index(
        [
            {
                "id": "AGENCY-AAA-RD",
                "type": "Agency",
                "name": "Research & Development Agency",
                "aliases": [],
            }
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert uncovered_surface(exact_full, "AAA", "Research & Development Agency") is None
    assert uncovered_surface(exact_full, "AAA", "The Research & Development Agency") is None
    assert uncovered_surface(exact_full, "AAA", "A Research & Development Agency") is None
    assert canonical_review_surface(exact_full, "AAA", "The Research & Development Agency") == "Research & Development Agency"

    genuine_article = build_name_index(
        [
            {
                "id": "AGENCY-AAA-THE-RD",
                "type": "Agency",
                "name": "The Research & Development Agency",
                "aliases": [],
            }
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert canonical_review_surface(
        genuine_article, "AAA", "The Research & Development Agency"
    ) == "The Research & Development Agency"
    assert uncovered_surface(genuine_article, "AAA", "The Research & Development Agency") is None

    exact_corporate = build_name_index(
        [
            {
                "id": "ORG-AAA-RD-INC",
                "type": "Organization",
                "name": "Research & Development, Inc.",
                "aliases": [],
            }
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert uncovered_surface(exact_corporate, "AAA", "Research & Development, Inc") is None
    assert uncovered_surface(exact_corporate, "AAA", "The Research & Development, Inc") is None

    exact_list = build_name_index(
        [
            {"id": "AGENCY-AAA-ALPHA", "type": "Agency", "name": "Agency Alpha", "aliases": []},
            {"id": "PROJECT-AAA-AURORA", "type": "Project", "name": "Project Aurora", "aliases": []},
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert uncovered_surface(exact_list, "AAA", "Agency Alpha & Project Aurora") is None
    assert uncovered_surface(exact_list, "AAA", "The Agency Alpha & Project Aurora") is None
    assert uncovered_surface(exact_list, "AAA", "Agency Alpha & the Project Aurora") is None
    partial_list = build_name_index(
        [{"id": "AGENCY-AAA-ALPHA", "type": "Agency", "name": "Agency Alpha", "aliases": []}],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    partial = uncovered_surface(partial_list, "AAA", "Agency Alpha & Project Aurora")
    assert partial == (["Agency Alpha", "Project Aurora"], ["Project Aurora"]), partial
    print("State dossier standalone-ampersand title coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_AMPERSAND_TITLES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier standalone-ampersand title completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
