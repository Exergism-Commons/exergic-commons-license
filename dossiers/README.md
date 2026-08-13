# Evidence dossiers

Dossiers are the canonical per-entity evidence/governance records for ECL.

- `states/` — 195 State dossiers.
- `organizations/` — organization/legal-entity dossiers.
- `persons/` — individualized natural-person dossiers.
- `projects/` — project/program/deployment dossiers.

A dossier has **no licensing effect by itself**.

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
