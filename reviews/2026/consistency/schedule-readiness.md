# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-14**

## Current answer

A post-ECL-0.2 Schedule candidate **can be generated from frozen records**, but it is **not yet ready for adoption**. State identity/project translation and the identity-freeze queue are complete. The remaining State gate is factual: current-status, attribution and remediation review for the residual non-renderable `S` records.

## State inventory

Current State governance after applying all `registry/state-outcome-overrides*.yml` in lexical order is:

- `R`: **34**
- `S`: **83**
- `U`: **31**
- `N`: **47**
- total: **195**

The outcome overlays have precedence over the base State registry until the next consolidated snapshot.

## Schedule engineering status

### `R`

**34 / 34 identity freezes complete.**

Source: `registry/schedule-state-r-freeze.yml`.

### `S`

All **83 active `S`** dossiers have completed Schedule translation.

Current freeze/readiness status:

- **19** fully frozen;
- **57** additional active `S` records with at least one precise renderable subset;
- **76 / 83** active `S` States therefore have at least one Schedule-renderable frozen entry;
- **7** active `S` States remain behind a current-status, attribution or remediation gate; and
- **0** remain blocked merely because identity or project-boundary translation is unfinished.

Canonical aggregate counts are maintained in `registry/schedule-progress-overrides.yml`, which supersedes stale aggregate State-`S` progress numbers in `registry/schedule-translations.yml`. Explicit renderer blocking is maintained in `registry/schedule-status-overrides.yml`.

The 2026-08-14 reconciliation captures the previously unpropagated CAF/Ouanda-Djale ready freeze plus the Moldova and Greece revalidations; the Schedule CI ready-set is authoritative for this coverage check.

## Narrowed-subset rule

A Schedule entry may be narrower than its governance dossier. A precise frozen subset can be rendered while residual scope remains governance-only.

A renderable subset requires:

1. objectively knowable identity or project boundary;
2. explicit capacity limitation;
3. explicit exclusions;
4. Material Participation as the connection rule; and
5. no silent incorporation of residual dossier scope.

## Current freeze registries

State `S` freeze records are maintained under `registry/schedule-state-s-freezes/`. Direct-project freezes are maintained in `registry/schedule-project-freezes.yml`. Organization and armed-organization freezes are maintained in their dedicated Schedule registries.

`registry/schedule-translations.yml` is a base index/work-queue snapshot, not the current aggregate source of truth once later progress/status overlays apply.

## Revalidation rule

Solved identity does not prove current restrictability. If a system, measure, facility or project may have been suspended, invalidated, remediated or materially changed, current-status review must complete before Schedule rendering.

On 2026-08-14 Moldova (`MDA`) passed that gate for one narrow subset: the informal-prisoner-hierarchy control project at Penitentiary no. 2 Lipcani, no. 6 Soroca and no. 15 Cricova. Greece (`GRC`) also passed for one incident-specific subset: the 26 January 2025 Athens Tempi-demonstration stun-grenade / Marios Lolos incident and its accountability project. Both freezes are Material-Participation-limited and leave residual dossier scope governance-only.

## Direct-project rule

ECL 0.2 may designate an exact Restricted Project directly without converting its entire parent institution into a Restricted Party. This is preferred where project identity is more precise than institutional identity.

## Schedule generation gate

`tools/render_schedule.py` renders a deterministic, non-operative Schedule candidate from frozen registries. The renderer applies all `state-outcome-overrides*.yml` in lexical order so later outcome layers cannot be silently ignored.

A generated candidate is not adoption-ready until every included entry passes:

- identity/project knowability;
- overlap and duplicate-scope reconciliation;
- controlled-class membership review;
- remediation/exclusion synchronization;
- internal legal-consistency review; and
- exact ECL-version compatibility review.

Schedule CI independently validates active `R`/`S` coverage against the canonical progress overlays before rendering the candidate.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 material. `ECL-RP-0.5-PARTIAL-DRAFT` remains non-operative test material.

## Current queue

Immediate State work is now **7 factual/current-status/attribution/remediation reviews and 0 identity/project-freeze translations**.

The priority is to resolve those factual gates with named cases, facilities, orders or projects where the current evidence supports a narrow freeze; where remediation or attribution defeats the prior `S`, the correct action is to narrow or downgrade the governance outcome rather than force a Schedule entry.
