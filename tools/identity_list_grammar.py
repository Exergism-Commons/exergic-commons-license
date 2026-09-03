#!/usr/bin/env python3
"""Shared closed-world coordinator grammar for identity lists.

Keep list coordinator spellings centralized so State-dossier and Schedule completeness guards
cannot silently diverge. This module defines syntax only; callers remain responsible for
identity-span protection, role semantics, and fail-closed review behavior.
"""
from __future__ import annotations


# Keep this aligned with the repository's strong composite-connector semantics. In particular,
# ``plus``, ``together with``, and ``alongside`` must behave like the other explicit
# identity-list coordinators so a trailing member cannot disappear from State person or
# Schedule capacity-list completeness checks.
WORD_COORDINATOR_PATTERN = r"(?:and\s*/\s*or|and-or|and/or|as\s+well\s+as|together\s+with|alongside|plus|and|or)"
COORDINATOR_PATTERN = rf"(?:{WORD_COORDINATOR_PATTERN}|&)"
