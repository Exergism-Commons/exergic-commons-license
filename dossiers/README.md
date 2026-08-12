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

The complete first-pass State adjudication remains preserved under `../reviews/2026/`. All **46 States initially classified `R`** have been normalized after whole-State adversarial review, including the 11 cases subsequently downgraded to `S`.

Scoped reviews normalized so far:

- high-impact review: United Kingdom, Morocco and Ukraine;
- tranche 1: Denmark, France, Netherlands and Serbia;
- tranche 2: Algeria, Angola, Bahrain, Benin, Bhutan, Bosnia and Herzegovina, Brazil and Cameroon;
- tranche 3: Central African Republic, Colombia, Côte d’Ivoire, Democratic Republic of the Congo, Dominican Republic, Ecuador, Equatorial Guinea and Ethiopia;
- tranche 4: Greece, Guatemala, Guinea-Bissau, Haiti, Honduras, Hungary, Iceland and Indonesia;
- tranche 5: Iraq, Italy, Jordan, Kazakhstan, Kenya, Kyrgyzstan, Laos and Lebanon.

That makes **83 unique State dossiers with completed detailed normalization** at the 2026-08-11 evidence cutoff. Kazakhstan and Kyrgyzstan were already counted among the 46 initially-`R` dossiers normalized during whole-State adversarial review, so tranche 5 adds six new unique normalized dossiers rather than eight.

Remaining State dossiers retain canonical metadata and review links and will be expanded as their reviews are completed.
