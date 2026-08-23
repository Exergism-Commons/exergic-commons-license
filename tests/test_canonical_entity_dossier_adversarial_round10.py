#!/usr/bin/env python3
"""Round-ten regressions for Markdown, SVG visibility, and visualModel anchoring."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import canonical_dossier_contract as contract  # noqa: E402
import check_visual_evidence_semantics_hardened as hardened  # noqa: E402
import check_visual_evidence_semantics_live as live  # noqa: E402


class StateContextRenderedMarkdownTests(unittest.TestCase):
    def _errors(self, body: str, live_code: str = "N") -> list[str]:
        return live.validate_live_state_context_text(
            body,
            "dossiers/organizations/EXAMPLE.md",
            "ORG-EXAMPLE",
            "USA",
            live_code,
            "No current ECL-relevant basis",
        )

    def test_unbold_stale_outcome_is_rejected(self) -> None:
        dossier = """# Example

## State governance context

The USA State dossier records S — Scoped restriction.
"""
        self.assertTrue(self._errors(dossier))

    def test_split_emphasis_stale_outcome_is_rejected(self) -> None:
        dossier = """# Example

## State governance context

The USA State dossier records **S** — Scoped restriction.
"""
        self.assertTrue(self._errors(dossier))

    def test_inline_code_stale_outcome_is_rejected(self) -> None:
        dossier = """# Example

## State governance context

The USA State dossier records `S — Scoped restriction`.
"""
        self.assertTrue(self._errors(dossier))

    def test_fake_heading_inside_fence_cannot_redirect_parser(self) -> None:
        dossier = """# Example

```md
## State governance context
S — Scoped restriction
```

## State governance context

The USA State dossier records N — No current ECL-relevant basis.
"""
        self.assertEqual([], self._errors(dossier))


class CanonicalMarkdownSurfaceTests(unittest.TestCase):
    def test_raw_html_escape_hatch_is_forbidden_for_every_canonical_dossier(self) -> None:
        text = """# Example

## State governance context

<div>The USA State dossier records S — Scoped restriction.</div>
"""
        errors = contract.validate_dossier_commonmark_surface(
            text, Path("dossiers/organizations/EXAMPLE.md")
        )
        self.assertTrue(errors)

    def test_plain_commonmark_surface_remains_valid(self) -> None:
        text = """# Example

## State governance context

The USA State dossier records N — No current ECL-relevant basis.
"""
        self.assertEqual(
            [],
            contract.validate_dossier_commonmark_surface(
                text, Path("dossiers/organizations/EXAMPLE.md")
            ),
        )


class FailClosedSvgVisibilityTests(unittest.TestCase):
    def _visible(self, body: str, viewbox: str = "0 0 100 100") -> str | None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.svg"
            path.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">'
                + body
                + "</svg>",
                encoding="utf-8",
            )
            return hardened.visible_svg_text(path)

    def test_zero_area_clip_fails_closed(self) -> None:
        body = (
            '<defs><clipPath id="c"><rect x="10" y="20" width="0" height="20"/></clipPath></defs>'
            '<text x="10" y="20" clip-path="url(#c)" font-size="12">REQUIRED</text>'
        )
        self.assertIsNone(self._visible(body))

    def test_tiny_semantic_text_fails_closed(self) -> None:
        self.assertIsNone(
            self._visible('<text x="10" y="20" font-size="0.001">REQUIRED</text>')
        )

    def test_transparent_semantic_text_fails_closed(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="transparent">REQUIRED</text>'
            )
        )

    def test_near_zero_opacity_fails_closed(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" opacity="0.001">REQUIRED</text>'
            )
        )

    def test_nested_opacity_is_multiplied_fail_closed(self) -> None:
        self.assertIsNone(
            self._visible(
                '<g opacity="0.1"><g opacity="0.1">'
                '<text x="10" y="20" font-size="12">REQUIRED</text>'
                '</g></g>'
            )
        )

    def test_transparent_stroke_only_text_fails_closed(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="none" '
                'stroke="transparent" stroke-width="1">REQUIRED</text>'
            )
        )

    def test_near_transparent_alpha_hex_fill_fails_closed(self) -> None:
        self.assertIsNone(
            self._visible(
                '<text x="10" y="20" font-size="12" fill="#00000001">REQUIRED</text>'
            )
        )

    def test_missing_viewbox_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<text x="10" y="20" font-size="12">REQUIRED</text></svg>',
                encoding="utf-8",
            )
            self.assertIsNone(hardened.visible_svg_text(path))


class LegacyVisualModelTextualAnchorTests(unittest.TestCase):
    DOSSIER = """# Example

## Identity scope

The Ombudsman accountability role of the example court.

## State governance context

The USA State dossier records N — No current ECL-relevant basis and is not inherited.

## Evidence record

The Ombudsman may ask the court to review a judgment under its review powers.

## Attribution and exclusions

This does not establish participation or culpability.

## Evidence gaps

No case-specific outcome is asserted.

## Sources

Rwanda Office of the Ombudsman — powers.

## Governance boundary

State context is not inherited and does not create culpability.
"""

    def test_anchored_legacy_visual_model_passes(self) -> None:
        model = {
            "source": "Ombudsman powers",
            "proposition": "Ombudsman review power",
            "boundary": "No State N inheritance",
        }
        self.assertEqual(
            [],
            live.validate_visual_model_textual_anchor(
                self.DOSSIER,
                "dossiers/institutions/EXAMPLE.md",
                "INSTITUTION-EXAMPLE",
                1,
                model,
            ),
        )

    def test_unrelated_stronger_visual_model_is_rejected(self) -> None:
        model = {
            "source": "Ombudsman powers",
            "proposition": "Missile command culpability",
            "boundary": "No State N inheritance",
        }
        errors = live.validate_visual_model_textual_anchor(
            self.DOSSIER,
            "dossiers/institutions/EXAMPLE.md",
            "INSTITUTION-EXAMPLE",
            1,
            model,
        )
        self.assertTrue(any("visualModel.proposition is not textually anchored" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
