#!/usr/bin/env python3
"""Fail closed on named State-dossier candidates hidden across Markdown soft line breaks."""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import review_state_dossier_candidates as reviewed

ROOT = base.ROOT
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
LIST_RE = re.compile(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")


def visible_line(raw: str) -> str:
    line = base.URL_RE.sub("", raw)
    return base.MD_LINK_RE.sub(lambda match: match.group(1), line)


def strip_quote(raw: str) -> str:
    return re.sub(r"^\s{0,3}(?:>\s*)+", "", raw)


def prose_blocks(body: str) -> list[dict]:
    """Build paragraph/list-item blocks while preserving every source-line boundary."""
    blocks: list[dict] = []
    section = "preamble"
    fence_marker: str | None = None
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and current["lines"]:
            blocks.append(current)
        current = None

    for line_no, raw in enumerate(body.splitlines(), 1):
        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)[0]
            if fence_marker is None:
                flush()
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            continue
        if fence_marker is not None:
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
            current = {
                "relative_line": line_no,
                "section": section,
                "raw_lines": [raw],
                "lines": [visible_line(strip_quote(raw[list_match.end():])).strip()],
            }
            continue

        value = visible_line(strip_quote(raw)).strip()
        if current is None:
            current = {"relative_line": line_no, "section": section, "raw_lines": [raw], "lines": [value]}
        else:
            current["raw_lines"].append(raw)
            current["lines"].append(value)
    flush()
    return blocks


def cross_line_candidates(body: str) -> list[dict]:
    """Extract TITLE_RE candidates whose match crosses one or more rendered line boundaries."""
    found: list[dict] = []
    for block in prose_blocks(body):
        lines = [line for line in block["lines"] if line]
        if len(lines) < 2:
            continue
        joined_parts: list[str] = []
        boundaries: list[int] = []
        length = 0
        for index, line in enumerate(lines):
            if index:
                boundaries.append(length)
                joined_parts.append(" ")
                length += 1
            joined_parts.append(line)
            length += len(line)
        joined = "".join(joined_parts)
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
    rows = cross_line_candidates("Australian Human\nRights Commission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in rows), rows
    three = cross_line_candidates("Australian\nHuman Rights\nCommission reported findings.\n")
    assert any(row["candidate"] == "Australian Human Rights Commission" for row in three), three
    assert cross_line_candidates("- Example Vendor\n- Technology supplied software\n") == []
    assert cross_line_candidates("```text\nAustralian Human\nRights Commission\n```\n") == []
    assert cross_line_candidates("## Australian Human\nRights Commission\n") == []
    print("State dossier soft-wrap coverage self-test: OK")


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
    print("State dossier soft-wrap coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
