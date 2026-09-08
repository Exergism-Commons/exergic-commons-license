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
import commonmark_fences as fences


# This companion deliberately owns comma/sentence boundaries while reusing the base Unicode
# start/mark classes. Preserve the historical rule that a normal title word cannot absorb a
# period; only an explicit dotted acronym form may contain one.
TITLE_WORD = (
    rf"(?:{base.UNICODE_TITLE_START}(?:[^\W_]|{base.UNICODE_TITLE_MARK}|[&'’/-])*"
    r"|(?:[A-Z]\.){2,})"
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
TERMINAL_CLASS_TERMS = base.ORG_TERMS | base.PROJECT_TERMS


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
        # A complete reconstructed identity must end on its class-bearing token. This prevents
        # a hard sentence boundary from turning the pre-boundary fragment into review debt merely
        # because an earlier token happened to contain e.g. ``Commission``.
        terminal = candidate.rsplit(maxsplit=1)[-1].strip(".,")
        if terminal not in TERMINAL_CLASS_TERMS:
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
        hidden_lines = fences.fenced_line_numbers(body)
        for rel_line, raw in enumerate(body.splitlines(), 1):
            if rel_line in hidden_lines or not raw.strip():
                continue
            if raw.startswith("# "):
                continue
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                rendered=markup.rendered_line(raw),
                snippet=raw,
            )

        for block in softwrap.prose_blocks(body, hidden_lines=hidden_lines):
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
    fences.self_test()
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

    unicode_comma = (
        "National Commission for Human Rights, Public Security Police and Civil Žandarmerija Agency"
    )
    unicode_comma_found = comma_long_title_surfaces(unicode_comma)
    assert (unicode_comma, "actor-or-institution") in unicode_comma_found, unicode_comma_found

    decomposed_comma = (
        "National Commission for Human Rights, Public Security Police and Civil E\u0301quipe Agency"
    )
    decomposed_comma_found = comma_long_title_surfaces(decomposed_comma)
    assert (decomposed_comma, "actor-or-institution") in decomposed_comma_found, decomposed_comma_found

    # Ordinary short comma-bearing names do not enter this long-title guard.
    assert comma_long_title_surfaces("Research, Development Agency") == []

    # Sentence-ending punctuation remains a hard boundary and cannot glue title fragments or
    # turn the class word occurring earlier in the phrase into a truncated complete identity.
    for punctuation in (".", ";", ":", "?", "!"):
        separated = comma_long_title_surfaces(
            "National Commission for the Prevention of Torture and Other Cruel, "
            f"Inhuman{punctuation} Degrading Treatment Agency"
        )
        assert separated == [], (punctuation, separated)

    # Concrete composition regression: a NBSP-prefixed fence opener is visible CommonMark prose.
    # The following table row is intentionally absent from prose_blocks(), so the same-line scan
    # must not disappear behind a Python-\s fence state. It contains the complete long comma title.
    table_title = (
        "National Commission for the Prevention of Torture and Other Cruel, "
        "Inhuman or Degrading Treatment Agency"
    )
    pseudo_fence_table = f"\u00a0```text\n| {table_title} | evidence |\n"
    hidden = fences.fenced_line_numbers(pseudo_fence_table)
    assert hidden == set(), hidden
    table_line = pseudo_fence_table.splitlines()[1]
    assert any(value == table_title for value, _ in comma_long_title_surfaces(table_line)), table_line

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
