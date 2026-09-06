#!/usr/bin/env python3
"""Build deterministic derived RDF from the Git-native JSON-LD ABox.

The RDF dataset is disposable. Canonical identity/provenance remains in Git
ABox sources and ontology; governance remains in dossiers/decisions/Schedules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rdflib import Graph
from rdflib.compare import to_canonical_graph


def _canonical_source_iri(value: str) -> str:
    if value.startswith("ecl:"):
        return "https://id.exergism.org/ecl#" + value.removeprefix("ecl:")
    return value


def iter_abox_files(root: Path) -> list[Path]:
    paths = sorted(set(root.rglob("*.json")) | set(root.rglob("*.jsonld")))
    result: list[Path] = []
    seen_iris: dict[str, Path] = {}
    seen_ids: dict[str, Path] = {}
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot parse JSON-LD candidate {path}: {exc}") from exc
        if isinstance(data, dict) and "@context" in data and ("iri" in data or "@id" in data):
            iri = data.get("iri", data.get("@id"))
            if not isinstance(iri, str) or not iri:
                raise ValueError(f"ABox source {path} has an invalid iri/@id")
            canonical_iri = _canonical_source_iri(iri)
            previous_iri = seen_iris.get(canonical_iri)
            if previous_iri is not None:
                raise ValueError(
                    f"duplicate ABox IRI {canonical_iri}: {previous_iri} and {path}"
                )
            seen_iris[canonical_iri] = path

            stable_id = data.get("id")
            if stable_id is not None:
                if not isinstance(stable_id, str) or not stable_id:
                    raise ValueError(f"ABox source {path} has an invalid stable id")
                previous_id = seen_ids.get(stable_id)
                if previous_id is not None:
                    raise ValueError(
                        f"duplicate ABox stable id {stable_id}: {previous_id} and {path}"
                    )
                seen_ids[stable_id] = path
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


def canonical_ntriples(graph: Graph) -> str:
    """Return a stable N-Triples serialization, including stable blank-node IDs."""
    canonical = to_canonical_graph(graph)
    serialized = canonical.serialize(format="nt")
    lines = sorted(line for line in serialized.splitlines() if line.strip())
    return "\n".join(lines) + "\n"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(knowledge_root: Path, ontology_path: Path, output_dir: Path) -> dict[str, object]:
    abox_files = iter_abox_files(knowledge_root)
    if not abox_files:
        raise ValueError(f"no JSON-LD ABox records found under {knowledge_root}")

    abox = Graph()
    for path in abox_files:
        abox.parse(path, format="json-ld")

    tbox = Graph().parse(ontology_path, format="turtle")
    combined = Graph()
    for triple in tbox:
        combined.add(triple)
    for triple in abox:
        combined.add(triple)

    output_dir.mkdir(parents=True, exist_ok=True)
    abox_ttl = output_dir / "ecl-abox.ttl"
    graph_ttl = output_dir / "ecl-knowledge.ttl"
    abox_nt = output_dir / "ecl-abox.nt"
    graph_nt = output_dir / "ecl-knowledge.nt"
    metadata_path = output_dir / "knowledge-build.json"

    # Turtle is kept for humans. Canonical N-Triples is the deterministic build
    # target used for byte-for-byte reproducibility and graph digests.
    abox.serialize(abox_ttl, format="turtle")
    combined.serialize(graph_ttl, format="turtle")
    abox_text = canonical_ntriples(abox)
    graph_text = canonical_ntriples(combined)
    abox_nt.write_text(abox_text, encoding="utf-8")
    graph_nt.write_text(graph_text, encoding="utf-8")

    metadata = {
        "abox_files": [path.relative_to(knowledge_root).as_posix() for path in abox_files],
        "abox_source_sha256": source_digest(abox_files, knowledge_root),
        "ontology_sha256": file_sha256(ontology_path),
        "abox_rdf_sha256": text_sha256(abox_text),
        "combined_rdf_sha256": text_sha256(graph_text),
        "abox_triples": len(abox),
        "combined_triples": len(combined),
        "deterministic_format": "canonical sorted N-Triples",
        "note": "RDF serializations are derived. Snapshot identity binds Git/source/ontology/RDF digests, never a triplestore."
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
