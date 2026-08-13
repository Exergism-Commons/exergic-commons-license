# Changelog

## Unreleased

### Repository architecture

- Separated operative license text, specifications, schedules, dossiers, reviews, registry data and immutable versions.
- Moved 2026 adjudication and adversarial-review tranches out of the repository root.
- Introduced canonical per-State dossier entry points for all 195 State dossiers.
- Introduced a machine-readable State governance registry.
- Archived the deprecated global-ranking screening methodology.
- Preserved previous adjudication and adversarial-review records without granting them independent licensing effect.
- Defined normalized dossiers as self-contained canonical records: historical review files remain procedural history and are not required to understand the current determination.
- Preserved the immutable ECL 0.1 snapshot in `versions/licenses/ECL-0.1.md` while advancing the root working text to **ECL 0.2-DRAFT**.

### Governance and evidence

- Whole-State adversarial review of the initial `R` cohort is complete.
- Scoped/project-level adversarial review of the `S` cohort is complete through scoped tranche 10.
- Full adversarial review of all 45 entries that entered the `U` phase is complete in `reviews/2026/adversarial/under-review/full-cohort.md`.
- The `U` phase produced 14 `U → S`, 9 `U → N`, 22 retained `U`, and no `U → R` outcomes.
- Full adversarial review of all 44 States originally classified `N` is complete in `reviews/2026/adversarial/no-basis/full-cohort.md`.
- The original-`N` phase produced 38 retained `N`, 6 `N → U`, and no `N → S/R` outcomes. Austria, Costa Rica, Japan, Nauru, Samoa and South Africa moved to `U`.
- **All 195 State dossiers have completed detailed factual/adversarial normalization** at the 2026-08-11 evidence cutoff.
- Added `reviews/2026/consistency/global-license-fit-audit.md`, which identified a material mismatch between the non-domination standard expressed in `spec/PRINCIPLES.md` / `spec/GOVERNANCE.md` and the narrower operative wording of ECL 0.1.
- Completed `reviews/2026/consistency/ecl-0.2-state-delta.md`, reconciling every State dossier against the exact ECL 0.2-DRAFT language.
- ECL 0.2 State delta result: **34 `R`, 86 `S`, 28 `U`, 47 `N` = 195**.
- United States and Israel were narrowed **`R → S`** because whole-federal/whole-governmental classes were inconsistent with materially independent judicial/audit/remedial functions and the narrowest-accurate-attribution rule.
- Singapore retained `S` but its `capital-punishment/execution` component was removed as a standalone ECL basis; POFMA/information-control and qualifying public-order repression remain the scoped basis.
- All 28 current `U` dossiers were re-read under ECL 0.2 and retained `U`; their unresolved issues are factual, attribution, persistence or remediation questions rather than merely the former drafting gap.

### ECL 0.2-DRAFT

- Added §5.6, **Systematic coercive domination and unlawful political repression**, translating the existing non-domination principle into operative license language while retaining an explicit safeguard for ordinary lawful or merely controversial governmental activity.
- Clarified that capital punishment, detention, deportation, conscription, protest regulation and similar exercises of State power are **not standalone ECL categories**; the Software-enabled use must independently satisfy an operative prohibited-use criterion.
- Renumbered circumvention to §5.7.
- Expanded `Restricted Project` so an exact incorporated Schedule may designate a project directly, in addition to project status arising through Restricted-Party participation, direction, benefit or circumvention.
- Added the narrowly bounded **Independent Remediation Activity** exception for genuinely independent investigation, judicial review, audit, prosecution of official abuse, legal defence, disclosure and remediation, while expressly excluding ordinary operations merely relabelled as compliance or accountability.
- Made the substantive designation threshold and narrowest-accurate-scope rule visible in the operative license, while preserving Schedule knowability for licensees.
- Aligned `spec/GOVERNANCE.md`, `spec/DESIGNATION-STANDARD.md` and `spec/TERMINOLOGY.md` with the ECL 0.2-DRAFT model and current repository paths.

### Schedule status

- `schedules/ECL-RP-0.4-DRAFT.md` predates the completed 195-State adversarial cycle, ECL 0.2 normative audit and State delta audit. It must not be treated as ready for adoption with ECL 0.2-DRAFT.
- The old Draft 0.4 blanket Israel and U.S. federal classes no longer match the canonical post-delta scopes.
- The next Schedule should be regenerated from the post-0.2 determinations rather than patched piecemeal from Draft 0.4.

### Next work

- Reconcile State, organization, person and project designations, especially technology suppliers, government customers, named conflict/security projects and Covered-Associate boundaries.
- Audit exact class knowability, controlled-entity treatment and duplicate/overlapping designations.
- Generate a fresh post-0.2 Schedule candidate from the reconciled governance records.
- Define stable governance decision mechanics, conflict-of-interest rules and dissent documentation.
- Obtain specialist legal review before proposing stable ECL 1.0, including patent, termination/reinstatement, Schedule-incorporation, hosted-service and cross-jurisdiction enforceability questions.

No item in this changelog changes an incorporated license or Restricted Parties Schedule retroactively.
