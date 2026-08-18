#!/usr/bin/env python3
"""Audit named non-State entities/projects mentioned by canonical State dossiers.

Discovery only: this tool never creates ABox identities, Claims, assessments, or
GovernanceDecision records. Unresolved names are intentionally scoped to the State
dossier that mentioned them so generic labels such as "Constitutional Court" do not
silently merge unrelated institutions across jurisdictions.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "dossiers" / "states"
ENTITY_DIR = ROOT / "knowledge" / "entities"

ORG_TERMS = {
    "Administration", "Agency", "Army", "Authority", "Bank", "Brigade", "Brigades",
    "Bureau", "Command", "Commission", "Committee", "Council", "Court", "Department",
    "Directorate", "Forces", "Force", "Group", "Guard", "Institute", "Intelligence",
    "Laboratories", "Ministry", "Network", "Office", "Police", "Service", "Services",
    "Technologies", "University", "Ltd", "Limited", "Inc", "Corp", "Corporation",
}
PROJECT_TERMS = {
    "Campaign", "CCTV", "Database", "Deployment", "Model", "Operation", "Platform",
    "Program", "Programme", "Project", "System", "Systems", "Tool", "Tools", "VSA",
}
STOP_PHRASES = {
    "Current determination", "ECL criteria", "Evidence supporting", "Counter evidence",
    "Adversarial determination", "Review trigger", "Review triggers", "Procedural history",
    "Restricted Project", "Restricted Projects", "State dossier", "State review",
    "Schedule boundary", "Governance record", "No current", "Ordinary State",
    "Human Rights", "International Law", "Current ECL", "Schedule translation",
    "State-wide", "State level", "State-level", "whole State", "State apparatus",
}
ACRONYM_STOP = {
    "AI", "ECL", "EU", "GDP", "ISO", "NATO", "NGO", "OSCE", "R", "S", "U", "N",
    "UN", "URL", "USA", "UK", "RISK", "STATE", "PROJECT", "ORG", "AGENCY",
    "UPHOLD", "UPHELD", "NARROW", "DEFINE", "DOWNGRADE", "ESCALATE", "RETAIN",
    "REMOVE", "REVIEW", "ADVERSARIAL", "UNKNOWN", "TODO", "TBD",
}

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
INLINE_CODE_RE = re.compile(r"`([^`\n]{2,120})`")
QUOTED_RE = re.compile(r"[\"“]([^\"”\n]{2,120})[\"”]")
TITLE_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.'’/-]*|[A-Z]{2,})"
    r"(?:\s+(?:of|the|and|for|de|del|la|le|des|[A-Z][A-Za-z0-9&.'’/-]*|[A-Z]{2,})){0,8}\b"
)
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9-]{2,14}\b")
URL_RE = re.compile(r"https?://\S+")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
CANONICAL_STATE_ID_RE = re.compile(r"^ECL-STATE-([A-Z]{3})$")
ENTITY_ID_RE = re.compile(r"(?:ORG|AGENCY|PERSON|PROJECT|DEPLOYMENT|INSTITUTION)-[A-Z0-9-]+$")
PATHISH_RE = re.compile(r"(?:^\.?\.?/|[/\\]|\.(?:md|yml|yaml|json|ttl|rq|py)$)", re.I)


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def clean_candidate(text: str) -> str:
    text = text.strip(" \t\r\n.,;:()[]{}<>*_#'\"")
    return re.sub(r"\s+", " ", text)


def parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    m = FRONT_RE.match(text)
    if not m:
        return {}, 0
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip("\"'")
    return out, m.end()


def canonical_state_dossiers() -> list[tuple[Path, dict[str, str], int]]:
    dossiers: list[tuple[Path, dict[str, str], int]] = []
    seen_iso: set[str] = set()
    for path in sorted(STATE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        front, body_offset = parse_frontmatter(text)
        match = CANONICAL_STATE_ID_RE.fullmatch(front.get("id", ""))
        iso = front.get("iso3", "")
        if not match or iso != match.group(1):
            continue
        if iso in seen_iso:
            raise ValueError(f"duplicate canonical State dossier for {iso}")
        seen_iso.add(iso)
        dossiers.append((path, front, body_offset))
    return dossiers


def load_identity_index() -> tuple[dict[str, str], set[str], Counter]:
    names: dict[str, str] = {}
    ids: set[str] = set()
    types: Counter = Counter()
    for path in sorted(ENTITY_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entity_id = data.get("id")
        entity_type = data.get("type")
        if not isinstance(entity_id, str) or not isinstance(entity_type, str):
            continue
        types[entity_type] += 1
        if entity_type == "State":
            continue
        ids.add(entity_id)
        for value in [data.get("name"), *(data.get("aliases") or [])]:
            if isinstance(value, str) and norm(value):
                names[norm(value)] = entity_id
    return names, ids, types


def classify(text: str) -> str | None:
    words = set(re.findall(r"[A-Za-z]+", text))
    if words & PROJECT_TERMS:
        return "project-or-deployment"
    if words & ORG_TERMS:
        return "actor-or-institution"
    if ACRONYM_RE.fullmatch(text) and text not in ACRONYM_STOP and not text.endswith("-"):
        return "acronym-review"
    return None


def pathish(text: str) -> bool:
    return bool(PATHISH_RE.search(text)) or text.startswith("ecl:") or text.startswith("urn:")


def plausible(text: str) -> bool:
    if len(text) < 3 or len(text) > 120 or pathish(text):
        return False
    if "→" in text or "=>" in text or " != " in text or " == " in text:
        return False
    n = norm(text)
    if not n or n in {norm(x) for x in STOP_PHRASES}:
        return False
    if text in ACRONYM_STOP or (text.isupper() and text in ACRONYM_STOP):
        return False
    if re.fullmatch(r"[RSUN]", text):
        return False
    return True


def looks_named_opaque(text: str) -> bool:
    if not plausible(text):
        return False
    if len(text.split()) > 8:
        return False
    # Quoted/backticked product and program names can lack a generic cue, but should
    # still look like a proper name rather than a prose/status fragment.
    return bool(re.search(r"[A-Z]", text)) and not text.lower().startswith((
        "last_", "asof", "review_", "provisional_", "evidence_", "state-",
    ))


def material_section(section: str) -> bool:
    s = section.lower()
    return any(token in s for token in (
        "participant", "attribution", "scope", "current determination", "criteria engaged",
        "evidence supporting", "material", "project", "deployment",
    ))


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
    resolved_id: str | None


def iter_occurrences(
    path: Path,
    front: dict[str, str],
    body_offset: int,
    identity_names: dict[str, str],
    identity_ids: set[str],
) -> Iterable[Occurrence]:
    text = path.read_text(encoding="utf-8")
    body = text[body_offset:]
    line_offset = text[:body_offset].count("\n")
    state = front["iso3"]
    outcome = front.get("provisional_outcome")
    section = "preamble"

    for relative_lineno, raw in enumerate(body.splitlines(), 1):
        lineno = line_offset + relative_lineno
        hm = HEADING_RE.match(raw)
        if hm:
            section = hm.group(1).strip()
            continue
        line = URL_RE.sub("", raw)
        line = MD_LINK_RE.sub(lambda m: m.group(1), line)
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        extracted: list[tuple[str, str, str | None]] = []
        for m in INLINE_CODE_RE.finditer(line):
            value = clean_candidate(m.group(1))
            if ENTITY_ID_RE.fullmatch(value):
                extracted.append((value, "id-reference", value if value in identity_ids else None))
            elif looks_named_opaque(value):
                extracted.append((value, "opaque-name", identity_names.get(norm(value))))
        for m in QUOTED_RE.finditer(line):
            value = clean_candidate(m.group(1))
            if looks_named_opaque(value):
                extracted.append((value, "quoted-name", identity_names.get(norm(value))))
        for m in TITLE_RE.finditer(line):
            value = clean_candidate(m.group(0))
            kind = classify(value)
            if kind and plausible(value):
                extracted.append((value, kind, identity_names.get(norm(value))))
        for m in ACRONYM_RE.finditer(line):
            value = m.group(0)
            if plausible(value) and value not in ACRONYM_STOP and not value.endswith("-"):
                extracted.append((value, "acronym-review", identity_names.get(norm(value))))

        seen_line: set[tuple[str, str]] = set()
        for value, kind, resolved in extracted:
            marker = (norm(value), kind)
            if marker in seen_line:
                continue
            seen_line.add(marker)
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
                resolved_id=resolved,
            )


def audit() -> dict:
    identity_names, identity_ids, entity_types = load_identity_index()
    dossiers = canonical_state_dossiers()
    occurrences: list[Occurrence] = []
    for path, front, body_offset in dossiers:
        occurrences.extend(iter_occurrences(path, front, body_offset, identity_names, identity_ids))

    # Global same-text statistics are informative, but unresolved candidates remain
    # State-scoped. This prevents accidental same-name identity merges.
    same_text_states: dict[str, set[str]] = defaultdict(set)
    for occ in occurrences:
        same_text_states[occ.normalized].add(occ.state)

    groups: dict[str, list[Occurrence]] = defaultdict(list)
    for occ in occurrences:
        if occ.resolved_id:
            key = f"resolved::{occ.resolved_id}"
        else:
            key = f"unresolved::{occ.state}::{occ.normalized}"
        groups[key].append(occ)

    candidates = []
    for key, occs in sorted(groups.items()):
        display = Counter(o.candidate for o in occs).most_common(1)[0][0]
        resolved = next((o.resolved_id for o in occs if o.resolved_id), None)
        states = sorted({o.state for o in occs})
        outcomes = sorted({o.outcome for o in occs if o.outcome})
        kinds = sorted({o.kind for o in occs})
        material_occurrences = sum(1 for o in occs if material_section(o.section))
        restricted_occurrences = sum(1 for o in occs if o.outcome in {"R", "S"})
        global_state_count = len(same_text_states[occs[0].normalized])
        review_priority = (
            (30 if restricted_occurrences else 0)
            + min(material_occurrences, 10) * 3
            + (8 if "actor-or-institution" in kinds else 0)
            + (7 if "project-or-deployment" in kinds else 0)
            + (4 if global_state_count > 1 else 0)
        )
        candidates.append({
            "candidate": display,
            "normalized": occs[0].normalized,
            "candidate_key": key,
            "kinds": kinds,
            "resolution": "materialized" if resolved else "review-candidate",
            "resolved_id": resolved,
            "states": states,
            "outcomes": outcomes,
            "occurrence_count": len(occs),
            "material_section_occurrences": material_occurrences,
            "restricted_state_occurrences": restricted_occurrences,
            "same_text_global_state_count": global_state_count,
            "review_priority": review_priority,
            "occurrences": [asdict(o) for o in occs],
        })

    candidates.sort(key=lambda x: (
        x["resolution"] != "review-candidate",
        -x["review_priority"],
        x["states"][0] if x["states"] else "",
        x["candidate"].lower(),
    ))
    unresolved = [c for c in candidates if c["resolution"] == "review-candidate"]
    resolved = [c for c in candidates if c["resolution"] == "materialized"]
    non_state_count = sum(v for k, v in entity_types.items() if k != "State")
    return {
        "schema_version": 2,
        "semantics": {
            "purpose": "candidate discovery only",
            "unresolved_identity_scope": "State-scoped until reviewed/disambiguated",
            "non_inference": [
                "mention is not identity proof",
                "identity is not attribution",
                "association is not participation/control/operation",
                "same text in multiple States is not proof of the same identity",
                "no candidate or priority value has governance effect",
            ],
        },
        "counts": {
            "canonical_state_dossiers": len(dossiers),
            "all_entity_files": sum(entity_types.values()),
            "existing_non_state_entity_files": non_state_count,
            "entity_types": dict(sorted(entity_types.items())),
            "candidate_groups": len(candidates),
            "resolved_groups": len(resolved),
            "unresolved_state_scoped_candidates": len(unresolved),
            "occurrences": len(occurrences),
        },
        "candidates": candidates,
    }


def write_markdown(report: dict, path: Path, limit: int = 300) -> None:
    counts = report["counts"]
    rows = [
        "# State dossier entity/project mention audit",
        "",
        "> Discovery output only. A row is not an identity assertion, Claim, attribution, assessment, or governance decision.",
        "",
        f"- Canonical State dossiers scanned: **{counts['canonical_state_dossiers']}**",
        f"- Existing ABox entity files: **{counts['all_entity_files']}**",
        f"- Existing non-State entity/project files: **{counts['existing_non_state_entity_files']}**",
        f"- Unresolved State-scoped review candidates: **{counts['unresolved_state_scoped_candidates']}**",
        f"- Candidate occurrences: **{counts['occurrences']}**",
        "",
        "## Highest-priority unresolved review candidates",
        "",
        "| State | Candidate | Kind | Occurrences | Material-section | Same text in States | Priority |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    unresolved = [c for c in report["candidates"] if c["resolution"] == "review-candidate"][:limit]
    for c in unresolved:
        name = c["candidate"].replace("|", "\\|")
        kinds = ", ".join(c["kinds"]).replace("|", "\\|")
        rows.append(
            f"| {','.join(c['states'])} | {name} | {kinds} | {c['occurrence_count']} | "
            f"{c['material_section_occurrences']} | {c['same_text_global_state_count']} | {c['review_priority']} |"
        )
    rows += [
        "",
        "## Review rule",
        "",
        "Unresolved names remain jurisdiction-scoped until a reviewer proves that they denote a stable, disambiguated referent. "
        "Materialize identity-only records independently of governance. Create `operates`, `controls`, `participatesIn`, supply, "
        "or other material relations only as Claims backed by proposition-specific EvidenceItems. Never derive R/S/U/N from this audit.",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8")


def self_test() -> None:
    assert norm("Udbetaling Danmark / ATP") == "udbetaling danmark atp"
    assert classify("National Police Service") == "actor-or-institution"
    assert classify("Project Maven System") == "project-or-deployment"
    assert classify("ordinary prose") is None
    assert not plausible("ECL")
    assert not plausible("../../reviews/2026/foo.md")
    assert not plausible("UPHOLD")
    assert plausible("OHCHR")
    front, offset = parse_frontmatter("---\nid: ECL-STATE-DNK\niso3: DNK\n---\n# Denmark\n")
    assert front["iso3"] == "DNK" and offset > 0
    print("entity audit self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fail-if-empty", action="store_true")
    parser.add_argument("--require-state-count", type=int, default=195)
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
    count = report["counts"]["canonical_state_dossiers"]
    if args.fail_if_empty and count == 0:
        return 2
    if args.require_state_count is not None and count != args.require_state_count:
        print(f"ERROR: expected {args.require_state_count} canonical State dossiers, found {count}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
