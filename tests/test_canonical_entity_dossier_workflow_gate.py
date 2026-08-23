from __future__ import annotations

import ast
import fnmatch
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

WORKFLOWS = (
    ".github/workflows/canonical-entity-dossiers.yml",
    ".github/workflows/living-update-integrity.yml",
)
PYTHON_TOOL_RE = re.compile(r"\bpython(?:3)?\s+(tools/[A-Za-z0-9_./-]+\.py)\b")


def _workflow_python_entrypoints(workflow_text: str) -> tuple[str, ...]:
    """Discover repository tools executed in the simple direct-python form."""
    return tuple(sorted(set(PYTHON_TOOL_RE.findall(workflow_text))))


def _local_tool_dependencies(entrypoints: tuple[str, ...]) -> set[str]:
    """Return the recursive tools/*.py import closure for discovered entrypoints."""
    pending = [ROOT / path for path in entrypoints]
    seen: set[Path] = set()

    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names.add(node.module.split(".", 1)[0])

        for module_name in module_names:
            candidate = TOOLS / f"{module_name}.py"
            if candidate.is_file() and candidate not in seen:
                pending.append(candidate)

    return {path.relative_to(ROOT).as_posix() for path in seen}


def _event_paths(workflow_text: str, event: str) -> set[str]:
    """Extract one top-level Actions event's paths list without a YAML dependency."""
    lines = workflow_text.splitlines()
    event_marker = f"  {event}:"
    try:
        start = lines.index(event_marker) + 1
    except ValueError as exc:
        raise AssertionError(f"workflow is missing {event_marker.strip()!r}") from exc

    end = len(lines)
    for index in range(start, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            end = index
            break

    block = lines[start:end]
    try:
        paths_index = block.index("    paths:") + 1
    except ValueError as exc:
        raise AssertionError(f"workflow event {event!r} is missing paths") from exc

    paths: set[str] = set()
    for line in block[paths_index:]:
        if not line.startswith("      - "):
            if line.strip():
                break
            continue
        value = line[len("      - ") :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        paths.add(value)
    return paths


def _covered(path: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


class CanonicalWorkflowGateTests(unittest.TestCase):
    def test_every_tools_change_unconditionally_triggers_normative_workflows(self) -> None:
        """Do not depend on reconstructing Python command/import syntax to trigger CI."""
        probes = (
            "tools/__future_helper__.py",
            "tools/nested/__future_helper__.py",
            "tools/check_visual_evidence_semantics_hardened.py",
        )
        for workflow_rel in WORKFLOWS:
            workflow_text = (ROOT / workflow_rel).read_text(encoding="utf-8")
            for event in ("push", "pull_request"):
                patterns = _event_paths(workflow_text, event)
                self.assertIn(
                    "tools/**",
                    patterns,
                    f"{workflow_rel} {event}.paths must contain the unconditional tools/** guard",
                )
                for probe in probes:
                    self.assertTrue(
                        _covered(probe, patterns),
                        f"{workflow_rel} {event}.paths does not cover arbitrary tool {probe}",
                    )

    def test_discovered_executed_python_tools_and_imports_remain_ci_path_covered(self) -> None:
        """Retain recursive discovery as defense in depth, not as the sole trigger guard."""
        for workflow_rel in WORKFLOWS:
            with self.subTest(workflow=workflow_rel):
                workflow_text = (ROOT / workflow_rel).read_text(encoding="utf-8")
                entrypoints = _workflow_python_entrypoints(workflow_text)
                self.assertTrue(
                    entrypoints,
                    f"{workflow_rel}: no directly executed tools/*.py entrypoints discovered",
                )

                dependencies = _local_tool_dependencies(entrypoints)
                self.assertTrue(dependencies, workflow_rel)
                self.assertTrue(set(entrypoints) <= dependencies, workflow_rel)

                for event in ("push", "pull_request"):
                    patterns = _event_paths(workflow_text, event)
                    missing = sorted(
                        path for path in dependencies if not _covered(path, patterns)
                    )
                    self.assertEqual(
                        [],
                        missing,
                        f"{workflow_rel} {event}.paths does not cover executed Python tools/imports: {missing}",
                    )


if __name__ == "__main__":
    unittest.main()
