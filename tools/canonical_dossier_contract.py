#!/usr/bin/env python3
"""Public canonical dossier contract with backward-compatible clipping diagnostics."""
from __future__ import annotations

from markdown_it import MarkdownIt

import canonical_dossier_contract_impl as _impl

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_original_validate_generated_svg_clipping = _impl.validate_generated_svg_clipping
_original_embedded_resource_targets = _impl.embedded_resource_targets


def commonmark_image_targets(text: str) -> list[str]:
    """Return every image destination that CommonMark actually renders."""
    targets: list[str] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type != "image":
                continue
            target = (child.attrGet("src") or "").strip()
            if target:
                targets.append(target)
    return targets


def embedded_resource_targets(text: str) -> list[str]:
    """Union legacy raw-syntax discovery with rendered CommonMark image destinations."""
    targets = list(_original_embedded_resource_targets(text))
    targets.extend(commonmark_image_targets(text))
    return list(dict.fromkeys(targets))


# Functions defined in the implementation module resolve this global at call time.
# Patch the implementation namespace as well as the public wrapper so every caller,
# including validate_universe(), receives the rendered CommonMark surface.
_impl.embedded_resource_targets = embedded_resource_targets


def validate_generated_svg_clipping(root):
    return [
        error.replace(
            "outside active clipPath",
            "outside clipPath; outside active clipPath",
        )
        for error in _original_validate_generated_svg_clipping(root)
    ]
