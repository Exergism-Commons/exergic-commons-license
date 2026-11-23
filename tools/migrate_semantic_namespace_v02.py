#!/usr/bin/env python3
"""Migrate active ECL semantic sources to the EC identifier architecture.

Only *vocabulary* moves. ECL classes and properties leave ``urn:ecl:`` for the
persistent ``https://id.exergism.org/ecl#`` namespace, and the compact prefix
``ecl:`` now means that namespace. Generic terms move to Commons (``ec:``), the
formal exergic variables to Exergism (``ex:``) and the ECL decision class
becomes ``ecl:ECLGovernanceDecision``.

ABox instances keep their ``urn:ecl:`` IRIs. Compact references to them are
written out in full (``ecl:STATE-USA`` becomes ``urn:ecl:STATE-USA``, or
``<urn:ecl:STATE-USA>`` where Turtle/SPARQL syntax needs an IRI reference) and
no ``urn:ecl:`` instance IRI is rewritten.

A local name denotes an instance when it follows the repository stable-ID
grammar ``^[A-Z][A-Z0-9-]+$`` (``entity.schema.json`` ``id``; this includes
prefixes such as ``STATE-`` that code completes), when it is the value of an
``"iri"`` key, or when it is interpolated (``f"ecl:{stable_id}"``). Any other
``[A-Za-z_][A-Za-z0-9_-]*`` local name is a vocabulary term. ``urn:ecl:``
identifiers with a further colon (``urn:ecl:schema:entity``,
``urn:ecl:graph:claims``) are neither and stay as they are.

Scope: tracked files with the suffixes below, outside historical surfaces
(releases, versions, bundles, snapshots, archive, generated) and GitHub
workflows, which are reviewed and edited by hand. The one generated file that
is rewritten is the State ABox manifest: its conflict-detection hashes cover
each State ``iri``, so a hash is re-certified only when it matched the record
before migration.

The script is idempotent and may be rerun on any branch. ``--check`` reports
pending changes without writing them. Code that builds or parses IRIs
dynamically cannot be classified mechanically; those sites are listed for
manual review.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD_ECL_NAMESPACE = "urn:ecl:"
ECL_INSTANCE_NAMESPACE = OLD_ECL_NAMESPACE
COMMONS_NAMESPACE = "https://id.exergism.org/commons#"
GOVERNANCE_NAMESPACE = "https://id.exergism.org/governance#"
EXERGISM_NAMESPACE = "https://id.exergism.org/exergism#"
ECL_NAMESPACE = "https://id.exergism.org/ecl#"
ONTOLOGY_IRIS = {"urn:ecl:ontology": "https://id.exergism.org/ontology/ecl"}

PREFIX_NAMESPACES = {"ec": COMMONS_NAMESPACE, "ex": EXERGISM_NAMESPACE, "ecl": ECL_NAMESPACE}
PYTHON_NAMESPACES = {"ec": "EC", "ex": "EX"}

# Immutable/history-like surfaces and workflows are deliberately outside the
# automated rewrite. Workflow edits are reviewed and committed explicitly.
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
EXCLUDED_FILES = {
    "tools/migrate_semantic_namespace_v02.py",
    "tests/test_migrate_semantic_namespace_v02.py",
}
STATE_MANIFEST = "knowledge/generated/state-abox-manifest.json"
STATE_RECORD = re.compile(r"knowledge/entities/STATE-([A-Z]{3})\.json")

TEXT_SUFFIXES = {".py", ".ttl", ".rq", ".json", ".jsonld", ".yaml", ".yml"}
IRI_REFERENCE_SUFFIXES = {".ttl", ".rq", ".py"}

SHARED_TERMS = frozenset({
    "Actor",
    "Person",
    "Organization",
    "ReleaseArtifact",
    "stableId",
    "title",
    "status",
    "rationale",
    "provenance",
    "supersedes",
    "reviewDue",
    "operative",
    "sha256",
})
FORMAL_VARIABLES = frozenset({"P", "A", "V_ep", "L", "O", "U", "C", "S", "R", "Ecol"})

INSTANCE_LOCAL = re.compile(r"[A-Z][A-Z0-9-]+")
COMPACT_ECL = re.compile(r"(?<![A-Za-z0-9_:/#.@<-])ecl:([A-Za-z0-9_-]*)")
FULL_ECL = re.compile(r"(?<![A-Za-z0-9_])urn:ecl:([A-Za-z0-9_-]*)")
HTTP_ECL_INSTANCE = re.compile(r"https://id\.exergism\.org/ecl#([A-Z][A-Z0-9-]+)(?![A-Za-z0-9_])")
IRI_VALUE_BEFORE = re.compile(r"""["']iri["']\s*\]?\s*[:=]\s*[rRbB]?[fF]?[rR]?["']$""")
FSTRING_START_BEFORE = re.compile(r"""(?<![A-Za-z0-9_])[rRbB]?[fF][rR]?["']$""")

NAMESPACE_BINDINGS = (
    re.compile(r"(@prefix\s+ecl:\s*<)urn:ecl:(>)"),
    re.compile(r"(PREFIX\s+ecl:\s*<)urn:ecl:(>)", re.IGNORECASE),
    re.compile(r"""(["']ecl["']\s*:\s*["'])urn:ecl:(["'])"""),
    re.compile(r"""(Namespace\(\s*["'])urn:ecl:(["']\s*\))"""),
    re.compile(r"""(\.bind\(\s*["']ecl["']\s*,\s*["'])urn:ecl:(["'])"""),
)
PYTHON_ECL_NAMESPACE = re.compile(
    r"""^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*Namespace\(\s*["'](?:urn:ecl:|https://id\.exergism\.org/ecl#)["']\s*\)""",
    re.MULTILINE,
)
PREFIX_DECLARATION = re.compile(
    r"^([ \t]*)(@prefix|PREFIX)([ \t]+)ecl:[ \t]*<[^>\n]*>([ \t]*\.)?[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)

REVIEW_PATTERNS = (
    (re.compile(r"""["']ecl:["']"""), "bare ecl: prefix string; ecl: now expands to the vocabulary namespace"),
    (re.compile(r"""[fF]["'][^"'\n]*[^"'\n:]ecl:\{"""), "interpolated compact IRI inside a longer string"),
    (re.compile(r"""[fF]["']urn:ecl:\{"""), "interpolated urn:ecl: IRI, kept as an instance"),
    (re.compile(r"""(?<![A-Za-z0-9_.])ECL\[(?!\s*[fF]?["'])"""), "dynamic subscript on the ECL vocabulary namespace"),
    (re.compile(r"""(?<![A-Za-z0-9_.])ECL\[\s*[fF]["']"""), "interpolated subscript left on the ECL vocabulary namespace"),
)
WORKFLOW_REVIEW = re.compile(r"urn:ecl:|(?<![A-Za-z0-9_:/#.@<-])ecl:[A-Z][A-Z0-9-]+")


def is_instance_local(local: str) -> bool:
    return INSTANCE_LOCAL.fullmatch(local) is not None


def migrate_term(local: str) -> tuple[str, str]:
    """Return the compact prefix and local name of a v0.1 ECL vocabulary term."""
    if local in SHARED_TERMS:
        return "ec", local
    if local in FORMAL_VARIABLES:
        return "ex", local
    if local.startswith("GovernanceDecision"):
        return "ecl", "ECL" + local
    return "ecl", local


def _iri_value_at(text: str, start: int) -> bool:
    return IRI_VALUE_BEFORE.search(text[max(0, start - 40) : start]) is not None


def _fstring_starts_at(text: str, start: int) -> bool:
    return FSTRING_START_BEFORE.search(text[max(0, start - 4) : start]) is not None


def _instance_reference(local: str, text: str, start: int, suffix: str) -> str:
    """Spell out an instance reference in the urn:ecl: namespace."""
    iri = ECL_INSTANCE_NAMESPACE + local
    previous = text[start - 1 : start] if start else ""
    if suffix in IRI_REFERENCE_SUFFIXES and previous not in {'"', "'", "^", "`"}:
        return f"<{iri}>"
    return iri


def migrate_compact(text: str, suffix: str) -> str:
    def replace(match: re.Match[str]) -> str:
        local = match.group(1)
        start = match.start()
        following = text[match.end() : match.end() + 1]
        if following == ":":
            return match.group(0)
        if not local:
            # f"ecl:{stable_id}": interpolated local names are stable IDs.
            if following == "{" and _fstring_starts_at(text, start):
                return ECL_INSTANCE_NAMESPACE
            return match.group(0)
        if is_instance_local(local) or _iri_value_at(text, start):
            return _instance_reference(local, text, start, suffix)
        prefix, migrated = migrate_term(local)
        return f"{prefix}:{migrated}"

    return COMPACT_ECL.sub(replace, text)


def migrate_full(text: str) -> str:
    for old, new in ONTOLOGY_IRIS.items():
        text = re.sub(rf"{re.escape(old)}(?![A-Za-z0-9_:-])", new, text)

    def replace(match: re.Match[str]) -> str:
        local = match.group(1)
        following = text[match.end() : match.end() + 1]
        if not local or following == ":":
            return match.group(0)
        if is_instance_local(local) or _iri_value_at(text, match.start()):
            return match.group(0)
        prefix, migrated = migrate_term(local)
        return PREFIX_NAMESPACES[prefix] + migrated

    text = FULL_ECL.sub(replace, text)
    # Instances never live in the vocabulary namespace.
    return HTTP_ECL_INSTANCE.sub(lambda match: ECL_INSTANCE_NAMESPACE + match.group(1), text)


def migrate_bindings(text: str) -> str:
    for pattern in NAMESPACE_BINDINGS:
        text = pattern.sub(lambda match: match.group(1) + ECL_NAMESPACE + match.group(2), text)
    return text


def python_ecl_namespaces(text: str) -> set[str]:
    return {match.group(1) for match in PYTHON_ECL_NAMESPACE.finditer(text)}


def _instance_subscript(fprefix: str, content: str) -> bool:
    if fprefix and "{" in content:
        # ECL[f"CLAIM-TEST-{suffix}"]: the literal head must be a stable-ID prefix.
        head = content.split("{", 1)[0]
        return head.endswith("-") and is_instance_local(head)
    return is_instance_local(content)


def migrate_python(text: str, ecl_names: set[str]) -> str:
    for name in sorted(ecl_names):
        # ECL["STATE-USA"] names an instance, so it leaves the vocabulary namespace.
        subscript = re.compile(
            rf"""(?<![A-Za-z0-9_.]){re.escape(name)}\[\s*([fF]?)(?:"([^"\n]*)"|'([^'\n]*)')\s*\]"""
        )

        def replace_subscript(match: re.Match[str]) -> str:
            fprefix = match.group(1)
            quote = '"' if match.group(2) is not None else "'"
            content = match.group(2) if match.group(2) is not None else match.group(3)
            if not _instance_subscript(fprefix, content):
                return match.group(0)
            return f"URIRef({fprefix}{quote}{ECL_INSTANCE_NAMESPACE}{content}{quote})"

        text = subscript.sub(replace_subscript, text)

    for name in sorted(ecl_names | {"ECL"}):
        attribute = re.compile(rf"(?<![A-Za-z0-9_.]){re.escape(name)}\.([A-Za-z_][A-Za-z0-9_]*)")

        def replace_attribute(match: re.Match[str]) -> str:
            prefix, migrated = migrate_term(match.group(1))
            return f"{PYTHON_NAMESPACES.get(prefix, name)}.{migrated}"

        text = attribute.sub(replace_attribute, text)

    return ensure_python_imports(text)


def ensure_python_imports(text: str) -> str:
    anchor = PYTHON_ECL_NAMESPACE.search(text)
    if anchor is not None:
        indent = re.match(r"[ \t]*", text[anchor.start() :]).group(0)
        lines = []
        for prefix, owner in PYTHON_NAMESPACES.items():
            used = re.search(rf"(?<![A-Za-z0-9_.]){owner}\.[A-Za-z_]", text)
            defined = re.search(rf"^[ \t]*{owner}[ \t]*=[ \t]*Namespace\(", text, flags=re.MULTILINE)
            if used and not defined:
                lines.append(f'\n{indent}{owner} = Namespace("{PREFIX_NAMESPACES[prefix]}")')
        if lines:
            text = text[: anchor.end()] + "".join(lines) + text[anchor.end() :]

    if "URIRef(" in text and not re.search(r"^[ \t]*from rdflib import [^\n]*\bURIRef\b", text, flags=re.MULTILINE):
        match = re.search(r"^([ \t]*from rdflib import )([^\n(]+)$", text, flags=re.MULTILINE)
        if match:
            names = [part.strip() for part in match.group(2).split(",") if part.strip()]
            text = text[: match.start()] + match.group(1) + ", ".join([*names, "URIRef"]) + text[match.end() :]
    return text


def _ensure_prefix_block(block: str, usage: str) -> str:
    declaration = PREFIX_DECLARATION.search(block)
    if declaration is None:
        return block
    indent, keyword, spacing, dot = declaration.group(1), declaration.group(2), declaration.group(3), declaration.group(4)
    insertions = []
    for prefix in ("ec", "ex"):
        used = re.search(rf"(?<![A-Za-z0-9_:/#.<@-]){prefix}:[A-Za-z_]", usage)
        declared = re.search(rf"(?:@prefix|PREFIX)\s+{prefix}:", block, flags=re.IGNORECASE)
        if used and not declared:
            terminator = " ." if dot else ""
            insertions.append(f"{indent}{keyword}{spacing}{prefix}: <{PREFIX_NAMESPACES[prefix]}>{terminator}\n")
    if not insertions:
        return block
    return block[: declaration.start()] + "".join(insertions) + block[declaration.start() :]


def ensure_rdf_prefixes(text: str, suffix: str) -> str:
    """Declare ec:/ex: next to each ecl: declaration that now needs them."""
    if suffix == ".rq":
        return _ensure_prefix_block(text, text)
    parts = text.split('"""')
    if suffix == ".ttl":
        parts[0] = _ensure_prefix_block(parts[0], "".join(parts[0::2]))
    for index in range(1, len(parts), 2):
        parts[index] = _ensure_prefix_block(parts[index], parts[index])
    return '"""'.join(parts)


def migrate_text(path: Path, text: str) -> str:
    suffix = path.suffix.lower()
    ecl_names = python_ecl_namespaces(text) if suffix == ".py" else set()

    text = migrate_compact(text, suffix)
    if suffix == ".py":
        text = migrate_python(text, ecl_names)
    text = migrate_full(text)
    text = migrate_bindings(text)
    if suffix in {".ttl", ".rq", ".py", ".yaml", ".yml"}:
        text = ensure_rdf_prefixes(text, suffix)
    return text


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode("utf-8")
    return [ROOT / item for item in output.split("\0") if item]


def active_text_files(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.as_posix() in EXCLUDED_FILES:
            continue
        result.append(path)
    return sorted(result)


def _load_state_abox_module():
    path = ROOT / "tools" / "migrate_state_abox.py"
    name = "_ecl_v02_migrate_state_abox"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def recertify_state_manifest(changes: dict[str, tuple[str, str]]) -> tuple[str | None, list[str]]:
    """Carry State manifest hashes over the iri rewrite, never over a conflict."""
    manifest = ROOT / STATE_MANIFEST
    states = {
        match.group(1): pair
        for relative, pair in changes.items()
        if (match := STATE_RECORD.fullmatch(relative))
    }
    if not states or not manifest.is_file():
        return None, []
    module = _load_state_abox_module()
    hashes, legacy = module.load_manifest(manifest)
    updated = dict(hashes)
    warnings: list[str] = []
    for iso3, (before, after) in sorted(states.items()):
        stored = hashes.get(iso3)
        migrated = module.phash(json.loads(after))
        if stored is None or stored == migrated:
            continue
        if module.phash(json.loads(before)) != stored:
            warnings.append(f"STATE-{iso3}: generator-owned fields already diverged from the manifest; hash left as is")
            continue
        updated[iso3] = migrated
    text = module.manifest_text(updated, legacy=legacy)
    return (None if text == manifest.read_bytes().decode("utf-8") else text), warnings


def review_sites(paths: list[Path], changes: dict[str, tuple[str, str]]) -> list[str]:
    sites: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        workflow = relative.startswith(".github/workflows/")
        if relative in EXCLUDED_FILES or not (workflow or path.suffix.lower() == ".py"):
            continue
        if not workflow and any(part in EXCLUDED_PARTS for part in Path(relative).parts):
            continue
        if relative in changes:
            text = changes[relative][1]
        else:
            try:
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
        for number, line in enumerate(text.splitlines(), 1):
            reasons = [reason for pattern, reason in REVIEW_PATTERNS if pattern.search(line)]
            if workflow and WORKFLOW_REVIEW.search(line):
                reasons.append("workflow is not rewritten automatically")
            for reason in reasons:
                sites.append(f"{relative}:{number}: {reason}: {line.strip()[:120]}")
    return sites


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report pending changes without writing; exit 1 if any")
    args = parser.parse_args(argv)

    tracked = tracked_files()
    changes: dict[str, tuple[str, str]] = {}
    for path in active_text_files(tracked):
        try:
            before = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        after = migrate_text(path, before)
        if after != before:
            changes[path.relative_to(ROOT).as_posix()] = (before, after)

    manifest_text, warnings = recertify_state_manifest(changes)
    if manifest_text is not None:
        current = (ROOT / STATE_MANIFEST).read_bytes().decode("utf-8")
        changes[STATE_MANIFEST] = (current, manifest_text)

    if not args.check:
        for relative, (_, after) in changes.items():
            (ROOT / relative).write_text(after, encoding="utf-8", newline="\n")

    verb = "would migrate" if args.check else "migrated"
    print(f"{verb} {len(changes)} active semantic files")
    for relative in sorted(changes):
        print(relative)
    for warning in warnings:
        print(f"warning: {warning}")
    sites = review_sites(tracked, changes)
    if sites:
        print(f"review by hand ({len(sites)} sites build or parse IRIs dynamically):")
        for site in sites:
            print(f"  {site}")
    return 1 if args.check and changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
