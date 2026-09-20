#!/usr/bin/env python3
"""Strict JSON helpers that reject duplicate object member names at any depth."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DuplicateJSONMemberError(ValueError):
    pass


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONMemberError(f"duplicate JSON object member {key!r}")
        result[key] = value
    return result


def loads(text: str, *, source: str = "<json>") -> Any:
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except DuplicateJSONMemberError as exc:
        raise DuplicateJSONMemberError(f"{source}: {exc}") from exc


def load(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"), source=str(path))
