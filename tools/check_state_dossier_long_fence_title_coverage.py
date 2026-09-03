#!/usr/bin/env python3
"""Fail closed on State-dossier title identities hidden after long Markdown fences.

Several title companions historically remembered only the fence marker character. A shorter run
inside a longer fence could therefore close it early and make the real closer look like a new opener,
hiding later visible identity prose. This independent guard tracks marker *and opening run length*
and accepts a closer only when it uses the same marker, an equal-or-longer run, and closing-fence
syntax. It then applies the existing rendered/CommonMark ampersand and ordinary title coverage rules
to every visible post-fence line.

Identity coverage is neutral and creates no attribution, participation, control, operation, supply,
membership, culpability, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_ampersand_title_coverage as amp
import check_state_dossier_commonmark_escape_coverage as commonmark
import check_state_dossier_rendered_markup_coverage as markup
import review_state_dossier_candidates as reviewed


FENCE_RE = re.compile(r"^\s{0,3}(?P<run>`{3,}|~{3,})(?P<tail>.*)$")


def fence_transition(raw: str, state: tuple[str, int] | None) -> tuple[tuple[str, int] | None, bool]:
    """Advance a CommonMark fence state and report whether this is a fence-like line."""
    match = FENCE_RE.match(raw)
    if match is None:
        return state, False

    run = match.group("run")
    tail = match.group("tail")
    marker = run[0]
    if state is None:
        if marker == "`" and "`" in tail:
            return None, False
        return (marker, len(run)), True

    open_marker, open_length = state
    if marker == open_marker and len(run) >= open_length and not tail.strip():
        return None, True
    return state, True


def visible_lines(body: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    state: tuple[str, int] | None = None
    for line_no, raw in enumerate(body.splitlines(), 1):
        state, fence_line = fence_transition(raw, state)
        if fence_line:
            continue
        if state is not None:
            continue
        out.append((line_no, raw))
    return out


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    dispositions, _ = reviewed.load_dispositions()
    failures_by_key: dict[tuple[str, str, str, int, str], dict] = {}

    def inspect(*, state: str, source: str, line: int, raw: str) -> None:
        if not raw.strip() or raw.lstrip().startswith("# "):
            return

        rendered = commonmark.rendered_with_commonmark_escapes(raw)

        for normalized, (candidate, kind) in markup.title_candidates(rendered).items():
            if base.resolve_name(identity_index, state, candidate) is not None:
                continue
            if dispositions.get((state, normalized)) is not None:
                continue
            key = (state, normalized, source, line, "ordinary-title")
            failures_by_key[key] = {
                "state": state,
                "candidate": candidate,
                "normalized": normalized,
                "kind": kind,
                "reason": "visible title after Markdown fence lacks identity coverage",
                "source": source,
                "line": line,
                "snippet": raw[:420],
            }

        for raw_value, raw_kind in amp.ampersand_title_surfaces(rendered):
            value = amp.canonical_review_surface(identity_index, state, raw_value)
            kind = amp.classify_ampersand_surface(value) or raw_kind
            normalized = base.norm(value)
            uncovered = amp.uncovered_surface(identity_index, state, value)
            if uncovered is None:
                continue
            members, unresolved = uncovered
            key = (state, normalized, source, line, "ampersand-title")
            failures_by_key[key] = {
                "state": state,
                "candidate": value,
                "normalized": normalized,
                "kind": kind,
                "reason": "visible standalone-ampersand title after Markdown fence lacks complete exact coverage",
                "members": members,
                "unresolved_members": unresolved,
                "source": source,
                "line": line,
                "snippet": raw[:420],
            }

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))
        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        for relative_line, raw in visible_lines(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                line=line_offset + relative_line,
                raw=raw,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    body = (
        "````markdown\n"
        "Research \\& Hidden Agency\n"
        "```\n"
        "Research \\& Still Hidden Agency\n"
        "```` trailing\n"
        "~~~~\n"
        "`````\n"
        "Research \\& Development Agency\n"
    )
    lines = visible_lines(body)
    assert lines == [(8, r"Research \& Development Agency")], lines

    state: tuple[str, int] | None = None
    state, handled = fence_transition("````python", state)
    assert handled and state == ("`", 4), state
    state, handled = fence_transition("```", state)
    assert handled and state == ("`", 4), state
    state, handled = fence_transition("`````", state)
    assert handled and state is None, state

    visible = commonmark.rendered_with_commonmark_escapes(lines[0][1])
    candidates = amp.ampersand_title_surfaces(visible)
    assert ("Research & Development Agency", "actor-or-institution") in candidates, candidates

    invalid = visible_lines("```bad`info\nResearch \\& Development Agency\n")
    assert invalid[0][0] == 1 and invalid[1][0] == 2, invalid

    print("State dossier long-fence title coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_LONG_FENCE_TITLES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier long-fence title completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
