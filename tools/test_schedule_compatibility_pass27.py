#!/usr/bin/env python3
"""CODEX-0.3-045 regressions for spoofed repository-root authentication."""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RENDERER = TOOLS / "render_schedule.py"


class BootstrapImplementationAuthenticationRegressions(unittest.TestCase):
    def run_renderer(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", "-S", str(path), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def create_spoofed_repository(root: Path) -> None:
        for relative in (
            "LICENSE",
            "registry/states.yml",
            "versions/licenses/ECL-0.3-DRAFT.md",
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("spoofed sentinel\n", encoding="utf-8")

    def test_complete_spoofed_sentinel_root_cannot_execute_attacker_impl(self):
        fake_root = ROOT / "build" / "pass27-spoof-root"
        fake_tools = fake_root / "tools"
        shutil.rmtree(fake_root, ignore_errors=True)
        fake_tools.mkdir(parents=True)
        wrapper_copy = fake_tools / "render_schedule.py"
        marker = "CODEX_PASS27_SPOOFED_IMPL_EXECUTED"
        try:
            shutil.copy2(RENDERER, wrapper_copy)
            self.create_spoofed_repository(fake_root)
            (fake_tools / "render_schedule_impl.py").write_text(
                f'raise RuntimeError("{marker}")\n', encoding="utf-8"
            )

            result = self.run_renderer(wrapper_copy)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "implementation bytes do not match the reviewed bootstrap trust anchor",
                result.stderr,
            )
            self.assertNotIn(marker, result.stderr)
        finally:
            shutil.rmtree(fake_root, ignore_errors=True)

    def test_canonical_repository_wrapper_still_executes(self):
        result = self.run_renderer(RENDERER)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_authenticates_and_executes_same_impl_bytes(self):
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("_EXPECTED_IMPL_GIT_BLOB_SHA1", source)
        self.assertIn('with open(_IMPL_PATH, "rb") as _handle:', source)
        self.assertIn("_hashlib.sha1(_impl_blob_frame).hexdigest()", source)
        self.assertIn("_source = _impl_bytes.decode(\"utf-8\")", source)
        self.assertEqual(source.count("open(_IMPL_PATH"), 1)

    def test_schedule_workflows_run_pass27_regression(self):
        for relative in (
            ".github/workflows/schedule-integrity.yml",
            ".github/workflows/schedule-release-readiness.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn('- "tools/test_schedule_compatibility_pass27.py"', text)
            self.assertIn("python -I tools/test_schedule_compatibility_pass27.py", text)
            self.assertIn("python -I -S tools/render_schedule.py --validate-only", text)


if __name__ == "__main__":
    unittest.main()
