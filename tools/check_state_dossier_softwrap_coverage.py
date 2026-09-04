#!/usr/bin/env python3
"""Fail closed on named State-dossier candidates hidden across Markdown soft/hard line breaks."""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_rendered_markup_coverage as markup
import commonmark_fences as fences
import review_state_dossier_candidates as reviewed

ROOT = base.ROOT
LIST_RE = re.compile(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
BOUNDARY = "\ue000"
MULTILINE_INLINE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\([^\)]+\)", re.S)
MULTILINE_REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\[[^\]]*\]", re.S)


def source_line(raw: str) -> str:
    # A backslash immediately before a source newline is a CommonMark hard-break marker,
    # not visible prose. Remove it while preserving inline markup until the complete prose
    # block has been assembled; markup may itself span the source-line boundary.
    return re.sub(r"\\\s*$", "", raw)


def strip_quote(raw: str) -> str:
    return re.sub(r"^\s{0,3}(?:>\s*)+", "", raw)


def render_prose_block(lines: list[str]) -> tuple[str, list[int]]:
    """Render one assembled prose block while retaining source-line boundary positions.

    A private-use sentinel is inserted between source lines before Markdown normalization.
    This lets inline/reference links, emphasis and code spans be decoded across a soft break
    while still proving that a discovered identity actually crosses an original line boundary.
    """
    assembled = BOUNDARY.join(lines)
    assembled = MULTILINE_INLINE_LINK_RE.sub(lambda match: match.group(1), assembled)
    assembled = MULTILINE_REFERENCE_LINK_RE.sub(lambda match: match.group(1), assembled)
    rendered = markup.rendered_line(assembled)
    # Defensive cleanup for unmatched delimiter runs; completed code spans are already rendered
    # by markup.rendered_line(), including spans that cross the sentinel boundary.
    rendered = re.sub(r"`+", "", rendered)
    boundaries = [match.start() for match in re.finditer(re.escape(BOUNDARY), rendered)]
    return rendered.replace(BOUNDARY, " "), boundaries


def prose_blocks(body: str, *, hidden_lines: set[int] | None = None) -> list[dict]:
    """Build visible paragraph/list-item blocks while preserving source-line boundaries.

    ``hidden_lines`` is the authoritative set of 1-based fenced-code source lines when a caller has
    already parsed the CommonMark block structure. If omitted, this function derives that set once
    through the shared CommonMark parser. The assembler itself never recognizes fence marker syntax,
    so parser-visible backticks inside raw HTML cannot open a conflicting downstream fence state.
    """
    blocks: list[dict] = []
    section = "preamble"
    current: dict | None = None
    if hidden_lines is None:
        hidden_lines = fences.fenced_line_numbers(body)

    def flush() -> None:
        nonlocal current
        if current and current["lines"]:
            blocks.append(current)
        current = None

    for line_no, raw in enumerate(body.splitlines(), 1):
        if line_no in hidden_lines:
            flush()
            continue
        heading = base.HEADING_RE.match(raw)
        if heading:
            flush()
            section = heading.group(1).strip()
            continue
        if not raw.strip() or TABLE_RE.match(raw):
            flush()
            continue

        list_match = LIST_RE.match(raw)
        if list_match:
            flush()
            value = source_line(strip_quote(raw[list_match.end():])).strip()
            current = {
                "relative_line": line_no,
                "section": section,
                "raw_lines": [raw],
                "lines": [value],
            }
            continue

        value = source_line(strip_quote(raw)).strip()
        if current is None:
            current = {"relative_line": line_no, "section": section, "raw_lines": [raw], "lines": [value]}
        else:
            current["raw_lines"].append(raw)
            current["lines"].append(value)
    flush()
    return blocks


def cross_line_candidates(body: str) -> list[dict]:
    """Extract TITLE_RE candidates whose rendered match crosses a source-line boundary."""
    found: list[dict] = []
    for block in prose_blocks(body):
        lines = [line for line in block["lines"] if line]
        if len(lines) < 2:
            continue
        joined, boundaries = render_prose_block(lines)
        for match in base.TITLE_RE.finditer(joined):
            if not any(match.start() <= boundary < match.end() for boundary in boundaries):
                continue
            value = base.clean_candidate(match.group(0))
            kind = base.classify(value)
            if kind and base.plausible(value):
                found.append({
                    "relative_line": block["relative_line"],
                    "section": block["section"],
                    "candidate": value,
                    "normalized": base.norm(value),
                    "kind": kind,
                    "snippet": " / ".join(raw.strip() for raw in block["raw_lines"])[:420],
                })
    dedup: dict[tuple[int, str, str], dict] = {}
    for row in found:
        dedup[(row["relative_line"], row["normalized"], row["kind"])] = row
    return list(dedup.values())


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    state_codes = {front["iso3"] for _, front, _ in dossiers}
    identity_index, _, _ = base.load_identity_index(state_codes)
    dispositions, _ = reviewed.load_dispositions()
    failures: list[dict] = []
    for path, front, body_offset in dossiers:
        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        state = front["iso3"]
        for row in cross_line_candidates(text[body_offset:]):
            resolved = base.resolve_name(identity_index, state, row["candidate"])
            disposition = dispositions.get((state, row["normalized"]))
            if resolved is not None or disposition is not None:
                continue
            failures.append({
                "state": state,
                "candidate": row["candidate"],
                "normalized": row["normalized"],
                "kind": row["kind"],
                "dossier": str(path.relative_to(ROOT)),
                "line": line_offset + row["relative_line"],
                "section": row["section"],
                "snippet": row["snippet"],
            })
    return failures


def self_test() -> None:
    fences.self_test()
    rows = cross_line_candidates("Australian Human\nRights Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in rows), rows
    hard = cross_line_candidates("Australian Human\\\nRights Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in hard), hard
    three = cross_line_candidates("Australian\nHuman Rights\nCommission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in three), three
    bold = cross_line_candidates("Australian **Human\nRights** Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in bold), bold
    html_split = cross_line_candidates("Australian <strong>Human\nRights</strong> Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in html_split), html_split
    code_split = cross_line_candidates("Australian `Human\nRights` Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in code_split), code_split
    link_split = cross_line_candidates("National [Cyber\nCrime Investigation](https://e.test) Agency reported findings.\n")
    assert any(row["candidate"] == "National Cyber Crime Investigation Agency" for row in link_split), link_split
    reference_split = cross_line_candidates("National [Cyber\nCrime Investigation][nccia] Agency reported findings.\n")
    assert any(row["candidate"] == "National Cyber Crime Investigation Agency" for row in reference_split), reference_split
    assert cross_line_candidates("- Example Vendor\n- Technology supplied software\n") == []
    assert cross_line_candidates("```text\nAustralian Human\nRights Commission\n```\n") == []
    assert cross_line_candidates("## Australian Human\nRights Commission\n") == []

    # Parser-composition regression: a fence-looking line inside raw HTML is visible CommonMark
    # content and must never switch this assembler into a second, legacy fence state. The visible
    # title after the raw HTML block therefore remains part of the auditable soft-wrap stream.
    raw_html_fence = (
        "<pre>\n"
        "```text\n"
        "</pre>\n"
        "Research \\&\n"
        "Development Agency\n"
    )
    parser_hidden = fences.fenced_line_numbers(raw_html_fence)
    assert parser_hidden == set(), parser_hidden
    raw_blocks = prose_blocks(raw_html_fence, hidden_lines=parser_hidden)
    assert any(
        r"Research \&" in block["lines"] and "Development Agency" in block["lines"]
        for block in raw_blocks
    ), raw_blocks

    # A true CommonMark fence is still excluded when its parser-derived ranges are supplied rather
    # than reinterpreted by the assembler.
    true_fence_body = "```text\nHidden Agency\n```\nAustralian Human\nRights Commission\n"
    true_hidden = fences.fenced_line_numbers(true_fence_body)
    true_fence = prose_blocks(true_fence_body, hidden_lines=true_hidden)
    assert all("Hidden Agency" not in line for block in true_fence for line in block["lines"]), true_fence
    assert any(
        block["lines"] == ["Australian Human", "Rights Commission"]
        for block in true_fence
    ), true_fence

    print("State dossier soft/hard-wrap + inline-markup coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNREVIEWED_SOFTWRAP_CANDIDATES=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("State dossier soft/hard-wrap + inline-markup coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
