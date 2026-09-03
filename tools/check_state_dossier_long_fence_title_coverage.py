#!/usr/bin/env python3
"""Fail closed on State-dossier title identities hidden after long Markdown fences.

Several title companions historically remembered only the fence marker character. A shorter run
inside a longer fence could therefore close it early and make the real closer look like a new opener,
hiding later visible identity prose. This independent guard tracks marker *and opening run length*
and accepts a closer only when it uses the same marker, an equal-or-longer run, and closing-fence
syntax. It audits both individual visible lines and complete post-fence prose blocks so a title split
across a soft wrap cannot disappear at the composition boundary.

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
import check_state_dossier_softwrap_coverage as softwrap
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
        # A backtick info string may not itself contain a backtick. Such a line is ordinary prose,
        # not an opener; tilde fences have no equivalent restriction here.
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


def fence_safe_body(body: str) -> str:
    """Blank fenced-code lines while preserving source line numbers for block assembly.

    The existing soft-wrap renderer is useful after fences are removed, but its own historical
    marker-only fence state cannot safely decide which lines are visible. This pre-pass therefore
    makes that decision with the full-run grammar and replaces every opener/content/closer line by
    an empty line. The remaining text can then be assembled with the established block renderer
    without allowing a shorter internal run to invert visibility.
    """
    out: list[str] = []
    state: tuple[str, int] | None = None
    for raw in body.splitlines():
        previous_state = state
        state, fence_line = fence_transition(raw, state)
        if fence_line or previous_state is not None or state is not None:
            out.append("")
        else:
            out.append(raw)
    return "\n".join(out)


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

    def inspect_rendered(
        *, state: str, source: str, line: int, rendered: str, snippet: str, scope: str
    ) -> None:
        for normalized, (candidate, kind) in markup.title_candidates(rendered).items():
            if base.resolve_name(identity_index, state, candidate) is not None:
                continue
            if dispositions.get((state, normalized)) is not None:
                continue
            if markup.covered_by_visible_materialized_identity(
                identity_index,
                state=state,
                candidate=candidate,
                kind=kind,
                rendered=rendered,
            ):
                continue
            key = (state, normalized, source, line, f"ordinary-title:{scope}")
            failures_by_key[key] = {
                "state": state,
                "candidate": candidate,
                "normalized": normalized,
                "kind": kind,
                "reason": "visible title after Markdown fence lacks identity coverage",
                "source": source,
                "line": line,
                "snippet": snippet[:420],
            }

        for raw_value, raw_kind in amp.ampersand_title_surfaces(rendered):
            value = amp.canonical_review_surface(identity_index, state, raw_value)
            kind = amp.classify_ampersand_surface(value) or raw_kind
            normalized = base.norm(value)
            uncovered = amp.uncovered_surface(identity_index, state, value)
            if uncovered is None:
                continue
            members, unresolved = uncovered
            key = (state, normalized, source, line, f"ampersand-title:{scope}")
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
                "snippet": snippet[:420],
            }

    def inspect_raw(*, state: str, source: str, line: int, raw: str, scope: str) -> None:
        if not raw.strip() or raw.lstrip().startswith("# "):
            return
        inspect_rendered(
            state=state,
            source=source,
            line=line,
            rendered=commonmark.rendered_with_commonmark_escapes(raw),
            snippet=raw,
            scope=scope,
        )

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))
        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        body = text[body_offset:]

        # Same-line/heading/table/list protection after the full-run visibility decision.
        for relative_line, raw in visible_lines(body):
            inspect_raw(
                state=state,
                source=source,
                line=line_offset + relative_line,
                raw=raw,
                scope="line",
            )

        # Composition protection: blank the true fenced region with the full-run parser first,
        # then let the established soft-wrap assembler join only actually visible prose. This
        # catches e.g. `Research \\&` + `Development Agency` after a four-backtick fence whose
        # contents include a literal three-backtick line.
        safe_body = fence_safe_body(body)
        for block in softwrap.prose_blocks(safe_body):
            lines = [line for line in block["lines"] if line]
            if not lines:
                continue
            raw_block = " ".join(lines)
            inspect_raw(
                state=state,
                source=source,
                line=line_offset + block["relative_line"],
                raw=raw_block,
                scope="block",
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

    # Composition regression from review: the internal three-backtick run stays fenced; after the
    # true four-backtick closer, a soft-wrapped escaped-ampersand identity must be reassembled.
    wrapped = (
        "````text\n"
        "Research \\& Hidden Agency\n"
        "```\n"
        "still fenced\n"
        "````\n"
        "Research \\&\n"
        "Development Agency reported findings.\n"
    )
    safe = fence_safe_body(wrapped)
    blocks = softwrap.prose_blocks(safe)
    rendered_blocks = [
        commonmark.rendered_with_commonmark_escapes(" ".join(line for line in block["lines"] if line))
        for block in blocks
        if block["lines"]
    ]
    wrapped_surfaces = [
        surface
        for rendered_block in rendered_blocks
        for surface in amp.ampersand_title_surfaces(rendered_block)
    ]
    assert ("Research & Development Agency", "actor-or-institution") in wrapped_surfaces, (
        safe,
        blocks,
        rendered_blocks,
        wrapped_surfaces,
    )
    assert not any("Hidden Agency" in value for value, _ in wrapped_surfaces), wrapped_surfaces

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
