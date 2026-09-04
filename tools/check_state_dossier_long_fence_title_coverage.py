#!/usr/bin/env python3
"""Fail closed on State-dossier title identities hidden after Markdown fences.

Several title companions historically carried independent fence state. This guard now delegates all
fenced-code visibility to the same CommonMark parser used by Person and vendor coverage, then audits
both individual visible lines and complete visible prose blocks so a title split across a soft wrap
cannot disappear at the composition boundary.

Identity coverage is neutral and creates no attribution, participation, control, operation, supply,
membership, culpability, or governance semantics.
"""
from __future__ import annotations

import argparse
import json

import audit_state_dossier_entities as base
import check_state_dossier_ampersand_title_coverage as amp
import check_state_dossier_commonmark_escape_coverage as commonmark
import check_state_dossier_rendered_markup_coverage as markup
import check_state_dossier_softwrap_coverage as softwrap
import commonmark_fences as fences
import review_state_dossier_candidates as reviewed


def visible_lines(body: str, *, hidden_lines: set[int] | None = None) -> list[tuple[int, str]]:
    """Return source lines outside the authoritative CommonMark fence-token ranges."""
    if hidden_lines is None:
        hidden_lines = fences.fenced_line_numbers(body)
    return [
        (line_no, raw)
        for line_no, raw in enumerate(body.splitlines(), 1)
        if line_no not in hidden_lines
    ]


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

        # Parse block visibility once. Every downstream path consumes this exact set and may not
        # reinterpret fence-looking syntax independently.
        hidden_lines = fences.fenced_line_numbers(body)

        # Same-line/heading/table/list protection after the parser-derived visibility decision.
        for relative_line, raw in visible_lines(body, hidden_lines=hidden_lines):
            inspect_raw(
                state=state,
                source=source,
                line=line_offset + relative_line,
                raw=raw,
                scope="line",
            )

        # Composition protection: pass the parser-derived fence ranges directly into the soft-wrap
        # assembler. The assembler joins paragraph/list text but does not recognize fence syntax.
        for block in softwrap.prose_blocks(body, hidden_lines=hidden_lines):
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
    fences.self_test()
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
    hidden = fences.fenced_line_numbers(body)
    lines = visible_lines(body, hidden_lines=hidden)
    assert lines == [(8, r"Research \& Development Agency")], lines

    visible = commonmark.rendered_with_commonmark_escapes(lines[0][1])
    candidates = amp.ampersand_title_surfaces(visible)
    assert ("Research & Development Agency", "actor-or-institution") in candidates, candidates

    invalid_body = "```bad`info\nResearch \\& Development Agency\n"
    invalid = visible_lines(
        invalid_body, hidden_lines=fences.fenced_line_numbers(invalid_body)
    )
    assert invalid[0][0] == 1 and invalid[1][0] == 2, invalid

    # Tab-indented fence-looking text is indented code, so it cannot hide a later title surface.
    tab_body = "\t```text\nResearch \\& Development Agency\n"
    tab_indented = visible_lines(tab_body, hidden_lines=fences.fenced_line_numbers(tab_body))
    assert tab_indented[0][0] == 1 and tab_indented[1][0] == 2, tab_indented

    # Raw HTML block precedence is delegated to CommonMark. A fence-looking line inside <pre> is
    # literal HTML content and the title after </pre> must remain visible.
    raw_html_body = (
        "<pre>\n```text\nliteral HTML content\n</pre>\nResearch \\& Development Agency\n"
    )
    raw_html_hidden = fences.fenced_line_numbers(raw_html_body)
    assert raw_html_hidden == set(), raw_html_hidden
    raw_html = visible_lines(raw_html_body, hidden_lines=raw_html_hidden)
    assert raw_html[-1] == (5, r"Research \& Development Agency"), raw_html

    # Prior composition regression: an internal three-backtick run stays fenced; after the true
    # four-backtick closer, a soft-wrapped escaped-ampersand identity is reassembled from the exact
    # same parser-derived visibility set.
    wrapped = (
        "````text\n"
        "Research \\& Hidden Agency\n"
        "```\n"
        "still fenced\n"
        "````\n"
        "Research \\&\n"
        "Development Agency reported findings.\n"
    )
    wrapped_hidden = fences.fenced_line_numbers(wrapped)
    blocks = softwrap.prose_blocks(wrapped, hidden_lines=wrapped_hidden)
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
        wrapped_hidden,
        blocks,
        rendered_blocks,
        wrapped_surfaces,
    )
    assert not any("Hidden Agency" in value for value, _ in wrapped_surfaces), wrapped_surfaces

    # Exact latest review composition: CommonMark reports no fence inside raw <pre>, and that exact
    # parser decision is passed into the assembler without any second fence interpretation. The
    # title split across the two following source lines must therefore be reconstructed completely.
    raw_html_wrapped = (
        "<pre>\n"
        "```text\n"
        "</pre>\n"
        "Research \\&\n"
        "Development Agency\n"
    )
    raw_html_wrapped_hidden = fences.fenced_line_numbers(raw_html_wrapped)
    assert raw_html_wrapped_hidden == set(), raw_html_wrapped_hidden
    raw_html_blocks = softwrap.prose_blocks(
        raw_html_wrapped, hidden_lines=raw_html_wrapped_hidden
    )
    raw_html_rendered = [
        commonmark.rendered_with_commonmark_escapes(
            " ".join(line for line in block["lines"] if line)
        )
        for block in raw_html_blocks
        if block["lines"]
    ]
    raw_html_surfaces = [
        surface
        for rendered_block in raw_html_rendered
        for surface in amp.ampersand_title_surfaces(rendered_block)
    ]
    assert ("Research & Development Agency", "actor-or-institution") in raw_html_surfaces, (
        raw_html_blocks,
        raw_html_rendered,
        raw_html_surfaces,
    )

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
