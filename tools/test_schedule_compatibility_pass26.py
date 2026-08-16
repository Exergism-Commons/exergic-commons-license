#!/usr/bin/env python3
"""CODEX-0.3-044 regressions for copied/bootstrap-replica redirection."""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RENDERER = TOOLS / "render_schedule.py"


class BootstrapRepositoryIdentityRegressions(unittest.TestCase):
    def run_renderer(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", str(path), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_literal_wrapper_copy_cannot_select_attacker_sibling(self):
        alt = ROOT / "build" / "pass26-copy"
        shutil.rmtree(alt, ignore_errors=True)
        alt.mkdir(parents=True)
        wrapper_copy = alt / "render_schedule.py"
        marker = "CODEX_PASS26_COPIED_IMPL_EXECUTED"
        try:
            shutil.copy2(RENDERER, wrapper_copy)
            (alt / "render_schedule_impl.py").write_text(
                f'raise RuntimeError("{marker}")\n', encoding="utf-8"
            )
            result = self.run_renderer(wrapper_copy)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refuses bootstrap copies", result.stderr)
            self.assertNotIn(marker, result.stderr)
        finally:
            shutil.rmtree(alt, ignore_errors=True)

    def test_nested_tools_shaped_copy_is_not_treated_as_repository_slot(self):
        alt_root = ROOT / "build" / "pass26-fake-root"
        alt_tools = alt_root / "tools"
        shutil.rmtree(alt_root, ignore_errors=True)
        alt_tools.mkdir(parents=True)
        wrapper_copy = alt_tools / "render_schedule.py"
        marker = "CODEX_PASS26_FAKE_ROOT_IMPL_EXECUTED"
        try:
            shutil.copy2(RENDERER, wrapper_copy)
            (alt_tools / "render_schedule_impl.py").write_text(
                f'raise RuntimeError("{marker}")\n', encoding="utf-8"
            )
            result = self.run_renderer(wrapper_copy)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refuses bootstrap copies", result.stderr)
            self.assertNotIn(marker, result.stderr)
        finally:
            shutil.rmtree(alt_root, ignore_errors=True)

    def test_canonical_repository_wrapper_still_executes(self):
        result = self.run_renderer(RENDERER)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_schedule_workflows_run_pass26_regression(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "tools/test_schedule_compatibility_pass26.py"', text)
            self.assertIn("python -I tools/test_schedule_compatibility_pass26.py", text)
            self.assertIn("python -I -S tools/render_schedule.py --validate-only", text)


if __name__ == "__main__":
    unittest.main()
