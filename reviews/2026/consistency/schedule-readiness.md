# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-13**

## 1. Question

Can the current post-ECL-0.2 governance records be converted directly into a new Restricted Parties Schedule without creating vague or unknowable licensing obligations?

**Answer: not yet.** The State and core non-State evidence cycles are sufficiently mature to generate Schedule candidates, but many current `S` scopes still need a final **identity/class translation**. An evidence finding such as `border apparatus`, `police project`, `security/detention systems` or `specified enforcement structures` is appropriate in a dossier but may be too ambiguous to bind a downstream licensee.

A new Schedule must therefore be generated only from entries that pass both:

1. **substantive ECL fit**, already tested in the 0.2 State delta / cross-entity review; and
2. **knowability**, meaning a reasonable licensee can determine whether the actor/project is included without reconstructing political institutions or historical evidence.

## 2. Current governance inventory

### States

Post-0.2 delta:

- `R`: 34
- `S`: 86
- `U`: 28
- `N`: 47

Only `R`/`S` are potential Schedule inputs. `U` and `N` have no restriction effect.

### Organizations

Current registry:

- `R`: Al-Qaida; ISIL/Da'esh; Izz al-Din al-Qassam Brigades; Rapid Support Forces.
- `S`: NSO Group; Candiru; Intellexa/Predator network; Hamas; Sudanese Armed Forces; SDF/RADA.
- `U`: Palantir Technologies Inc.

### Projects

- `R`: Mitiga Prison / SDF-RADA detention apparatus.
- `S`: Operation Epic Fury — Minab school targeting chain.
- `U`: ICE ICM/Investigative Analytics; Maven Smart System.

### Persons

- No current `R` or `S` person candidate.
- Osama Elmasry Njeem remains `U` under the heightened person-level standard.

## 3. Schedule-readiness levels

### Level A — identity substantially knowable; candidate can be drafted now

Examples:

- Al-Qaida — exact UN permanent reference can serve as an identity anchor while the ECL basis remains independent.
- ISIL/Da'esh — exact current UN identity/aliases can be frozen in the Schedule.
- Izz al-Din al-Qassam Brigades — named organization with explicit aliases and scope.
- Rapid Support Forces — named armed organization; undefined `associated forces` must be excluded.
- Mitiga Prison / SDF-RADA detention apparatus — exact project/facility/organization relationship defined in canonical dossiers.
- Operation Epic Fury — Minab targeting chain — named incident/project scope with express exclusion of the rest of the operation.

These entries still require legal-drafting review but are not blocked on basic identity.

### Level B — substantive finding is mature but legal-identity/class translation is still required

Examples:

- NSO Group / Candiru — exact Schedule legal entity names, jurisdictions and successor/control treatment should be frozen rather than relying only on trade names.
- Intellexa/Predator network — dossier is mature, but the Schedule must list Intellexa S.A., Intellexa Limited, Cytrox AD, Cytrox Holdings ZRT, Thalestris Limited and any separately justified enablers by exact legal name rather than `Intellexa Consortium`.
- Hamas — the `S` scope must identify armed-command/hostage/detention structures or other reasonably determinable organizational classes and state what civilian/political functions are excluded.
- SAF — must remain synchronized with the canonical Sudan State scope and must not duplicate or broaden it.
- SDF/RADA — exact aliases/organizational boundary and relationship to Mitiga must be stated.
- United States / Israel State `S` findings — blanket whole-government classes are explicitly rejected by the State delta; a future Schedule must name exact agencies/projects/classes rather than resurrect the old Draft 0.4 wording.

### Level C — current governance scope is too descriptive for direct Schedule use

A substantial portion of the 86 State `S` findings use dossier-appropriate descriptions such as:

- police/public-order apparatus;
- detention/correctional system;
- border/migration enforcement;
- intelligence/security project;
- military/state-aligned operations;
- media/civic-control systems; or
- discriminatory/administrative project.

Those findings are substantively reviewed, but before licensing effect they need a **Schedule Translation Record** identifying one or more of:

1. exact ministry/agency/unit legal name;
2. named programme/system/project;
3. objectively determinable controlled class;
4. precise capacity limitation; and
5. explicit exclusions/remediation functions.

A generic State institution label should not become law-like Schedule text merely because it is understandable to researchers.

## 4. State `R` readiness

The 34 current `R` outcomes are stronger candidates for apparatus-level classes because their normalized dossiers found qualifying conduct central/cross-institutional to the relevant governing or coercive apparatus.

Even here, the Schedule should not simply write `Government of X` where the dossier actually means a de facto military authority, Taliban governing apparatus, junta/security apparatus or other narrower governing structure.

Each `R` requires a one-line **identity freeze** specifying the exact apparatus/class intended and any materially independent remedial exclusion that can be stated without undermining knowability.

## 5. State `S` translation requirement

The 86 `S` dossiers are **not failed or unfinished evidence records**. Their final remaining problem is translation from evidence/governance language into contract-readable identity.

The next Schedule-preparation pass should create one `Schedule Translation Record` per current `S` State containing:

```yaml
state: ISO3
outcome: S
candidate_parties:
  - exact legal name or objectively determinable class
candidate_projects:
  - exact named project/program where applicable
capacity_limit: ...
exclusions:
  - ...
criteria:
  - ECL-0.2 §5.x
identity_sources:
  - official registry / statute / agency page
status: ready | needs-identity | needs-project-boundary
```

This should be machine-readable before the Schedule itself is drafted.

## 6. External-list rule

The next Schedule will **not** contain blanket classes such as:

- `all actors on the UN ISIL/Al-Qaida list`; or
- `all public ICC atrocity-warrant subjects`.

UN/ICC records may provide authoritative identity/evidence, but ECL must make its own substantive and scope decision. External lists can change under different criteria and cannot silently mutate an ECL Schedule after release.

If a future Schedule uses an external identifier, it must freeze the exact named entry/reference as of the Schedule's adoption date rather than incorporate an automatically updating list by reference.

## 7. Supplier/project rule

The Schedule should not list a supplier as a Restricted Party merely because it participates in a sensitive government programme.

Current examples:

- Palantir Technologies Inc. remains `U` at organization level.
- ICE ICM/IA remains `U` at project level.
- Maven Smart System remains `U` at project level.
- Minab's targeting chain is independently `S` without attributing that strike to Palantir/Maven absent evidence.

This prevents contractual association from becoming guilt by procurement graph.

## 8. Person-level rule

No person is currently Schedule-ready. The old ICC-warrant class is not carried forward.

A person-level entry requires an individualized ECL dossier and heightened review. A warrant/charge may be evidence but is not criminal guilt and is not automatically the ECL threshold.

## 9. Schedule generation gate

A fresh post-0.2 Schedule candidate should be generated only after:

- all 34 State `R` identity freezes are completed;
- all 86 State `S` Schedule Translation Records are completed;
- Level-B organization identities/scopes are frozen;
- State↔organization/project duplicate scopes are reconciled;
- candidate classes are tested for objective membership/knowability; and
- the candidate Schedule explicitly declares compatibility with **ECL 0.2-DRAFT only** unless later re-audited.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 draft material and must not be patched into apparent readiness.

## 10. Next executable artifact

Create a machine-readable **`registry/schedule-translations.yml`** containing all current `R`/`S` State translation records plus the non-State Level-A/Level-B candidates. The Schedule should then be rendered from that registry rather than manually maintained as a parallel source of truth.
