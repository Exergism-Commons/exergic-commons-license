#!/usr/bin/env python3
"""Shared CommonMark fenced-code visibility semantics for State dossier audits.

This module is intentionally small and parser-only. Identity auditors should not carry their own
fence regex/state machine: doing so lets visibility semantics drift between Person, vendor and title
coverage. The functions here model only the CommonMark fenced-code properties the audits need:

- an opener is indented by at most three literal spaces (a leading tab is indented code, not a fence),
- the opening run is at least three backticks or tildes,
- a backtick fence info string may not contain a backtick,
- a closer uses the same marker with a run at least as long as the opener,
- a closer may contain only ASCII spaces/tabs after the marker run.

The module does not render Markdown or infer any identity semantics.
"""
from __future__ import annotations

import argparse
import re
from typing import TypeAlias


FenceState: TypeAlias = tuple[str, int]

# CommonMark permits up to three *spaces* of indentation before a fenced-code marker. Using \s
# here is incorrect because a leading tab advances to an indented-code column and is not a fence.
FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<run>`{3,}|~{3,})(?P<tail>.*)$")
CLOSING_TAIL_RE = re.compile(r"[ \t]*$")


def fence_transition(raw: str, state: FenceState | None) -> tuple[FenceState | None, bool]:
    """Advance fenced-code state and report whether ``raw`` is fence syntax/content boundary.

    ``handled`` is true for a valid opener and for any fence-shaped line while already inside a
    fence. Consumers should still use the returned state to suppress ordinary content inside an
    open fence. An invalid would-be opener (for example tab-indented or a backtick-bearing backtick
    info string) returns ``handled=False`` and therefore remains visible prose.
    """
    match = FENCE_RE.match(raw)
    if match is None:
        return state, False

    run = match.group("run")
    tail = match.group("tail")
    marker = run[0]

    if state is None:
        if marker == "`" and "`" in tail:
            return None, False
        return (marker, len(run)), True

    open_marker, open_length = state
    if (
        marker == open_marker
        and len(run) >= open_length
        and CLOSING_TAIL_RE.fullmatch(tail) is not None
    ):
        return None, True
    return state, True


def visible_lines(body: str) -> list[tuple[int, str]]:
    """Return 1-based source lines that are outside valid fenced-code blocks."""
    out: list[tuple[int, str]] = []
    state: FenceState | None = None
    for line_no, raw in enumerate(body.splitlines(), 1):
        previous_state = state
        state, handled = fence_transition(raw, state)
        if handled or previous_state is not None or state is not None:
            continue
        out.append((line_no, raw))
    return out


def blank_fenced_lines(body: str) -> str:
    """Blank valid fenced-code regions while preserving source line count."""
    out: list[str] = []
    state: FenceState | None = None
    for raw in body.splitlines():
        previous_state = state
        state, handled = fence_transition(raw, state)
        if handled or previous_state is not None or state is not None:
            out.append("")
        else:
            out.append(raw)
    return "\n".join(out)


def self_test() -> None:
    # Run length: a shorter same-marker run is content, not a closer.
    body = (
        "````text\n"
        "hidden\n"
        "```\n"
        "still hidden\n"
        "`````\n"
        "visible\n"
    )
    assert visible_lines(body) == [(6, "visible")]

    # Marker family and trailing closer syntax are part of the same shared transition.
    mixed = "~~~~text\n```\n~~~~ trailing\n~~~~\nvisible"
    assert visible_lines(mixed) == [(5, "visible")]

    # Backtick info strings cannot contain backticks; tilde info strings may.
    invalid_info = "```bad`info\nvisible"
    assert visible_lines(invalid_info) == [(1, "```bad`info"), (2, "visible")]
    assert visible_lines("~~~bad`info\nhidden\n~~~") == []

    # The review finding: tabs are not part of the up-to-three-space opener indentation.
    for prefix in ("\t", " \t", "  \t", "   \t"):
        candidate = f"{prefix}```text\nvisible"
        assert visible_lines(candidate) == [(1, f"{prefix}```text"), (2, "visible")]

    # Zero through three literal spaces are valid; four spaces are indented code, not a fence.
    for spaces in range(4):
        assert visible_lines(" " * spaces + "```text\nhidden\n```") == []
    four_space = "    ```text\nvisible"
    assert visible_lines(four_space) == [(1, "    ```text"), (2, "visible")]

    # A tab-indented pseudo-closer cannot terminate a valid fence; a <=3-space closer can.
    tab_close = "```text\nhidden\n\t```\nstill hidden\n```\nvisible"
    assert visible_lines(tab_close) == [(6, "visible")]
    assert visible_lines("```text\nhidden\n   ```\nvisible") == [(4, "visible")]

    # Only ASCII space/tab is legal after a closer; arbitrary trailing text stays fenced content.
    trailing = "```text\nhidden\n``` trailing\nstill hidden\n```\nvisible"
    assert visible_lines(trailing) == [(6, "visible")]

    safe = blank_fenced_lines("````\nhidden\n```\n````\nvisible")
    assert safe.splitlines() == ["", "", "", "", "visible"]
    print("Shared CommonMark fenced-code semantics self-test: OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
