#!/usr/bin/env python3
"""One CommonMark interpretation for canonical dossier structure and resources."""
from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt


def normalized(value: str) -> str:
    return " ".join(value.split())


def body_without_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    return text[end + 5 :] if end >= 0 else text


def image_alt_text(token) -> str:
    if getattr(token, "children", None):
        pieces: list[str] = []
        for child in token.children or []:
            if child.type in {"text", "code_inline"}:
                pieces.append(child.content)
            elif child.type in {"softbreak", "hardbreak"}:
                pieces.append(" ")
        if pieces:
            return normalized("".join(pieces))
    return normalized(token.content)


def rendered_inline_text(token, *, include_images: bool = False, include_code: bool = True) -> str:
    if not token.children:
        return normalized(token.content)
    pieces: list[str] = []
    for child in token.children:
        if child.type == "text":
            pieces.append(child.content)
        elif child.type == "code_inline" and include_code:
            pieces.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            pieces.append(" ")
        elif child.type == "image" and include_images:
            pieces.append(image_alt_text(child))
    return normalized("".join(pieces))


@dataclass
class MarkdownSurface:
    tokens: list
    sections: dict[str, list]
    section_counts: dict[str, int]
    h2_titles: list[str]
    images: list[tuple[str, str]]


def parse_surface(source: str) -> MarkdownSurface:
    tokens = MarkdownIt("commonmark").parse(body_without_frontmatter(source))
    sections: dict[str, list] = {}
    counts: dict[str, int] = {}
    h2_titles: list[str] = []
    images: list[tuple[str, str]] = []
    current: str | None = None

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and i + 2 < len(tokens):
            inline = tokens[i + 1]
            top_level = token.level == 0
            if top_level and token.tag in {"h1", "h2"}:
                current = None
            if top_level and token.tag == "h2" and inline.type == "inline":
                title = rendered_inline_text(inline, include_images=False, include_code=True)
                h2_titles.append(title)
                counts[title] = counts.get(title, 0) + 1
                sections.setdefault(title, [])
                current = title
            i += 3
            continue

        if token.type == "inline":
            for child in token.children or []:
                if child.type == "image":
                    images.append((image_alt_text(child), (child.attrGet("src") or "").strip()))
            if current is not None:
                sections.setdefault(current, []).append(token)
        elif current is not None and token.type != "heading_close":
            sections.setdefault(current, []).append(token)
        i += 1

    return MarkdownSurface(tokens, sections, counts, h2_titles, images)


def section_text_from_surface(surface: MarkdownSurface, heading: str, *, include_code: bool = True) -> str | None:
    if surface.section_counts.get(heading, 0) != 1:
        return None
    pieces: list[str] = []
    for token in surface.sections.get(heading, []):
        if token.type != "inline":
            continue
        value = rendered_inline_text(token, include_images=False, include_code=include_code)
        if value:
            pieces.append(value)
    return normalized(" ".join(pieces))


def section_visible_text(source: str, heading: str, *, include_code: bool = True) -> str | None:
    return section_text_from_surface(parse_surface(source), heading, include_code=include_code)


def image_references(source: str) -> list[tuple[str, str]]:
    return parse_surface(source).images


def image_targets(source: str) -> list[str]:
    return [target for _alt, target in image_references(source) if target]


def top_level_h2_titles(source: str) -> list[str]:
    return parse_surface(source).h2_titles
