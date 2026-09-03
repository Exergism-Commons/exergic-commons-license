#!/usr/bin/env python3
"""Fail closed on modal active-progressive custody mentions in State dossiers.

This companion closes the active ``modal + be + -ing`` family (for example
``authorities will be detaining Jane Doe``) without weakening passive parsing. It reuses the
closed modal/adverb/action vocabularies and the Unicode/honorific/uncased name parser already
reviewed elsewhere. Body prose is routed through the full-run fence-safe Person segmenter so the
modal grammar composes with four-or-more-backtick fenced code. Identity coverage is neutral and
creates no attribution, participation, culpability, control, operation, membership, or governance
semantics.
"""
from __future__ import annotations

import argparse
import json
import re

import audit_schedule_reference_coverage as schedule
import audit_state_dossier_entities as base
import check_schedule_exact_identity_completeness as exact
import check_state_dossier_fence_mononym_person_coverage as fence_guard
import check_state_dossier_named_person_coverage as person
import check_state_dossier_plural_present_passive_person_coverage as passive
import check_state_dossier_unicode_held_person_coverage as unicode_people


MODAL_ACTIVE_PROGRESSIVE_AUX = (
    rf"(?i:{passive.PASSIVE_MODAL})\s+{passive.ADVERB_SEQ}"
    rf"(?i:be)\s+{passive.ADVERB_SEQ}"
)
MODAL_ACTIVE_PROGRESSIVE_PREFIX_RE = re.compile(
    rf"\b{MODAL_ACTIVE_PROGRESSIVE_AUX}(?i:{unicode_people.ACTIVE_PROGRESSIVE_VERB})\s+"
    rf"(?:(?i:(?:{person.ROLE}))(?:/(?i:(?:{person.ROLE})))?\s+)?"
)


def names_from_modal_active_progressive(prose: str) -> list[str]:
    names: list[str] = []
    for match in MODAL_ACTIVE_PROGRESSIVE_PREFIX_RE.finditer(prose):
        tail = prose[match.end():]
        for candidate in (
            unicode_people.leading_names(tail)
            + unicode_people.leading_uncased_names(tail)
        ):
            if candidate not in names:
                names.append(candidate)
    return names


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    entities, _, identity_index = schedule.load_entities()
    failures_by_key: dict[tuple[str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, prose: str, snippet: str) -> None:
        for name in names_from_modal_active_progressive(prose):
            if exact.materialized_person_ids_for_mention(name, entities, identity_index, state):
                continue
            if exact.materialized_non_person_ids_for_mention(name, entities, identity_index, state):
                continue
            key = (state, schedule.norm(name))
            row = failures_by_key.setdefault(
                key,
                {
                    "state": state,
                    "name": name,
                    "normalized": schedule.norm(name),
                    "reason": "modal active-progressive custody prose names an unmaterialized person",
                    "occurrences": [],
                },
            )
            row["occurrences"].append(
                {"source": source, "location": location, "snippet": snippet[:420]}
            )

    for path, front, body_offset in dossiers:
        state = front.get("iso3")
        if not isinstance(state, str):
            continue
        source = str(path.relative_to(base.ROOT))

        for field in person.FRONTMATTER_PERSON_KEYS:
            value = front.get(field)
            if isinstance(value, str) and value.strip():
                inspect(
                    state=state,
                    source=source,
                    location=f"frontmatter:{field}",
                    prose=person.frontmatter_visible_prose(value),
                    snippet=value,
                )

        text = path.read_text(encoding="utf-8")
        line_offset = text[:body_offset].count("\n")
        # Do not reuse the historical marker-only segmenter here. The fence companion tracks the
        # complete opening run, so a literal ``` inside a ```` fence cannot hide later modal prose.
        for rel_line, snippet, prose in fence_guard.fence_safe_person_segments(text[body_offset:]):
            inspect(
                state=state,
                source=source,
                location=f"line:{line_offset + rel_line}",
                prose=prose,
                snippet=snippet,
            )

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    assert names_from_modal_active_progressive("authorities will be detaining Jane Doe") == ["Jane Doe"]
    assert names_from_modal_active_progressive("authorities may be prosecuting Jane Doe") == ["Jane Doe"]
    assert names_from_modal_active_progressive(
        "authorities should currently be arbitrarily detaining Jane Doe and John Roe"
    ) == ["Jane Doe", "John Roe"]
    assert names_from_modal_active_progressive(
        "authorities might not be unlawfully detaining Dr. Łukasz Żak"
    ) == ["Łukasz Żak"]
    assert names_from_modal_active_progressive("authorities will be detaining أحمد منصور") == ["أحمد منصور"]
    assert names_from_modal_active_progressive("authorities may be detaining 王小明") == ["王小明"]

    # Composition regression: the shorter run is literal fenced content, not the closer. The
    # later modal-progressive prose must remain visible after the true four-backtick closer.
    fenced = (
        "````text\n"
        "authorities will be detaining Hidden Person\n"
        "```\n"
        "still fenced\n"
        "````\n"
        "authorities will be detaining Jane Doe\n"
    )
    segments = fence_guard.fence_safe_person_segments(fenced)
    modal_names = [
        name
        for _, _, prose in segments
        for name in names_from_modal_active_progressive(prose)
    ]
    assert modal_names == ["Jane Doe"], (segments, modal_names)

    # Keep the action family closed; modal progressive prose is not generic person discovery.
    assert names_from_modal_active_progressive("authorities will be interviewing Jane Doe") == []
    assert names_from_modal_active_progressive("authorities plan to be detaining Jane Doe") == []

    print("State dossier modal active-progressive Person coverage self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    failures = audit()
    if failures:
        print("UNMATERIALIZED_STATE_DOSSIER_MODAL_ACTIVE_PROGRESSIVE_PEOPLE=" + json.dumps(
            failures, ensure_ascii=False, sort_keys=True
        ))
        return 2
    print("State dossier modal active-progressive Person completeness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
