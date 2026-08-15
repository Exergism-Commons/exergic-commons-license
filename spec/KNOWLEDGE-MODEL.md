# ECL Knowledge Model

> **Status: Draft data/governance specification.** This model has no licensing effect by itself.

## 1. Architecture

ECL uses a semantic stack with strict separation of concerns:

```text
Dossiers          -> current human governance synthesis
OWL 2 TBox        -> domain semantics and safe inference
JSON-LD ABox      -> Git-native individuals/facts/events
SHACL Shapes      -> canonical repository/data validity constraints
RDF Dataset       -> derived common graph/index model
SPARQL            -> derived integrity, dependency and review queries
GitHub issues     -> public review/provenance surface, never the database
Schedules         -> immutable legal/release artifacts when incorporated
Governance rules  -> procedural escalation; never hidden ontology law
```

The canonical editable semantic records remain in Git. Any RDF database/triplestore is a disposable index and MUST be reconstructible from repository sources. Governance synthesis remains in dossiers until an explicit reviewed decision/release procedure says otherwise.

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

or any score-to-tier function. ECL deliberately defines no actor-relation `owl:propertyChainAxiom` that can propagate participation, culpability or governance status.

Graph reachability can create a **review dependency** in tooling but never inherited guilt/designation.

## 3. JSON-LD ABox

Concrete actors/objects are stored as JSON-LD-compatible records under `knowledge/`.

Each record separates:

- an RDF IRI such as `urn:ecl:STATE-USA`; and
- a human/tooling stable ID such as `STATE-USA`.

The State dossier's governance identifier remains `ECL-STATE-USA`. That dossier ID, the semantic stable ID and the RDF IRI are deterministic but serve different layers.

ABox records SHOULD remain small and reviewable in ordinary Git diffs. A State Actor may contain semantic identity, provenance, review-clock metadata and explicitly curated relations; it MUST NOT contain `R/S/U/N`, tier, restriction status or an equivalent direct governance classification.

`trackedObjects` on a State is a legacy compatibility/review projection serialized as direct `ecl:tracks` edges. Once the same edge is represented by a first-class Claim, the Claim is the auditable proposition carrying status, evidence and provenance; `trackedObjects` is not an independent governance or evidentiary store. Repository integrity tooling MUST require every non-empty State `trackedObjects` edge to have exactly one active (`candidate`, `accepted` or `disputed`) `ecl:tracks` Claim with the same subject/object and resolving supporting evidence. The inverse is deliberately not required: a reviewed `ecl:tracks` Claim may exist without being copied back into the legacy projection. No tracking edge or Claim implies operation, control, culpability or inherited governance.

`partOf` is direct institutional identity/context metadata for Actors. It records only the explicitly curated immediate parent edge (for example, HSI → ICE or CENTCOM → DoD). `partOf` is deliberately non-transitive in the TBox and tooling MUST NOT synthesize ancestor edges. It also MUST NOT propagate `controls`, `participatesIn`, `operates`, `tracks`, culpability, restriction status or GovernanceOutcome. Attribution-sensitive functional relations remain first-class Claims with their own evidence even when the relevant actors are connected by `partOf`.

Review clocks preserve uncertainty. `hot`, `active` and `stable` identify scheduled review classes and therefore require an explicit `reviewDue`. `manual` means no automatic cadence is asserted; `reviewDue` may be absent until a reviewer curates one. Tooling MUST NOT synthesize a due date merely to satisfy a schema.

## 4. Claims as first-class individuals

Material facts are represented as explicit `Claim` individuals rather than inferred from prose alone.

A claim can carry:

- subject;
- predicate;
- object/literal value;
- temporal validity;
- supporting and contrary evidence;
- status (`candidate`, `accepted`, `disputed`, `rejected`, `superseded`);
- affected Exergism variables / ECL criteria when reviewed;
- provenance to the dossier and underlying evidence.

This explicit claim-node pattern is preferred over relying on RDF-star/OWL 1.2-only features until the project deliberately adopts them.

The 195-State identity migration intentionally does **not** NLP-convert dossier prose into claims. A structured fact is added only when it is sufficiently explicit and reviewable; uncertainty is preserved rather than converted into a guessed triple.

## 5. SHACL

`ontology/ecl.shacl.ttl` defines closed operational invariants that OWL's open-world semantics should not be asked to enforce.

Examples:

- every tracked object has exactly one stable ID/name/dossier;
- every State has exactly one ISO3, dossier mapping and public-review IRI;
- State stable ID / IRI / ISO3 / dossier paths agree;
- State ISO3 and dossier mappings are one-to-one;
- scheduled review classes require an explicit due date while `manual` may remain unscheduled;
- no State carries a direct governance/tier/restriction-status predicate or direct GovernanceOutcome relation;
- every active claim has an exact subject/predicate and evidence basis;
- evidence grades are from the allowed `E0-E3` set;
- update cases have fingerprints/priorities;
- release/snapshot/bundle records contain required hashes and references;
- stable IDs are globally unique.

A SHACL failure is a repository-integrity failure, not a moral/legal inference.

## 6. Derived RDF and SPARQL

`tools/build_knowledge_graph.py` parses ABox JSON-LD and the OWL TBox and emits rebuildable RDF. Human-readable Turtle remains available, while canonicalized sorted N-Triples provide a byte-deterministic build target and RDF digest.

`tools/run_sparql_checks.py` executes integrity queries under `sparql/integrity/`; any returned row is a CI failure. The State corpus queries assert exact cardinality, unique mappings, identifier consistency and the governance-separation guardrails.

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

Only the third can lead toward an ECL governance decision, and even then only through the defined review process. A relation such as `partOf`, `controls`, `tracks`, `participatesIn`, `operates` or `deploys` is evidence/review/identity structure, never inherited restriction. In particular, institutional ancestry does not inherit a subordinate actor's functional Claim, and a parent actor does not acquire participation, operation or control merely because a child actor has such a Claim.

## 8. Reproducibility

The RDF store is never the authoritative history. A `KnowledgeSnapshot` can bind:

- Git commit;
- canonical ABox source digest;
- ontology digest;
- evidence cutoff;
- deterministic RDF digest.

Thus a reviewer can delete the generated RDF/triplestore and rebuild the same knowledge state from Git.

For State identities, `knowledge/generated/state-abox-manifest.json` additionally hashes the generator-owned projection of every ISO3. It is conflict-detection metadata, not ABox data and not governance.

## 9. Current implementation boundary

The Git-native ABox now contains **195 State Actors**, one for every canonical `dossiers/states/ISO3.md` dossier. The migration is generated and checked by `tools/migrate_state_abox.py` and CI requires 195 unique State IRIs, stable IDs, ISO3 values and dossier mappings.

The bounded Agency hierarchy scale-out adds only explicitly curated institutional identities needed by canonical project attribution. Agency `partOf` edges are identity/context metadata; functional attribution remains Claim/Evidence data and is not inherited across hierarchy edges.

This completes the State **identity/provenance** migration only. It does not imply that all 195 dossiers have complete formal Exergism assessments, fully normalized Claim/EvidenceItem graphs or accepted machine-readable GovernanceDecision records. Those are separate reviewed migrations and must not be fabricated merely to fill the graph.

Generator-owned State fields are reconstructed from dossier frontmatter; curated aliases, review clocks, tracked objects, monitors and semantic relations are preserved. New States default to `reviewClass: manual` without inventing a `reviewDue`; a due date appears only when the repository contains a curated cadence. The generator validates `provisional_outcome` but never materializes it into the Actor.
