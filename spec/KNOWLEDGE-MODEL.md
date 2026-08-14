# ECL Knowledge Model

> **Status: Draft data/governance specification.** This model has no licensing effect by itself.

## 1. Architecture

ECL uses a semantic stack with strict separation of concerns:

```text
OWL 2 TBox        -> domain semantics and safe inference
JSON-LD ABox      -> Git-native individuals/facts/records
SHACL Shapes      -> repository/data validity constraints
RDF Dataset       -> derived common graph model
SPARQL            -> integrity, dependency and review queries
Governance rules  -> procedural escalation; never hidden ontology law
```

The canonical editable records remain in Git. Any RDF database/triplestore is a disposable index and MUST be reconstructible from repository sources.

## 2. OWL TBox

`ontology/ecl.owl.ttl` defines classes and properties for actors, projects, deployments, evidence, claims, formal assessments, governance decisions, update cases and release/versioning artifacts.

OWL axioms may express genuine domain semantics such as:

- `State subClassOf Actor`;
- `Agency subClassOf Organization`;
- property domains/ranges;
- safe inverse properties such as `controls` / `controlledBy`;
- category disjointness where conceptually sound.

OWL MUST NOT encode governance shortcuts such as:

```text
restricted(P) and participatesIn(A,P) -> restricted(A)
```

or any score-to-tier function.

Graph reachability can create a **review dependency** in tooling but never inherited guilt/designation.

## 3. JSON-LD ABox

Concrete actors/objects are stored as JSON-LD-compatible records under `knowledge/`.

Each record separates:

- an RDF IRI such as `urn:ecl:STATE-USA`; and
- a human/tooling stable ID such as `STATE-USA`.

The stable ID remains convenient for tickets and files; the IRI prevents path-relative RDF identity drift.

ABox records SHOULD remain small and reviewable in ordinary Git diffs.

## 4. Claims as first-class individuals

Material facts are represented as explicit `Claim` individuals rather than inferred from prose alone.

A claim can carry:

- subject;
- predicate;
- object/literal value;
- temporal validity;
- supporting and contrary evidence;
- status (`candidate`, `accepted`, `disputed`, `rejected`, `superseded`);
- affected Exergism variables / ECL criteria when reviewed.

This explicit claim-node pattern is preferred over relying on RDF-star/OWL 1.2-only features until the project deliberately adopts them.

## 5. SHACL

`ontology/ecl.shacl.ttl` defines closed operational invariants that OWL's open-world semantics should not be asked to enforce.

Examples:

- every tracked object has exactly one stable ID/name/dossier;
- every active claim has an exact subject/predicate and evidence basis;
- evidence grades are from the allowed `E0-E3` set;
- update cases have fingerprints/priorities;
- release/snapshot/bundle records contain required hashes and references;
- stable IDs are globally unique.

A SHACL failure is a repository-integrity failure, not a moral/legal inference.

## 6. Derived RDF and SPARQL

`tools/build_knowledge_graph.py` parses ABox JSON-LD and the OWL TBox and emits a rebuildable RDF dataset.

`tools/run_sparql_checks.py` executes integrity queries under `sparql/integrity/`; any returned row is a CI failure.

SPARQL is also the intended mechanism for later dependency queries such as:

```text
changed Claim
 -> dependent ExergicAssessment
 -> affected GovernanceDecision
 -> potentially stale ScheduleEntry
```

## 7. Reasoning boundary

Three forms of inference must remain distinct:

1. **ontological inference** — safe semantic consequences of OWL axioms;
2. **validation** — SHACL constraints over repository records;
3. **governance inference** — explicit review procedure implemented/documented outside the ontology.

Only the third can lead toward an ECL governance decision, and even then only through the defined review process.

## 8. Reproducibility

The RDF store is never the authoritative history. A `KnowledgeSnapshot` binds:

- Git commit;
- canonical ABox source digest;
- ontology digest;
- evidence cutoff.

Thus a reviewer can delete the generated RDF/triplestore and rebuild the same knowledge state from Git.

## 9. Current implementation boundary

The current branch contains a five-State pilot ABox. The 195-State migration begins only after the ontology/shapes/update/versioning architecture is adopted and CI is green.
