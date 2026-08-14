# ECL semantic knowledge layer

This directory is the Git-native **JSON-LD ABox** for living ECL governance.

It does **not** replace dossiers or immutable released Schedules. It stores structured identities, temporal claims, update events and—progressively—reviewed analytical/governance records needed to keep those layers reproducible.

## Semantic stack

```text
ontology/ecl.owl.ttl       OWL TBox
knowledge/**               JSON-LD ABox
ontology/ecl.shacl.ttl     SHACL constraints
        ↓
tools/build_knowledge_graph.py
        ↓
derived RDF dataset / optional triplestore
        ↓
SPARQL integrity + dependency queries
```

The triplestore is never canonical. It can be deleted and rebuilt from Git.

## Layout

```text
knowledge/
  entities/       stable actor/project/institution identities and review clocks
  claims/         atomic accepted/disputed/superseded propositions
  update-cases/   materialized review events after triage
  ...             future evidence/assessment/decision ABox records
```

Current pilot entity files use JSON syntax with an explicit JSON-LD context. Their RDF identity is an `urn:ecl:*` IRI; the separate `id` field is a stable human/tooling identifier.

## Authority

- ABox entity records are canonical for semantic identity once adopted;
- claim records are canonical for structured propositions/provenance once reviewed;
- update-case records preserve material update lifecycle/history;
- dossiers remain the canonical human-readable governance synthesis during migration;
- accepted `GovernanceDecision` records are intended to become the machine-readable source for generated registries;
- only an exact immutable Schedule incorporated into an exact ECL Bundle can have licensing effect.

## Graph rule

Relations such as `controls`, `participatesIn`, `deploys` or `materiallyBenefits` can create **review dependencies**, but never automatic inherited ECL status.

```text
ORG-A controls ORG-B
ORG-B participatesIn PROJECT-P
```

may cause evidence about `PROJECT-P` to trigger review of `ORG-B` and, if materially relevant, `ORG-A`. It does not make `ORG-A` restricted merely because a graph path exists.

## Transitional registry model

Current `registry/` files remain transitional materialized views. The intended direction is:

```text
accepted GovernanceDecision records -> generated registry views
```

so stacked override files disappear as a long-term source-of-truth mechanism.
