#!/usr/bin/env python3
"""Migrate and synchronize State public governance-review issue surfaces.

The canonical mapping and mutable review metadata are read from
`dossiers/states/ISO.md` frontmatter. GitHub issues remain a public review and
provenance surface, never a second governance source of truth.

Default mode is a deterministic dry-run. `--apply` requires a GitHub token and
updates issues in place without closing them or changing any governance outcome.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MARKER = "<!-- ecl-state-review-surface:v1"
METADATA_START = "<!-- ecl-state-review-metadata:start -->"
METADATA_END = "<!-- ecl-state-review-metadata:end -->"
HISTORY_OPEN = "<details>\n<summary>Historical issue body before public-review migration</summary>\n\n"
HISTORY_CLOSE = "\n\n</details>"
STATE_DOSSIER_NAME = re.compile(r"^[A-Z]{3}\.md$")
REVIEW_LABELS = {
    "review:external-needed": ("0e8a16", "Independent public review is still required"),
    "review:adversarial": ("5319e7", "Adversarial/falsification review surface"),
    "governance:state": ("1d76db", "State governance review"),
}


@dataclass(frozen=True)
class Dossier:
    path: Path
    iso3: str
    entity: str
    issue: int
    outcome: str
    scope: str
    evidence_cutoff: str
    review_stage: str
    exergism_status: str
    exergism_assessment: str | None


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = _unquote(value)
    raise ValueError("unterminated YAML frontmatter")


def load_dossiers(root: Path) -> list[Dossier]:
    dossiers: list[Dossier] = []
    seen_issues: set[int] = set()
    paths = [
        path
        for path in sorted(root.glob("*.md"))
        if STATE_DOSSIER_NAME.fullmatch(path.name)
    ]
    for path in paths:
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        required = ("iso3", "entity", "issue", "provisional_outcome")
        if any(not meta.get(key) for key in required):
            raise ValueError(f"{path}: missing one of {required}")
        if meta["iso3"] != path.stem:
            raise ValueError(
                f"{path}: frontmatter iso3={meta['iso3']} does not match filename"
            )
        issue = int(meta["issue"])
        if issue in seen_issues:
            raise ValueError(f"duplicate issue mapping #{issue}")
        seen_issues.add(issue)
        dossiers.append(
            Dossier(
                path=path,
                iso3=meta["iso3"],
                entity=meta["entity"],
                issue=issue,
                outcome=meta["provisional_outcome"],
                scope=meta.get("provisional_scope", "not recorded"),
                evidence_cutoff=meta.get("evidence_cutoff", "not recorded"),
                review_stage=meta.get("review_stage", "not recorded"),
                exergism_status=meta.get("exergism_status", "not recorded"),
                exergism_assessment=meta.get("exergism_assessment") or None,
            )
        )
    return dossiers


def review_title(dossier: Dossier) -> str:
    return (
        f"[STATE REVIEW] {dossier.entity} — adversarial review of canonical ECL dossier"
    )


def render_metadata(dossier: Dossier, repo: str) -> str:
    dossier_url = (
        f"https://github.com/{repo}/blob/main/dossiers/states/{dossier.iso3}.md"
    )
    assessment = (
        f"https://github.com/{repo}/blob/main/exergism/assessments/{dossier.iso3}.json"
        if dossier.exergism_assessment
        else None
    )
    assessment_line = f"- Formal assessment: {assessment}\n" if assessment else ""
    return f"""{METADATA_START}
- Canonical dossier: {dossier_url}
- Provisional outcome (derived): `{dossier.outcome}`
- Provisional scope (derived): {dossier.scope}
- Evidence cutoff (derived): `{dossier.evidence_cutoff}`
- Review stage (derived): `{dossier.review_stage}`
- Formal Exergism status (derived): `{dossier.exergism_status}`
{assessment_line}- Source-of-truth rule: if this metadata ever differs from the canonical dossier, **the dossier controls**.
{METADATA_END}"""


def extract_historical_body(body: str) -> str:
    start = body.find(HISTORY_OPEN)
    end = body.rfind(HISTORY_CLOSE)
    if start < 0 or end < 0 or end < start:
        raise ValueError("migrated review surface is missing its preserved historical body")
    return body[start + len(HISTORY_OPEN) : end]


def render_review_body(dossier: Dossier, repo: str, historical_body: str) -> str:
    historical_body = historical_body.rstrip()
    return f"""{MARKER} iso3={dossier.iso3} issue={dossier.issue} -->

## Public adversarial review surface

This issue is the public review thread for the **canonical State dossier**. It is not the canonical evidence record and has no licensing effect by itself. The metadata block below is a generated convenience view and is synchronized from the dossier; it is not an independent outcome store.

{render_metadata(dossier, repo)}

The current conclusion is a proposition to test, **not a result reviewers are expected to endorse**. Evidence supporting narrowing, removal or `N` must be handled as seriously as evidence supporting restriction or expansion.

### Independent review checklist

- [ ] Exact actor / institutional identity and current scope independently checked
- [ ] Material evidence supporting the current conclusion checked against primary/authoritative sources
- [ ] Material counter-evidence actively sought and evaluated
- [ ] Exact operative ECL criterion fit checked separately from general human-rights concern
- [ ] Attribution, control/participation and narrower alternatives checked
- [ ] Exclusions, counter-institutions and remediation/removal triggers checked
- [ ] Formal Exergism assessment reviewed, or `insufficient_evidence` / `not_applicable` justified
- [ ] Material objections resolved or recorded as documented dissent
- [ ] Minimum independent-review gate in `spec/PUBLIC-REVIEW.md` met
- [ ] Resulting `GovernanceDecision` recorded before this review cycle is treated as complete

### How to review

A substantive reviewer should state a disposition (`support-current-conclusion`, `support-with-narrowing`, `challenge-current-conclusion`, `insufficient-evidence`, or `conflict-disclosed / evidence-only`), identify what they checked, provide evidence/counter-evidence, and disclose material conflicts.

Reviews are **not votes**. A well-supported unresolved material objection cannot be overridden merely by accumulating approvals or reactions.

Accepted evidence or conclusions must be normalized into the repository. Comments remain the public deliberation/provenance surface.

See `spec/PUBLIC-REVIEW.md` and `spec/GOVERNANCE.md`.

{HISTORY_OPEN}{historical_body}{HISTORY_CLOSE}
"""


def already_migrated(body: str) -> bool:
    return MARKER in body


def synchronize_review_body(dossier: Dossier, repo: str, current_body: str) -> str:
    """Return the desired issue body without discarding public-review edits.

    New surfaces are rendered in full. Legacy v1 migrated surfaces are upgraded once
    using their preserved historical body. Once metadata delimiters exist, future
    synchronizations replace only that generated block so reviewer-maintained text,
    checkboxes and other body edits outside the block survive dossier updates.
    """
    if not already_migrated(current_body):
        return render_review_body(dossier, repo, current_body)

    if METADATA_START not in current_body or METADATA_END not in current_body:
        historical = extract_historical_body(current_body)
        return render_review_body(dossier, repo, historical)

    start = current_body.find(METADATA_START)
    end = current_body.find(METADATA_END, start)
    if start < 0 or end < 0:
        raise ValueError("invalid generated metadata delimiters")
    end += len(METADATA_END)
    return current_body[:start] + render_metadata(dossier, repo) + current_body[end:]


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc


def ensure_labels(repo: str, token: str) -> None:
    existing = github_request(
        "GET", f"https://api.github.com/repos/{repo}/labels?per_page=100", token
    )
    names = {item.get("name") for item in existing}
    for name, (color, description) in REVIEW_LABELS.items():
        if name in names:
            continue
        github_request(
            "POST",
            f"https://api.github.com/repos/{repo}/labels",
            token,
            {"name": name, "color": color, "description": description},
        )


def fetch_issue(repo: str, issue: int, token: str) -> dict[str, Any]:
    result = github_request(
        "GET", f"https://api.github.com/repos/{repo}/issues/{issue}", token
    )
    if "pull_request" in result:
        raise RuntimeError(f"#{issue} unexpectedly resolves to a pull request")
    return result


def migrate_one(
    dossier: Dossier, repo: str, token: str, apply: bool
) -> dict[str, Any]:
    issue = fetch_issue(repo, dossier.issue, token)
    old_body = issue.get("body") or ""
    was_migrated = already_migrated(old_body)
    try:
        desired_body = synchronize_review_body(dossier, repo, old_body)
    except ValueError as exc:
        raise RuntimeError(f"#{dossier.issue}: {exc}") from exc

    current_labels = [
        item.get("name") for item in issue.get("labels", []) if item.get("name")
    ]
    desired_labels = sorted(set(current_labels) | set(REVIEW_LABELS))
    desired_title = review_title(dossier)
    changed = (
        issue.get("title") != desired_title
        or old_body != desired_body
        or sorted(current_labels) != desired_labels
    )

    if not changed:
        return {
            "issue": dossier.issue,
            "iso3": dossier.iso3,
            "status": "already-current",
        }

    payload = {
        "title": desired_title,
        "body": desired_body,
        "labels": desired_labels,
        # State intentionally omitted: synchronization must not close/reopen threads.
    }
    if apply:
        github_request(
            "PATCH",
            f"https://api.github.com/repos/{repo}/issues/{dossier.issue}",
            token,
            payload,
        )

    if was_migrated:
        status = "refreshed" if apply else "would-refresh"
    else:
        status = "migrated" if apply else "would-migrate"
    return {
        "issue": dossier.issue,
        "iso3": dossier.iso3,
        "status": status,
        "title": desired_title,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dossiers", type=Path, default=Path("dossiers/states")
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get(
            "GITHUB_REPOSITORY", "Papishushi/exergic-commons-license"
        ),
    )
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="mutate GitHub issues; default is dry-run",
    )
    parser.add_argument(
        "--issue", type=int, action="append", help="limit to mapped issue numbers"
    )
    parser.add_argument(
        "--iso3", action="append", help="limit to one or more ISO3 dossier IDs"
    )
    parser.add_argument(
        "--limit", type=int, help="limit number of dossiers after filtering"
    )
    args = parser.parse_args(argv)

    try:
        dossiers = load_dossiers(args.dossiers)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.issue:
        wanted = set(args.issue)
        dossiers = [d for d in dossiers if d.issue in wanted]
        missing = wanted - {d.issue for d in dossiers}
        if missing:
            print(
                f"error: no State dossier mapping for issues {sorted(missing)}",
                file=sys.stderr,
            )
            return 2
    if args.iso3:
        wanted_iso3 = {item.upper() for item in args.iso3}
        dossiers = [d for d in dossiers if d.iso3 in wanted_iso3]
        missing_iso3 = wanted_iso3 - {d.iso3 for d in dossiers}
        if missing_iso3:
            print(
                f"error: no State dossier mapping for ISO3 {sorted(missing_iso3)}",
                file=sys.stderr,
            )
            return 2
    if args.limit is not None:
        if args.limit < 0:
            parser.error("--limit must be >= 0")
        dossiers = dossiers[: args.limit]

    # Even dry-run fetches current issue bodies so the transformation is checked
    # against the actual public review surface.
    if not args.token:
        print(
            "error: GITHUB_TOKEN is required to read current issue bodies",
            file=sys.stderr,
        )
        return 2

    if args.apply:
        ensure_labels(args.repo, args.token)

    failures = 0
    results: list[dict[str, Any]] = []
    for dossier in dossiers:
        try:
            results.append(migrate_one(dossier, args.repo, args.token, args.apply))
        except RuntimeError as exc:
            failures += 1
            results.append(
                {
                    "issue": dossier.issue,
                    "iso3": dossier.iso3,
                    "status": "error",
                    "error": str(exc),
                }
            )

    json.dump(results, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
