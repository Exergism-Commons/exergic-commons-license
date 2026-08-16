#!/usr/bin/env python3
"""CODEX-0.3-042 regressions for root-path and alternate-invocation shadowing."""

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


class BootstrapIsolationRegressions(unittest.TestCase):
    def run_process(self, args: list[str], *, env=None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_executable_rejects_nonisolated_python_before_renderer_imports(self):
        result = self.run_process([sys.executable, str(RENDERER), "--validate-only"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires isolated Python", result.stderr)

    def test_executable_rejects_isolated_mode_without_site_suppression(self):
        result = self.run_process(
            [sys.executable, "-I", str(RENDERER), "--validate-only"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires site-disabled isolation", result.stderr)

    def test_package_style_module_invocation_fails_closed(self):
        result = self.run_process(
            [sys.executable, "-m", "tools.render_schedule", "--validate-only"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires isolated Python", result.stderr)

    def test_isolated_site_disabled_run_ignores_root_and_pythonpath_shadows(self):
        argparse_shadow = ROOT / "argparse.py"
        yaml_shadow = ROOT / "yaml"
        self.assertFalse(argparse_shadow.exists(), "test refuses to overwrite argparse.py")
        self.assertFalse(yaml_shadow.exists(), "test refuses to overwrite root yaml package")
        marker_argparse = "CODEX_PASS24_ROOT_ARGPARSE_SHADOW"
        marker_yaml = "CODEX_PASS24_ROOT_YAML_SHADOW"
        try:
            argparse_shadow.write_text(
                f'raise RuntimeError("{marker_argparse}")\n', encoding="utf-8"
            )
            yaml_shadow.mkdir()
            (yaml_shadow / "__init__.py").write_text(
                f'raise RuntimeError("{marker_yaml}")\n', encoding="utf-8"
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            result = self.run_process(
                [sys.executable, "-I", "-S", str(RENDERER), "--validate-only"],
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(marker_argparse, result.stderr)
            self.assertNotIn(marker_yaml, result.stderr)
        finally:
            argparse_shadow.unlink(missing_ok=True)
            shutil.rmtree(yaml_shadow, ignore_errors=True)
            pycache = ROOT / "__pycache__"
            if pycache.exists():
                for cached in pycache.glob("argparse.*.pyc"):
                    cached.unlink(missing_ok=True)

    def test_schedule_workflows_enforce_isolated_bootstrap_invocation(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "tools/test_schedule_compatibility_pass24.py"', text)
            self.assertIn("python -I tools/test_schedule_compatibility_pass24.py", text)
            self.assertIn("python -I -S tools/render_schedule.py --validate-only", text)
            self.assertIn("python -I -S tools/render_schedule.py --output", text)
            self.assertNotIn("run: python tools/render_schedule.py --validate-only", text)
            self.assertNotIn("run: python tools/render_schedule.py --output", text)


if __name__ == "__main__":
    unittest.main()
