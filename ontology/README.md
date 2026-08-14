# ECL ontology and validation layer

- `ecl.owl.ttl` — OWL 2 TBox.
- `ecl-context.jsonld` — JSON-LD context used by Git-native ABox records.
- `ecl.shacl.ttl` — SHACL validation shapes.

The canonical data architecture is described in `../spec/KNOWLEDGE-MODEL.md`.

The ontology deliberately does **not** infer ECL restriction from association, control-chain reachability or formal Exergism scores. Those facts may trigger review only through explicit governance procedure.

RDF datasets/triplestores are derived indexes. They must remain rebuildable from the versioned TBox and ABox in Git.
