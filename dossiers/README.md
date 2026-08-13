# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal entities.
- `persons/` — specifically designated natural persons where necessary.
- `projects/` — project/program-specific records.

A dossier has **no licensing effect by itself**. Only a versioned Schedule under `../schedules/` can designate a Restricted Party for licensing purposes.

GitHub issues are discussion/submission threads; review tranche/cohort files are procedural history; the dossier is the version-controlled canonical current record.

## Normalization rule

A normalized dossier must be understandable and auditable without reconstructing its conclusion from historical review files. It records current outcome/scope, ECL criteria, supporting evidence, counter-evidence/exergic institutions, attribution boundaries, adversarial outcome, objective review/removal triggers, stable sources where possible and procedural history. Historical review files may explain how a conclusion was reached, but they must not be required to understand the current dossier. The schema is in `states/_TEMPLATE.md`.

## 2026 normalization status

The complete first-pass State adjudication remains preserved under `../reviews/2026/`.

Completed adversarial/normalization phases:

- all 46 States initially classified `R`: whole-State adversarial review and normalization;
- scoped/current `S` work: high-impact review plus scoped tranches 1–10, including second falsification passes for former `R → S` cases;
- full 45-entry `U` phase: `../reviews/2026/adversarial/under-review/full-cohort.md`;
- full 44-entry original-`N` phase: `../reviews/2026/adversarial/no-basis/full-cohort.md`.

The `U`-phase review produced **14 `U → S`, 9 `U → N`, 22 retained `U`, and 0 `U → R`**.

The original-`N` review produced **38 retained `N`, 6 `N → U`, and 0 `N → S/R`**. Austria, Costa Rica, Japan, Nauru, Samoa and South Africa moved to `U` because current developments defeated a confident no-basis finding while attribution, deployment or the exact ECL §5 prohibited-use nexus remained insufficient for `S`.

## Complete State normalization

**195 / 195 State dossiers now have completed detailed normalization at the 2026-08-11 evidence cutoff.**

Every State entry point is therefore intended to be independently auditable without opening the historical tranche/cohort records. `U` now means genuinely unresolved after review; `N` means no current ECL-prohibited State/project basis under the narrower operative §5 standard, not ethical endorsement.

The next phase is a global cross-dossier consistency audit, especially for whether each `S` scope is tied to the actual prohibited-use categories in `LICENSE` §5 rather than to a general human-rights concern. That audit is followed by normative governance changes, Schedule design/freeze and specialist legal review before any stable ECL 1.0 adoption.
