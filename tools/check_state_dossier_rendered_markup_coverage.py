#!/usr/bin/env python3
"""Fail closed on named State-dossier candidates hidden by rendered inline markup."""
from __future__ import annotations

import argparse
import html
import json
import re

import audit_state_dossier_entities as base
import review_state_dossier_candidates as reviewed

ROOT = base.ROOT
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\[[^\]\n]*\]")
BRACKET_LABEL_RE = re.compile(r"(?<!!)\[([^\]\n]{2,120})\]")
HTML_BREAK_TAG_RE = re.compile(
    r"</?(?:br|p|div|li|ul|ol|table|tr|td|th|blockquote|section|article|h[1-6])\b[^>\n]*>", re.I
)
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
EMPHASIS_RE = re.compile(r"(?<!\\)(?:\*{1,3}|_{1,3}|~{2})")
CODE_SPAN_RE = re.compile(r"(`+)([^\n]*?)\1")


def baseline_line(raw: str) -> str:
    line = base.URL_RE.sub("", raw)
    return base.MD_LINK_RE.sub(lambda match: match.group(1), line)


def rendered_line(raw: str) -> str:
    line = baseline_line(raw)
    line = REFERENCE_LINK_RE.sub(lambda match: match.group(1), line)
    line = BRACKET_LABEL_RE.sub(lambda match: match.group(1), line)
    line = CODE_SPAN_RE.sub(lambda match: " ".join(match.group(2).split()), line)
    line = HTML_BREAK_TAG_RE.sub(" ", line)
    line = HTML_TAG_RE.sub("", line)
    line = EMPHASIS_RE.sub("", line)
    return html.unescape(line)


def title_candidates(text: str) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for match in base.TITLE_RE.finditer(text):
        value = base.clean_candidate(match.group(0))
        kind = base.classify(value)
        if kind and base.plausible(value):
            result.setdefault(base.norm(value), (value, kind))
    return result


def rendered_only_candidates(raw: str) -> list[tuple[str, str, str]]:
    before = title_candidates(baseline_line(raw))
    after = title_candidates(rendered_line(raw))
    return [(normalized, value, kind) for normalized, (value, kind) in after.items() if normalized not in before]


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {front["iso3"] for _, front, _ in dossiers}
    identity_index, _, _ = base.load_identity_index(states)
    dispositions, _ = reviewed.load_dispositions()
    failures: list[dict] = []

    for path, front, body_offset in dossiers:
        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        state = front["iso3"]
        section = "preamble"
        fence_marker: str | None = None
        for relative_line, raw in enumerate(text[body_offset:].splitlines(), 1):
            fence = FENCE_RE.match(raw)
            if fence:
                marker = fence.group(1)[0]
                if fence_marker is None:
                    fence_marker = marker
                elif marker == fence_marker:
                    fence_marker = None
                continue
            if fence_marker is not None:
                continue
            heading = base.HEADING_RE.match(raw)
            if heading:
                section = heading.group(1).strip()
                continue
            if not raw.strip():
                continue
            for normalized, candidate, kind in rendered_only_candidates(raw):
                resolved = base.resolve_name(identity_index, state, candidate)
                disposition = dispositions.get((state, normalized))
                if resolved is not None or disposition is not None:
                    continue
                failures.append({
                    "state": state,
                    "candidate": candidate,
                    "normalized": normalized,
                    "kind": kind,
                    "dossier": str(path.relative_to(ROOT)),
                    "line": line_offset + relative_line,
                    "section": section,
                    "snippet": raw.strip()[:420],
                })
    return failures


def self_test() -> None:
    bold = rendered_only_candidates("Australian **Human Rights** Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in bold), bold
    html_split = rendered_only_candidates("Australian <strong>Human Rights</strong> Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in html_split), html_split
    code_span = rendered_only_candidates("Australian `Human Rights` Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in code_span), code_span
    multi_code = rendered_only_candidates("Australian ``Human Rights`` Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in multi_code), multi_code
    assert rendered_only_candidates("Australian Human Rights Commission reported findings") == []
    print("State dossier rendered-markup coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNREVIEWED_RENDERED_MARKUP_CANDIDATES=" + json.dumps(failures, ensure_ascii=False, sort_keys=True))
        return 2
    print("State dossier rendered-markup coverage: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
