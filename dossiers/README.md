# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal/organizational actors.
- `persons/` — individualized natural-person records where necessary.
- `projects/` — project/program/deployment-specific records.

A dossier has **no licensing effect by itself**. Only an exact Schedule expressly incorporated with an exact ECL version can create an operative Restricted Party or Restricted Project for a software release.

GitHub issues are discussion/submission threads; review tranche/cohort/audit files are procedural history; the dossier is the version-controlled canonical current governance record.

## Normalization rule

A normalized dossier must be understandable and auditable without reconstructing its conclusion from historical review files. It records the current outcome/scope, ECL criteria, supporting evidence, counter-evidence, attribution boundaries, adversarial result, review/removal triggers, sources and procedural history.

Historical review files may explain how a conclusion was reached but are not required to understand the current dossier.

## 2026 State corpus

**195 / 195 State dossiers have completed detailed factual/adversarial normalization at the 2026-08-11 evidence cutoff.**

The ECL 0.2 State delta is also complete. Current provisional distribution:

- **34 `R`**
- **86 `S`**
- **28 `U`**
- **47 `N`**
- **195 total**

Canonical machine-readable outcome source: `../registry/states.yml`.

`R/S/U/N` are governance outcomes, not generic human-rights ratings and not operative licensing designations. Each current dossier must be read through the exact ECL 0.2 criteria and its attribution/exclusion section.

## Cross-entity status

Organization, project and person schemas and canonical registries now exist. The first cross-entity reconciliation cycle is complete for the core non-State corpus.

Canonical registries:

- `../registry/organizations.yml`
- `../registry/projects.yml`
- `../registry/persons.yml`

Older Schedule entries are not carried forward merely because they existed previously. External lists may support identity/evidence but do not automatically create ECL status.

## Schedule translation and freeze

State factual normalization is complete; current work is **contract-readable Schedule engineering**.

- **34 / 34 State `R`** candidate apparatus identity freezes are complete.
- **86 / 86 State `S`** Schedule Translation Records are complete.
- **19 State `S`** records are fully frozen.
- **18 additional State `S`** records contain at least one precise renderable subset.
- **3 State `S`** records require current-status/remediation revalidation.
- **46 State `S`** records still require exact identity/project-boundary work.

Therefore **37 / 86 State `S` dossiers currently have at least one Schedule-renderable entry**.

Live work queue: `../registry/schedule-translations.yml`.

Freeze records:

- `../registry/schedule-state-r-freeze.yml`
- `../registry/schedule-state-s-freezes/`
- `../registry/schedule-project-freezes.yml`

A frozen Schedule entry may be narrower than the dossier that supports it. Residual unfrozen scope remains governance-only until separately frozen.

## Next phase

Continue resolving the remaining identity/project and current-status blockers, then deduplicate State ↔ organization ↔ project scope and render a fresh post-0.2 Schedule candidate from the registries.

`schedules/ECL-RP-0.4-DRAFT.md` remains historical/pre-0.2 material and must not be patched into apparent compatibility.
