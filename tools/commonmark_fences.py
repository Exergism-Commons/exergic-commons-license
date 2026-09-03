#!/usr/bin/env python3
"""Shared CommonMark fenced-code visibility semantics for State dossier audits.

Fence visibility is intentionally delegated to a standards-conformant CommonMark block parser.
Identity auditors must not carry their own regex/state machine: fenced-code recognition interacts
with other block constructs (notably raw HTML, indented code and block containers), so even a locally
accurate fence grammar can be wrong in context.

This module asks markdown-it-py's CommonMark parser which source ranges are actual ``fence`` tokens,
then exposes only the two operations the audits need: visible source lines and a line-preserving body
with true fenced-code regions blanked. It does not render Markdown or infer identity semantics.
"""
from __future__ import annotations

import argparse

from markdown_it import MarkdownIt


# HTML parsing must be enabled for CommonMark block precedence to be represented faithfully. In
# particular, fence-looking lines inside raw HTML blocks such as <pre> are literal HTML content and
# cannot open a Markdown fence that hides later dossier prose.
PARSER = MarkdownIt("commonmark", {"html": True})


def fenced_line_numbers(body: str) -> set[int]:
    """Return 1-based source line numbers belonging to actual CommonMark fence tokens."""
    hidden: set[int] = set()
    for token in PARSER.parse(body):
        if token.type != "fence" or token.map is None:
            continue
        start, end = token.map
        hidden.update(range(start + 1, end + 1))
    return hidden


def visible_lines(body: str) -> list[tuple[int, str]]:
    """Return 1-based source lines outside actual CommonMark fenced-code blocks."""
    hidden = fenced_line_numbers(body)
    return [
        (line_no, raw)
        for line_no, raw in enumerate(body.splitlines(), 1)
        if line_no not in hidden
    ]


def blank_fenced_lines(body: str) -> str:
    """Blank true fenced-code regions while preserving source line count."""
    hidden = fenced_line_numbers(body)
    return "\n".join(
        "" if line_no in hidden else raw
        for line_no, raw in enumerate(body.splitlines(), 1)
    )


def self_test() -> None:
    # Run length: a shorter same-marker run is content, not a closer.
    body = (
        "````text\n"
        "hidden\n"
        "```\n"
        "still hidden\n"
        "`````\n"
        "visible\n"
    )
    assert visible_lines(body) == [(6, "visible")]

    # Marker family and trailing closer syntax remain CommonMark parser decisions.
    mixed = "~~~~text\n```\n~~~~ trailing\n~~~~\nvisible"
    assert visible_lines(mixed) == [(5, "visible")]

    # Backtick info strings cannot contain backticks; tilde info strings may.
    invalid_info = "```bad`info\nvisible"
    assert visible_lines(invalid_info) == [(1, "```bad`info"), (2, "visible")]
    assert visible_lines("~~~bad`info\nhidden\n~~~") == []

    # Tabs and four-space indentation produce indented code, not a fenced-code opener.
    for prefix in ("\t", " \t", "  \t", "   \t"):
        candidate = f"{prefix}```text\nvisible"
        assert visible_lines(candidate) == [(1, f"{prefix}```text"), (2, "visible")]
    for spaces in range(4):
        assert visible_lines(" " * spaces + "```text\nhidden\n```") == []
    four_space = "    ```text\nvisible"
    assert visible_lines(four_space) == [(1, "    ```text"), (2, "visible")]

    # A tab-indented pseudo-closer cannot terminate a valid fence; a <=3-space closer can.
    tab_close = "```text\nhidden\n\t```\nstill hidden\n```\nvisible"
    assert visible_lines(tab_close) == [(6, "visible")]
    assert visible_lines("```text\nhidden\n   ```\nvisible") == [(4, "visible")]

    # Arbitrary or Unicode trailing content does not silently become a valid closer.
    trailing = "```text\nhidden\n``` trailing\nstill hidden\n```\nvisible"
    assert visible_lines(trailing) == [(6, "visible")]
    unicode_tail = "```text\nhidden\n```\u00a0\nstill hidden\n```\nvisible"
    assert visible_lines(unicode_tail) == [(6, "visible")]

    # Review regression: raw HTML block precedence is resolved by CommonMark itself. The backticks
    # are literal <pre> content; the later Person/title prose remains visible and no fence exists.
    raw_html = (
        "<pre>\n"
        "```text\n"
        "literal HTML content\n"
        "</pre>\n"
        "authorities will be detaining Jane Doe\n"
        "Research \\& Development Agency reported findings.\n"
    )
    assert fenced_line_numbers(raw_html) == set()
    raw_html_visible = visible_lines(raw_html)
    assert raw_html_visible[-2:] == [
        (5, "authorities will be detaining Jane Doe"),
        (6, r"Research \& Development Agency reported findings."),
    ]

    # Cover additional raw-block families so this remains a block-parser contract rather than a
    # one-tag exception. Fence-looking text inside these blocks likewise cannot create a fence.
    for raw_block in (
        "<script>\n```text\n</script>\nvisible",
        "<style>\n```text\n</style>\nvisible",
        "<!--\n```text\n-->\nvisible",
    ):
        assert fenced_line_numbers(raw_block) == set(), raw_block
        assert visible_lines(raw_block)[-1][1] == "visible", raw_block

    # Real fences are still blanked line-for-line for downstream soft-wrap assembly.
    safe = blank_fenced_lines("````\nhidden\n```\n````\nvisible")
    assert safe.splitlines() == ["", "", "", "", "visible"]
    print("Shared CommonMark fenced-code visibility self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
