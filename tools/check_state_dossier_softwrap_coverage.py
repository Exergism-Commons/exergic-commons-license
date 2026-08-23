#!/usr/bin/env python3
"""Fail closed on named State-dossier candidates hidden across Markdown soft line breaks."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import audit_state_dossier_entities as base
import review_state_dossier_candidates as reviewed

ROOT = Path(__file__).resolve().parents[1]
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
LIST_RE = re.compile(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")


def visible_line(raw: str) -> str:
    line = base.URL_RE.sub("", raw)
    return base.MD_LINK_RE.sub(lambda match: match.group(1), line)


def strip_quote(raw: str) -> str:
    return re.sub(r"^\s{0,3}(?:>\s*)+", "", raw)


def cross_line_candidates(body: str) -> list[dict]:
    """Extract only TITLE_RE candidates whose regex match crosses a valid line boundary."""
    lines = body.splitlines()
    sections: list[str] = []
    section = "preamble"
    fence_marker: str | None = None
    usable: list[bool] = []

    for raw in lines:
        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)[0]
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            sections.append(section)
            usable.append(False)
            continue
        if fence_marker is not None:
            sections.append(section)
            usable.append(False)
            continue
        heading = base.HEADING_RE.match(raw)
        if heading:
            section = heading.group(1).strip()
            sections.append(section)
            usable.append(False)
            continue
        sections.append(section)
        usable.append(bool(raw.strip()) and not TABLE_RE.match(raw))

    found: list[dict] = []
    for index in range(len(lines) - 1):
        if not usable[index] or not usable[index + 1] or sections[index] != sections[index + 1]:
            continue
        left_raw, right_raw = lines[index], lines[index + 1]
        # A new list item is a separate block. A list item followed by continuation prose
        # is one block and remains eligible.
        if LIST_RE.match(right_raw):
            continue
        left = LIST_RE.sub("", strip_quote(left_raw), count=1)
        right = strip_quote(right_raw)
        left = visible_line(left)
        right = visible_line(right)
        if not left.strip() or not right.strip():
            continue
        joined = left.rstrip() + " " + right.lstrip()
        boundary = len(left.rstrip())
        for match in base.TITLE_RE.finditer(joined):
            if not (match.start() <= boundary < match.end()):
                continue
            value = base.clean_candidate(match.group(0))
            kind = base.classify(value)
            if kind and base.plausible(value):
                found.append({
                    "relative_line": index + 1,
                    "section": sections[index],
                    "candidate": value,
                    "normalized": base.norm(value),
                    "kind": kind,
                    "snippet": f"{left_raw.strip()} / {right_raw.strip()}"[:420],
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
