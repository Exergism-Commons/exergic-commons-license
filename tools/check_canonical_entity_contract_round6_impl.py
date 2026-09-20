#!/usr/bin/env python3
"""Round-six fail-closed guards for JSON-LD identity, CommonMark and media safety."""
from __future__ import annotations

import argparse
import html
import json
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from markdown_it import MarkdownIt

import canonical_dossier_contract as contract
import canonical_markdown as markdown
import strict_json
import check_canonical_entity_contract as prior

ROOT = Path(__file__).resolve().parents[1]
ENTITY_SUFFIXES_EXACT = {".json", ".jsonld"}
SVG_NS = "{http://www.w3.org/2000/svg}"
ACTIVE_SVG_TAGS = {
    "a", "animate", "animateMotion", "animateTransform", "discard",
    "foreignObject", "image", "script", "set", "style", "textPath", "use",
}
SAFE_STATIC_SVG_TAGS = {
    "svg", "title", "desc", "metadata", "defs", "clipPath",
    "rect", "g", "line", "polygon", "text", "tspan",
}
REQUIRED_SECTIONS = {
    "Identity scope", "State governance context", "Evidence record",
    "Attribution and exclusions", "Visual evidence", "Evidence gaps",
    "Sources", "Governance boundary",
}
IDENTITY_ONLY_FORBIDDEN_FRONTMATTER = {
    "currentGovernance", "governanceStatus", "restrictionStatus", "tier",
    "outcome", "provisional_outcome", "status",
}


def _load_json(path: Path) -> dict:
    value = strict_json.load(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _entity_schema(root: Path) -> tuple[dict, set[str]]:
    schema = _load_json(root / "schemas/entity.schema.json")
    enum = schema["properties"]["type"]["enum"]
    if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
        raise ValueError("schemas/entity.schema.json: invalid entity type enum")
    return schema, set(enum)


def _context_error(root: Path, path: Path, value: dict) -> str | None:
    context = value.get("@context")
    if not isinstance(context, str) or not context:
        return f"{path.relative_to(root)}: canonical Git-native ABox requires one local string @context"
    parsed = urlsplit(context)
    if parsed.scheme or parsed.netloc or context.startswith("//"):
        return f"{path.relative_to(root)}: remote/non-local JSON-LD @context {context!r} is forbidden"
    if (path.parent / context).resolve() != (root / "ontology/ecl-context.jsonld").resolve():
        return (
            f"{path.relative_to(root)}: @context must resolve to the repository canonical "
            f"ontology/ecl-context.jsonld, got {context!r}"
        )
    return None


def _builder_paths(root: Path) -> list[Path]:
    knowledge = root / "knowledge"
    return sorted(set(knowledge.rglob("*.json")) | set(knowledge.rglob("*.jsonld")))


def validate_abox_dialect(root: Path) -> list[str]:
    """Canonicalize JSON-LD syntax so raw placement and RDF semantics cannot diverge."""
    errors: list[str] = []
    try:
        schema, entity_types = _entity_schema(root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [str(exc)]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    knowledge = root / "knowledge"
    entity_root = root / "knowledge/entities"

    for path in sorted(knowledge.rglob("*")):
        if path.is_file() and path.suffix.lower() in ENTITY_SUFFIXES_EXACT and path.suffix not in ENTITY_SUFFIXES_EXACT:
            errors.append(
                f"{path.relative_to(root)}: ABox suffix must be lowercase .json/.jsonld to match builder discovery"
            )

    for path in _builder_paths(root):
        try:
            value = strict_json.load(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or "@context" not in value or not ("iri" in value or "@id" in value):
            continue
        context_problem = _context_error(root, path, value)
        if context_problem:
            errors.append(context_problem)
        if "@id" in value or "@type" in value:
            errors.append(
                f"{path.relative_to(root)}: direct @id/@type is forbidden; use canonical iri/type aliases"
            )
        if not isinstance(value.get("iri"), str) or not isinstance(value.get("type"), str):
            errors.append(f"{path.relative_to(root)}: canonical ABox candidates require compact iri and type fields")
            continue
        record_type = value["type"]
        if record_type in entity_types:
            try:
                path.relative_to(entity_root)
            except ValueError:
                errors.append(
                    f"{path.relative_to(root)}: entity-typed ABox record is outside knowledge/entities"
                )

    for path in sorted(set(entity_root.rglob("*.json")) | set(entity_root.rglob("*.jsonld"))):
        try:
            value = strict_json.load(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: invalid entity JSON: {exc}")
            continue
        for violation in sorted(validator.iter_errors(value), key=lambda err: list(err.absolute_path)):
            location = ".".join(str(part) for part in violation.absolute_path) or "<root>"
            errors.append(f"{path.relative_to(root)}: entity schema violation at {location}: {violation.message}")
        if not isinstance(value, dict):
            continue
        entity_id = value.get("id")
        if isinstance(entity_id, str) and value.get("iri") != f"ecl:{entity_id}":
            errors.append(
                f"{path.relative_to(root)}: entity iri {value.get('iri')!r} must equal stable identity 'ecl:{entity_id}'"
            )
    return errors


def _body_without_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text[end + 5 :] if end >= 0 else text


def _visible_inline_text(token) -> str:
    return markdown.rendered_inline_text(token, include_images=False, include_code=False)


def validate_commonmark_identity_dossiers(root: Path) -> list[str]:
    errors: list[str] = []
    for _version, _manifest_path, row in prior._manifest_rows(root):
        dossier_rel = row.get("dossier")
        entity_id = row.get("id", "<missing-id>")
        if not isinstance(dossier_rel, str):
            continue
        dossier = root / dossier_rel
        if not dossier.is_file():
            continue
        source = dossier.read_text(encoding="utf-8")
        fm, fm_errors = prior.strict_frontmatter(source)
        errors.extend(f"{dossier_rel}: {entity_id}: {problem}" for problem in fm_errors)
        for key in sorted(IDENTITY_ONLY_FORBIDDEN_FRONTMATTER & set(fm)):
            errors.append(f"{dossier_rel}: {entity_id}: forbidden identity-only governance key {key!r}")

        surface = markdown.parse_surface(source)
        if any(token.type in {"html_block", "html_inline"} for token in surface.tokens):
            errors.append(f"{dossier_rel}: {entity_id}: raw HTML is forbidden on identity-only canonical dossiers")
        for title, count in sorted(surface.section_counts.items()):
            if count > 1:
                errors.append(f"{dossier_rel}: {entity_id}: duplicate rendered top-level H2 section {title!r}")
        for heading in sorted(REQUIRED_SECTIONS):
            if surface.section_counts.get(heading, 0) != 1:
                errors.append(f"{dossier_rel}: {entity_id}: CommonMark is missing/ambiguous required section ## {heading}")
                continue
            positive = markdown.section_text_from_surface(surface, heading, include_code=(heading == "Sources"))
            if not positive:
                errors.append(f"{dossier_rel}: {entity_id}: CommonMark section ## {heading} has no positive rendered prose")

        visuals = row.get("visuals")
        if isinstance(visuals, list):
            for visual in visuals:
                if not isinstance(visual, str):
                    continue
                expected = prior._expected_relative_visual(dossier_rel, visual)
                matches = [(alt, src) for alt, src in surface.images if src == expected]
                if len(matches) != 1:
                    errors.append(f"{dossier_rel}: {entity_id}: CommonMark must render exactly one image for {expected!r}; found {len(matches)}")
                    continue
                problem = prior._meaningful_alt_error(matches[0][0], visual)
                if problem:
                    errors.append(f"{dossier_rel}: {entity_id}: {problem}")
    return errors


def validate_encoded_resources(root: Path) -> list[str]:
    errors: list[str] = []
    for _version, _manifest_path, row in prior._manifest_rows(root):
        dossier_rel = row.get("dossier")
        entity_id = row.get("id", "<missing-id>")
        if not isinstance(dossier_rel, str):
            continue
        dossier = root / dossier_rel
        if not dossier.is_file():
            continue
        for target in contract.embedded_resource_targets(dossier.read_text(encoding="utf-8")):
            decoded = html.unescape(target.strip())
            if "\\" in decoded or decoded.startswith("//"):
                errors.append(f"{dossier_rel}: {entity_id}: escaped/protocol-relative embedded resource {target!r} is forbidden")
                continue
            parsed = urlsplit(decoded)
            if parsed.scheme or parsed.netloc:
                errors.append(f"{dossier_rel}: {entity_id}: non-local embedded resource {target!r} resolves to {decoded!r}")
    return errors


def validate_all_generated_svg_static(root: Path) -> list[str]:
    errors: list[str] = []
    directory = root / "dossiers/assets/generated"
    if not directory.is_dir():
        return ["dossiers/assets/generated: missing generated visual directory"]
    for path in sorted(directory.glob("*.svg")):
        rel = path.relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8")
        lowered = raw.lower()
        for marker in ("<!doctype", "<!entity", "<?xml-stylesheet"):
            if marker in lowered:
                errors.append(f"{rel}: active/external XML construct {marker!r} is forbidden")
        try:
            svg = ET.fromstring(raw)
        except ET.ParseError as exc:
            errors.append(f"{rel}: invalid SVG/XML: {exc}")
            continue
        for element in svg.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            namespace = element.tag[: element.tag.rfind("}") + 1] if "}" in element.tag else ""
            if namespace not in {"", SVG_NS}:
                errors.append(f"{rel}: foreign XML namespace element {element.tag!r} is forbidden")
            if tag not in SAFE_STATIC_SVG_TAGS:
                errors.append(f"{rel}: unsupported SVG element <{tag}> is forbidden by the canonical static allowlist")
            if tag in ACTIVE_SVG_TAGS:
                errors.append(f"{rel}: active/indirect SVG element <{tag}> is forbidden")
            if tag == "clipPath" and element.get("clipPathUnits") not in {None, "userSpaceOnUse"}:
                errors.append(f"{rel}: clipPathUnits must be userSpaceOnUse/absent")
            for raw_name, value in element.attrib.items():
                name = raw_name.rsplit("}", 1)[-1].lower()
                if name.startswith("on") or name == "href":
                    errors.append(f"{rel}: active/indirect SVG attribute {name!r} is forbidden")
                if "url(" in value.lower():
                    allowed_clip = name == "clip-path" and __import__("re").fullmatch(r"url\(#[-A-Za-z0-9_.:]+\)", value.strip())
                    if not allowed_clip:
                        errors.append(f"{rel}: external/indirect SVG url() reference in {name!r} is forbidden")
    return errors


def _valid_raster(path: Path) -> bool:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required for source-facsimile verification") from exc
    expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}.get(path.suffix.lower())
    if expected is None:
        return False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format != expected or image.width <= 0 or image.height <= 0:
                    return False
                image.verify()
            with Image.open(path) as image:
                image.load()
        return True
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombWarning):
        return False


def validate_decoded_rasters(root: Path) -> list[str]:
    errors: list[str] = []
    directory = root / "dossiers/evidence-images"
    if not directory.exists():
        return errors
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in contract.RASTER_FACSIMILE_EXTENSIONS and not _valid_raster(path):
            errors.append(
                f"{path.relative_to(root)}: Pillow cannot decode/verify the declared PNG/JPEG/WebP facsimile"
            )
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    errors.extend(validate_abox_dialect(root))
    errors.extend(validate_commonmark_identity_dossiers(root))
    errors.extend(validate_encoded_resources(root))
    errors.extend(validate_all_generated_svg_static(root))
    errors.extend(validate_decoded_rasters(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--abox-only", action="store_true")
    args = parser.parse_args()
    errors = validate_abox_dialect(ROOT) if args.abox_only else prior.main.__globals__["contract"].validate(ROOT) + prior.validate_hardening(ROOT) + validate(ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"round-six canonical hardening: FAILED ({len(errors)} error(s))")
        return 1
    print("round-six canonical hardening: OK (canonical JSON-LD identity, CommonMark AST, all-SVG static safety, decoded rasters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
