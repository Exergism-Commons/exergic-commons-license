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


FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
REVIEW_PATH = base.ROOT / "knowledge/generated/state-dossier-long-title-dispositions-v1.json"
TITLE_WORD = r"(?:[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9&.'’/-]*|[A-ZÀ-ÖØ-Þ]{2,})"
# Lowercase connectors are token-bounded so ``de`` cannot consume the prefix of ``described``.
# ``or`` is required for complete institutional names such as ``... Cruel Inhuman or Degrading ...``.
TITLE_CONNECTOR = r"(?:(?:of|the|and|or|for|against|on|in|to|de|del|la|le|des|da|di|do|dos|van|von)\b)"
TITLE_TOKEN = rf"(?:{TITLE_CONNECTOR}|{TITLE_WORD})"
OVERFLOW_RE = re.compile(rf"(?P<tail>(?:\s+{TITLE_TOKEN})+)")
DISTINCT_COORDINATION_RE = re.compile(r"\band\s+the\s+", re.I)


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
        if distinct_concept_coordination(full):
            continue
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
