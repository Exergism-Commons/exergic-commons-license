# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal entities.
- `persons/` — specifically designated natural persons where necessary.
- `projects/` — project/program-specific records.

A dossier has **no licensing effect by itself**. Only a versioned Schedule under `../schedules/` can designate a Restricted Party for licensing purposes.

GitHub issues are discussion/submission threads; review tranche files are procedural history; the dossier is the version-controlled canonical current record.

## Normalization rule

A normalized dossier must be understandable and auditable without reconstructing its conclusion from historical review files. It records current outcome/scope, ECL criteria, supporting evidence, counter-evidence/exergic institutions, attribution boundaries, adversarial outcome, objective review/removal triggers, stable sources where possible and procedural history. Historical tranches may explain how a conclusion was reached, but they must not be required to understand the current dossier. The schema is in `states/_TEMPLATE.md`.

## 2026 normalization status

The complete first-pass State adjudication remains preserved under `../reviews/2026/`.

Completed adversarial/normalization phases:

- all 46 States initially classified `R`: whole-State adversarial review and normalization;
- current `S` cohort: scoped/high-impact review through scoped tranche 10, including second falsification passes for former `R → S` cases;
- full 45-entry `U` cohort: reviewed together in `../reviews/2026/adversarial/under-review/full-cohort.md`.

The `U`-cohort review produced **14 `U → S`, 9 `U → N`, 22 retained `U`, and 0 `U → R`**. Forty-one previously minimal `U` dossiers were expanded into self-contained canonical records. Honduras, Lebanon, Nepal and Trinidad and Tobago were already self-contained from earlier scoped downgrades and were revalidated without rewriting their historical tranche records.

There are now **151 unique State dossiers with completed detailed normalization** at the 2026-08-11 evidence cutoff.

The remaining normalization workload is exactly the **44 States that were already `N` in the initial adjudication**. Once those are normalized, all 195 State entry points will be independently auditable without requiring the historical review files.
