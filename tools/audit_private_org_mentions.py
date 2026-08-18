#!/usr/bin/env python3
"""Discover private-company/vendor/contractor names in canonical State dossiers.

This is deliberately high-signal and non-authoritative. It scans only sentences whose
language explicitly concerns a supplier, vendor, contractor, company, private actor,
product or technology. Output is review debt, never an attribution or governance edge.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "dossiers" / "states"
ENTITY_DIR = ROOT / "knowledge" / "entities"
FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
STATE_ID_RE = re.compile(r"^ECL-STATE-([A-Z]{3})$")
CONTEXT_RE = re.compile(
    r"\b(?:supplier|vendor|contractor|company|companies|private\s+(?:actor|actors|company|companies|contractor|contractors)|"
    r"product|technology|technologies|software|spyware|platform|forensic(?:s)?\s+tool|mobile-forensic)\b",
    re.I,
)
# Proper-name token/phrase. Context gating is what makes this useful; false positives
# remain review candidates and are never promoted automatically.
NAME_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.'’/-]{2,}|[A-Z]{2,})"
    r"(?:\s+(?:[A-Z][A-Za-z0-9&.'’/-]{1,}|[A-Z]{2,}|of|the|and|for|de|del|la)){0,5}\b"
)
STOP = {
    "State", "States", "Restricted Party", "Restricted Parties", "Covered Associate",
    "Covered Associates", "ECL", "Schedule", "Project", "Projects", "Restricted Project",
    "Restricted Projects", "Material Participation", "Independent Remediation Activity",
    "High Court", "Court of Appeal", "Federal Government", "State Delta", "State-level",
    "No", "Current", "Historical", "Ordinary", "Amnesty", "Human Rights Watch", "UN",
    "United Nations", "European Union", "EU", "Government", "Ministry", "Police",
}


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def frontmatter(text: str) -> tuple[dict[str, str], int]:
    match = FRONT_RE.match(text)
    if not match:
        return {}, 0
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip("\"'")
    return data, match.end()


def canonical_dossiers() -> list[tuple[Path, str, int]]:
    rows: list[tuple[Path, str, int]] = []
    for path in sorted(STATE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        front, offset = frontmatter(text)
        match = STATE_ID_RE.fullmatch(front.get("id", ""))
        if not match:
            continue
        iso = match.group(1)
        if front.get("iso3") != iso or path.stem != iso:
            continue
        rows.append((path, iso, offset))
    return rows


def identity_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for path in ENTITY_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "State":
            continue
        for value in [data.get("name"), *(data.get("aliases") or [])]:
            if isinstance(value, str) and norm(value):
                names[norm(value)] = data["id"]
    return names


def plausible(name: str) -> bool:
    if name in STOP or len(name) < 3:
        return False
    if name.startswith(("State ", "Current ", "Historical ", "Ordinary ")):
        return False
    if name.isupper() and len(name) <= 3:
        return False
    return True


def audit() -> dict:
    known = identity_names()
    occurrences: list[dict] = []
    for path, iso, offset in canonical_dossiers():
        text = path.read_text(encoding="utf-8")
        body = text[offset:]
        line_offset = text[:offset].count("\n")
        for rel_line, raw in enumerate(body.splitlines(), 1):
            if not CONTEXT_RE.search(raw):
                continue
            # Avoid URLs/backticked repo paths dominating proper-name extraction.
            line = re.sub(r"https?://\S+", "", raw)
            line = re.sub(r"`[^`]+`", "", line)
            for match in NAME_RE.finditer(line):
                name = match.group(0).strip(" .,;:()[]")
                if not plausible(name):
                    continue
                occurrences.append({
                    "state": iso,
                    "candidate": name,
                    "normalized": norm(name),
                    "resolved_id": known.get(norm(name)),
                    "dossier": str(path.relative_to(ROOT)),
                    "line": line_offset + rel_line,
                    "snippet": raw.strip()[:420],
                })

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        # State-scope unresolved candidates so same brand-like word is never silently
        # treated as one corporate identity across jurisdictions.
        key = ("resolved:" + row["resolved_id"], row["normalized"]) if row["resolved_id"] else (row["state"], row["normalized"])
        groups[key].append(row)

    candidates: list[dict] = []
    for _, rows in groups.items():
        display = Counter(row["candidate"] for row in rows).most_common(1)[0][0]
        resolved = next((row["resolved_id"] for row in rows if row["resolved_id"]), None)
        candidates.append({
            "candidate": display,
            "states": sorted({row["state"] for row in rows}),
            "resolution": "materialized" if resolved else "review-candidate",
            "resolved_id": resolved,
            "occurrence_count": len(rows),
            "occurrences": rows,
        })
    candidates.sort(key=lambda row: (row["resolution"] != "review-candidate", -row["occurrence_count"], row["candidate"].lower()))
    unresolved = [row for row in candidates if row["resolution"] == "review-candidate"]
    resolved = [row for row in candidates if row["resolution"] == "materialized"]
    return {
        "schema_version": 1,
        "semantics": {
            "purpose": "high-signal discovery of named private-organization/vendor candidates",
            "non_inference": [
                "private-organization context does not prove corporate identity",
                "identity does not prove supply, participation, control or culpability",
                "supplier remediation/counter-evidence is represented symmetrically",
                "unresolved generic contractor classes must remain unresolved rather than receive invented company names"
            ]
        },
        "counts": {
            "canonical_state_dossiers": len(canonical_dossiers()),
            "candidate_groups": len(candidates),
            "resolved_groups": len(resolved),
            "unresolved_review_candidates": len(unresolved),
            "occurrences": len(occurrences),
        },
        "candidates": candidates,
    }


def write_markdown(report: dict, path: Path) -> None:
    counts = report["counts"]
    lines = [
        "# Private organization/vendor mention audit", "",
        "> Discovery only. A candidate is not an identity assertion, supplier relation, attribution, or governance decision.", "",
        f"- State dossiers: **{counts['canonical_state_dossiers']}**",
        f"- Candidate groups: **{counts['candidate_groups']}**",
        f"- Already resolved: **{counts['resolved_groups']}**",
        f"- Unresolved review candidates: **{counts['unresolved_review_candidates']}**", "",
        "## Unresolved candidates", "",
        "| State(s) | Candidate | Occurrences |", "|---|---|---:|",
    ]
    for row in report["candidates"]:
        if row["resolution"] != "review-candidate":
            continue
        name = row["candidate"].replace("|", "\\|")
        lines.append(f"| {','.join(row['states'])} | {name} | {row['occurrence_count']} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> None:
    assert CONTEXT_RE.search("Cellebrite halted product use")
    assert CONTEXT_RE.search("private contractor support")
    assert norm("Cellebrite") == "cellebrite"
    print("private organization audit self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = audit()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.markdown)
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
