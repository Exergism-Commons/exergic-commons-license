# ECL semantic knowledge layer

This directory is the Git-native **JSON-LD ABox** for ECL semantic/event data.

It does **not** replace State dossiers, public review procedure or immutable released Schedules. The semantic layer stores stable identity, explicitly reviewed relations, claims, evidence, assessments and events so those layers can be queried and reconstructed without turning RDF into a second governance database.

## Authority map

```text
dossiers/states/*.md        current human governance synthesis
ontology/ecl.owl.ttl        semantic vocabulary / OWL TBox
knowledge/**                canonical Git-native JSON-LD ABox data
ontology/ecl.shacl.ttl      canonical structural/data constraints
build/* RDF                 derived, disposable query/index representation
sparql/**                   derived integrity/dependency query layer
GitHub State review issue   public review/provenance surface, not a database
ScheduleRelease / Schedule  legal/release artifact; only exact incorporated versions operate
```

A discrepancy between a State identity record and its dossier is an integrity error. A discrepancy about governance outcome/scope is **not resolved by copying governance into the State Actor**: the dossier/review/decision procedure must be reconciled instead.

## Semantic stack

```text
ontology/ecl.owl.ttl       OWL TBox
knowledge/**               JSON-LD ABox
ontology/ecl.shacl.ttl     SHACL constraints
        ↓
tools/build_knowledge_graph.py
        ↓
derived canonical RDF / optional triplestore
        ↓
SPARQL integrity + dependency queries
```

The triplestore is never canonical. It can be deleted and rebuilt from Git.

## Layout

```text
knowledge/
  entities/       stable actor/project/institution identities and review clocks
  generated/      non-ABox generator metadata used for conflict detection
  claims/         atomic accepted/disputed/superseded propositions
  update-cases/   materialized review events after triage
  ...             evidence/assessment/decision ABox records as reviewed
```

State actors use `STATE-ISO3` stable IDs and `urn:ecl:STATE-ISO3` RDF IRIs. The dossier keeps the governance identifier `ECL-STATE-ISO3`; these roles are intentionally distinct and deterministic.

## 195-State identity migration

`knowledge/entities/STATE-*.json` contains one State Actor for every canonical `dossiers/states/ISO3.md` dossier. Generated identity/provenance fields are deliberately narrow:

- stable IRI and `STATE-ISO3` ID;
- canonical dossier `entity` name;
- ISO3;
- dossier mapping;
- public GitHub review issue;
- `lastSubstantiveReview` derived from `last_reviewed`.

The migration **validates** `provisional_outcome` only to reject malformed dossier frontmatter. It never writes `R/S/U/N`, scope, tier, restriction status or an equivalent governance shortcut into the State Actor.

Fields such as additional aliases, review clocks/reasons, tracked objects, monitor IDs and explicit semantic relations are curated ABox data and are preserved by regeneration. New records receive the neutral `manual` review class, but **no `reviewDue` date is invented**. Under `manual`, absence of `reviewDue` means no scheduled cadence has yet been curated; the living-review sweep therefore emits no timer-based signal. `hot`, `active` and `stable` classes require an explicit reviewed due date.

`knowledge/generated/state-abox-manifest.json` contains only hashes of generator-owned projections. It is not JSON-LD, is not loaded into the ABox and is not a governance source. Its purpose is to detect a human edit to generator-owned fields so the migration fails with a conflict rather than silently overwriting it.

## Running the migration

From the repository root:

```bash
# Verify that all 195 checked-in records are current and idempotent.
python tools/migrate_state_abox.py --check

# Preview changes without writing.
python tools/migrate_state_abox.py --dry-run

# Preview/check a single State while still validating the full 195-dossier set.
python tools/migrate_state_abox.py --iso3 USA --dry-run

# Apply deterministic identity/provenance updates.
python tools/migrate_state_abox.py --summary state-abox-summary.json
```

When a dossier changes, run `--check` first. If a generator-owned field was manually edited since the last generated projection, the tool reports a conflict and refuses to overwrite it. Resolve the canonical identity discrepancy explicitly, then rerun. Curated semantic fields are not deleted by the generator.

Do not use this tool to change a dossier outcome/scope or Schedule. Those changes follow `spec/GOVERNANCE.md`, `spec/PUBLIC-REVIEW.md` and release procedure.

## Claims and evidence

The State identity migration does not convert prose into RDF claims heuristically. Material facts that require a `Claim` remain explicit first-class records with subject/predicate/object or literal, status, evidence, temporal validity, affected variables/criteria and provenance. Evidence URLs should be represented through reviewed `EvidenceItem` provenance rather than copied as semantically untyped links.

This conservative boundary is intentional: absence of structured evidence produces uncertainty or later curation, not fabricated triples.

## Authority

- ABox entity records are canonical for semantic identity once adopted;
- reviewed claim/evidence records are canonical for structured semantic propositions/provenance;
- update-case records preserve material update lifecycle/history;
- dossiers remain the canonical human-readable governance synthesis;
- a `GovernanceDecision` is a separate governance-event object, never an identity property on a State;
- GitHub issues are public review surfaces and provenance, never the governance database;
- only an exact immutable Schedule incorporated into an exact ECL Bundle can have licensing effect.

## Graph rule

Relations such as `controls`, `participatesIn`, `deploys`, `tracks` or `materiallyBenefits` can create **review dependencies**, but never automatic inherited ECL status.

```text
ORG-A controls ORG-B
ORG-B participatesIn PROJECT-P
```

may cause evidence about `PROJECT-P` to trigger review of `ORG-B` and, if materially relevant, `ORG-A`. It does not make `ORG-A` restricted merely because a graph path exists.

No OWL property chain may turn actor relations into participation, culpability or a `GovernanceOutcome`. SHACL/SPARQL guard this data boundary; governance remains procedural.

## Transitional registry model

Current `registry/` files remain transitional materialized views. They are not an input to State identity migration because they can lag a canonical dossier during governance work. The intended direction remains:

```text
accepted GovernanceDecision records -> generated registry views
```

so stacked override files disappear as a long-term source-of-truth mechanism.
