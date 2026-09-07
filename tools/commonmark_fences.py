#!/usr/bin/env python3
"""Shared CommonMark fenced-code visibility semantics for State dossier audits.

Fence visibility is intentionally delegated to a standards-conformant CommonMark block parser.
Identity auditors must not carry their own regex/state machine: fenced-code recognition interacts
with other block constructs (notably raw HTML, indented code and block containers), so even a locally
accurate fence grammar can be wrong in context.

The audit pipeline has historically assembled prose with Python's ``str.splitlines()`` while
markdown-it-py reports token maps in CommonMark source-line coordinates. Python recognizes several
additional Unicode/control separators that CommonMark keeps inside the current source line. Rather
than let different consumers reinterpret those characters differently, this module rejects them
fail-closed. Accepted audit source therefore has one unambiguous line model: CRLF, CR and LF are the
only source line endings, matching CommonMark token maps and every downstream ``splitlines()`` loop.
"""
from __future__ import annotations

import argparse
from typing import Any


_PARSER: Any | None = None

# str.splitlines() treats these characters as line boundaries, but CommonMark does not. Allowing
# them would give parser token maps and downstream prose assemblers different structural line
# models; repeated/adjacent separators can even manufacture an empty Python line and flush a
# visible identity out of a paragraph. Reject the entire class instead of chasing compositions.
_NON_COMMONMARK_LINE_SEPARATORS = {
    "\x0b": "VT",
    "\x0c": "FF",
    "\x1c": "FS",
    "\x1d": "GS",
    "\x1e": "RS",
    "\x85": "NEL",
    "\u2028": "LINE SEPARATOR",
    "\u2029": "PARAGRAPH SEPARATOR",
}


def validate_source_line_model(body: str) -> None:
    """Reject source separators that disagree with CommonMark's CR/LF line model."""
    found = sorted(
        {
            (ord(char), name)
            for char, name in _NON_COMMONMARK_LINE_SEPARATORS.items()
            if char in body
        }
    )
    if found:
        rendered = ", ".join(f"U+{codepoint:04X} {name}" for codepoint, name in found)
        raise ValueError(
            "unsupported non-CommonMark source line separator(s): "
            f"{rendered}; use ordinary CR/LF line endings or visible whitespace"
        )


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

    ``validate_source_line_model`` guarantees that only CRLF, CR and LF may create source-line
    boundaries, so Python and CommonMark advance in lockstep. The explicit mapping remains useful
    as an executable invariant for consumers and regression tests.
    """
    validate_source_line_model(body)
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
    # Validate before parsing so every caller fails closed before it can assemble prose with a
    # structurally different notion of a line.
    validate_source_line_model(body)
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

    # Adversarial line-model regression: every separator that Python would split but CommonMark
    # would retain inside a source line is rejected before any consumer can assemble prose. Cover
    # both a single separator and the exact repeated-separator composition that previously created
    # an artificial empty Python line and flushed the visible title.
    for separator, name in _NON_COMMONMARK_LINE_SEPARATORS.items():
        for injected in (separator, separator + separator, separator + "\n", "\n" + separator):
            shifted = (
                f"Research &{injected}Development Agency\n"
                "```text\n"
                "hidden\n"
                "```\n"
                "visible\n"
            )
            try:
                fenced_line_numbers(shifted)
            except ValueError as exc:
                message = str(exc)
                assert name in message and "non-CommonMark" in message, (separator, message)
            else:
                raise AssertionError((separator, injected, "non-CommonMark separator was accepted"))

    # Ordinary CRLF, bare CR and LF remain supported and advance CommonMark source lines exactly.
    assert splitline_commonmark_numbers("a\r\nb\rc\nd") == [1, 2, 3, 4]
    crlf_fence = "visible\r\n```text\r\nhidden\r\n```\r\nafter"
    assert fenced_line_numbers(crlf_fence) == {2, 3, 4}
    assert visible_lines(crlf_fence) == [(1, "visible"), (5, "after")]

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
