#!/usr/bin/env python3
"""Fail closed on long State-dossier identity titles containing internal commas.

The baseline title grammar and the historical-overflow companion both treat a comma as a
boundary. That can fragment a complete long institutional name such as ``National Commission
for the Prevention of Torture and Other Cruel, Inhuman or Degrading Treatment Agency``.

This independent guard reconstructs long title-shaped runs with a narrowly bounded comma
separator between title tokens. Sentence-ending punctuation (period, semicolon, colon,
question mark and exclamation mark) remains a hard boundary. Complete surfaces must resolve
to a current State-safe identity; this guard does not infer identity equivalence or governance.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_rendered_markup_coverage as markup
import check_state_dossier_softwrap_coverage as softwrap


FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
TITLE_WORD = (
    r"(?:"
    r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9&'’/-]*"
    r"|(?:[A-Z]\.){2,}"
    r"|[A-ZÀ-ÖØ-Þ]{2,}"
    r")"
)
TITLE_CONNECTOR = (
    r"(?:(?:of|the|and|or|for|against|on|in|to|de|del|la|le|des|da|di|do|dos|van|von)\b)"
)
TITLE_TOKEN = rf"(?:{TITLE_CONNECTOR}|{TITLE_WORD})"
# A comma is accepted only as punctuation *between* two title tokens. Other sentence-level
# punctuation is not part of the separator grammar and therefore terminates the run.
TITLE_SEPARATOR = r"(?:\s+|,\s+)"
LONG_COMMA_TITLE_RE = re.compile(
    rf"\b(?P<title>{TITLE_WORD}(?:{TITLE_SEPARATOR}{TITLE_TOKEN}){{9,}})"
)


def comma_long_title_surfaces(text: str) -> list[tuple[str, str]]:
    text = " ".join(text.split())
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in LONG_COMMA_TITLE_RE.finditer(text):
        raw = match.group("title")
        if "," not in raw:
            continue
        candidate = base.clean_candidate(raw)
        # Ten or more lexical/title tokens are required independently of punctuation.
        if len(re.findall(TITLE_TOKEN, candidate)) < 10:
            continue
        kind = base.classify(candidate)
        if kind is None or not base.plausible(candidate):
            continue
        marker = (base.norm(candidate), kind)
        if marker in seen:
            continue
        seen.add(marker)
        out.append((candidate, kind))
    return out


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, rendered: str, snippet: str) -> None:
        for candidate, kind in comma_long_title_surfaces(rendered):
            if base.resolve_name(identity_index, state, candidate) is not None:
                continue
            normalized = base.norm(candidate)
            key = (state, normalized, source, location)
            failures_by_key[key] = {
                "state": state,
                "candidate": candidate,
                "normalized": normalized,
                "kind": kind,
                "reason": "long comma-bearing title lacks exact State-safe materialization",
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

        for block in softwrap.prose_blocks(body):
            lines = [line for line in block["lines"] if line]
            if not lines:
                continue
            rendered_block, _ = softwrap.render_prose_block(lines)
            inspect(
                state=state,
                source=source,
                location=f"softwrap:{line_offset + block['relative_line']}",
                rendered=rendered_block,
                snippet=" / ".join(line.strip() for line in block["raw_lines"]),
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    reported = (
        "National Commission for the Prevention of Torture and Other Cruel, "
        "Inhuman or Degrading Treatment Agency"
    )
    found = comma_long_title_surfaces(reported + " reported findings")
    assert (reported, "actor-or-institution") in found, found

    # The comma may occur before the historical ninth-token boundary too; this guard does not
    # depend on TITLE_RE first reaching its old ceiling.
    early_comma = (
        "National Commission for Torture, Cruel Inhuman or Degrading Treatment Oversight Agency"
    )
    early_found = comma_long_title_surfaces(early_comma)
    assert (early_comma, "actor-or-institution") in early_found, early_found

    # Ordinary short comma-bearing names do not enter this long-title guard.
    assert comma_long_title_surfaces("Research, Development Agency") == []

    # Sentence-ending punctuation remains a hard boundary and cannot glue title fragments.
    for punctuation in (".", ";", ":", "?", "!"):
        separated = comma_long_title_surfaces(
            "National Commission for the Prevention of Torture and Other Cruel, "
            f"Inhuman{punctuation} Degrading Treatment Agency"
        )
        assert separated == [], (punctuation, separated)

    print("State dossier long comma-title coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_LONG_COMMA_TITLES=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier long comma-title identity completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
