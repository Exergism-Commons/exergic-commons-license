#!/usr/bin/env python3
"""CODEX-0.3-043 regressions for bootstrap filesystem aliases."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RENDERER = TOOLS / "render_schedule.py"


class BootstrapFilesystemAliasRegressions(unittest.TestCase):
    def run_renderer(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", str(path), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_symlink_wrapper_cannot_redirect_implementation_selection(self):
        alt = ROOT / "build" / "pass25-symlink"
        shutil.rmtree(alt, ignore_errors=True)
        alt.mkdir(parents=True)
        wrapper_alias = alt / "render_schedule.py"
        marker = "CODEX_PASS25_SYMLINK_IMPL_EXECUTED"
        try:
            wrapper_alias.symlink_to(RENDERER)
            (alt / "render_schedule_impl.py").write_text(
                f'raise RuntimeError("{marker}")\n', encoding="utf-8"
            )
            result = self.run_renderer(wrapper_alias)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refuses symlink invocation", result.stderr)
            self.assertNotIn(marker, result.stderr)
        finally:
            shutil.rmtree(alt, ignore_errors=True)

    def test_hardlink_wrapper_alias_is_rejected_before_sibling_open(self):
        alt = ROOT / "build" / "pass25-hardlink"
        shutil.rmtree(alt, ignore_errors=True)
        alt.mkdir(parents=True)
        wrapper_alias = alt / "render_schedule.py"
        marker = "CODEX_PASS25_HARDLINK_IMPL_EXECUTED"
        try:
            try:
                os.link(RENDERER, wrapper_alias)
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable on test filesystem: {exc}")
            (alt / "render_schedule_impl.py").write_text(
                f'raise RuntimeError("{marker}")\n', encoding="utf-8"
            )
            result = self.run_renderer(wrapper_alias)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refuses hardlink aliases", result.stderr)
            self.assertNotIn(marker, result.stderr)
        finally:
            shutil.rmtree(alt, ignore_errors=True)

    def test_canonical_wrapper_still_executes_reviewed_implementation(self):
        result = self.run_renderer(RENDERER)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_schedule_workflows_run_pass25_regression(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "tools/test_schedule_compatibility_pass25.py"', text)
            self.assertIn("python -I tools/test_schedule_compatibility_pass25.py", text)
            self.assertIn("python -I -S tools/render_schedule.py --validate-only", text)


if __name__ == "__main__":
    unittest.main()
