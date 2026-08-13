# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal entities.
- `persons/` — specifically designated natural persons where necessary.
- `projects/` — project/program-specific records.

A dossier has **no licensing effect by itself**. Only an exact Schedule expressly incorporated with an exact ECL version can create a Restricted Party or Restricted Project for a software release.

GitHub issues are discussion/submission threads; review tranche/cohort/audit files are procedural history; the dossier is the version-controlled canonical current evidence/governance record.

## Normalization rule

A normalized dossier must be understandable and auditable without reconstructing its conclusion from historical review files. It records current outcome/scope, ECL criteria, supporting evidence, counter-evidence/exergic institutions, attribution boundaries, adversarial outcome, objective review/removal triggers, stable sources where possible and procedural history. Historical review files may explain how a conclusion was reached, but they must not be required to understand the current dossier. The schema is in `states/_TEMPLATE.md`.

## 2026 factual/adversarial normalization status

Completed phases:

- all 46 States initially classified `R`: whole-State adversarial review and normalization;
- scoped/current `S` work: high-impact review plus scoped tranches 1–10, including second falsification passes for former `R → S` cases;
- full 45-entry `U` phase: `../reviews/2026/adversarial/under-review/full-cohort.md`;
- full 44-entry original-`N` phase: `../reviews/2026/adversarial/no-basis/full-cohort.md`;
- global license-fit audit: `../reviews/2026/consistency/global-license-fit-audit.md`;
- full ECL 0.2 State delta: `../reviews/2026/consistency/ecl-0.2-state-delta.md`.

## Complete State normalization

**195 / 195 State dossiers have completed detailed factual/adversarial normalization at the 2026-08-11 evidence cutoff.**

Every State entry point is intended to be independently auditable without opening historical tranche/cohort records.

## ECL 0.2 delta result

The global consistency audit found that ECL 0.1 under-expressed the non-domination rule already present in the project principles/governance standard. The root `LICENSE` is now **ECL 0.2-DRAFT**; the immutable ECL 0.1 snapshot remains under `../versions/licenses/`.

The full 195-State delta audit against ECL 0.2 is complete. Current provisional distribution:

- **34 `R`**
- **86 `S`**
- **28 `U`**
- **47 `N`**
- **195 total**

Key normative corrections:

- United States: `R → S`, replacing blanket federal-government attribution with identified materially participating federal projects/agencies/units.
- Israel: `R → S`, replacing blanket governmental/legal attribution with identified occupation/security/detention/displacement/discriminatory projects and participating organs.
- Singapore: `S` upheld but narrowed; capital punishment/execution is no longer a standalone ECL basis, while qualifying POFMA/information-control and public-order repression remain in scope.
- All 28 `U` dossiers retained `U` after explicit 0.2 re-read; their uncertainty remains factual/attribution-based rather than merely lexical.
- All 47 `N` dossiers retained `N`.

A dossier that remains `R` or `S` after the delta audit must be read through the exact ECL 0.2 criteria rather than as a generic human-rights rating. Capital punishment, detention, migration policy, conscription, protest regulation and comparable State powers are not standalone ECL categories.

## Next phase

State-by-State evidence normalization and ECL 0.2 delta review are complete. The next governance work is cross-entity reconciliation across State, organization, person and project dossiers, followed by creation of a fresh post-0.2 Schedule candidate. `ECL-RP-0.4-DRAFT` is pre-0.2 historical draft material and should not be patched into apparent compatibility.
