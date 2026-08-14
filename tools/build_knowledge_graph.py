#!/usr/bin/env python3
"""Build the ECL RDF dataset from Git-native JSON-LD ABox records.

The triplestore/dataset is derived and disposable. Canonical sources remain the
versioned repository files. A KnowledgeSnapshot can bind the Git commit plus the
ABox-source and ontology SHA-256 digests emitted by this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rdflib import Graph


def iter_abox_files(root: Path) -> list[Path]:
    paths = sorted(set(root.rglob("*.json")) | set(root.rglob("*.jsonld")))
    result: list[Path] = []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot parse JSON-LD candidate {path}: {exc}") from exc
        if isinstance(data, dict) and "@context" in data and ("iri" in data or "@id" in data):
            result.append(path)
    return result


def source_digest(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(canonical.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(knowledge_root: Path, ontology_path: Path, output_dir: Path) -> dict[str, object]:
    abox_files = iter_abox_files(knowledge_root)
    if not abox_files:
        raise ValueError(f"no JSON-LD ABox records found under {knowledge_root}")

    abox = Graph()
    for path in abox_files:
        abox.parse(path, format="json-ld")

    tbox = Graph()
    tbox.parse(ontology_path, format="turtle")

    combined = Graph()
    for triple in tbox:
        combined.add(triple)
    for triple in abox:
        combined.add(triple)

    output_dir.mkdir(parents=True, exist_ok=True)
    abox_path = output_dir / "ecl-abox.ttl"
    graph_path = output_dir / "ecl-knowledge.ttl"
    metadata_path = output_dir / "knowledge-build.json"

    abox.serialize(abox_path, format="turtle")
    combined.serialize(graph_path, format="turtle")

    metadata = {
        "abox_files": [path.relative_to(knowledge_root).as_posix() for path in abox_files],
        "abox_source_sha256": source_digest(abox_files, knowledge_root),
        "ontology_sha256": file_sha256(ontology_path),
        "abox_triples": len(abox),
        "combined_triples": len(combined),
        "note": "RDF serializations are derived. Snapshot identity binds Git commit plus source digests, not blank-node serialization labels."
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-root", type=Path, default=Path("knowledge"))
    parser.add_argument("--ontology", type=Path, default=Path("ontology/ecl.owl.ttl"))
    parser.add_argument("--output-dir", type=Path, default=Path("build"))
    args = parser.parse_args()

    try:
        metadata = build(args.knowledge_root, args.ontology, args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
