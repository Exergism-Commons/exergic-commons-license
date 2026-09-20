#!/usr/bin/env python3
"""Shared conservative text metrics and color contrast for canonical dossier SVGs."""
from __future__ import annotations

import re
import unicodedata


def glyph_width(ch: str, font_size: float) -> float:
    category = unicodedata.category(ch)
    if unicodedata.combining(ch) or category in {"Cc", "Cf"}:
        return 0.0
    if ch in "\r\n\t":
        return 0.0
    if ch in {" ", "\u00a0"}:
        factor = 0.32
    elif ch in {"\u2002", "\u2007"}:
        factor = 0.50
    elif ch in {"\u2003", "\u3000"}:
        factor = 1.00
    elif ch in {"\u2009", "\u202f"}:
        factor = 0.30
    elif unicodedata.east_asian_width(ch) in {"W", "F"} or category in {"So", "Sk"}:
        factor = 1.00
    elif ch in "il.,'|!:;" or ch == chr(96):
        factor = 0.32
    elif ch in "mwMW@#%&":
        factor = 0.90
    elif ch.isupper():
        factor = 0.72
    elif ch.isdigit():
        factor = 0.62
    else:
        factor = 0.60
    return font_size * factor


def measured_width(text: str, font_size: float) -> float:
    return sum(glyph_width(ch, font_size) for ch in text)


def _channel(value: int) -> float:
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(value: str) -> float:
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
        raise ValueError(f"unsupported canonical color {value!r}")
    r, g, b = (int(value[index:index + 2], 16) for index in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    a, b = relative_luminance(foreground), relative_luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)
