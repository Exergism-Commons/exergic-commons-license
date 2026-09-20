#!/usr/bin/env python3
"""Regressions for the exhaustive P2 review of canonical entity dossiers."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import canonical_markdown as markdown  # noqa: E402
import check_canonical_entity_dossiers as dossiers  # noqa: E402
import check_visual_evidence_semantics_hardened as hardened  # noqa: E402
import check_visual_evidence_semantics_live as live  # noqa: E402
import dossier_svg_metrics as metrics  # noqa: E402
import render_dossier_visuals as renderer  # noqa: E402
import strict_json  # noqa: E402


class CommonMarkSurfaceTests(unittest.TestCase):
    def test_formatted_equivalent_h2_is_same_identity(self) -> None:
        surface = markdown.parse_surface("## State governance context\nOne.\n\n## State *governance* context\nTwo.\n")
        self.assertEqual(surface.section_counts.get("State governance context"), 2)

    def test_image_alt_does_not_supply_visible_prose(self) -> None:
        self.assertEqual(markdown.section_visible_text("## Evidence record\n\n![Only alt](x.svg)\n", "Evidence record"), "")

    def test_nested_h2_is_not_canonical_section(self) -> None:
        surface = markdown.parse_surface("## Evidence record\n\n- item\n  ## Sources\n  nested\n")
        self.assertEqual(surface.section_counts.get("Sources", 0), 0)

    def test_top_level_h1_closes_h2_section(self) -> None:
        self.assertEqual(markdown.section_visible_text("## Evidence record\n\n# Other\n\nOutside.\n", "Evidence record"), "")

    def test_escaped_alt_uses_commonmark_parser(self) -> None:
        self.assertEqual(markdown.image_references(r"![State context \[audited\]](../assets/generated/X-status.svg)"), [("State context [audited]", "../assets/generated/X-status.svg")])


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_member_is_rejected_at_nested_depth(self) -> None:
        with self.assertRaises(strict_json.DuplicateJSONMemberError):
            strict_json.loads('{"outer":{"id":"A","id":"B"}}', source="fixture")


class SvgSurfaceTests(unittest.TestCase):
    def _visible(self, body: str, *, name: str = "x.svg", width: str = "", height: str = "") -> str | None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            attrs = ' viewBox="0 0 100 100"'
            if width:
                attrs += f' width="{width}"'
            if height:
                attrs += f' height="{height}"'
            path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"{attrs}>' + body + "</svg>", encoding="utf-8")
            return hardened.visible_svg_text(path)

    def test_inherited_text_anchor_is_rejected(self) -> None:
        self.assertIsNone(self._visible('<g text-anchor="end"><text x="20" y="30" font-size="12">REQUIRED</text></g>'))

    def test_bidi_override_is_rejected(self) -> None:
        self.assertIsNone(self._visible('<text x="10" y="30" font-size="12">\u202eREQUIRED\u202c</text>'))

    def test_nonrendering_clip_geometry_is_rejected(self) -> None:
        self.assertIsNone(self._visible('<defs><clipPath id="c"><rect x="0" y="0" width="100" height="100" display="none"/></clipPath></defs><text x="10" y="30" font-size="12" clip-path="url(#c)">REQUIRED</text>'))

    def test_duplicate_svg_ids_are_rejected(self) -> None:
        self.assertIsNone(self._visible('<defs><clipPath id="c"><rect x="0" y="0" width="20" height="20"/></clipPath><clipPath id="c"><rect x="0" y="0" width="100" height="100"/></clipPath></defs><text x="10" y="15" font-size="8" clip-path="url(#c)">X</text>'))

    def test_nested_svg_viewport_is_rejected(self) -> None:
        self.assertIsNone(self._visible('<svg x="90" y="90" width="1" height="1"><text x="10" y="30">REQUIRED</text></svg>'))

    def test_vertical_glyph_extent_must_fit_clip(self) -> None:
        self.assertIsNone(self._visible('<defs><clipPath id="c"><rect x="0" y="20" width="100" height="20"/></clipPath></defs><text x="10" y="21" font-size="12" clip-path="url(#c)">REQUIRED</text>'))

    def test_canonical_status_zero_viewport_is_rejected(self) -> None:
        self.assertIsNone(self._visible('<rect width="100" height="100" fill="#FFFFFF"/><text x="10" y="30" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="#101828">X</text>', name="X-status.svg", width="0", height="300"))

    def test_cjk_width_is_conservative(self) -> None:
        self.assertGreaterEqual(metrics.glyph_width("界", 12), 12)


class StateSemanticTests(unittest.TestCase):
    def test_state_identity_mismatch_is_rejected(self) -> None:
        errors = live.validate_live_state_context_text("## State governance context\n\nThe USA State dossier records S — Scoped restriction.\n", "x.md", "ORG-X", "ESP", "S", "Scoped restriction")
        self.assertTrue(any("USA State dossier" in error for error in errors), errors)

    def test_code_and_canonical_label_must_agree(self) -> None:
        errors = live.validate_live_state_context_text("## State governance context\n\nThe ESP State dossier records S — No restriction.\n", "x.md", "ORG-X", "ESP", "S", "Scoped restriction")
        self.assertTrue(any("code/label contradiction" in error for error in errors), errors)

    def test_color_and_state_must_agree(self) -> None:
        errors = live.validate_live_state_context_text("## State governance context\n\nThe ESP State dossier records S. The red S is context only.\n", "x.md", "ORG-X", "ESP", "S", "Scoped restriction")
        self.assertTrue(any("palette prose contradiction" in error for error in errors), errors)


class PaletteAndRendererTests(unittest.TestCase):
    def test_all_palette_foregrounds_meet_45_contrast(self) -> None:
        palette = json.loads((ROOT / "knowledge/generated/dossier-visual-palette-v1.json").read_text(encoding="utf-8"))
        for code, item in palette["states"].items():
            with self.subTest(code=code):
                self.assertGreaterEqual(metrics.contrast_ratio(item["foreground"], item["hex"]), 4.5)

    def test_v40_normalization_preserves_visible_name(self) -> None:
        entity = {"id": "ORG-X", "name": "Current Name", "_normalized_visual_v40": True, "visualModel": {}}
        self.assertEqual(renderer.normalized(entity)["name"], "Current Name")

    def test_palette_semantics_are_fully_pinned(self) -> None:
        palette = json.loads((ROOT / "knowledge/generated/dossier-visual-palette-v1.json").read_text(encoding="utf-8"))
        for key, expected in dossiers.EXPECTED_STATE_VOCABULARY.items():
            self.assertEqual(palette["states"][key], expected)


class WorkflowReachabilityTests(unittest.TestCase):
    def test_full_pipeline_uses_actual_hardened_entrypoints(self) -> None:
        text = (ROOT / "tests/test_canonical_entity_dossier_full_pipeline_e2e.py").read_text(encoding="utf-8")
        self.assertIn("check_canonical_entity_contract_round6.py", text)
        self.assertIn("check_visual_evidence_semantics_live.py", text)

    def test_jsonld_semantics_is_executed_by_workflow(self) -> None:
        text = (ROOT / ".github/workflows/canonical-entity-dossiers.yml").read_text(encoding="utf-8")
        self.assertIn("tests.test_jsonld_context_semantics", text)
        self.assertIn("check_canonical_json_strictness.py", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
