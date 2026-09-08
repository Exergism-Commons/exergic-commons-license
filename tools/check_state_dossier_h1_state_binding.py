#!/usr/bin/env python3
"""Fail closed when a canonical State dossier title drifts from its State identity.

The structural H1 checker historically compared the H1 stem to the dossier's own mutable
``entity`` field. This companion guard anchors both surfaces to the reviewed ``STATE-<ISO>``
identity instead, so changing ``entity`` and H1 together cannot turn a State title into an
unaudited project or organization title.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import check_state_dossier_identity_sets as identity_sets


ROOT = identity_sets.ROOT
DOSSIERS = identity_sets.DOSSIERS
ENTITIES = identity_sets.ENTITIES
# CommonMark permits up to three literal spaces before an ATX heading marker. Python ``\s`` is
# broader (NBSP, tabs, Unicode spaces, etc.) and must not be allowed to manufacture a canonical
# H1 that the Markdown renderer does not recognize as the dossier heading.
COMMONMARK_H1_RE = re.compile(r"^ {0,3}#(?!#)[ \t]+(.+?)[ \t]*$")


def load_state_identity(iso: str) -> dict:
    path = ENTITIES / f"STATE-{iso}.json"
    if not path.is_file():
        raise ValueError(f"missing corresponding State identity for {iso}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid corresponding State identity for {iso}: {exc}") from exc
    if data.get("type") != "State" or data.get("id") != f"STATE-{iso}" or data.get("iso3") != iso:
        raise ValueError(f"malformed corresponding State identity for {iso}")
    name = data.get("name")
    aliases = data.get("aliases")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"State identity {iso} lacks a canonical name")
    if not isinstance(aliases, list) or not all(isinstance(item, str) and item.strip() for item in aliases):
        raise ValueError(f"State identity {iso} has invalid aliases")
    return data


def non_commonmark_h1_like_line(text: str) -> str | None:
    """Return an H1 accepted by the legacy Python-\s regex but not by CommonMark syntax."""
    front = identity_sets.FRONT.match(text)
    if front is None:
        return None
    body = text[front.end():]
    for raw in body.splitlines():
        if identity_sets.H1_RE.fullmatch(raw) and COMMONMARK_H1_RE.fullmatch(raw) is None:
            return raw
    return None


def binding_error(text: str, front: dict[str, object], state_identity: dict) -> str | None:
    iso = front.get("iso3")
    entity = front.get("entity")
    if not isinstance(iso, str) or not isinstance(entity, str) or not entity.strip():
        return "canonical State dossier lacks textual iso3/entity"
    if state_identity.get("id") != f"STATE-{iso}" or state_identity.get("iso3") != iso:
        return "State dossier and State identity ISO binding disagree"

    pseudo_h1 = non_commonmark_h1_like_line(text)
    if pseudo_h1 is not None:
        return (
            "canonical State dossier contains an H1-like line accepted only by Python whitespace "
            f"semantics, not CommonMark: {pseudo_h1!r}"
        )

    name = state_identity.get("name")
    aliases = state_identity.get("aliases") or []
    reviewed_surfaces = {
        identity_sets.norm(value)
        for value in [name, *aliases]
        if isinstance(value, str) and identity_sets.norm(value)
    }
    if identity_sets.norm(entity) not in reviewed_surfaces:
        return f"frontmatter entity {entity!r} is not a reviewed name/alias of STATE-{iso}"

    try:
        title = identity_sets.canonical_h1_title(text, entity, list(aliases))
    except ValueError as exc:
        return str(exc)
    stem, _ = identity_sets.split_h1_title_aliases(title)
    if identity_sets.norm(stem) not in reviewed_surfaces:
        return f"canonical H1 stem {stem!r} is not a reviewed name/alias of STATE-{iso}"
    return None


def audit() -> list[dict]:
    failures: list[dict] = []
    for path in sorted(DOSSIERS.glob("*.md")):
        iso = path.stem
        text = path.read_text(encoding="utf-8")
        try:
            front = identity_sets.parse_frontmatter_text(text)
        except ValueError as exc:
            failures.append({"dossier": str(path.relative_to(ROOT)), "state": iso, "reason": str(exc)})
            continue
        if front.get("id") != f"ECL-STATE-{iso}" or front.get("iso3") != iso:
            continue
        try:
            state_identity = load_state_identity(iso)
            reason = binding_error(text, front, state_identity)
        except ValueError as exc:
            reason = str(exc)
        if reason:
            failures.append({"dossier": str(path.relative_to(ROOT)), "state": iso, "reason": reason})
    return failures


def self_test() -> None:
    identity = {
        "id": "STATE-PRK",
        "type": "State",
        "iso3": "PRK",
        "name": "Democratic People's Republic of Korea",
        "aliases": ["PRK", "DPRK", "North Korea", "North Korea (DPRK)"],
    }
    canonical = (
        "---\n"
        "id: ECL-STATE-PRK\n"
        "entity: North Korea\n"
        "iso3: PRK\n"
        "---\n"
        "# North Korea (DPRK)\n\n"
        "## 1. Current determination\n"
    )
    front = identity_sets.parse_frontmatter_text(canonical)
    assert binding_error(canonical, front, identity) is None

    # CommonMark also accepts one to three literal leading spaces on ATX headings.
    three_space = canonical.replace("# North Korea (DPRK)", "   # North Korea (DPRK)")
    assert binding_error(three_space, identity_sets.parse_frontmatter_text(three_space), identity) is None

    drifted = canonical.replace("entity: North Korea", "entity: Project Aurora").replace(
        "# North Korea (DPRK)", "# Project Aurora"
    )
    drifted_front = identity_sets.parse_frontmatter_text(drifted)
    reason = binding_error(drifted, drifted_front, identity)
    assert reason and "not a reviewed name/alias" in reason, reason

    unknown_alias = canonical.replace("# North Korea (DPRK)", "# North Korea (Project Aurora)")
    reason = binding_error(unknown_alias, identity_sets.parse_frontmatter_text(unknown_alias), identity)
    assert reason and "not present on the State identity" in reason, reason

    # Legacy H1_RE uses Python \s and would accept these as the one canonical H1. CommonMark does
    # not: NBSP remains paragraph text and a tab creates indentation rather than <=3 spaces.
    for prefix in ("\u00a0", "\t", " \t"):
        pseudo = canonical.replace("# North Korea (DPRK)", prefix + "# North Korea (DPRK)")
        assert identity_sets.H1_RE.fullmatch((prefix + "# North Korea (DPRK)")) is not None
        reason = binding_error(pseudo, identity_sets.parse_frontmatter_text(pseudo), identity)
        assert reason and "not CommonMark" in reason, (prefix, reason)

    print("State dossier H1/State identity binding self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("STATE_DOSSIER_H1_BINDING_FAILURES=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("State dossier H1/State identity binding: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
