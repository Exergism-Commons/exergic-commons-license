#!/usr/bin/env python3
"""Fail closed on standalone-ampersand identities split by rendered Markdown boundaries.

The primary ampersand checker historically inspected visible prose and inline-code contents as
separate candidate sources. That is insufficient when the rendered identity crosses a markup
boundary, for example ``Research & `Development Agency``` or the same shape across a soft line
break. This companion renders the complete source surface first and only then applies the
standalone-ampersand identity grammar.

Identity coverage is neutral: this checker never infers attribution, participation, control,
operation, supply, membership, culpability, or governance.
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


def rendered_ampersand_surfaces(raw: str) -> list[tuple[str, str]]:
    """Render the complete raw surface before extracting standalone-ampersand titles."""
    return amp.ampersand_title_surfaces(markup.rendered_line(raw))


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, rendered_text: str, snippet: str) -> None:
        for raw_value, raw_kind in amp.ampersand_title_surfaces(rendered_text):
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
                "reason": "rendered standalone-ampersand title lacks complete exact identity coverage",
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

        # Frontmatter values are already YAML-decoded. Render the whole scalar, including
        # decoded line breaks inside links/code spans, before applying the ampersand grammar.
        for field, line_no, raw in base.frontmatter_identity_values(text, front):
            inspect(
                state=state,
                source=source,
                location=f"frontmatter:{field}:{line_no}",
                rendered_text=markup.rendered_line(raw),
                snippet=f"{field}: {raw}",
            )

        line_offset = text[:body_offset].count("\n")
        body = text[body_offset:]

        # Scan every non-fenced source line after complete inline rendering. This closes the
        # same-line boundary class (e.g. ``Research & `Development Agency```), including
        # headings, table cells and list items.
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
                # The canonical H1 is structurally constrained by the State identity parity
                # checker and is outside this explicitly non-State identity guard.
                continue
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                rendered_text=markup.rendered_line(raw),
                snippet=raw,
            )

        # Then render complete paragraph/list blocks so code spans, links or emphasis crossing
        # source-line boundaries cannot split an ampersand identity either.
        for block in softwrap.prose_blocks(body):
            lines = [line for line in block["lines"] if line]
            if not lines:
                continue
            rendered_block, _ = softwrap.render_prose_block(lines)
            raw_lines = block["raw_lines"]
            inspect(
                state=state,
                source=source,
                location=f"rendered-block:{line_offset + block['relative_line']}",
                rendered_text=rendered_block,
                snippet=" / ".join(line.strip() for line in raw_lines),
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    same_line = rendered_ampersand_surfaces("Research & `Development Agency`")
    assert ("Research & Development Agency", "actor-or-institution") in same_line, same_line

    reverse = rendered_ampersand_surfaces("`Research` & Development Agency")
    assert ("Research & Development Agency", "actor-or-institution") in reverse, reverse

    emphasized = rendered_ampersand_surfaces("Research **& `Development Agency`**")
    assert ("Research & Development Agency", "actor-or-institution") in emphasized, emphasized

    linked = rendered_ampersand_surfaces("Research & [Development Agency](https://example.test)")
    assert ("Research & Development Agency", "actor-or-institution") in linked, linked

    multiline_scalar = rendered_ampersand_surfaces("Research & `Development\nAgency`")
    assert ("Research & Development Agency", "actor-or-institution") in multiline_scalar, multiline_scalar

    block, _ = softwrap.render_prose_block(["Research & `Development", "Agency` reported findings"])
    cross_line = amp.ampersand_title_surfaces(block)
    assert ("Research & Development Agency", "actor-or-institution") in cross_line, cross_line

    # A complete code span remains covered too; this companion must compose with the existing
    # guard rather than regress the already-fixed whole-code-span case.
    whole_code = rendered_ampersand_surfaces("`Research & Development Agency` is named")
    assert ("Research & Development Agency", "actor-or-institution") in whole_code, whole_code

    print("State dossier rendered-boundary ampersand coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_RENDER_BOUNDARY_AMPERSAND_TITLES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier rendered-boundary ampersand completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
