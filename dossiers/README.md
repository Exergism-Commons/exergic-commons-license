# Evidence dossiers

Dossiers are the canonical per-entity entry points for ECL evidence, counter-evidence, scope analysis, determinations and future review.

- `states/` — 195 State dossiers plus the canonical State schema.
- `organizations/` — companies, organizations and other legal entities.
- `persons/` — specifically designated natural persons where necessary.
- `projects/` — project/program-specific records.

A dossier has **no licensing effect by itself**. Only a versioned Schedule under `../schedules/` can designate a Restricted Party for licensing purposes.

GitHub issues are discussion/submission threads; review tranche files are procedural history; the dossier is the version-controlled canonical current record.

## Normalization rule

A normalized dossier should be understandable without reconstructing its conclusion from historical review files. It records:

1. current outcome and exact scope;
2. ECL criteria engaged;
3. supporting evidence and attribution;
4. counter-evidence / exergic institutions;
5. exclusions and attribution boundaries;
6. adversarial outcome;
7. objective review/removal triggers;
8. principal sources; and
9. procedural history.

The schema is in `states/_TEMPLATE.md`.

## 2026 normalization status

The complete first-pass State adjudication remains preserved under `../reviews/2026/`. All **46 States initially classified `R`** have now been normalized after whole-State adversarial review, including the 11 cases subsequently downgraded to `S`. The high-impact scoped dossiers for the United Kingdom, Morocco and Ukraine and the first scoped algorithm/surveillance tranche (Denmark, France, Netherlands and Serbia) are also normalized.

Remaining State dossiers retain their canonical metadata and review links and will be expanded as their scoped/under-review/no-current-basis reviews are completed.
