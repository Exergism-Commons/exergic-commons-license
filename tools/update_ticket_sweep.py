#!/usr/bin/env python3
"""Generate deduplicated ECL living-review signals.

Initial scope: deterministic review-due signals from knowledge/entities/*.json.

The tool can run in dry-run mode (default) or create GitHub Issues when
--github is supplied. It never changes ECL outcomes, dossiers or Schedules.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


PRIORITY_BY_CLASS = {
    "hot": "P1",
    "active": "P2",
    "stable": "P3",
    "manual": "P3",
}


def load_entities(root: Path) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object")
        data["_path"] = str(path)
        entities.append(data)
    return entities


def parse_date(value: Any, label: str) -> dt.date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO date string")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} is not a valid ISO date: {value}") from exc


def fingerprint(subject: str, due: dt.date) -> str:
    raw = f"{subject}|review-due|{due.isoformat()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def build_signal(entity: dict[str, Any], today: dt.date) -> dict[str, Any] | None:
    review = entity.get("review")
    if not isinstance(review, dict):
        raise ValueError(f"{entity.get('_path')}: missing review object")

    due = parse_date(review.get("nextReview"), f"{entity.get('id')}.review.nextReview")
    if due > today:
        return None

    subject = entity.get("id")
    if not isinstance(subject, str) or not subject:
        raise ValueError(f"{entity.get('_path')}: missing id")

    review_class = review.get("reviewClass", "manual")
    priority = PRIORITY_BY_CLASS.get(str(review_class), "P3")
    fp = fingerprint(subject, due)
    signal_id = f"ECL-UPD-REVIEW-DUE-{subject}-{due.isoformat()}"

    return {
        "id": signal_id,
        "fingerprint": fp,
        "subject": subject,
        "entityName": entity.get("name"),
        "currentGovernance": entity.get("currentGovernance"),
        "dossier": entity.get("dossier"),
        "type": "review-due",
        "priority": priority,
        "dueDate": due.isoformat(),
        "lastSubstantiveReview": review.get("lastSubstantiveReview"),
        "reason": review.get("reason", "Scheduled substantive review is due."),
        "sourceEntityPath": entity.get("_path"),
    }


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc


def issue_exists(repo: str, token: str, fp: str) -> bool:
    marker = f"ecl-update-fingerprint: {fp}"
    query = f'repo:{repo} "{marker}" in:body'
    url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query)
    result = github_request("GET", url, token)
    return int(result.get("total_count", 0)) > 0


def issue_body(signal: dict[str, Any]) -> str:
    return f"""<!-- ecl-update-fingerprint: {signal['fingerprint']} -->
<!-- ecl-update-signal-id: {signal['id']} -->

## Automatic ECL review-due signal

**Subject:** `{signal['subject']}` — {signal.get('entityName') or ''}  
**Current provisional governance:** `{signal.get('currentGovernance')}`  
**Priority:** `{signal['priority']}`  
**Last substantive review:** `{signal.get('lastSubstantiveReview')}`  
**Review due:** `{signal['dueDate']}`

**Why this fired:** {signal.get('reason')}

This issue is an **automatic review signal only**. It is not evidence of misconduct, remediation, restriction or exoneration, and it has no licensing effect.

### Required triage

1. Check new material evidence and counter-evidence since the last evidence cutoff.
2. Confirm the exact actor/project/deployment object still exists at the recorded scope.
3. Materialize an `UpdateCase` only if the review finds a non-duplicate material event or a substantive current-status revalidation is required.
4. Apply `spec/EVIDENCE-VALUATION.md` to new evidence.
5. Re-run only the affected formal Exergism variables first; escalate to full analysis if required by `spec/LIVING-UPDATE-SYSTEM.md`.
6. Re-test exact ECL criterion fit separately from the formal score.
7. If nothing material changed, close this signal with the new review/evidence cutoff and set the next review date through a normal PR.

**Dossier:** `{signal.get('dossier')}`  
**Entity record:** `{signal.get('sourceEntityPath')}`
"""


def create_issue(repo: str, token: str, signal: dict[str, Any]) -> str:
    if issue_exists(repo, token, signal["fingerprint"]):
        return "duplicate"
    title = (
        f"[ECL UPDATE] {signal['subject']} — review due — "
        f"{signal['dueDate']}"
    )
    url = f"https://api.github.com/repos/{repo}/issues"
    result = github_request(
        "POST",
        url,
        token,
        {"title": title, "body": issue_body(signal)},
    )
    return str(result.get("html_url", "created"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("entity_root", nargs="?", default="knowledge/entities", type=Path)
    parser.add_argument("--today", help="override current UTC date (YYYY-MM-DD)")
    parser.add_argument("--lookahead-days", type=int, default=0)
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args(argv)

    if args.lookahead_days < 0:
        parser.error("--lookahead-days must be >= 0")

    base_today = (
        parse_date(args.today, "--today")
        if args.today
        else dt.datetime.now(dt.timezone.utc).date()
    )
    horizon = base_today + dt.timedelta(days=args.lookahead_days)

    try:
        signals = [
            signal
            for entity in load_entities(args.entity_root)
            if (signal := build_signal(entity, horizon)) is not None
        ]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.github:
        json.dump(signals, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("error: --github requires GITHUB_TOKEN and GITHUB_REPOSITORY", file=sys.stderr)
        return 2

    failures = 0
    for signal in signals:
        try:
            result = create_issue(repo, token, signal)
            print(f"{signal['id']}: {result}")
        except RuntimeError as exc:
            failures += 1
            print(f"{signal['id']}: error: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
