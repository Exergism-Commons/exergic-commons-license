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
AMPERSAND_TITLE_RE = re.compile(
    rf"\b(?P<surface>{TITLE_SIDE}(?:\s+{AMPERSAND}\s+{TITLE_SIDE})+)\b"
)
AMPERSAND_SPLIT_RE = re.compile(rf"\s+{AMPERSAND}\s+")


def ampersand_title_surfaces(prose: str) -> list[tuple[str, str]]:
    """Return complete classified title surfaces containing standalone ampersands."""
    text = " ".join(prose.split())
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in AMPERSAND_TITLE_RE.finditer(text):
        value = base.clean_candidate(match.group("surface"))
        kind = base.classify(value)
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


def uncovered_surface(index, state: str, value: str) -> tuple[list[str], list[str]] | None:
    """Return unresolved member diagnostics, or None when the complete surface is covered.

    Exact materialization of the complete ``A & B`` surface is authoritative. Otherwise the
    ampersand is accepted as a list separator only when *every* complete member independently
    resolves to a current State-safe identity. This is intentionally stricter than guessing
    from capitalization: if any member is not exact, the complete surface remains review debt
    and cannot disappear behind the dossier-tree ratchet.
    """
    if exact_id(index, state, value) is not None:
        return None
    members = [base.clean_candidate(part) for part in AMPERSAND_SPLIT_RE.split(value)]
    members = [member for member in members if member]
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
        for value, kind in candidates:
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
    assert ampersand_title_surfaces("Alpha & Beta") == []
    assert ampersand_title_surfaces("research & development agency") == []

    empty = build_name_index([], state_codes={"AAA"}, normalizer=base.norm)
    debt = uncovered_surface(empty, "AAA", "Research & Development Agency")
    assert debt == (["Research", "Development Agency"], ["Research", "Development Agency"]), debt

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

    exact_list = build_name_index(
        [
            {"id": "AGENCY-AAA-ALPHA", "type": "Agency", "name": "Agency Alpha", "aliases": []},
            {"id": "PROJECT-AAA-AURORA", "type": "Project", "name": "Project Aurora", "aliases": []},
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert uncovered_surface(exact_list, "AAA", "Agency Alpha & Project Aurora") is None
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
