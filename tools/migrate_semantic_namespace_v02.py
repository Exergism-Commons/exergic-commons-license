#!/usr/bin/env python3
"""Migrate active ECL semantic sources to the EC identifier architecture.

This script is intentionally scoped to active machine-readable/code surfaces.
Historical releases, archived material, generated snapshots and immutable bundle
artifacts are excluded. GitHub workflows are migrated explicitly outside this
materializer because GitHub App tokens cannot rewrite workflow files. The script
is idempotent and may be rerun during the v0.2 migration branch.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
OLD_ECL_NAMESPACE = "urn:ecl:"
COMMONS_NAMESPACE = "https://id.exergism.org/commons#"
GOVERNANCE_NAMESPACE = "https://id.exergism.org/governance#"
EXERGISM_NAMESPACE = "https://id.exergism.org/exergism#"
ECL_NAMESPACE = "https://id.exergism.org/ecl#"

# Immutable/history-like surfaces and workflows are deliberately outside the
# automated rewrite. Workflow edits are performed explicitly through GitHub.
EXCLUDED_PARTS = {
    ".git",
    ".github",
    "archive",
    "releases",
    "versions",
    "bundles",
    "snapshots",
    "generated",
    "__pycache__",
}

TEXT_SUFFIXES = {".py", ".ttl", ".rq", ".json", ".jsonld", ".yaml", ".yml"}

SHARED_COMPACT = {
    "ecl:Actor": "ec:Actor",
    "ecl:Person": "ec:Person",
    "ecl:Organization": "ec:Organization",
    "ecl:ReleaseArtifact": "ec:ReleaseArtifact",
    "ecl:stableId": "ec:stableId",
    "ecl:title": "ec:title",
    "ecl:status": "ec:status",
    "ecl:rationale": "ec:rationale",
    "ecl:provenance": "ec:provenance",
    "ecl:supersedes": "ec:supersedes",
    "ecl:reviewDue": "ec:reviewDue",
    "ecl:operative": "ec:operative",
    "ecl:sha256": "ec:sha256",
}

SHARED_PYTHON = {
    "ECL.Actor": "EC.Actor",
    "ECL.Person": "EC.Person",
    "ECL.Organization": "EC.Organization",
    "ECL.ReleaseArtifact": "EC.ReleaseArtifact",
    "ECL.stableId": "EC.stableId",
    "ECL.title": "EC.title",
    "ECL.status": "EC.status",
    "ECL.rationale": "EC.rationale",
    "ECL.provenance": "EC.provenance",
    "ECL.supersedes": "EC.supersedes",
    "ECL.reviewDue": "EC.reviewDue",
    "ECL.operative": "EC.operative",
    "ECL.sha256": "EC.sha256",
}

FORMAL_VARIABLES = ("P", "A", "V_ep", "L", "O", "U", "C", "S", "R", "Ecol")


def active_text_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.as_posix() == "tools/migrate_semantic_namespace_v02.py":
            continue
        result.append(path)
    return sorted(result)


def ensure_turtle_prefix(text: str, prefix: str, namespace: str) -> str:
    marker = f"@prefix {prefix}:"
    if marker in text:
        return text
    match = re.search(r"^@prefix ecl:.*$", text, flags=re.MULTILINE)
    if match:
        return text[: match.start()] + f"@prefix {prefix}: <{namespace}> .\n" + text[match.start() :]
    return text


def ensure_sparql_prefix(text: str, prefix: str, namespace: str) -> str:
    marker = f"PREFIX {prefix}:"
    if marker in text:
        return text
    match = re.search(r"^PREFIX ecl:.*$", text, flags=re.MULTILINE)
    if match:
        return text[: match.start()] + f"PREFIX {prefix}: <{namespace}>\n" + text[match.start() :]
    return text


def ensure_python_namespaces(text: str) -> str:
    if "EC." in text and "EC = Namespace(" not in text:
        match = re.search(r'^ECL = Namespace\(["\'][^"\']+["\']\)\s*$', text, flags=re.MULTILINE)
        if match:
            insertion = match.group(0) + f'\nEC = Namespace("{COMMONS_NAMESPACE}")'
            text = text[: match.start()] + insertion + text[match.end() :]
    if "EX." in text and "EX = Namespace(" not in text:
        match = re.search(r'^ECL = Namespace\(["\'][^"\']+["\']\)\s*$', text, flags=re.MULTILINE)
        if match:
            insertion = match.group(0) + f'\nEX = Namespace("{EXERGISM_NAMESPACE}")'
            text = text[: match.start()] + insertion + text[match.end() :]
    return text


def migrate_text(path: Path, text: str) -> str:
    # Active full IRIs now use the persistent HTTP namespace.
    text = text.replace(OLD_ECL_NAMESPACE, ECL_NAMESPACE)

    # Generic cross-project concepts no longer belong to ecl#.
    for old, new in SHARED_COMPACT.items():
        text = text.replace(old, new)
    for old, new in SHARED_PYTHON.items():
        text = text.replace(old, new)

    # The generic governance root is no longer owned by ECL. ECL decisions are
    # an explicit domain specialization of governance#GovernanceDecision.
    text = text.replace("ecl:GovernanceDecision", "ecl:ECLGovernanceDecision")
    text = text.replace("ECL.GovernanceDecision", "ECL.ECLGovernanceDecision")

    # Formal exergic variables are canonical in Exergism.
    for symbol in FORMAL_VARIABLES:
        text = text.replace(f"ecl:{symbol}", f"ex:{symbol}")
        text = text.replace(f"ECL.{symbol}", f"EX.{symbol}")

    if path.suffix == ".ttl":
        if "ec:" in text:
            text = ensure_turtle_prefix(text, "ec", COMMONS_NAMESPACE)
        if "ex:" in text:
            text = ensure_turtle_prefix(text, "ex", EXERGISM_NAMESPACE)
    elif path.suffix == ".rq":
        if "ec:" in text:
            text = ensure_sparql_prefix(text, "ec", COMMONS_NAMESPACE)
        if "ex:" in text:
            text = ensure_sparql_prefix(text, "ex", EXERGISM_NAMESPACE)
    elif path.suffix == ".py":
        text = ensure_python_namespaces(text)

    return text


def main() -> int:
    changed: list[str] = []
    for path in active_text_files():
        try:
            before = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        after = migrate_text(path, before)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(path.relative_to(ROOT).as_posix())

    print(f"migrated {len(changed)} active semantic files")
    for relative in changed:
        print(relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
