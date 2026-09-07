#!/usr/bin/env python3
"""Shared CommonMark fenced-code visibility semantics for State dossier audits.

Fence visibility is intentionally delegated to a standards-conformant CommonMark block parser.
Identity auditors must not carry their own regex/state machine: fenced-code recognition interacts
with other block constructs (notably raw HTML, indented code and block containers), so even a locally
accurate fence grammar can be wrong in context.

The audit pipeline has historically assembled prose with Python's ``str.splitlines()`` and
``str.strip()`` while markdown-it-py applies CommonMark source-line and blank-line semantics. Python
recognizes extra line separators and also treats several extra Unicode/control characters as
whitespace-only lines that CommonMark keeps inside the current paragraph. Rather than let consumers
reinterpret either class differently, this module rejects both discrepancies fail-closed. Accepted
audit source therefore has one unambiguous structural line model: CRLF, CR and LF are the only source
line endings, and only ASCII space/tab may make a non-empty source line structurally blank.
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

# Python's strip()/isspace() classify these as whitespace, while CommonMark blank lines are made
# only from spaces and tabs. A line containing only one of these remains paragraph content to
# CommonMark but historically caused Python prose assemblers to flush the paragraph. Keep the
# explicit runtime set as regression documentation; validation below is predicate-based so a future
# Python Unicode-table addition fails closed too instead of silently creating a new bypass class.
_PYTHON_ONLY_BLANK_WHITESPACE = (
    "\x1f",
    "\u00a0",
    "\u1680",
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u202f",
    "\u205f",
    "\u3000",
)


def validate_source_line_model(body: str) -> None:
    """Reject source constructs for which Python and CommonMark disagree structurally."""
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

    # CommonMark defines a blank line using ASCII space/tab. Python's strip() removes a larger
    # Unicode whitespace class. All downstream assemblers use strip() for structural blank checks,
    # so reject only the dangerous composition: a non-empty physical line that Python would erase
    # completely but CommonMark would retain as paragraph content. Unicode whitespace remains legal
    # inside any line that also contains visible content.
    for line_no, raw in enumerate(body.splitlines(), 1):
        if not raw or raw.strip():
            continue
        unexpected = sorted({ord(char) for char in raw if char not in " \t"})
        if not unexpected:
            continue
        rendered = ", ".join(f"U+{codepoint:04X}" for codepoint in unexpected)
        raise ValueError(
            "unsupported Python-only blank source line "
            f"{line_no} containing {rendered}; use ASCII space/tab for blank lines or add visible content"
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

    # Arbitrary or Unicode trailing content does not silently become a valid closer. NBSP is legal
    # when the physical line also contains visible content; only Python-only blank lines are banned.
    trailing = "```text\nhidden\n``` trailing\nstill hidden\n```\nvisible"
    assert visible_lines(trailing) == [(6, "visible")]
    unicode_tail = "```text\nhidden\n```\u00a0\nstill hidden\n```\nvisible"
    assert visible_lines(unicode_tail) == [(6, "visible")]
    assert visible_lines("Research\u00a0& Development Agency") == [(1, "Research\u00a0& Development Agency")]

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

    # Adversarial blank-line regression: Python strips a larger Unicode whitespace class than
    # CommonMark recognizes as a blank line. Each of these used to split one CommonMark paragraph
    # into two Python prose blocks and could hide a complete cross-line identity.
    for whitespace in _PYTHON_ONLY_BLANK_WHITESPACE:
        shifted = f"Research &\n{whitespace}\nDevelopment Agency\n"
        try:
            fenced_line_numbers(shifted)
        except ValueError as exc:
            message = str(exc)
            assert "Python-only blank" in message and f"U+{ord(whitespace):04X}" in message, (
                whitespace,
                message,
            )
        else:
            raise AssertionError((whitespace, "Python-only blank source line was accepted"))

        # Mixed ASCII space/tab plus the same character is the same structural mismatch.
        mixed_blank = f"Research &\n \t{whitespace}\t \nDevelopment Agency\n"
        try:
            fenced_line_numbers(mixed_blank)
        except ValueError as exc:
            assert "Python-only blank" in str(exc), (whitespace, str(exc))
        else:
            raise AssertionError((whitespace, "mixed Python-only blank source line was accepted"))

    # Pin the current Python whitespace table so a runtime Unicode change cannot silently extend
    # strip()'s structural blank class without an explicit regression update.
    current_python_only_blank = tuple(
        chr(codepoint)
        for codepoint in range(0x110000)
        if chr(codepoint).isspace()
        and chr(codepoint) not in " \t\r\n"
        and chr(codepoint) not in _NON_COMMONMARK_LINE_SEPARATORS
    )
    assert current_python_only_blank == _PYTHON_ONLY_BLANK_WHITESPACE, current_python_only_blank

    # Ordinary CommonMark blanks made only from ASCII spaces/tabs remain supported.
    ascii_blank = "before\n \t \nafter"
    assert fenced_line_numbers(ascii_blank) == set()
    assert visible_lines(ascii_blank) == [(1, "before"), (2, " \t "), (3, "after")]

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
