#!/usr/bin/env python3
"""CODEX-0.3-041 regressions for repository-local import shadowing."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RENDERER = TOOLS / "render_schedule.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_schedule_pass23", RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ImportShadowingRegressions(unittest.TestCase):
    def run_renderer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RENDERER), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_hashlib_sibling_cannot_shadow_stdlib(self):
        shadow = TOOLS / "hashlib.py"
        self.assertFalse(shadow.exists(), "test refuses to overwrite an existing tools/hashlib.py")
        try:
            shadow.write_text(
                'raise RuntimeError("repository-local hashlib shadow was imported")\n',
                encoding="utf-8",
            )
            result = self.run_renderer()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("repository-local hashlib shadow was imported", result.stderr)
        finally:
            shadow.unlink(missing_ok=True)
            pycache = TOOLS / "__pycache__"
            if pycache.exists():
                for cached in pycache.glob("hashlib.*.pyc"):
                    cached.unlink(missing_ok=True)

    def test_yaml_sibling_package_cannot_shadow_pinned_pyyaml(self):
        shadow_dir = TOOLS / "yaml"
        self.assertFalse(shadow_dir.exists(), "test refuses to overwrite an existing tools/yaml package")
        try:
            shadow_dir.mkdir()
            (shadow_dir / "__init__.py").write_text(
                'raise RuntimeError("repository-local yaml shadow was imported")\n',
                encoding="utf-8",
            )
            result = self.run_renderer()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("repository-local yaml shadow was imported", result.stderr)
        finally:
            shutil.rmtree(shadow_dir, ignore_errors=True)

    def test_compatibility_evidence_binds_bootstrap_and_implementation(self):
        renderer = load_renderer()
        bound = {
            str(path.resolve().relative_to(ROOT))
            for path in renderer.schedule_renderer_control_paths()
        }
        self.assertIn("tools/render_schedule.py", bound)
        self.assertIn("tools/render_schedule_impl.py", bound)


if __name__ == "__main__":
    unittest.main()
