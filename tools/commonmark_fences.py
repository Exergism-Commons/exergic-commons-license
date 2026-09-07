#!/usr/bin/env python3
"""Shared CommonMark fenced-code visibility semantics for State dossier audits.

Fence visibility is intentionally delegated to a standards-conformant CommonMark block parser.
Identity auditors must not carry their own regex/state machine: fenced-code recognition interacts
with other block constructs (notably raw HTML, indented code and block containers), so even a locally
accurate fence grammar can be wrong in context.

This module asks markdown-it-py's CommonMark parser which source ranges are actual ``fence`` tokens,
then translates those parser line ranges into the exact 1-based indices produced by Python's
``str.splitlines()``. That translation matters because ``splitlines()`` also separates Unicode line
separators that CommonMark does not treat as source line endings; returning consumer-native indices
prevents an earlier visible fragment from shifting the fence mask onto later prose.
"""
from __future__ import annotations

import argparse
from typing import Any


_PARSER: Any | None = None


def parser() -> Any:
    """Return the shared CommonMark parser, importing markdown-it only on first use."""
    global _PARSER
    if _PARSER is None:
        from markdown_it import MarkdownIt

        # HTML parsing must be enabled for CommonMark block precedence to be represented faithfully.
        # In particular, fence-looking lines inside raw HTML blocks such as <pre> are literal HTML
        # content and cannot open a Markdown fence that hides later dossier prose.
        _PARSER = MarkdownIt("commonmark", {"html": True})
    return _PARSER


def splitline_commonmark_numbers(body: str) -> list[int]:
    """Map each ``str.splitlines()`` element to its 1-based CommonMark source line.

    Python recognizes several additional line boundaries (for example NEL, VT, FF, U+2028 and
    U+2029) that CommonMark keeps inside the current source line. Consumers intentionally continue
    to use ``splitlines()`` for prose assembly, so parser-derived ranges must be projected into that
    indexing scheme instead of assuming the two notions of a line are identical.
    """
    commonmark_line = 1
    mapping: list[int] = []
    for raw in body.splitlines(keepends=True):
        mapping.append(commonmark_line)
        # CommonMark normalizes CRLF, CR and LF as source line endings. A CRLF pair is one ending;
        # this branch increments exactly once because the conditions are mutually exclusive.
        if raw.endswith("\r\n"):
            commonmark_line += 1
        elif raw.endswith("\r") or raw.endswith("\n"):
            commonmark_line += 1
    return mapping


def fenced_line_numbers(body: str) -> set[int]:
    """Return 1-based ``str.splitlines()`` indices belonging to actual CommonMark fence tokens."""
    commonmark_hidden: set[int] = set()
    for token in parser().parse(body):
        if token.type != "fence" or token.map is None:
            continue
        start, end = token.map
        commonmark_hidden.update(range(start + 1, end + 1))

    return {
        splitline_no
        for splitline_no, commonmark_line in enumerate(splitline_commonmark_numbers(body), 1)
        if commonmark_line in commonmark_hidden
    }


def visible_lines(body: str) -> list[tuple[int, str]]:
    """Return 1-based Python source fragments outside actual CommonMark fenced-code blocks."""
    hidden = fenced_line_numbers(body)
    return [
        (line_no, raw)
        for line_no, raw in enumerate(body.splitlines(), 1)
        if line_no not in hidden
    ]


def blank_fenced_lines(body: str) -> str:
    """Blank true fenced-code regions while preserving ``str.splitlines()`` indexing."""
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

    # Python's splitlines() recognizes boundaries that are not CommonMark source newlines. These
    # fragments must remain mapped to the same CommonMark line so they cannot shift a later fence
    # mask backwards onto visible identity prose. This is the adversarial review regression.
    for separator in ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
        shifted = (
            f"Research &{separator}Development Agency\n"
            "```text\n"
            "hidden\n"
            "```\n"
            "visible\n"
        )
        assert splitline_commonmark_numbers(shifted) == [1, 1, 2, 3, 4, 5], separator
        assert fenced_line_numbers(shifted) == {3, 4, 5}, separator
        assert visible_lines(shifted) == [
            (1, "Research &"),
            (2, "Development Agency"),
            (6, "visible"),
        ], separator

    # CRLF and bare CR are CommonMark source line endings and therefore advance parser line maps.
    assert splitline_commonmark_numbers("a\r\nb\rc\nd") == [1, 2, 3, 4]

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
    parser_arg = argparse.ArgumentParser()
    parser_arg.add_argument("--self-test", action="store_true")
    args = parser_arg.parse_args()
    if args.self_test:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
