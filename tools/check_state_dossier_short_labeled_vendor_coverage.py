#!/usr/bin/env python3
"""Fail closed on short private-vendor names behind explicit vendor labels.

The broad private-organization audit intentionally requires longer proper-name tokens for precision.
Two-character brands are nevertheless high-confidence identity mentions when dossier prose explicitly
labels them as a supplier, vendor, contractor, private company, or technology provider. This
companion owns only that narrow intersection and requires exact current State-safe materialization.

Identity coverage is neutral: a label or mention does not prove supply, participation, control,
culpability, or governance semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_private_org_mentions as private
from audit_state_dossier_entities import frontmatter_identity_values, parse_frontmatter
from entity_identity_resolution import resolve_normalized


# Exactly two visible brand characters (HP, GE, 3M, M3), or a two-initial dotted spelling (H.P.).
# Three-or-more-character names remain owned by the established private-organization audit.
SHORT_VENDOR = r"(?:[A-Z0-9]{2}|(?:[A-Z]\.){2})"
SHORT_LABELED_PRIVATE_RE = re.compile(
    rf"\b(?i:(?:supplier|vendor|contractor|private\s+company|technology\s+provider)\s+)"
    rf"(?P<name>{SHORT_VENDOR})(?=\s|[.,;:!?\)\]\}}]|$)"
)


def short_labeled_vendor_names(prose: str) -> list[str]:
    names: list[str] = []
    for match in SHORT_LABELED_PRIVATE_RE.finditer(prose):
        candidate = private.clean(match.group("name"))
        # A bare two-digit token is not a private identity even after a label; require a letter.
        if not candidate or not any("A" <= char <= "Z" for char in candidate):
            continue
        if candidate not in names:
            names.append(candidate)
    return names


def audit() -> list[dict]:
    dossiers = private.canonical_dossiers()
    states = {iso for _, iso, _ in dossiers}
    known = private.identity_index(states)
    failures: list[dict] = []

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in short_labeled_vendor_names(prose):
            matches = resolve_normalized(known, state=state, normalized=private.norm(name))
            if len(matches) == 1:
                continue
            failures.append(
                {
                    "state": state,
                    "name": name,
                    "normalized": private.norm(name),
                    "source": source,
                    "location": location,
                    "snippet": snippet[:420],
                    "resolved_ids": matches,
                    "reason": (
                        "short explicitly labeled private-vendor name lacks one exact current "
                        "State-safe non-State identity"
                    ),
                }
            )

    for path, state, body_offset in dossiers:
        text = path.read_text(encoding="utf-8")
        front, parsed_offset = parse_frontmatter(text)
        if parsed_offset != body_offset:
            raise ValueError(f"frontmatter offset drift while auditing {path}")
        source = str(path.relative_to(private.ROOT))
        line_offset = text[:body_offset].count("\n")

        for field, line_no, raw in frontmatter_identity_values(text, front):
            inspect(
                state=state,
                source=source,
                location=f"frontmatter:{field}:line:{line_no}",
                prose=private.visible_prose(raw),
                snippet=f"{field}: {raw}",
            )

        for rel_line, snippet, prose in private.rendered_prose_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return failures


def self_test() -> None:
    # Exact Codex bypass and common two-character brand spellings under explicit labels.
    assert short_labeled_vendor_names("vendor HP supplied software") == ["HP"]
    assert short_labeled_vendor_names("supplier GE provided software") == ["GE"]
    assert short_labeled_vendor_names("technology provider 3M licensed software") == ["3M"]
    assert short_labeled_vendor_names("private company M3 developed tools") == ["M3"]
    assert short_labeled_vendor_names("contractor H.P. supplied software") == ["H.P"]

    # The explicit label is the precision boundary; arbitrary short tokens stay outside this guard.
    assert short_labeled_vendor_names("HP supplied software") == []
    assert short_labeled_vendor_names("vendor hp supplied software") == []
    assert short_labeled_vendor_names("vendor 42 supplied software") == []
    assert short_labeled_vendor_names("vendor H supplied software") == []
    assert short_labeled_vendor_names("the US supplied software evidence") == []

    # Rendered Markdown labels remain visible before the short-name grammar runs.
    assert short_labeled_vendor_names(
        private.visible_prose("vendor **HP** supplied software")
    ) == ["HP"]
    assert short_labeled_vendor_names(
        private.visible_prose("vendor [HP](https://example.test) supplied software")
    ) == ["HP"]

    print("State dossier short labeled vendor coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    failures = audit()
    if failures:
        print("UNMATERIALIZED_SHORT_LABELED_VENDORS=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier short labeled vendor completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
