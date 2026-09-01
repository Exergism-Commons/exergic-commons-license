#!/usr/bin/env python3
"""Shared closed-world coordinator grammar for identity lists.

Keep list coordinator spellings centralized so State-dossier and Schedule completeness guards
cannot silently diverge. This module defines syntax only; callers remain responsible for
identity-span protection, role semantics, and fail-closed review behavior.
"""
from __future__ import annotations


WORD_COORDINATOR_PATTERN = r"(?:and\s*/\s*or|and-or|and/or|as\s+well\s+as|and|or)"
COORDINATOR_PATTERN = rf"(?:{WORD_COORDINATOR_PATTERN}|&)"
