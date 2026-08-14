# ECL semantic knowledge layer

This directory is the proposed Git-native semantic source layer for living ECL governance.

It does **not** replace dossiers or Schedules. It stores the structured identity, temporal claim and update-event data needed to keep them reproducible over time.

## Layout

```text
knowledge/
  entities/       stable actor/project/institution identities and review clocks
  claims/         atomic accepted/disputed/superseded propositions
  update-cases/   materialized review events after triage
```

The JSON records are designed to be JSON-LD-compatible through `../ontology/ecl-context.jsonld`, while remaining readable and validatable without requiring an RDF database.

## Authority

- entity records are canonical for semantic identifiers/aliases/relations once adopted;
- claim records are canonical for structured propositions and provenance once reviewed;
- update-case records are canonical for the lifecycle/history of a material update;
- dossiers remain the canonical human-readable governance synthesis;
- governance decisions remain subject to the ECL governance/designation standards;
- only an exact incorporated Schedule has licensing effect.

## Graph rule

Relations such as `controls`, `participatesIn`, `deploys` or `materiallyBenefits` can create **review dependencies**, but never automatic inherited ECL status.

For example:

```text
ORG-A controls ORG-B
ORG-B participatesIn PROJECT-P
```

may cause evidence about `PROJECT-P` to trigger review of `ORG-B` and, if materially relevant, `ORG-A`. It does not make `ORG-A` restricted merely because a graph path exists.

## Transitional registry model

Current files under `registry/` remain in use. The intended migration is that accepted `GovernanceDecision` records eventually generate those compact registries as materialized views, eliminating stacked outcome overrides as a long-term source-of-truth mechanism.
