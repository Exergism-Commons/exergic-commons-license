#!/usr/bin/env python3
"""Run SPARQL SELECT integrity queries; any returned row is a CI failure."""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Dataset, Graph


QUAD_FORMATS = {"nquads", "trig"}


def graph_format(path: Path) -> str | None:
    return {
        ".ttl": "turtle",
        ".nt": "nt",
        ".nq": "nquads",
        ".trig": "trig",
        ".jsonld": "json-ld",
        ".json": "json-ld",
    }.get(path.suffix.lower())


def load_query_graph(path: Path) -> Graph | Dataset:
    """Load triples or quads into a query view that includes every context."""
    fmt = graph_format(path)
    if fmt in QUAD_FORMATS:
        dataset = Dataset(default_union=True)
        dataset.parse(path, format=fmt)
        return dataset

    graph = Graph()
    graph.parse(path, format=fmt)
    return graph


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path)
    parser.add_argument("query_dir", type=Path, nargs="?", default=Path("sparql/integrity"))
    args = parser.parse_args()

    graph = load_query_graph(args.graph)

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
