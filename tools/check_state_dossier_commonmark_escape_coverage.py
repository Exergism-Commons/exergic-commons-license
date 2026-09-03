#!/usr/bin/env python3
"""Fail closed on State-dossier identities exposed only after CommonMark backslash escapes.

A valid Markdown escape such as ``Research \\& Development Agency`` renders as
``Research & Development Agency``. The existing rendered-markup helper intentionally leaves
backslashes in place, so this independent companion performs the final CommonMark escape step
before applying the already-reviewed standalone-ampersand identity grammar.

Inline-code contents are protected while escapes are decoded: backslash escapes are not active
inside CommonMark code spans, and this guard must not manufacture identities from literal code.
Identity coverage remains neutral and creates no attribution, participation, control, supply,
culpability, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_ampersand_title_coverage as amp
import check_state_dossier_rendered_markup_coverage as markup
import check_state_dossier_softwrap_coverage as softwrap


FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
BACKSLASH_ESCAPE_RE = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])")


def rendered_with_commonmark_escapes(raw: str) -> str:
    """Render inline Markdown plus backslash escapes, preserving literal code-span contents."""
    code_spans: list[tuple[str, str]] = []

    def stash_code(match: re.Match[str]) -> str:
        token = f"\ue000CMCODE{len(code_spans)}\ue001"
        code_spans.append((token, " ".join(match.group(2).split())))
        return token

    # Protect code spans before any escape processing. The shared renderer can then handle
    # links/emphasis/HTML around them without changing literal backslashes inside the spans.
    skeleton = markup.CODE_SPAN_RE.sub(stash_code, raw)
    rendered = markup.rendered_line(skeleton)
    rendered = BACKSLASH_ESCAPE_RE.sub(lambda match: match.group(1), rendered)
    for token, code in code_spans:
        rendered = rendered.replace(token, code)
    return rendered


def commonmark_ampersand_surfaces(raw: str) -> list[tuple[str, str]]:
    return amp.ampersand_title_surfaces(rendered_with_commonmark_escapes(raw))


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, raw: str, snippet: str) -> None:
        for raw_value, raw_kind in commonmark_ampersand_surfaces(raw):
            value = amp.canonical_review_surface(identity_index, state, raw_value)
            kind = amp.classify_ampersand_surface(value) or raw_kind
            normalized = base.norm(value)
            uncovered = amp.uncovered_surface(identity_index, state, value)
            if uncovered is None:
                continue
            members, unresolved = uncovered
            key = (state, normalized, source, location)
            failures_by_key[key] = {
                "state": state,
                "candidate": value,
                "normalized": normalized,
                "kind": kind,
                "reason": "CommonMark-escaped standalone-ampersand title lacks complete exact identity coverage",
                "members": members,
                "unresolved_members": unresolved,
                "source": source,
                "location": location,
                "snippet": snippet[:420],
            }

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))
        text = path.read_text(encoding="utf-8")

        for field, line_no, raw in base.frontmatter_identity_values(text, front):
            inspect(
                state=state,
                source=source,
                location=f"frontmatter:{field}:{line_no}",
                raw=raw,
                snippet=f"{field}: {raw}",
            )

        line_offset = text[:body_offset].count("\n")
        body = text[body_offset:]
        fence_marker: str | None = None
        for rel_line, raw in enumerate(body.splitlines(), 1):
            fence = FENCE_RE.match(raw)
            if fence:
                marker = fence.group(1)[0]
                if fence_marker is None:
                    fence_marker = marker
                elif marker == fence_marker:
                    fence_marker = None
                continue
            if fence_marker is not None or not raw.strip():
                continue
            if raw.lstrip().startswith("# "):
                continue
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                raw=raw,
                snippet=raw,
            )

        # Assemble complete prose blocks before rendering so an escaped ampersand or adjacent
        # markup split by a source soft-wrap cannot form a second bypass class.
        for block in softwrap.prose_blocks(body):
            raw_lines = [line for line in block["raw_lines"] if line]
            if not raw_lines:
                continue
            raw_block = " ".join(line.strip() for line in raw_lines)
            inspect(
                state=state,
                source=source,
                location=f"commonmark-block:{line_offset + block['relative_line']}",
                raw=raw_block,
                snippet=" / ".join(line.strip() for line in raw_lines),
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    escaped = commonmark_ampersand_surfaces(r"Research \& Development Agency reported findings")
    assert ("Research & Development Agency", "actor-or-institution") in escaped, escaped

    boundary = commonmark_ampersand_surfaces(r"Research \& `Development Agency`")
    assert ("Research & Development Agency", "actor-or-institution") in boundary, boundary

    multiline = commonmark_ampersand_surfaces("Research \\&\nDevelopment Agency")
    assert ("Research & Development Agency", "actor-or-institution") in multiline, multiline

    escaped_emphasis = rendered_with_commonmark_escapes(r"Research \*literal\* text")
    assert escaped_emphasis == "Research *literal* text", escaped_emphasis

    # Backslash escapes are literal inside code spans. Do not turn this into an ampersand title.
    literal_code = commonmark_ampersand_surfaces(r"`Research \& Development Agency`")
    assert literal_code == [], literal_code

    print("State dossier CommonMark escape coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_COMMONMARK_ESCAPE_IDENTITIES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier CommonMark escape identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
