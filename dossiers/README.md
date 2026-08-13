# Evidence dossiers

Dossiers are the canonical per-entity evidence/governance records for ECL.

- `states/` — 195 State dossiers.
- `organizations/` — organization/legal-entity dossiers.
- `persons/` — individualized natural-person dossiers.
- `projects/` — project/program/deployment dossiers.

A dossier has **no licensing effect by itself**. Only an exact Schedule expressly incorporated with an exact ECL version can have licensing effect.

## State status

**195 / 195 State dossiers are normalized and self-contained.**

Read current State governance from `../registry/states.yml` together with the higher-precedence `../registry/state-outcome-overrides.yml`.

Current provisional counts:

- **34 `R`**
- **85 `S`**
- **29 `U`**
- **47 `N`**

## Schedule engineering

- **34 / 34 `R`** identity freezes complete.
- All active `S` dossiers have completed translation.
- **71 / 85 active `S`** have at least one Schedule-renderable frozen entry.
- **14 / 85 active `S`** remain in factual/current-status/attribution/remediation review.
- **0** remain blocked merely by unresolved identity/project translation.

Live sources:

- `../registry/schedule-progress-overrides.yml`
- `../registry/schedule-status-overrides.yml`
- `../registry/schedule-state-r-freeze.yml`
- `../registry/schedule-state-s-freezes/`
- `../registry/schedule-project-freezes.yml`

A Schedule entry may be narrower than its supporting dossier. Residual unfrozen scope remains governance-only.

## Cross-entity sources

- `../registry/organizations.yml`
- `../registry/projects.yml`
- `../registry/persons.yml`

## Next phase

Resolve the remaining factual/status reviews, freeze outstanding non-State identities/aliases, deduplicate State↔organization↔project scope and render the first post-0.2 Schedule candidate from frozen records only.
