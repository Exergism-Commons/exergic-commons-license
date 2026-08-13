# Changelog

## Unreleased

### Repository architecture

- Separated operative license text, specifications, schedules, dossiers, reviews, registry data and immutable versions.
- Moved 2026 adjudication and adversarial-review tranches out of the repository root.
- Introduced canonical per-State dossier entry points for all 195 State dossiers.
- Introduced machine-readable State governance and Schedule-translation registries.
- Added canonical schemas and machine-readable registries for organization, person and project dossiers.
- Archived the deprecated global-ranking screening methodology.
- Preserved previous adjudication and adversarial-review records without granting them independent licensing effect.
- Defined normalized dossiers as self-contained canonical records: historical review files remain procedural history and are not required to understand the current determination.
- Preserved the immutable ECL 0.1 snapshot in `versions/licenses/ECL-0.1.md` while advancing the root working text to **ECL 0.2-DRAFT**.

### State governance and evidence

- Whole-State adversarial review of the initial `R` cohort is complete.
- Scoped/project-level adversarial review of the `S` cohort is complete through scoped tranche 10.
- Full adversarial review of all 45 entries that entered the `U` phase is complete in `reviews/2026/adversarial/under-review/full-cohort.md`.
- Full adversarial review of all 44 States originally classified `N` is complete in `reviews/2026/adversarial/no-basis/full-cohort.md`.
- **All 195 State dossiers have completed detailed factual/adversarial normalization** at the 2026-08-11 evidence cutoff.
- Added `reviews/2026/consistency/global-license-fit-audit.md`, identifying a material mismatch between the non-domination standard expressed in project principles/governance and the narrower ECL 0.1 operative wording.
- Completed `reviews/2026/consistency/ecl-0.2-state-delta.md`, reconciling every State dossier against ECL 0.2-DRAFT.
- Current post-delta State governance: **34 `R`, 86 `S`, 28 `U`, 47 `N` = 195**.
- United States and Israel were narrowed **`R → S`** because blanket whole-government classes conflicted with materially independent judicial/audit/remedial functions and the narrowest-accurate-attribution rule.
- Singapore retained `S` but its `capital-punishment/execution` component was removed as a standalone ECL basis.
- All 28 current `U` dossiers retained `U` after explicit 0.2 re-read; residual uncertainty remains factual/attribution/persistence/remediation-based rather than merely lexical.

### ECL 0.2-DRAFT

- Added §5.6, **Systematic coercive domination and unlawful political repression**, translating the existing non-domination principle into operative license language while retaining explicit safeguards for ordinary lawful or merely controversial governmental activity.
- Clarified that capital punishment, detention, deportation, conscription, protest regulation and similar State powers are **not standalone ECL categories**; a Software-enabled use must independently satisfy an operative prohibited-use criterion.
- Renumbered circumvention to §5.7.
- Expanded `Restricted Project` so an exact incorporated Schedule may designate a project directly.
- Added the narrowly bounded **Independent Remediation Activity** exception.
- Made the substantive designation threshold, narrowest-accurate-scope rule and Schedule knowability visible in the operative license.
- Aligned `spec/GOVERNANCE.md`, `spec/DESIGNATION-STANDARD.md` and `spec/TERMINOLOGY.md` with the ECL 0.2-DRAFT model; `R/S/U/N` terminology is now defined across State, organization, project and person dossiers.

### Cross-entity reconciliation

- Added `reviews/2026/consistency/cross-entity-reconciliation.md` and rejected the Draft 0.4 assumption that prior non-State Schedule entries remain valid without canonical dossiers.
- Added organization/project/person templates and lifecycle rules.
- Added `registry/organizations.yml`, `registry/projects.yml` and `registry/persons.yml`.
- Current core organization registry: **4 `R`, 6 `S`, 1 `U`**.
- Current core project registry: **1 `R`, 1 `S`, 2 `U`**.
- Current person registry: **1 `U`; no person-level `R/S` candidate**.
- Palantir Technologies Inc. changed from old whole-company Draft-0.4 restriction to **`U` organization-level review**; ICE ICM/IA and Maven Smart System are separate `U` projects pending prohibited-use evidence.
- NSO Group and Candiru are scoped `S` commercial-spyware organization candidates based on direct official evidence tying supplied spyware to malicious targeting/transnational repression.
- Added an Intellexa/Predator network `S` dossier; a future Schedule must name exact legal entities rather than an undefined consortium label.
- Al-Qaida and ISIL/Da'esh are `R` organization candidates, but the full dynamically updating UN sanctions list is **not** automatically imported into ECL.
- Hamas was narrowed to `S`; Izz al-Din al-Qassam Brigades is an `R` organization candidate.
- Rapid Support Forces is an `R` organization candidate; Sudanese Armed Forces is `S` and must remain synchronized with the canonical Sudan State scope.
- SDF/RADA is a scoped `S` organization candidate; Mitiga Prison/SDF-RADA detention apparatus is an `R` project candidate.
- Osama Elmasry Njeem remains `U` after heightened person-level review; the old `all public ICC atrocity-warrant subjects` class is rejected as an automatic ECL rule.
- Operation Epic Fury's Minab targeting chain is a scoped `S` project candidate without inferring Palantir/Maven participation absent evidence.

### Schedule readiness

- `schedules/ECL-RP-0.4-DRAFT.md` is historical/pre-0.2 draft material and must not be adopted with ECL 0.2-DRAFT.
- Added `reviews/2026/consistency/schedule-readiness.md`.
- Added `registry/schedule-translations.yml` as the machine-readable work queue for Schedule generation.
- Added `registry/schedule-state-r-freeze.yml`: **all 34 current State `R` candidates now have frozen candidate apparatus identities** and common exclusions for population/nationality, independent private actors, unrelated non-controlled entities and qualifying Independent Remediation Activity.
- The main remaining Schedule gate is translation of all **86 State `S` outcomes** into exact agencies, units, named projects or objectively determinable classes with capacity limits and exclusions.
- External UN sanctions and ICC warrant records are identity/evidence sources, not automatically updating ECL classes.
- A supplier is not Restricted merely because it supplies a sensitive customer; project-level Material Participation and prohibited-use evidence control.

### Next work

- Complete the 86 State-`S` Schedule Translation Records and freeze exact identities/project boundaries.
- Reconcile State ↔ organization/project duplicate scopes and exact controlled-entity treatment.
- Render a fresh post-0.2 Schedule only from translation records that pass knowability; do not patch Draft 0.4.
- Define stable governance decision mechanics, conflict-of-interest rules and dissent documentation.
- Obtain specialist legal review before proposing stable ECL 1.0, including patent, termination/reinstatement, Schedule-incorporation, hosted-service and cross-jurisdiction enforceability questions.

No item in this changelog changes an incorporated license or Restricted Parties Schedule retroactively.
