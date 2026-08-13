# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-13**

## Current answer

A post-ECL-0.2 Schedule is **not yet ready for adoption**. The evidence and translation layers are complete; identity/project freeze is still in progress.

## State inventory

Current State governance remains:

- `R`: **34**
- `S`: **86**
- `U`: **28**
- `N`: **47**
- total: **195**

## Schedule engineering status

### `R`

**34 / 34 identity freezes complete.**

Source: `registry/schedule-state-r-freeze.yml`.

### `S`

**86 / 86 translation records complete.**

Current freeze status:

- **19** fully frozen;
- **18** additional records with at least one precise renderable subset;
- **3** pending current-status/remediation review rather than identity work;
- **46** still requiring an exact identity or project-boundary freeze.

Therefore **37 / 86 State `S` dossiers have at least one Schedule-renderable entry**.

Live counts are maintained in `registry/schedule-translations.yml`.

## Narrowed-subset rule

A Schedule entry may be narrower than its governance dossier. A precise frozen subset can be rendered while residual scope remains governance-only.

A renderable subset requires:

1. objectively knowable identity or project boundary;
2. explicit capacity limitation;
3. explicit exclusions;
4. Material Participation as the connection rule; and
5. no silent incorporation of residual dossier scope.

## Current freeze registries

State `S` freeze records are maintained under `registry/schedule-state-s-freezes/`. Direct-project freezes are maintained in `registry/schedule-project-freezes.yml`.

`registry/schedule-translations.yml` is an index/work queue, not a duplicate entity registry.

## Revalidation rule

Solved identity does not prove current restrictability. If a system, measure or project may have been suspended, invalidated, remediated or materially changed, current-status review must complete before Schedule rendering.

## Direct-project rule

ECL 0.2 may designate an exact Restricted Project directly without converting its entire parent institution into a Restricted Party. This is preferred where project identity is more precise than institutional identity.

## Schedule generation gate

A post-0.2 **draft candidate** may be rendered from frozen entries while unfrozen scope is omitted.

It is not adoption-ready until every included entry passes:

- identity/project knowability;
- overlap and duplicate-scope reconciliation;
- controlled-class membership review;
- remediation/exclusion synchronization;
- internal legal-consistency review; and
- exact ECL-version compatibility review.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 material.

## Current queue

Immediate State work: **46 identity/project freezes + 3 current-status/remediation reviews**.

A previously attempted write that was rejected by the repository connector is not included in completed counts.
