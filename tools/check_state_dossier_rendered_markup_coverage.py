#!/usr/bin/env python3
"""Fail closed on named State-dossier candidates hidden by rendered inline markup."""
from __future__ import annotations

import argparse
import html
import json
import re

import audit_state_dossier_entities as base
import review_state_dossier_candidates as reviewed
from entity_identity_resolution import build_name_index

ROOT = base.ROOT
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
REFERENCE_LINK_RE = re.compile(r"(?<!!)\[([^\]\n]+)\]\[[^\]\n]*\]")
BRACKET_LABEL_RE = re.compile(r"(?<!!)\[([^\]\n]{2,120})\]")
HTML_BREAK_TAG_RE = re.compile(
    r"</?(?:br|p|div|li|ul|ol|table|tr|td|th|blockquote|section|article|h[1-6])\b[^>\n]*>", re.I
)
HTML_TAG_RE = re.compile(r"<[^>\n]+>")
EMPHASIS_RE = re.compile(r"(?<!\\)(?:\*{1,3}|_{1,3}|~{2})")
# YAML-decoded frontmatter scalars may contain literal/folded line breaks inside a Markdown
# code span. CommonMark renders those line endings as spaces, so allow them here and keep the
# existing whitespace normalization in rendered_line(). Body fenced code remains excluded by
# the audit loop and is not widened into identity-bearing prose.
CODE_SPAN_RE = re.compile(r"(`+)(.*?)\1", re.S)
LEADING_DISCOURSE_RE = re.compile(r"^(?:only\s+the\s+|only\s+|the\s+)", re.I)


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


def strip_discourse_prefix(candidate: str) -> str:
    return LEADING_DISCOURSE_RE.sub("", candidate, count=1).strip()


def identity_kind_matches(index, entity_id: str, kind: str) -> bool:
    entity = index.by_id.get(entity_id) or {}
    is_project = entity.get("type") in {"Project", "Deployment"}
    return is_project if kind == "project-or-deployment" else not is_project


def covered_by_visible_materialized_identity(index, *, state: str, candidate: str, kind: str, rendered: str) -> bool:
    """Accept only a syntactic fragment of one fully visible, already materialized identity.

    Rendered markup can make TITLE_RE surface a grammatical prefix (`Only X`) or stop at an
    em dash inside an exact canonical name (`Parent — Division`). We do not create broad
    aliases for those fragments. Instead, coverage is accepted only when either:
      * removing a narrow discourse determiner yields an exact resolvable identity; or
      * that stripped fragment is the prefix of a unique in-scope canonical name/alias and
        the complete canonical name/alias is visibly present on the same rendered line.
    This prevents a partial regex match from being mistaken for representation of an
    independently named parent body.
    """
    stripped = strip_discourse_prefix(candidate)
    if stripped != candidate:
        exact = base.resolve_name(index, state, stripped)
        if exact is not None and identity_kind_matches(index, exact, kind):
            return True

    candidate_norm = base.norm(stripped)
    rendered_norm = base.norm(rendered)
    if not candidate_norm or not rendered_norm:
        return False

    name_maps = [index.state_names.get(state, {}), index.global_names]
    for name_map in name_maps:
        for full_name, ids in name_map.items():
            if len(ids) != 1:
                continue
            entity_id = next(iter(ids))
            if not identity_kind_matches(index, entity_id, kind):
                continue
            if not full_name.startswith(candidate_norm + " "):
                continue
            if f" {full_name} " not in f" {rendered_norm} ":
                continue
            return True
    return False


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

        def inspect_rendered_surface(raw: str, *, line: int, section: str, snippet: str) -> None:
            rendered = rendered_line(raw)
            for normalized, candidate, kind in rendered_only_candidates(raw):
                resolved = base.resolve_name(identity_index, state, candidate)
                disposition = dispositions.get((state, normalized))
                if resolved is not None or disposition is not None:
                    continue
                if covered_by_visible_materialized_identity(
                    identity_index, state=state, candidate=candidate, kind=kind, rendered=rendered
                ):
                    continue
                failures.append({
                    "state": state,
                    "candidate": candidate,
                    "normalized": normalized,
                    "kind": kind,
                    "dossier": str(path.relative_to(ROOT)),
                    "line": line,
                    "section": section,
                    "snippet": snippet[:420],
                })

        # The same rendered-markup companion that protects body prose also protects the two
        # contract-authorized identity-bearing frontmatter fields. YAML decoding happens first,
        # so folded/literal scalars and inline markup cannot form a separate coverage bypass.
        for field, line_no, raw in base.frontmatter_identity_values(text, front):
            inspect_rendered_surface(
                raw,
                line=line_no,
                section=f"frontmatter:{field}",
                snippet=f"{field}: {raw}",
            )

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
            inspect_rendered_surface(
                raw,
                line=line_offset + relative_line,
                section=section,
                snippet=raw.strip(),
            )
    return failures


def self_test() -> None:
    bold = rendered_only_candidates("Australian **Human Rights** Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in bold), bold
    nccia = rendered_only_candidates("National **Cyber Crime Investigation** Agency")
    assert any(candidate == "National Cyber Crime Investigation Agency" for _, candidate, _ in nccia), nccia
    html_split = rendered_only_candidates("Australian <strong>Human Rights</strong> Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in html_split), html_split
    code_span = rendered_only_candidates("Australian `Human Rights` Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in code_span), code_span
    multi_code = rendered_only_candidates("Australian ``Human Rights`` Commission reported findings")
    assert any(candidate == "Australian Human Rights Commission" for _, candidate, _ in multi_code), multi_code
    multiline_code = rendered_only_candidates("National `Cyber\nCrime Investigation` Agency")
    assert any(
        candidate == "National Cyber Crime Investigation Agency" for _, candidate, _ in multiline_code
    ), multiline_code
    multiline_multi_code = rendered_only_candidates("National ``Cyber\nCrime Investigation`` Agency")
    assert any(
        candidate == "National Cyber Crime Investigation Agency" for _, candidate, _ in multiline_multi_code
    ), multiline_multi_code
    assert rendered_line("National `Cyber\nCrime Investigation` Agency") == "National Cyber Crime Investigation Agency"
    assert rendered_only_candidates("Australian Human Rights Commission reported findings") == []

    index = build_name_index(
        [
            {"id": "AGENCY-AAA-NCCIA", "type": "Agency", "name": "National Cyber Crime Investigation Agency", "aliases": ["NCCIA"]},
            {"id": "AGENCY-AAA-DIV", "type": "Agency", "name": "Immigration Department of Example — Detention Division", "aliases": ["Detention Division"]},
        ],
        state_codes={"AAA"},
        normalizer=base.norm,
    )
    assert covered_by_visible_materialized_identity(
        index,
        state="AAA",
        candidate="Only the National Cyber Crime Investigation Agency",
        kind="actor-or-institution",
        rendered="Only the National Cyber Crime Investigation Agency (NCCIA) is in scope",
    )
    assert covered_by_visible_materialized_identity(
        index,
        state="AAA",
        candidate="The Immigration Department of Example",
        kind="actor-or-institution",
        rendered="The Immigration Department of Example — Detention Division is in scope",
    )
    assert not covered_by_visible_materialized_identity(
        index,
        state="AAA",
        candidate="Immigration Department of Example",
        kind="actor-or-institution",
        rendered="Immigration Department of Example is separately named here",
    )
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