#!/usr/bin/env python3
"""Run SPARQL SELECT integrity queries; any returned row is a CI failure."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph


def graph_format(path: Path) -> str | None:
    return {
        ".ttl": "turtle",
        ".nt": "nt",
        ".nq": "nquads",
        ".trig": "trig",
        ".jsonld": "json-ld",
        ".json": "json-ld",
    }.get(path.suffix.lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path)
    parser.add_argument("query_dir", type=Path, nargs="?", default=Path("sparql/integrity"))
    args = parser.parse_args()

    graph = Graph()
    fmt = graph_format(args.graph)
    graph.parse(args.graph, format=fmt)

    failed = False
    queries = sorted(args.query_dir.glob("*.rq"))
    if not queries:
        parser.error(f"no .rq integrity queries found in {args.query_dir}")

    for path in queries:
        rows = list(graph.query(path.read_text(encoding="utf-8")))
        if rows:
            failed = True
            print(f"FAIL {path}: {len(rows)} violation(s)")
            for row in rows[:20]:
                print("  ", " | ".join(str(value) for value in row))
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
