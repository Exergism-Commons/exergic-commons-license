#!/usr/bin/env python3
"""Require exact set equality and identity integrity for canonical State dossiers."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from audit_state_dossier_entities import parse_frontmatter

ROOT = Path(__file__).resolve().parents[1]
DOSSIERS = ROOT / "dossiers" / "states"
ENTITIES = ROOT / "knowledge" / "entities"
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
DOSSIER_ID = re.compile(r"^ECL-STATE-([A-Z]{3})$")
ENTITY_ID = re.compile(r"^STATE-([A-Z]{3})$")
H1_RE = re.compile(r"^\s{0,3}#(?!#)\s+(.+?)\s*$")
TRAILING_H1_ALIAS_RE = re.compile(r"\s+\(([^()\n]+)\)\s*$")
# State-dossier frontmatter is intentionally a flat, reviewed contract. Identity-bearing prose
# belongs in the two explicit textual fields below or in the dossier body; a newly invented
# frontmatter key must be reviewed and added here instead of becoming an unaudited side channel.
ALLOWED_DOSSIER_FRONTMATTER_KEYS = {
    "id", "entity", "iso3", "issue", "provisional_outcome", "provisional_scope",
    "confidence", "evidence_cutoff", "last_reviewed", "review_stage", "adversarial_result",
    "exergism_status", "exergism_assessment", "operative",
}


class UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate YAML mapping keys after decoding them."""


def construct_unique_mapping(loader: UniqueKeySafeLoader, node: yaml.nodes.MappingNode, deep: bool = False):
    """Construct a mapping without PyYAML's last-key-wins duplicate behavior."""
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def strict_frontmatter_mapping(source: str) -> dict[str, object]:
    """Decode one YAML frontmatter mapping while rejecting semantic duplicate keys."""
    try:
        loaded = yaml.load(source, Loader=UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid State-dossier YAML frontmatter: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise ValueError("State-dossier frontmatter must be a YAML mapping with string keys")
    return dict(loaded)


def parse_frontmatter_text(text: str) -> dict[str, object]:
    """Parse the shared YAML mapping and reject duplicate keys by decoded YAML identity."""
    match = FRONT.match(text)
    if not match:
        return {}

    # Validate duplicate keys using decoded YAML values, not source spelling. Quoted and
    # unquoted forms of the same key are therefore the same key and fail closed before the
    # ordinary SafeLoader can apply its last-key-wins behavior.
    strict_data = strict_frontmatter_mapping(match.group(1))

    data, offset = parse_frontmatter(text)
    if offset != match.end():
        raise ValueError("State dossier frontmatter parser offset mismatch")
    if data != strict_data:
        raise ValueError("strict/shared State dossier frontmatter parser disagreement")
    return data


def frontmatter(path: Path) -> dict[str, object]:
    return parse_frontmatter_text(path.read_text(encoding="utf-8"))


def split_h1_title_aliases(title: str) -> tuple[str, list[str]]:
    """Separate a canonical H1 stem from each trailing parenthesized decoration."""
    stem = title.strip()
    aliases: list[str] = []
    while True:
        match = TRAILING_H1_ALIAS_RE.search(stem)
        if not match:
            break
        alias = match.group(1).strip()
        if not alias:
            raise ValueError("canonical State H1 contains an empty trailing alias")
        aliases.append(alias)
        stem = stem[:match.start()].rstrip()
    aliases.reverse()
    return stem, aliases


def state_h1_aliases(iso: str) -> list[str]:
    """Return the reviewed aliases on the corresponding State identity, if structurally usable."""
    path = ENTITIES / f"STATE-{iso}.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if data.get("type") != "State" or data.get("id") != f"STATE-{iso}":
        return []
    aliases = data.get("aliases")
    if not isinstance(aliases, list) or not all(isinstance(item, str) and item.strip() for item in aliases):
        return []
    return list(aliases)


def canonical_h1_title(text: str, expected_entity: str, allowed_aliases: list[str]) -> str:
    """Require one canonical State H1 and validate every trailing decoration as a State alias."""
    front = FRONT.match(text)
    if front is None:
        raise ValueError("canonical State dossier is missing YAML frontmatter")
    body = text[front.end():]
    h1s: list[tuple[int, str]] = []
    first_content_line: int | None = None
    for line_no, raw in enumerate(body.splitlines(), 1):
        if first_content_line is None and raw.strip():
            first_content_line = line_no
        match = H1_RE.fullmatch(raw)
        if match:
            h1s.append((line_no, match.group(1).strip()))
    if len(h1s) != 1:
        raise ValueError(f"canonical State dossier must contain exactly one H1; found {len(h1s)}")
    line_no, title = h1s[0]
    if first_content_line != line_no:
        raise ValueError("canonical State H1 must be the first non-blank body line")

    title_stem, trailing_aliases = split_h1_title_aliases(title)
    if norm(title_stem) != norm(expected_entity):
        raise ValueError(
            f"canonical State H1 {title!r} does not match frontmatter entity {expected_entity!r}"
        )

    allowed_normalized = {norm(alias) for alias in allowed_aliases if norm(alias)}
    unknown_aliases = [alias for alias in trailing_aliases if norm(alias) not in allowed_normalized]
    if unknown_aliases:
        raise ValueError(
            f"canonical State H1 {title!r} contains trailing alias(es) not present on the "
            f"State identity: {unknown_aliases!r}"
        )
    return title


def self_test_frontmatter_parser() -> None:
    continuation = (
        "---\n"
        "id: ECL-STATE-AAA\n"
        "iso3: AAA\n"
        "provisional_scope: >\n"
        "  Human Rights Watch: reporting remains material\n"
        "---\n"
    )
    parsed = parse_frontmatter_text(continuation)
    assert parsed["provisional_scope"] == "Human Rights Watch: reporting remains material"

    semantic_duplicate = (
        "---\n"
        "id: ECL-STATE-AAA\n"
        "iso3: AAA\n"
        "provisional_scope: hidden identity\n"
        "\"provisional_scope\": clean\n"
        "---\n"
    )
    try:
        parse_frontmatter_text(semantic_duplicate)
    except ValueError as exc:
        assert "duplicate key 'provisional_scope'" in str(exc)
    else:
        raise AssertionError("quoted/unquoted duplicate YAML keys must fail closed")

    canonical = (
        "---\n"
        "id: ECL-STATE-PRK\n"
        "entity: North Korea\n"
        "iso3: PRK\n"
        "---\n"
        "# North Korea (DPRK)\n\n"
        "## 1. Current determination\n"
    )
    aliases = ["PRK", "DPRK", "Democratic People's Republic of Korea", "North Korea (DPRK)"]
    assert canonical_h1_title(canonical, "North Korea", aliases) == "North Korea (DPRK)"
    assert canonical_h1_title(canonical.replace(" (DPRK)", ""), "North Korea", aliases) == "North Korea"

    invalid_h1s = (
        canonical + "\n# Project Aurora\n",
        canonical.replace("# North Korea (DPRK)", "# Project Aurora"),
        canonical.replace("# North Korea (DPRK)\n\n", "Preamble\n\n# North Korea (DPRK)\n\n"),
        canonical.replace("# North Korea (DPRK)", "# North Korea (Project Aurora)"),
        canonical.replace("# North Korea (DPRK)", "# North Korea (DPRK) (Project Aurora)"),
    )
    for invalid in invalid_h1s:
        try:
            canonical_h1_title(invalid, "North Korea", aliases)
        except ValueError:
            pass
        else:
            raise AssertionError("noncanonical/additional/unreviewed State-dossier H1 alias must fail closed")


def main() -> int:
    self_test_frontmatter_parser()
    dossier_by_iso: dict[str, str] = {}
    for path in sorted(DOSSIERS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            data = parse_frontmatter_text(text)
        except ValueError as exc:
            print(f"invalid State dossier frontmatter in {path.relative_to(ROOT)}: {exc}")
            return 14
        dossier_id = data.get("id")
        iso_value = data.get("iso3")
        match = DOSSIER_ID.fullmatch(dossier_id) if isinstance(dossier_id, str) else None
        if not match or iso_value != match.group(1):
            continue
        iso = match.group(1)
        if path.stem != iso:
            continue
        unexpected_keys = sorted(set(data) - ALLOWED_DOSSIER_FRONTMATTER_KEYS)
        if unexpected_keys:
            print(
                f"unexpected canonical State dossier frontmatter keys in {path.relative_to(ROOT)}: "
                f"{unexpected_keys}"
            )
            return 15
        entity_value = data.get("entity")
        if not isinstance(entity_value, str) or not entity_value.strip():
            print(f"canonical State dossier missing textual entity in {path.relative_to(ROOT)}")
            return 16
        try:
            canonical_h1_title(text, entity_value, state_h1_aliases(iso))
        except ValueError as exc:
            print(f"invalid canonical State dossier H1 in {path.relative_to(ROOT)}: {exc}")
            return 17
        if iso in dossier_by_iso:
            print(f"duplicate canonical dossier for {iso}: {dossier_by_iso[iso]} and {path}")
            return 2
        dossier_by_iso[iso] = str(path.relative_to(ROOT))

    identity_by_iso: dict[str, str] = {}
    state_names: dict[str, set[str]] = defaultdict(set)
    for path in sorted(ENTITIES.glob("STATE-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") != "State":
            continue
        match = ENTITY_ID.fullmatch(data.get("id", ""))
        if not match:
            print(f"malformed State identity id in {path.relative_to(ROOT)}: {data.get('id')!r}")
            return 3
        iso = match.group(1)
        entity_id = data["id"]
        if path.stem != entity_id:
            print(f"State identity filename/id mismatch: {path.relative_to(ROOT)} -> {entity_id!r}")
            return 4
        if data.get("iso3") != iso:
            print(f"State identity iso3/id mismatch: {path.relative_to(ROOT)} -> {data.get('iso3')!r} vs {iso}")
            return 5
        if data.get("iri") != f"ecl:{entity_id}":
            print(f"State identity iri/id mismatch: {path.relative_to(ROOT)} -> {data.get('iri')!r}")
            return 6
        name = data.get("name")
        aliases = data.get("aliases")
        if not isinstance(name, str) or not name.strip():
            print(f"State identity missing canonical name: {path.relative_to(ROOT)}")
            return 7
        if not isinstance(aliases, list) or not all(isinstance(item, str) and item.strip() for item in aliases):
            print(f"State identity aliases must be a string list: {path.relative_to(ROOT)}")
            return 8
        if iso not in aliases:
            print(f"State identity must preserve ISO3 as alias: {path.relative_to(ROOT)} -> {aliases!r}")
            return 9
        dossier_value = data.get("dossier")
        if not isinstance(dossier_value, str):
            print(f"State identity missing dossier path: {path.relative_to(ROOT)}")
            return 10
        resolved_dossier = (path.parent / dossier_value).resolve()
        expected_dossier = (DOSSIERS / f"{iso}.md").resolve()
        if resolved_dossier != expected_dossier or not resolved_dossier.is_file():
            print(
                f"State identity dossier mismatch: {path.relative_to(ROOT)} -> {dossier_value!r}; "
                f"expected {expected_dossier.relative_to(ROOT)}"
            )
            return 11
        if iso in identity_by_iso:
            print(f"duplicate State identity for {iso}: {identity_by_iso[iso]} and {path}")
            return 12
        identity_by_iso[iso] = str(path.relative_to(ROOT))
        for value in [name, *aliases]:
            normalized = norm(value)
            if normalized:
                state_names[normalized].add(iso)

    collisions = [
        {"normalized_name_or_alias": value, "states": sorted(states)}
        for value, states in sorted(state_names.items())
        if len(states) > 1
    ]
    if collisions:
        print("AMBIGUOUS_STATE_NAMES_OR_ALIASES=" + json.dumps(collisions, ensure_ascii=False, sort_keys=True))
        return 13

    dossier_set = set(dossier_by_iso)
    identity_set = set(identity_by_iso)
    missing_identity = sorted(dossier_set - identity_set)
    missing_dossier = sorted(identity_set - dossier_set)
    report = {
        "canonical_state_dossiers": len(dossier_set),
        "state_identities": len(identity_set),
        "dossiers_without_state_identity": [
            {"iso3": iso, "dossier": dossier_by_iso[iso]} for iso in missing_identity
        ],
        "state_identities_without_dossier": [
            {"iso3": iso, "entity": identity_by_iso[iso]} for iso in missing_dossier
        ],
        "state_name_or_alias_collisions": 0,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if missing_identity or missing_dossier else 0


if __name__ == "__main__":
    sys.exit(main())