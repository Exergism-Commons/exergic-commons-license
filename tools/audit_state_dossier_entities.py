#!/usr/bin/env python3
"""Audit named non-State entities/projects mentioned by canonical State dossiers.

This is a discovery tool, not an attribution engine. It emits review candidates and
never creates ABox individuals, Claims, assessments, or governance outcomes.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "dossiers" / "states"
ENTITY_DIR = ROOT / "knowledge" / "entities"

ORG_TERMS = (
    "Administration", "Agency", "Army", "Authority", "Bank", "Brigade", "Brigades",
    "Bureau", "Command", "Commission", "Committee", "Council", "Court", "Department",
    "Directorate", "Forces", "Force", "Group", "Guard", "Institute", "Intelligence",
    "Laboratories", "Ministry", "Network", "Office", "Police", "Service", "Services",
    "Technologies", "University", "Ltd", "Limited", "Inc", "Corp", "Corporation",
)
PROJECT_TERMS = (
    "Campaign", "CCTV", "Database", "Deployment", "Model", "Operation", "Platform",
    "Program", "Programme", "Project", "System", "Systems", "Tool", "Tools", "VSA",
)
# Phrases that are usually legal/policy/common-noun prose rather than an identity.
STOP_PHRASES = {
    "Current determination", "ECL criteria", "Evidence supporting", "Counter evidence",
    "Adversarial determination", "Review trigger", "Review triggers", "Procedural history",
    "Restricted Project", "Restricted Projects", "State dossier", "State review",
    "Schedule boundary", "Governance record", "No current", "Ordinary State",
    "Human Rights", "European Union", "United Nations", "International Law",
}
ACRONYM_STOP = {
    "AI", "ECL", "EU", "GDP", "ISO", "NATO", "NGO", "OSCE", "R", "S", "U", "N",
    "UN", "URL", "USA", "UK", "RISK", "STATE", "PROJECT", "ORG", "AGENCY",
}

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]{2,120})`")
QUOTED_RE = re.compile(r"[\"“]([^\"”\n]{2,120})[\"”]")
# Conservative title-case phrase. A cue term or acronym requirement is applied later.
TITLE_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.'’/-]*|[A-Z]{2,})(?:\s+(?:of|the|and|for|de|del|la|le|des|[A-Z][A-Za-z0-9&.'’/-]*|[A-Z]{2,})){0,8}\b"
)
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9-]{2,14}\b")
URL_RE = re.compile(r"https?://\S+")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def clean_candidate(text: str) -> str:
    text = text.strip(" \t\r\n.,;:()[]{}<>*_#'\"")
    text = re.sub(r"\s+", " ", text)
    return text


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONT_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip("\"'")
    return out


def load_identity_index() -> tuple[dict[str, str], set[str]]:
    names: dict[str, str] = {}
    ids: set[str] = set()
    for path in ENTITY_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entity_id = data.get("id")
        if not isinstance(entity_id, str):
            continue
        ids.add(entity_id)
        for value in [data.get("name"), *(data.get("aliases") or [])]:
            if isinstance(value, str) and norm(value):
                names[norm(value)] = entity_id
    return names, ids


def classify(text: str) -> str | None:
    words = set(re.findall(r"[A-Za-z]+", text))
    if words.intersection(PROJECT_TERMS):
        return "project-or-deployment"
    if words.intersection(ORG_TERMS):
        return "actor-or-institution"
    if ACRONYM_RE.fullmatch(text) and text not in ACRONYM_STOP:
        return "acronym-review"
    # Product/project names in inline code/quotes are retained by caller as opaque-name.
    return None


def plausible(text: str) -> bool:
    if len(text) < 3 or len(text) > 120:
        return False
    if text in STOP_PHRASES:
        return False
    n = norm(text)
    if not n or n in {norm(x) for x in STOP_PHRASES}:
        return False
    if text.isupper() and text in ACRONYM_STOP:
        return False
    if re.fullmatch(r"[RSUN]", text):
        return False
    return True


@dataclass(frozen=True)
class Occurrence:
    candidate: str
    normalized: str
    kind: str
    dossier: str
    state: str
    outcome: str | None
    section: str
    line: int
    snippet: str
    extraction: str
    resolved_id: str | None


def iter_occurrences(path: Path, identity_names: dict[str, str], identity_ids: set[str]) -> Iterable[Occurrence]:
    text = path.read_text(encoding="utf-8")
    front = parse_frontmatter(text)
    state = path.stem
    outcome = front.get("provisional_outcome")
    section = "frontmatter"
    body_start = text.find("\n---", 3)
    lines = text.splitlines()
    for lineno, raw in enumerate(lines, 1):
        hm = HEADING_RE.match(raw)
        if hm:
            section = hm.group(1).strip()
            continue
        if lineno <= 15 and raw.strip() == "---":
            continue
        line = URL_RE.sub("", raw)
        line = MD_LINK_RE.sub(lambda m: m.group(1), line)
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        extracted: list[tuple[str, str, str | None]] = []
        for m in INLINE_CODE_RE.finditer(line):
            value = clean_candidate(m.group(1))
            if re.fullmatch(r"(?:STATE|ORG|AGENCY|PERSON|PROJECT)-[A-Z0-9-]+", value):
                rid = value if value in identity_ids else None
                extracted.append((value, "id-reference", rid))
            elif plausible(value) and any(c.isalpha() for c in value):
                extracted.append((value, "opaque-name", identity_names.get(norm(value))))
        for m in QUOTED_RE.finditer(line):
            value = clean_candidate(m.group(1))
            if plausible(value):
                extracted.append((value, "quoted-name", identity_names.get(norm(value))))
        for m in TITLE_RE.finditer(line):
            value = clean_candidate(m.group(0))
            kind = classify(value)
            if kind and plausible(value):
                extracted.append((value, kind, identity_names.get(norm(value))))
        for m in ACRONYM_RE.finditer(line):
            value = m.group(0)
            if plausible(value) and value not in ACRONYM_STOP:
                extracted.append((value, "acronym-review", identity_names.get(norm(value))))

        seen_line: set[tuple[str, str]] = set()
        for value, kind, rid in extracted:
            key = (norm(value), kind)
            if key in seen_line:
                continue
            seen_line.add(key)
            yield Occurrence(
                candidate=value,
                normalized=norm(value),
                kind=kind,
                dossier=str(path.relative_to(ROOT)),
                state=state,
                outcome=outcome,
                section=section,
                line=lineno,
                snippet=raw.strip()[:360],
                extraction=kind,
                resolved_id=rid,
            )


def audit() -> dict:
    identity_names, identity_ids = load_identity_index()
    occurrences: list[Occurrence] = []
    for path in sorted(STATE_DIR.glob("*.md")):
        occurrences.extend(iter_occurrences(path, identity_names, identity_ids))

    groups: dict[str, list[Occurrence]] = defaultdict(list)
    for occ in occurrences:
        # ID references are grouped on the literal ID; names on normalized text.
        groups[occ.normalized].append(occ)

    candidates = []
    for key, occs in sorted(groups.items()):
        display = Counter(o.candidate for o in occs).most_common(1)[0][0]
        resolved = next((o.resolved_id for o in occs if o.resolved_id), None)
        states = sorted({o.state for o in occs})
        outcomes = sorted({o.outcome for o in occs if o.outcome})
        kinds = sorted({o.kind for o in occs})
        material_sections = sum(
            1 for o in occs
            if any(t in o.section.lower() for t in ("participant", "attribution", "evidence", "scope", "determination"))
        )
        restricted_mentions = sum(1 for o in occs if o.outcome in {"R", "S"})
        # Priority only orders human review; it is not a governance or attribution score.
        review_priority = (
            (30 if restricted_mentions else 0)
            + min(len(states), 10) * 3
            + min(material_sections, 10) * 2
            + (8 if "actor-or-institution" in kinds else 0)
            + (6 if "project-or-deployment" in kinds else 0)
        )
        candidates.append({
            "candidate": display,
            "normalized": key,
            "kinds": kinds,
            "resolution": "materialized" if resolved else "review-candidate",
            "resolved_id": resolved,
            "state_count": len(states),
            "states": states,
            "outcomes": outcomes,
            "occurrence_count": len(occs),
            "material_section_occurrences": material_sections,
            "restricted_state_occurrences": restricted_mentions,
            "review_priority": review_priority,
            "occurrences": [asdict(o) for o in occs],
        })

    candidates.sort(key=lambda x: (-x["review_priority"], -x["state_count"], x["candidate"].lower()))
    unresolved = [c for c in candidates if c["resolution"] == "review-candidate"]
    resolved = [c for c in candidates if c["resolution"] == "materialized"]
    return {
        "schema_version": 1,
        "semantics": {
            "purpose": "candidate discovery only",
            "non_inference": [
                "mention is not identity proof",
                "identity is not attribution",
                "association is not participation/control/operation",
                "no candidate or priority value has governance effect",
            ],
        },
        "counts": {
            "state_dossiers": len(list(STATE_DIR.glob("*.md"))),
            "existing_entity_files": len(list(ENTITY_DIR.glob("*.json"))),
            "candidate_groups": len(candidates),
            "resolved_groups": len(resolved),
            "unresolved_groups": len(unresolved),
            "occurrences": len(occurrences),
        },
        "candidates": candidates,
    }


def write_markdown(report: dict, path: Path, limit: int = 250) -> None:
    counts = report["counts"]
    rows = [
        "# State dossier entity/project mention audit",
        "",
        "> Discovery output only. A row is not an identity assertion, Claim, attribution, assessment, or governance decision.",
        "",
        f"- State dossiers scanned: **{counts['state_dossiers']}**",
        f"- Existing entity files: **{counts['existing_entity_files']}**",
        f"- Candidate groups: **{counts['candidate_groups']}**",
        f"- Already resolved groups: **{counts['resolved_groups']}**",
        f"- Unresolved review candidates: **{counts['unresolved_groups']}**",
        "",
        "## Highest-priority unresolved review candidates",
        "",
        "| Candidate | Kind | States | Occurrences | R/S mentions | Review priority |",
        "|---|---|---:|---:|---:|---:|",
    ]
    unresolved = [c for c in report["candidates"] if c["resolution"] == "review-candidate"][:limit]
    for c in unresolved:
        name = c["candidate"].replace("|", "\\|")
        kinds = ", ".join(c["kinds"]).replace("|", "\\|")
        rows.append(
            f"| {name} | {kinds} | {c['state_count']} | {c['occurrence_count']} | "
            f"{c['restricted_state_occurrences']} | {c['review_priority']} |"
        )
    rows += [
        "",
        "## Review rule",
        "",
        "Materialize an identity only after a human/reviewed rule establishes a stable, disambiguated referent. "
        "Create Claims for `operates`, `controls`, `participatesIn`, supply, or other material relations only from proposition-specific evidence. "
        "Never derive R/S/U/N from this audit.",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def self_test() -> None:
    assert norm("Udbetaling Danmark / ATP") == "udbetaling danmark atp"
    assert classify("National Police Service") == "actor-or-institution"
    assert classify("Project Maven System") == "project-or-deployment"
    assert classify("ordinary prose") is None
    assert not plausible("ECL")
    print("entity audit self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fail-if-empty", action="store_true")
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
    if args.fail_if_empty and report["counts"]["state_dossiers"] == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
