#!/usr/bin/env python3
"""Pass 21 regressions for Schedule compatibility input and YAML alias hardening."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "render_schedule.py"
SPEC = importlib.util.spec_from_file_location("render_schedule_pass21", MODULE_PATH)
RENDERER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RENDERER)


class ScheduleCompatibilityPass21Tests(unittest.TestCase):
    def test_complete_input_set_includes_selection_controls_and_renderer_code(self):
        clause_sources = RENDERER.schedule_clause_source_paths()
        controls = RENDERER.schedule_renderer_control_paths()
        complete = RENDERER.schedule_compatibility_input_paths()

        self.assertTrue(set(clause_sources).issubset(complete))
        self.assertIn(RENDERER.REG / "states.yml", controls)
        self.assertIn(RENDERER.REG / "states.yml", complete)
        self.assertIn(Path(RENDERER.__file__).resolve(), controls)
        self.assertIn(Path(RENDERER.__file__).resolve(), complete)

        status_override = RENDERER.REG / "schedule-status-overrides.yml"
        if status_override.exists():
            self.assertIn(status_override, controls)
            self.assertIn(status_override, complete)

        for overlay in sorted(RENDERER.REG.glob("state-outcome-overrides*.yml")):
            self.assertIn(overlay, controls)
            self.assertIn(overlay, complete)

    def test_clause_only_evidence_cannot_authorize_complete_state(self):
        clause_sources = RENDERER.schedule_clause_source_paths()
        complete_inputs = RENDERER.schedule_compatibility_input_paths()
        old_bindings = [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": RENDERER.sha256(path),
            }
            for path in clause_sources
        ]

        with self.assertRaisesRegex(
            ValueError, "does not bind the exact renderer source set"
        ):
            RENDERER.assert_exact_source_bindings(
                old_bindings,
                complete_inputs,
                "Schedule compatibility evidence",
            )

    def test_compatibility_status_passes_complete_input_set_to_review_gate(self):
        captured = []
        original = RENDERER.validate_compatibility_review

        def capture(sources, target_license):
            captured.extend(sources)
            self.assertEqual(target_license, RENDERER.TARGET_LICENSE)
            return False

        try:
            RENDERER.validate_compatibility_review = capture
            RENDERER.compatibility_status()
        finally:
            RENDERER.validate_compatibility_review = original

        self.assertEqual(captured, RENDERER.schedule_compatibility_input_paths())

    def test_alias_reused_as_mapping_key_is_rejected(self):
        document = yaml.compose(
            "key_name: &k reviewed_at\n"
            "*k: 2026-08-15\n"
        )
        self.assertIsNotNone(document)
        with self.assertRaisesRegex(ValueError, "must not use YAML aliases"):
            RENDERER.validate_evidence_yaml_node(document)

    def test_alias_from_mapping_key_into_value_is_rejected(self):
        document = yaml.compose(
            "&k reviewer: compatibility-regression-test\n"
            "alias_probe: *k\n"
        )
        self.assertIsNotNone(document)
        with self.assertRaisesRegex(ValueError, "must not use YAML aliases"):
            RENDERER.validate_evidence_yaml_node(document)


if __name__ == "__main__":
    unittest.main()
