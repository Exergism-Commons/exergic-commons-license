#!/usr/bin/env python3
"""Discover high-confidence private-company/vendor names in canonical State dossiers.

Precision is preferred over recall. Generic phrases such as "private contractors" are
representation debt only when a dossier actually names a contractor. Domestic company
identities auto-resolve only inside their State; transnational identities may resolve
globally. This tool never creates attribution or governance semantics.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit_state_dossier_entities import frontmatter_identity_values, parse_frontmatter
from entity_identity_resolution import build_name_index, resolve_normalized

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "dossiers" / "states"
ENTITY_DIR = ROOT / "knowledge" / "entities"
STATE_ID_RE = re.compile(r"^ECL-STATE-([A-Z]{3})$")
PROPER = r"[A-Z][A-Za-z0-9&.'’/-]{2,}(?:\s+[A-Z][A-Za-z0-9&.'’/-]{2,}){0,3}"

CORPORATE_FORM_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'’/-]*(?:\s+(?:[A-Z][A-Za-z0-9&.'’/-]*|of|the|and)){0,5}\s+"
    r"(?:Ltd\.?|Limited|Inc\.?|Corp\.?|Corporation|Company|Technologies|Technology|Systems|Group|S\.A\.|AD|ZRT|Pte\.?\s+Ltd\.?))\b"
)
DIRECT_SUPPLIER_ACTION_RE = re.compile(
    rf"\b({PROPER})\s+"
    r"(?i:(?:itself\s+)?(?:halted|stopped|suspended|withdrew|supplied|provided|developed|sold|licensed|disabled|blocked)\s+"
    r"(?:its\s+|the\s+|a\s+|an\s+)?(?:product|products|technology|technologies|software|spyware|platform|tools?|service|services))\b"
)
LABELED_PRIVATE_RE = re.compile(
    rf"\b(?i:(?:supplier|vendor|contractor|private\s+company|technology\s+provider)\s+)(?P<name>{PROPER})\b"
)
STOP = {
    "Restricted Party", "Restricted Project", "Material Participation", "Covered Associate",
    "State Security", "Human Rights", "State Delta", "Federal Government", "High Court",
    "Court of Appeal", "United Nations", "European Union",
}
INLINE_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\((?:[^()\n]|\([^()\n]*\))*\)")
REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\[[^\]\n]*\]")
BRACKET_LABEL_RE = re.compile(r"(?<!!)\[([^\]\n]{2,120})\]")
HTML_BREAK_TAG_RE = re.compile(
    r"</?(?:br|p|div|li|ul|ol|table|tr|td|th|blockquote|section|article|h[1-6])\b[^>\n]*>", re.I
)
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
URL_RE = re.compile(r"https?://\S+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
MARKDOWN_EMPHASIS_RE = re.compile(r"(?<!\\)(?:\*{1,3}|_{1,3}|~{2})")
# A backtick fence is not a CommonMark opener when its info string contains a backtick. Tilde
# fences do not have that restriction. Keeping the rule in the shared renderer protects every
# consumer rather than requiring each downstream audit to rediscover the same visibility edge.
FENCE_RE = re.compile(r"^\s{0,3}((?:`{3,}(?![^\n]*`)|~{3,}))")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
LIST_RE = re.compile(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def canonical_dossiers() -> list[tuple[Path, str, int]]:
    rows: list[tuple[Path, str, int]] = []
    for path in sorted(STATE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        front, offset = parse_frontmatter(text)
        entity_id = front.get("id")
        if not isinstance(entity_id, str):
            continue
        match = STATE_ID_RE.fullmatch(entity_id)
        if not match:
            continue
        iso = match.group(1)
        if front.get("iso3") == iso and path.stem == iso:
            rows.append((path, iso, offset))
    return rows


def identity_index(state_codes: set[str]):
    records: list[dict] = []
    for path in ENTITY_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") != "State":
            records.append(data)
    return build_name_index(records, state_codes=state_codes, normalizer=norm)


def clean(name: str) -> str:
    return name.strip(" .,;:()[]{}\"'“”")


def plausible(name: str) -> bool:
    if not name or name in STOP or len(name) < 3:
        return False
    if name.startswith(("State ", "Current ", "Historical ", "Ordinary ", "UN ")):
        return False
    if "Working Group" in name:
        return False
    return True


def visible_prose(text: str) -> str:
    text = INLINE_LINK_RE.sub(lambda match: match.group(1), text)
    text = REFERENCE_LINK_RE.sub(lambda match: match.group(1), text)
    text = BRACKET_LABEL_RE.sub(lambda match: match.group(1), text)
    # Structural HTML creates a rendered separation; inline tags do not. Keeping that
    # distinction prevents both `Cellebrite<br>supplied` and `Celle<strong>brite</strong>`
    # from becoming detector bypasses in opposite directions.
    text = HTML_BREAK_TAG_RE.sub(" ", text)
    text = HTML_TAG_RE.sub("", text)
    text = URL_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    text = MARKDOWN_EMPHASIS_RE.sub("", text)
    return html.unescape(text)


def rendered_line_fragment(text: str) -> str:
    """Normalize source-newline syntax that renders only as whitespace."""
    value = text.rstrip()
    if value.endswith("\\"):
        value = value[:-1]
    return value.strip()


def rendered_prose_segments(body: str) -> list[tuple[int, str, str]]:
    """Return paragraph-like rendered prose segments with 1-based source line numbers.

    CommonMark soft and hard line breaks inside a paragraph are whitespace, so vendor/action
    phrases may span source lines. Structural block boundaries are not joined. Fenced code
    is excluded consistently with the existing inline-code policy. Fence closing follows the
    opening marker and run length: a shorter run inside a longer fence remains code content.
    """
    result: list[tuple[int, str, str]] = []
    buffer: list[str] = []
    raw_buffer: list[str] = []
    start_line: int | None = None
    fence_marker: str | None = None
    fence_length = 0

    def flush() -> None:
        nonlocal buffer, raw_buffer, start_line
        if buffer and start_line is not None:
            parts = [rendered_line_fragment(part) for part in buffer]
            prose = visible_prose(" ".join(part for part in parts if part))
            if prose.strip():
                result.append((start_line, " ".join(part.strip() for part in raw_buffer)[:420], prose))
        buffer = []
        raw_buffer = []
        start_line = None

    for line_no, raw in enumerate(body.splitlines(), 1):
        stripped = raw.strip()
        fence = FENCE_RE.match(raw)
        if fence:
            run = fence.group(1)
            marker = run[0]
            if fence_marker is None:
                flush()
                fence_marker = marker
                fence_length = len(run)
                continue
            if marker == fence_marker and len(run) >= fence_length and not raw[fence.end():].strip():
                fence_marker = None
                fence_length = 0
            # A shorter same-marker run, a different marker, or a run with trailing content
            # remains fenced code and must not be interpreted as prose or a new opener.
            continue
        if fence_marker is not None:
            continue
        if not stripped:
            flush()
            continue
        if HEADING_RE.match(raw):
            flush()
            heading = HEADING_RE.sub("", raw, count=1)
            prose = visible_prose(heading)
            if prose.strip():
                result.append((line_no, raw.strip()[:420], prose))
            continue
        if TABLE_SEPARATOR_RE.match(raw) or (stripped.startswith("|") and stripped.endswith("|")):
            flush()
            if not TABLE_SEPARATOR_RE.match(raw):
                prose = visible_prose(raw)
                if prose.strip():
                    result.append((line_no, raw.strip()[:420], prose))
            continue
        list_match = LIST_RE.match(raw)
        if list_match:
            flush()
            start_line = line_no
            content = raw[list_match.end():]
            buffer.append(content)
            raw_buffer.append(raw)
            continue
        quote = re.sub(r"^\s{0,3}(?:>\s*)+", "", raw)
        if start_line is None:
            start_line = line_no
        buffer.append(quote)
        raw_buffer.append(raw)
    flush()
    return result


def extract_names(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in CORPORATE_FORM_RE.finditer(text):
        value = clean(match.group(1))
        if plausible(value):
            found.append((value, "corporate-form"))
    for match in DIRECT_SUPPLIER_ACTION_RE.finditer(text):
        value = clean(match.group(1))
        if plausible(value):
            found.append((value, "direct-supplier-action"))
    for match in LABELED_PRIVATE_RE.finditer(text):
        value = clean(match.group("name"))
        if plausible(value):
            found.append((value, "explicit-private-label"))
    result: dict[str, tuple[str, str]] = {}
    priority = {"corporate-form": 3, "direct-supplier-action": 2, "explicit-private-label": 1}
    for value, method in found:
        key = norm(value)
        previous = result.get(key)
        if previous is None or priority[method] > priority[previous[1]]:
            result[key] = (value, method)
    return list(result.values())


def audit() -> dict:
    dossiers = canonical_dossiers()
    states = {iso for _, iso, _ in dossiers}
    known = identity_index(states)
    occurrences: list[dict] = []
    for path, iso, offset in dossiers:
        text = path.read_text(encoding="utf-8")
        front, parsed_offset = parse_frontmatter(text)
        if parsed_offset != offset:
            raise ValueError(f"frontmatter offset drift while auditing {path}")
        line_offset = text[:offset].count("\n")
        dossier = str(path.relative_to(ROOT))

        def record(prose: str, line: int, snippet: str) -> None:
            for name, method in extract_names(prose):
                matches = resolve_normalized(known, state=iso, normalized=norm(name))
                resolved = matches[0] if len(matches) == 1 else None
                occurrences.append({
                    "state": iso,
                    "candidate": name,
                    "normalized": norm(name),
                    "extraction": method,
                    "resolved_id": resolved,
                    "dossier": dossier,
                    "line": line,
                    "snippet": snippet,
                })

        # The contract permits identity-bearing prose only in these two frontmatter fields.
        # YAML decoding happens in the shared broad-audit parser, so folded/literal block
        # scalars cannot turn a named vendor into an unaudited continuation line.
        for field, line_no, raw in frontmatter_identity_values(text, front):
            record(visible_prose(raw), line_no, f"{field}: {raw}"[:420])

        for rel_line, snippet, prose in rendered_prose_segments(text[offset:]):
            record(prose, line_offset + rel_line, snippet)

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        key = ("resolved:" + row["resolved_id"], row["normalized"]) if row["resolved_id"] else (row["state"], row["normalized"])
        groups[key].append(row)
    candidates: list[dict] = []
    for rows in groups.values():
        display = Counter(row["candidate"] for row in rows).most_common(1)[0][0]
        resolved = next((row["resolved_id"] for row in rows if row["resolved_id"]), None)
        candidates.append({
            "candidate": display,
            "states": sorted({row["state"] for row in rows}),
            "resolution": "materialized" if resolved else "review-candidate",
            "resolved_id": resolved,
            "extraction_methods": sorted({row["extraction"] for row in rows}),
            "occurrence_count": len(rows),
            "occurrences": rows,
        })
    candidates.sort(key=lambda row: (row["resolution"] != "review-candidate", -row["occurrence_count"], row["candidate"].lower()))
    unresolved = [row for row in candidates if row["resolution"] == "review-candidate"]
    resolved = [row for row in candidates if row["resolution"] == "materialized"]
    return {
        "schema_version": 10,
        "semantics": {
            "purpose": "high-precision discovery of named private-organization/vendor candidates",
            "precision_policy": "corporate-form or direct vendor/private action only; unnamed contractor/supplier classes are not fabricated",
            "identity_resolution": "domestic identities resolve automatically only inside their State; transnational identities may resolve globally",
            "visible_text_policy": "ordinary Markdown links/references/emphasis, structural versus inline HTML, HTML entities and CommonMark soft/hard line breaks are normalized to rendered prose; fenced/inline code is excluded",
            "non_inference": [
                "private-organization mention does not prove legal-entity precision",
                "identity does not prove supply, participation, control or culpability",
                "supplier remediation/counter-evidence is represented symmetrically",
                "an unnamed contractor/supplier class remains non-enumerated rather than receiving an invented identity",
            ],
        },
        "counts": {
            "canonical_state_dossiers": len(dossiers),
            "candidate_groups": len(candidates),
            "resolved_groups": len(resolved),
            "unresolved_review_candidates": len(unresolved),
            "occurrences": len(occurrences),
        },
        "candidates": candidates,
    }


def write_markdown(report: dict, path: Path) -> None:
    counts = report["counts"]
    lines = [
        "# Private organization/vendor mention audit", "",
        "> High-precision discovery only. A candidate is not an identity assertion, supplier relation, attribution, or governance decision.", "",
        f"- State dossiers: **{counts['canonical_state_dossiers']}**",
        f"- High-confidence candidate groups: **{counts['candidate_groups']}**",
        f"- Already resolved: **{counts['resolved_groups']}**",
        f"- Unresolved review candidates: **{counts['unresolved_review_candidates']}**", "",
        "## Unresolved candidates", "",
        "| State(s) | Candidate | Extraction | Occurrences |", "|---|---|---|---:|",
    ]
    for row in report["candidates"]:
        if row["resolution"] != "review-candidate":
            continue
        name = row["candidate"].replace("|", "\\|")
        lines.append(f"| {','.join(row['states'])} | {name} | {','.join(row['extraction_methods'])} | {row['occurrence_count']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> None:
    expected = [("Cellebrite", "direct-supplier-action")]
    assert extract_names("Cellebrite halted product use in Serbia") == expected
    assert extract_names(visible_prose("[Cellebrite](https://example.test) supplied software")) == expected
    assert extract_names(visible_prose("[**Cellebrite**](https://example.test) supplied software")) == expected
    assert extract_names(visible_prose("**Cellebrite** supplied software")) == expected
    assert extract_names(visible_prose("[Cellebrite][vendor] supplied software")) == expected
    assert extract_names(visible_prose("[Cellebrite] supplied software")) == expected
    assert extract_names(visible_prose('<a href="https://example.test"><strong>Cellebrite</strong></a>&nbsp;supplied software')) == expected
    assert extract_names(visible_prose("Cellebrite<br>supplied software")) == expected
    assert extract_names(visible_prose("Celle<strong>brite</strong> supplied software")) == expected
    soft = rendered_prose_segments("Cellebrite\nsupplied software\n")
    assert len(soft) == 1 and extract_names(soft[0][2]) == expected
    hard = rendered_prose_segments("Cellebrite\\\nsupplied software\n")
    assert len(hard) == 1 and extract_names(hard[0][2]) == expected
    separate_items = rendered_prose_segments("- Cellebrite\n- supplied software\n")
    assert not any(extract_names(segment[2]) for segment in separate_items)
    fenced = rendered_prose_segments("```text\nCellebrite supplied software\n```\n")
    assert fenced == []
    invalid_backtick_info = rendered_prose_segments(
        "```bad`info\nCellebrite supplied software\n"
    )
    assert any(extract_names(segment[2]) == expected for segment in invalid_backtick_info), invalid_backtick_info
    tilde_backtick_info = rendered_prose_segments(
        "~~~bad`info\nCellebrite supplied software\n~~~\n"
    )
    assert tilde_backtick_info == []
    long_fence = rendered_prose_segments(
        "````text\n"
        "Cellebrite supplied software\n"
        "```\n"
        "Cellebrite supplied software\n"
        "````\n"
        "Cellebrite supplied software\n"
    )
    assert len(long_fence) == 1 and extract_names(long_fence[0][2]) == expected
    longer_close = rendered_prose_segments(
        "````text\nCellebrite supplied software\n`````\nCellebrite supplied software\n"
    )
    assert len(longer_close) == 1 and extract_names(longer_close[0][2]) == expected
    different_marker = rendered_prose_segments(
        "````text\n~~~\nCellebrite supplied software\n````\nCellebrite supplied software\n"
    )
    assert len(different_marker) == 1 and extract_names(different_marker[0][2]) == expected
    assert extract_names("private contractor support was reported") == []
    assert extract_names("UN HRC Working Group reported a technology issue") == []
    names = extract_names("Example Technologies supplied software")
    assert any(name == "Example Technologies" for name, _ in names)
    sample = (
        "---\n"
        "id: ECL-STATE-AAA\n"
        "iso3: AAA\n"
        "provisional_scope: >\n"
        "  Cellebrite supplied software\n"
        "adversarial_result: |-\n"
        "  [Cellebrite](https://example.test) supplied software\n"
        "---\n"
        "# State\n"
    )
    front, offset = parse_frontmatter(sample)
    assert offset > 0
    front_rows = frontmatter_identity_values(sample, front)
    assert [field for field, _, _ in front_rows] == ["provisional_scope", "adversarial_result"]
    assert all(extract_names(visible_prose(raw)) == expected for _, _, raw in front_rows)
    assert norm("Cellebrite") == "cellebrite"
    local = build_name_index(
        [
            {"id":"ORG-AAA-EXAMPLE","name":"Example Technologies","aliases":[]},
            {"id":"ORG-GLOBAL-VENDOR","name":"Global Vendor","aliases":[]},
        ], state_codes={"AAA", "BBB"}, normalizer=norm,
    )
    assert resolve_normalized(local, state="AAA", normalized=norm("Example Technologies")) == ["ORG-AAA-EXAMPLE"]
    assert resolve_normalized(local, state="BBB", normalized=norm("Example Technologies")) == []
    assert resolve_normalized(local, state="BBB", normalized=norm("Global Vendor")) == ["ORG-GLOBAL-VENDOR"]
    print("private organization audit self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fail-on-unresolved-private", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = audit()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.markdown)
    print(json.dumps(report["counts"], sort_keys=True))
    if args.fail_on_unresolved_private and report["counts"]["unresolved_review_candidates"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())