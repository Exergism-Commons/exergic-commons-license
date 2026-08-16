#!/usr/bin/env python3
"""Pass 22 regressions for Schedule timestamp and parser-environment hardening."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "render_schedule.py"
SPEC = importlib.util.spec_from_file_location("render_schedule_pass22", MODULE_PATH)
RENDERER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RENDERER)


class ScheduleCompatibilityPass22Tests(unittest.TestCase):
    def test_rfc3339_rejects_unicode_decimal_digit_confusables(self):
        malformed = [
            "2026-08-15T0١:0٢:0٣Z",
            "2026-08-15T00:00:00+0١:0٢",
            "2026-08-15T00:00:00.١Z",
        ]
        for value in malformed:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError, "valid ISO date or RFC 3339 timestamp"
                ):
                    RENDERER.validate_reviewed_at(value)

    def test_rfc3339_accepts_ascii_clock_offset_and_fraction(self):
        for value in (
            "2026-08-15T01:02:03Z",
            "2026-08-15T01:02:03+01:02",
            "2026-08-15T01:02:03.123456Z",
        ):
            with self.subTest(value=value):
                RENDERER.validate_reviewed_at(value)

    def test_renderer_dependency_pin_is_exact_and_hash_bound(self):
        self.assertEqual(RENDERER.PINNED_PYYAML_VERSION, "6.0.3")
        self.assertEqual(RENDERER.yaml.__version__, RENDERER.PINNED_PYYAML_VERSION)
        self.assertEqual(
            RENDERER.SCHEDULE_REQUIREMENTS.read_text(encoding="utf-8"),
            "PyYAML==6.0.3\n",
        )
        self.assertIn(
            RENDERER.SCHEDULE_REQUIREMENTS,
            RENDERER.schedule_renderer_control_paths(),
        )
        self.assertIn(
            RENDERER.SCHEDULE_REQUIREMENTS,
            RENDERER.schedule_compatibility_input_paths(),
        )

    def test_renderer_rejects_unreviewed_pyyaml_version(self):
        original = RENDERER.yaml.__version__
        try:
            RENDERER.yaml.__version__ = "0.0.0-pass22-probe"
            with self.assertRaisesRegex(ValueError, "requires PyYAML 6.0.3"):
                RENDERER.validate_renderer_environment()
        finally:
            RENDERER.yaml.__version__ = original

    def test_schedule_workflows_install_the_pinned_environment_and_run_pass22(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "tools/schedule-requirements.txt"', text)
            self.assertIn('- "tools/test_schedule_compatibility_pass22.py"', text)
            self.assertIn("-r tools/schedule-requirements.txt", text)
            self.assertIn("python -I tools/test_schedule_compatibility_pass22.py", text)
            self.assertNotIn("pip install --disable-pip-version-check PyYAML", text)


if __name__ == "__main__":
    unittest.main()
