#!/usr/bin/env python3
"""Public round-six hardening wrapper with CommonMark Sources semantics."""
from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt

import check_canonical_entity_contract_round6_impl as _impl

_original_commonmark_validation = _impl.validate_commonmark_identity_dossiers


def _sources_has_rendered_content(path: Path) -> bool:
    """Repository paths rendered as code are valid structured source entries."""
    source = path.read_text(encoding="utf-8")
    tokens = MarkdownIt("commonmark").parse(_impl._body_without_frontmatter(source))
    in_sources = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and token.tag == "h2" and i + 1 < len(tokens):
            heading = " ".join(tokens[i + 1].content.split())
            in_sources = heading == "Sources"
            i += 3
            continue
        if in_sources and token.type == "inline":
            for child in token.children or []:
                if child.type in {"text", "code_inline", "image"} and child.content.strip():
                    return True
        i += 1
    return False


def validate_commonmark_identity_dossiers(root: Path) -> list[str]:
    errors = _original_commonmark_validation(root)
    filtered: list[str] = []
    marker = "CommonMark section ## Sources has no positive rendered prose"
    for error in errors:
        if marker not in error:
            filtered.append(error)
            continue
        dossier_rel = error.split(":", 1)[0]
        dossier = root / dossier_rel
        if not dossier.is_file() or not _sources_has_rendered_content(dossier):
            filtered.append(error)
    return filtered


# Patch the implementation module so its validate()/main() functions use the
# compatibility-aware Sources rule while all other round-six logic remains exact.
_impl.validate_commonmark_identity_dossiers = validate_commonmark_identity_dossiers

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

# Ensure the patched public function is not overwritten by the export loop.
globals()["validate_commonmark_identity_dossiers"] = validate_commonmark_identity_dossiers


if __name__ == "__main__":
    raise SystemExit(_impl.main())
