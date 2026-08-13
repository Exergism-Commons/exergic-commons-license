# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-13**

## 1. Current answer

A post-ECL-0.2 Schedule is **not yet ready for adoption**, but the work is now separated into evidence, identity and rendering layers.

The State evidence cycle and Schedule translation cycle are complete. The remaining State work is exact identity/project-boundary freeze.

## 2. State governance inventory

Current post-ECL-0.2 State registry:

- `R`: **34**
- `S`: **86**
- `U`: **28**
- `N`: **47**
- total: **195**

Only `R`/`S` can generate Schedule candidates. `U`/`N` remain non-operative governance outcomes.

## 3. State Schedule engineering status

### `R`

**34 / 34 identity freezes complete.**

The canonical freeze source is `registry/schedule-state-r-freeze.yml`.

### `S`

**86 / 86 Schedule Translation Records complete.**

Current freeze status from `registry/schedule-translations.yml`:

- **19** `S` records fully frozen;
- **11** additional `S` records with at least one precise, Schedule-renderable narrowed subset;
- **1** record where identity is resolved but current deployment/remediation status must be revalidated before rendering; and
- **55** records still requiring an exact identity, unit, case, facility, order, deployment or project boundary.

Therefore **30 / 86 State `S` dossiers already have at least one Schedule-renderable entry**.

## 4. Narrowed-subset rule

A governance dossier may support more than one coercive project. The Schedule does **not** need to operationalize every evidentiary scope at once.

A frozen subset may be rendered when:

1. the actor/project identity is objectively knowable;
2. the capacity limitation is explicit;
3. excluded functions are stated;
4. Material Participation remains the operative connection rule; and
5. every unfrozen residual scope remains governance-only.

This avoids two bad outcomes: either delaying every precise entry until the broadest dossier is fully frozen, or converting descriptive research labels into vague contractual classes.

## 5. Freeze work products created after translation

Current State `S` freeze files:

- `registry/schedule-state-s-freezes/batch-01-identity.yml`
- `registry/schedule-state-s-freezes/batch-02-statutory-agency.yml`
- `registry/schedule-state-s-freezes/batch-03a-usa.yml`
- `registry/schedule-state-s-freezes/batch-04-detention-digital.yml`

They add exact agency, statutory, project and temporal boundaries while preserving unfrozen residual scope as non-operative.

## 6. Current-status revalidation

Identity freeze and substantive currency are separate gates.

The Netherlands illustrates the distinction: the relevant probation algorithms and operators are now identified, but the February 2026 official record says the principal OXREC deployment was temporarily stopped. The Schedule must therefore confirm current deployment/remediation status before creating an operative candidate rather than treating a solved identity question as proof of present restriction.

## 7. Direct Restricted Project rule

ECL 0.2 permits an exact project to be designated directly without first converting the entire parent State or organization into a Restricted Party.

`registry/schedule-project-freezes.yml` now contains the first fully frozen direct-project record. Its boundary is incident/project-specific and expressly excludes unrelated operations, suppliers and personnel absent Material Participation.

This is the preferred architecture whenever a prohibited-use finding is more precise than the institution that contains it.

## 8. Cross-entity data sources

The Schedule work queue no longer duplicates full non-State candidate lists. Canonical sources are:

- `registry/organizations.yml`
- `registry/projects.yml`
- `registry/persons.yml`
- `registry/schedule-project-freezes.yml`

`registry/schedule-translations.yml` is now an index/progress file rather than a second parallel entity registry.

## 9. External-list and supplier rules

External sanctions/warrant records may provide evidence or identity anchors, but they are not dynamically imported as ECL classes.

Likewise, a supplier is not Restricted merely because it supplies a sensitive customer or system. Exact entity designation, direct Restricted Project designation or Material Participation in a qualifying frozen project is required.

## 10. Schedule generation gate

A fresh post-0.2 Schedule may be rendered as a **draft candidate** from frozen entries before every governance dossier is fully operationalized, provided unfrozen scope is omitted.

It must **not** be presented as ready for adoption until:

- every included entry has a frozen knowable identity/project boundary;
- overlaps between State, organization and project entries are deduplicated;
- controlled-class membership is objectively determinable;
- remediation/exclusion rules are synchronized;
- the candidate is reviewed for internal legal consistency; and
- compatibility is stated for the exact ECL version.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 material and must not be patched into apparent compatibility.

## 11. Current executable queue

The immediate State queue is **55 unresolved identity/project freezes**, plus one current-status revalidation case.

A previously attempted Ukraine freeze was not persisted because the repository connector rejected that write; it is therefore not counted as completed.

The source of truth for live counts is `registry/schedule-translations.yml`.
