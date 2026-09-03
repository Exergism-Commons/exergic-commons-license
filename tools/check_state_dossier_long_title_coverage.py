#!/usr/bin/env python3
"""Fail closed when the broad State title grammar reaches its historical token ceiling.

The baseline ``TITLE_RE`` historically admitted one leading title word plus at most eight
continuations. This companion does not replace broad discovery. Instead it detects the exact
failure mode: a baseline match that consumes all nine allowed tokens and is immediately
followed by more title-shaped identity text. It reconstructs the complete maximal title run
and requires the full surface to be materialized or explicitly reviewed.

This keeps ordinary short-title behavior unchanged while making the historical ceiling
fail-closed. Identity coverage is neutral and creates no attribution, participation, control,
operation, supply, culpability, membership, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_rendered_markup_coverage as markup
import check_state_dossier_softwrap_coverage as softwrap
import review_state_dossier_candidates as reviewed


FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
TITLE_WORD = r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9&.'’/-]*|[A-ZÀ-ÖØ-Þ]{2,})"
# Include common identity-internal prepositions/coordinators. In particular ``or`` is needed
# for reviewed institutional names such as ``... Cruel Inhuman or Degrading Treatment ...``.
TITLE_CONNECTOR = r"(?:of|the|and|or|for|against|on|in|to|de|del|la|le|des|da|di|do|dos|van|von)"
TITLE_TOKEN = rf"(?:{TITLE_CONNECTOR}|{TITLE_WORD})"
OVERFLOW_RE = re.compile(rf"(?P<tail>(?:\s+{TITLE_TOKEN})+)")


def overflow_title_surfaces(text: str) -> list[tuple[str, str]]:
    """Reconstruct classified title runs that continue after a nine-token baseline match."""
    text = " ".join(text.split())
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in base.TITLE_RE.finditer(text):
        baseline = base.clean_candidate(match.group(0))
        if len(baseline.split()) < 9:
            continue
        continuation = OVERFLOW_RE.match(text, match.end())
        if continuation is None:
            continue
        full = base.clean_candidate(baseline + continuation.group("tail"))
        kind = base.classify(full)
        if kind is None or not base.plausible(full):
            continue
        marker = (base.norm(full), kind)
        if marker in seen:
            continue
        seen.add(marker)
        out.append((full, kind))
    return out


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    dispositions, _ = reviewed.load_dispositions()
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, rendered: str, snippet: str) -> None:
        for candidate, kind in overflow_title_surfaces(rendered):
            normalized = base.norm(candidate)
            if base.resolve_name(identity_index, state, candidate) is not None:
                continue
            if dispositions.get((state, normalized)) is not None:
                continue
            key = (state, normalized, source, location)
            failures_by_key[key] = {
                "state": state,
                "candidate": candidate,
                "normalized": normalized,
                "kind": kind,
                "reason": "title surface continues beyond the baseline nine-token ceiling",
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
                rendered=markup.rendered_line(raw),
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
                rendered=markup.rendered_line(raw),
                snippet=raw,
            )

        # Reconstruct soft-wrapped title runs before checking the ceiling as a second line of
        # defense. Fenced code and canonical H1 handling remain owned by the shared block parser.
        for block in softwrap.prose_blocks(body):
            rendered_block = softwrap.render_prose_block(block)
            inspect(
                state=state,
                source=source,
                location=f"softwrap:{line_offset + block['relative_line']}",
                rendered=rendered_block,
                snippet=" / ".join(line.strip() for line in block["raw_lines"]),
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    long_name = (
        "National Commission for the Prevention of Torture and Other Cruel Inhuman or "
        "Degrading Treatment Agency"
    )
    found = overflow_title_surfaces(long_name + " reported findings")
    assert (long_name, "actor-or-institution") in found, found

    long_project = "National Program for the Protection of Human Rights and Civil Liberties Project"
    project_found = overflow_title_surfaces(long_project)
    assert (long_project, "project-or-deployment") in project_found, project_found

    short = overflow_title_surfaces("National Human Rights Commission reported findings")
    assert short == [], short

    # Punctuation terminates the run; a new sentence must never be glued to the identity.
    separated = overflow_title_surfaces(
        "National Commission for the Prevention of Torture and Other. Degrading Treatment Agency"
    )
    assert separated == [], separated

    print("State dossier long-title coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNREVIEWED_STATE_DOSSIER_LONG_TITLE_IDENTITIES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier long-title identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
