#!/usr/bin/env python3
"""Fail closed when the broad State title grammar reaches its historical token ceiling.

The baseline ``TITLE_RE`` historically admitted one leading title word plus at most eight
continuations. This companion detects exactly that failure mode: a full nine-token baseline
match followed immediately by more title-shaped identity text. The complete maximal surface
must either resolve to a current State-safe identity or carry an exact State/source/blob-pinned
review disposition.

Identity coverage is neutral and creates no attribution, participation, control, operation,
supply, culpability, membership, hierarchy, or governance semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re

import audit_state_dossier_entities as base
import check_state_dossier_rendered_markup_coverage as markup
import check_state_dossier_softwrap_coverage as softwrap
import commonmark_fences as fences


REVIEW_PATH = base.ROOT / "knowledge/generated/state-dossier-long-title-dispositions-v1.json"
# Reuse the exact shared sentence-safe title token contract. Ordinary words cannot contain a
# period; only explicit dotted acronyms and the closed abbreviation set can. This matters in the
# overflow tail too: otherwise a legitimate ``Inc.``/``St.`` after token nine truncates the full
# identity before the long-title guard can review it.
TITLE_WORD = base.TITLE_WORD_PATTERN
# Lowercase connectors are token-bounded so ``de`` cannot consume the prefix of ``described``.
# ``or`` is required for complete institutional names such as ``... Cruel Inhuman or Degrading ...``.
TITLE_CONNECTOR = r"(?:(?:of|the|and|or|for|against|on|in|to|de|del|la|le|des|da|di|do|dos|van|von)\b)"
TITLE_TOKEN = rf"(?:{TITLE_CONNECTOR}|{TITLE_WORD})"
OVERFLOW_RE = re.compile(rf"(?P<tail>(?:\s+{TITLE_TOKEN})+)")
DISTINCT_COORDINATION_RE = re.compile(r"\band\s+the\s+", re.I)
# Period is deliberately absent: the shared TITLE_WORD contract can consume it only as part of an
# explicit dotted token. Such bytes are linguistically ambiguous with a sentence ending, so this
# guard audits the complete reading while ``_post_dotted_views`` audits the post-period reading.
TRAILING_TITLE_PUNCTUATION = frozenset("&'’/-")


def strict_json(path):
    def object_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key {key!r} in {path.relative_to(base.ROOT)}")
            out[key] = value
        return out

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)


def git_blob_sha(path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_reviews() -> dict[tuple[str, str, str], dict]:
    data = strict_json(REVIEW_PATH)
    assert data.get("version") == 1, data.get("version")
    assert set(data.get("allowedStatuses") or []) == {"deferred", "rejected"}
    assert data.get("sourceAudit") == "tools/check_state_dossier_long_title_coverage.py"
    reviews: dict[tuple[str, str, str], dict] = {}
    for row in data.get("dispositions") or []:
        state = row.get("state")
        candidate = row.get("candidate")
        normalized = row.get("normalized")
        status = row.get("status")
        reason = row.get("reason")
        source = row.get("source")
        source_blob = row.get("source_blob")
        assert isinstance(state, str) and re.fullmatch(r"[A-Z]{3}", state), row
        assert isinstance(candidate, str) and candidate.strip(), row
        assert isinstance(normalized, str) and normalized == base.norm(candidate), row
        assert status in {"deferred", "rejected"}, row
        assert isinstance(reason, str) and reason.strip(), row
        assert isinstance(source, str) and source == f"dossiers/states/{state}.md", row
        source_path = base.ROOT / source
        assert source_path.is_file(), row
        assert isinstance(source_blob, str) and re.fullmatch(r"[0-9a-f]{40}", source_blob), row
        assert git_blob_sha(source_path) == source_blob, (
            f"stale long-title review source pin for {state} {candidate!r}: "
            f"expected {source_blob}, current {git_blob_sha(source_path)}"
        )
        key = (state, normalized, source)
        assert key not in reviews, f"duplicate long-title disposition key: {key}"
        reviews[key] = row
    return reviews


def distinct_concept_coordination(value: str) -> bool:
    """Do not merge ``<classified identity> and the <unclassified concept>`` into one identity."""
    for match in DISTINCT_COORDINATION_RE.finditer(value):
        left = base.clean_candidate(value[:match.start()])
        right = base.clean_candidate(value[match.end():])
        if left and right and base.classify(left) is not None and base.classify(right) is None:
            return True
    return False


def _overflow_title_surfaces_once(text: str) -> list[tuple[str, str]]:
    """Reconstruct overflow titles for one interpretation of the input text."""
    out: list[tuple[str, str]] = []
    for match in base.TITLE_RE.finditer(text):
        raw_baseline = match.group(0)
        baseline = base.clean_candidate(raw_baseline)
        if len(baseline.split()) < 9:
            continue
        # The baseline may end in punctuation that is genuinely structural for this grammar.
        # Explicit dotted acronyms/abbreviations are not in this set: they are intentionally
        # ambiguous and both the complete and post-period readings are audited fail-closed.
        if raw_baseline and raw_baseline[-1] in TRAILING_TITLE_PUNCTUATION:
            continue
        continuation = OVERFLOW_RE.match(text, match.end())
        if continuation is None:
            continue
        # Clean only after the complete surface is assembled. If the ninth baseline token is
        # `Inc.`/`U.S.`, cleaning the baseline first would treat its internal period as terminal
        # punctuation and silently reconstruct a different identity (`Inc Research ...`).
        full = base.clean_candidate(raw_baseline + continuation.group("tail"))
        if distinct_concept_coordination(full):
            continue
        kind = base.classify(full)
        if kind is None or not base.plausible(full):
            continue
        out.append((full, kind))
    return out


def _post_dotted_views(text: str) -> list[str]:
    """Return complete remaining text from every ambiguous dotted-token boundary in a title match."""
    views: list[str] = []
    for match in base.TITLE_RE.finditer(text):
        matched = match.group(0)
        for boundary in base.AMBIGUOUS_DOTTED_BOUNDARY_RE.finditer(matched):
            views.append(matched[boundary.end():] + text[match.end():])
    return views


def overflow_title_surfaces(text: str) -> list[tuple[str, str]]:
    """Reconstruct long titles for the complete and every ambiguous post-period reading."""
    normalized_text = " ".join(text.split())
    pending = [normalized_text]
    seen_views: set[str] = set()
    seen_surfaces: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []

    while pending:
        view = pending.pop()
        if not view or view in seen_views:
            continue
        seen_views.add(view)
        for candidate, kind in _overflow_title_surfaces_once(view):
            marker = (base.norm(candidate), kind)
            if marker in seen_surfaces:
                continue
            seen_surfaces.add(marker)
            out.append((candidate, kind))
        for suffix_view in _post_dotted_views(view):
            if suffix_view and suffix_view not in seen_views:
                pending.append(suffix_view)
    return out


def audit() -> list[dict]:
    dossiers = base.canonical_state_dossiers()
    states = {
        front["iso3"]
        for _, front, _ in dossiers
        if isinstance(front.get("iso3"), str)
    }
    identity_index, _, _ = base.load_identity_index(states)
    reviews = load_reviews()
    consumed: set[tuple[str, str, str]] = set()
    failures_by_key: dict[tuple[str, str, str, str], dict] = {}

    def inspect(*, state: str, source: str, location: str, rendered: str, snippet: str) -> None:
        for candidate, kind in overflow_title_surfaces(rendered):
            normalized = base.norm(candidate)
            if base.resolve_name(identity_index, state, candidate) is not None:
                continue
            review_key = (state, normalized, source)
            if review_key in reviews:
                consumed.add(review_key)
                continue
            key = (state, normalized, source, location)
            failures_by_key[key] = {
                "state": state,
                "candidate": candidate,
                "normalized": normalized,
                "kind": kind,
                "reason": "title surface continues beyond the baseline nine-token ceiling without exact materialization or pinned review",
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

        # Reconstruct soft-wrapped title runs before checking the ceiling as a second line of
        # defense. Fenced code and source-line semantics come from the exact shared parser result.
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

    for key, review in reviews.items():
        if key in consumed:
            continue
        state, normalized, source = key
        failures_by_key[(state, normalized, source, "stale-review")] = {
            "state": state,
            "candidate": review["candidate"],
            "normalized": normalized,
            "kind": "review-integrity",
            "reason": "stale long-title disposition no longer corresponds to a detected overflow surface",
            "source": source,
            "location": "review-manifest",
            "snippet": review["reason"][:420],
        }

    return [failures_by_key[key] for key in sorted(failures_by_key)]


def self_test() -> None:
    fences.self_test()
    long_name = (
        "National Commission for the Prevention of Torture and Other Cruel Inhuman or "
        "Degrading Treatment Agency"
    )
    found = overflow_title_surfaces(long_name + " reported findings")
    assert (long_name, "actor-or-institution") in found, found

    long_project = "National Program for the Protection of Human Rights and Civil Liberties Project"
    project_found = overflow_title_surfaces(long_project)
    assert (long_project, "project-or-deployment") in project_found, project_found

    unicode_tail = "National Commission for Human Rights and Public Security Police Žandarmerija"
    unicode_tail_found = overflow_title_surfaces(unicode_tail)
    assert (unicode_tail, "actor-or-institution") in unicode_tail_found, unicode_tail_found

    decomposed_tail = "National Commission for Human Rights and Public Security Police E\u0301quipe"
    decomposed_tail_found = overflow_title_surfaces(decomposed_tail)
    assert (decomposed_tail, "actor-or-institution") in decomposed_tail_found, decomposed_tail_found

    short = overflow_title_surfaces("National Human Rights Commission reported findings")
    assert short == [], short

    # Lowercase connector spellings are whole tokens, never prefixes of ordinary prose.
    described = overflow_title_surfaces(
        "Council of Europe's Department for the Execution of Judgments described the problem"
    )
    assert described == [], described

    # A classified institution coordinated with an unclassified legal/policy concept is not one identity.
    coordinated = overflow_title_surfaces(
        "Justice Ministry and the National Charter for Peace and Reconciliation"
    )
    assert coordinated == [], coordinated

    # An ordinary period remains a hard boundary because ordinary TITLE_WORD tokens cannot absorb it.
    baseline_period = overflow_title_surfaces(
        "National Commission for the Prevention of Torture and Other. Degrading Treatment Agency"
    )
    assert baseline_period == [], baseline_period

    # An ordinary period in the continuation likewise cannot glue title fragments.
    tail_period_text = (
        "National Commission for the Prevention of Torture and Other Cruel. "
        "Inhuman Degrading Treatment Agency"
    )
    tail_period = overflow_title_surfaces(tail_period_text)
    assert tail_period, tail_period
    assert all("Inhuman" not in value and "." not in value for value, _ in tail_period), tail_period

    # A dotted token inside the nine-token baseline is byte-for-byte ambiguous with a sentence
    # ending. Reconstruct and audit both the complete long reading and the complete long suffix;
    # auditing only the suffix's first nine tokens would recreate the historical ceiling bypass.
    dotted_long_suffix = (
        "National Commission for the Prevention of Torture and Other Cruel Agency"
    )
    dotted_long_full = "Acme Inc. " + dotted_long_suffix
    dotted_long = overflow_title_surfaces(dotted_long_full)
    assert (dotted_long_full, "actor-or-institution") in dotted_long, dotted_long
    assert (dotted_long_suffix, "actor-or-institution") in dotted_long, dotted_long

    # P1 regression: the explicit dotted abbreviation may itself occur only after the historical
    # nine-token ceiling. A private copy of the title token grammar used to stop at ``Inc.`` and
    # emit only a classified prefix, allowing the complete identity to remain outside review.
    dotted_overflow = (
        "National Commission for the Prevention of Torture and Other Cruel Inc. Research Agency"
    )
    dotted_overflow_found = overflow_title_surfaces(dotted_overflow)
    assert (dotted_overflow, "actor-or-institution") in dotted_overflow_found, dotted_overflow_found

    # The same ambiguity exists when the dotted abbreviation is exactly the ninth baseline token;
    # a blanket trailing-period guard must not suppress the legitimate complete reading.
    dotted_ninth = "National Commission for the Prevention of Torture and Inc. Research Agency"
    dotted_ninth_found = overflow_title_surfaces(dotted_ninth)
    assert (dotted_ninth, "actor-or-institution") in dotted_ninth_found, dotted_ninth_found

    # Table rows are deliberately outside prose_blocks(). A NBSP-prefixed backtick line is not a
    # CommonMark fence opener, so it cannot hide the only same-line scan of the following long title.
    pseudo_fence_table = f"\u00a0```text\n| {long_name} | evidence |\n"
    hidden = fences.fenced_line_numbers(pseudo_fence_table)
    assert hidden == set(), hidden
    table_line = pseudo_fence_table.splitlines()[1]
    assert (long_name, "actor-or-institution") in overflow_title_surfaces(table_line), table_line

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
