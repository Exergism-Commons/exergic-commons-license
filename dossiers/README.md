# Evidence dossiers

Dossiers are the canonical per-entity evidence/governance records for ECL.

- `states/` — 195 State dossiers.
- `organizations/` — organization/legal-entity dossiers.
- `persons/` — individualized natural-person dossiers.
- `projects/` — project/program/deployment dossiers.

A dossier has **no licensing effect by itself**.

## Historical evidence absorption

A dossier being canonical and self-contained does not mean every historical review sentence is copied into it. Historical material under `../reviews/2026/` and GitHub review issues remains provenance, while the dossier carries the current human synthesis needed to understand and audit the present state.

During ECL 1.0 evidence normalization, historical sources are handled explicitly:

- **absorbed** — missing substantive evidence, counter-evidence, uncertainty, attribution context or remediation is normalized into the dossier with provenance;
- **already represented** — the historical source has been reviewed and its substantive current content is already present, so it is not duplicated merely to prove migration;
- **historical-only / locator incomplete** — the record is preserved as provenance but is not promoted into the current evidence basis when its locator or current applicability is insufficient;
- **open conflict/gap** — a material disagreement or unresolved curation problem remains explicit rather than being silently reconciled.

Unreviewed historical material must never be presented as migrated. Source families without a precise historical locator must not be given fabricated precision.

This dossier-normalization work is human curation. It does **not** convert prose into `Claim` or `EvidenceItem` records, assign evidence grades, invent `asOf` dates, or execute Claim predicates as functional triples. Structured Claim/Evidence curation remains governed by `../spec/CLAIM-EVIDENCE-CURATION.md`, `../spec/EVIDENCE-VALUATION.md`, and `../spec/KNOWLEDGE-MODEL.md`.

Historical review files and GitHub issues are retained; normalization changes their role from required reconstruction material toward provenance/history.

## Current State source

All 195 State dossiers are normalized and self-contained.

Read `../registry/states.yml`, then apply every `../registry/state-outcome-overrides*.yml` in lexical order for current State governance.

## Current Schedule sources

Use:

- `../registry/schedule-progress-overrides.yml`
- `../registry/schedule-status-overrides.yml`
- `../registry/schedule-state-r-freeze.yml`
- `../registry/schedule-state-s-freezes/`
- `../registry/schedule-organization-freezes.yml`
- `../registry/schedule-armed-organization-freezes.yml`
- `../registry/schedule-project-freezes.yml`

A Schedule entry may be narrower than its supporting dossier. Residual unfrozen scope remains governance-only.

Only an exact Schedule expressly incorporated with an exact ECL version can have licensing effect.