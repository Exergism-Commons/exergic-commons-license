# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal entities.
- `persons/` — specifically designated natural persons where necessary.
- `projects/` — project/program-specific records.

A dossier has **no licensing effect by itself**. Only an exact Schedule expressly incorporated with an exact ECL version can create a Restricted Party or Restricted Project for a software release.

GitHub issues are discussion/submission threads; review tranche/cohort files are procedural history; the dossier is the version-controlled canonical current evidence/governance record.

## Normalization rule

A normalized dossier must be understandable and auditable without reconstructing its conclusion from historical review files. It records current outcome/scope, ECL criteria, supporting evidence, counter-evidence/exergic institutions, attribution boundaries, adversarial outcome, objective review/removal triggers, stable sources where possible and procedural history. Historical review files may explain how a conclusion was reached, but they must not be required to understand the current dossier. The schema is in `states/_TEMPLATE.md`.

## 2026 factual/adversarial normalization status

Completed phases:

- all 46 States initially classified `R`: whole-State adversarial review and normalization;
- scoped/current `S` work: high-impact review plus scoped tranches 1–10, including second falsification passes for former `R → S` cases;
- full 45-entry `U` phase: `../reviews/2026/adversarial/under-review/full-cohort.md`;
- full 44-entry original-`N` phase: `../reviews/2026/adversarial/no-basis/full-cohort.md`.

The `U`-phase review produced **14 `U → S`, 9 `U → N`, 22 retained `U`, and 0 `U → R`**.

The original-`N` review produced **38 retained `N`, 6 `N → U`, and 0 `N → S/R`**. Austria, Costa Rica, Japan, Nauru, Samoa and South Africa moved to `U`.

## Complete State normalization

**195 / 195 State dossiers have completed detailed factual/adversarial normalization at the 2026-08-11 evidence cutoff.**

Every State entry point is intended to be independently auditable without opening historical tranche/cohort records.

## ECL 0.2 normative delta phase

The global consistency audit in `../reviews/2026/consistency/global-license-fit-audit.md` found that ECL 0.1 under-expressed the non-domination rule already present in the project principles/governance standard. The root `LICENSE` is now **ECL 0.2-DRAFT**; the immutable ECL 0.1 snapshot remains under `../versions/licenses/`.

The factual/adversarial dossier results have **not** been mass-rewritten merely because the draft changed. The current registry remains provisional at `R 36 / S 84 / U 28 / N 47` until the exact 0.2 delta audit is complete.

That delta audit maps every current dossier to the exact operative draft criteria and tests whether its scope should be upheld, narrowed, moved to `U/N`, or re-opened. Priority consistency families include capital punishment, detention, migration/forced transfer, public-order repression and the new Independent Remediation Activity boundary.

A dossier that remains `R` or `S` after the delta audit should identify an exact ECL 0.2 criterion rather than rely on a generic statement that conduct is a serious human-rights concern.
