#!/usr/bin/env python3
"""Round-nine regression for live State-context prose coherence."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_visual_evidence_semantics_live as live_semantics  # noqa: E402


class CanonicalRoundNineTests(unittest.TestCase):
    def test_stale_explicit_state_outcome_in_markdown_is_rejected(self) -> None:
        dossier = """# Example

## State governance context

The canonical `USA` State dossier records **S — Scoped restriction**. That State status is context only.
"""
        errors = live_semantics.validate_live_state_context_text(
            dossier,
            "dossiers/organizations/EXAMPLE.md",
            "ORG-EXAMPLE",
            "USA",
            "N",
            "No current ECL-relevant basis",
        )
        self.assertTrue(any("text is stale" in error and "S" in error and "N" in error for error in errors), errors)

    def test_matching_explicit_state_outcome_is_accepted(self) -> None:
        dossier = """# Example

## State governance context

The canonical `USA` State dossier records **S — Scoped restriction**. That State status is context only.
"""
        self.assertEqual(
            [],
            live_semantics.validate_live_state_context_text(
                dossier,
                "dossiers/organizations/EXAMPLE.md",
                "ORG-EXAMPLE",
                "USA",
                "S",
                "Scoped restriction",
            ),
        )

    def test_outcome_neutral_state_context_prose_is_future_proof(self) -> None:
        dossier = """# Example

## State governance context

The canonical `USA` State dossier supplies the live governance context shown in the status card below. That State status is context only and is not inherited.
"""
        self.assertEqual(
            [],
            live_semantics.validate_live_state_context_text(
                dossier,
                "dossiers/organizations/EXAMPLE.md",
                "ORG-EXAMPLE",
                "USA",
                "N",
                "No current ECL-relevant basis",
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
