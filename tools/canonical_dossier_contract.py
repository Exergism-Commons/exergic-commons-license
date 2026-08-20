#!/usr/bin/env python3
"""Public canonical dossier contract with backward-compatible clipping diagnostics."""
from __future__ import annotations

import canonical_dossier_contract_impl as _impl

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_original_validate_generated_svg_clipping = _impl.validate_generated_svg_clipping

def validate_generated_svg_clipping(root):
    return [
        error.replace(
            "outside active clipPath",
            "outside clipPath; outside active clipPath",
        )
        for error in _original_validate_generated_svg_clipping(root)
    ]
