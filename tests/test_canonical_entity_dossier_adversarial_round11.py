#!/usr/bin/env python3
"""Round-eleven regressions for fail-closed CommonMark and SVG semantic surfaces."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import canonical_dossier_contract as contract  # noqa: E402
import check_visual_evidence_semantics_hardened as hardened  # noqa: E402


class CanonicalCommonMarkAmbiguityTests(unittest.TestCase):
    def test_duplicate_state_context_sections_fail_closed(self) -> None:
        text = """# Example

## State governance context

Outcome-neutral first section.

## Evidence record

Evidence.

## State governance context

The USA State dossier records S — Scoped restriction.
"""
        errors = contract.validate_dossier_commonmark_surface(
            text, Path("dossiers/organizations/EXAMPLE.md")
        )
        self.assertTrue(any("duplicate CommonMark H2" in error for error in errors), errors)

    def test_raw_html_block_fails_closed(self) -> None:
        text = """# Example

## State governance context

<div>The USA State dossier records S — Scoped restriction.</div>
"""
        errors = contract.validate_dossier_commonmark_surface(
            text, Path("dossiers/organizations/EXAMPLE.md")
        )
        self.assertTrue(any("raw HTML is forbidden" in error for error in errors), errors)

    def test_unique_plain_commonmark_sections_pass(self) -> None:
        text = """# Example

## State governance context

Outcome-neutral context.

## Evidence record

Evidence.
"""
        self.assertEqual(
            [],
            contract.validate_dossier_commonmark_surface(
                text, Path("dossiers/organizations/EXAMPLE.md")
            ),
        )


class StrictSvgSemanticSurfaceTests(unittest.TestCase):
    def _visible(self, body: str) -> str | None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                + body
                + "</svg>",
                encoding="utf-8",
            )
            return hardened.visible_svg_text(path)

    def test_inline_style_surface_is_rejected(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="#101828" '
                'style="opacity:0.001">REQUIRED</text>'
            )
        )

    def test_textlength_collapse_is_rejected(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="#101828" '
                'textLength="0.001" lengthAdjust="spacingAndGlyphs">REQUIRED</text>'
            )
        )

    def test_nested_opacity_is_multiplicative(self) -> None:
        self.assertIsNone(
            self._visible(
                '<g opacity="0.1"><g opacity="0.1">'
                '<text x="10" y="20" font-size="12" fill="#101828">REQUIRED</text>'
                '</g></g>'
            )
        )

    def test_stroke_only_semantics_do_not_count(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="none" '
                'stroke="#101828">REQUIRED</text>'
            )
        )

    def test_renderer_style_text_remains_visible(self) -> None:
        self.assertEqual(
            "REQUIRED",
            self._visible(
                '<text x="10" y="20" font-family="Arial, Helvetica, sans-serif" '
                'font-size="12" font-weight="700" fill="#101828">REQUIRED</text>'
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
