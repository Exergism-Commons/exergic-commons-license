# Exergic Commons License (ECL)

> **Status: Draft 0.2 — experimental source-available ethical software license.**

The **Exergic Commons License (ECL)** is a source-available software license designed to preserve and expand human agency, truthful understanding, reversibility, distributed capacity, and the ability of people and communities to shape their own futures.

ECL grants broad software rights while withholding permission from defined prohibited uses, Restricted Parties and Restricted Projects that materially contribute to coercive capture, systemic domination, deceptive population manipulation, repressive surveillance, unlawful coercive targeting, unlawful political repression or comparable destruction of meaningful agency.

ECL is **not OSI-approved Open Source** and is not intended to satisfy the Open Source Definition.

## Current working draft

`LICENSE` is **ECL 0.2-DRAFT**. It was created after the 2026 State-review consistency audit identified a mismatch between the broader non-domination rule in `spec/PRINCIPLES.md` / `spec/GOVERNANCE.md` and the narrower operative wording of ECL 0.1.

The immutable ECL 0.1 snapshot remains at [`versions/licenses/ECL-0.1.md`](versions/licenses/ECL-0.1.md). It has not been rewritten.

ECL 0.2-DRAFT adds or clarifies:

- an operative systematic-coercive-domination / unlawful-political-repression category consistent with the project principles;
- direct Schedule designation of exact Restricted Projects;
- a narrowly bounded `Independent Remediation Activity` exception for genuinely independent accountability/remedial functions;
- a more explicit designation standard and Schedule-knowability rule; and
- current repository paths and terminology.

The global drafting audit is recorded in [`reviews/2026/consistency/global-license-fit-audit.md`](reviews/2026/consistency/global-license-fit-audit.md), followed by the complete [`ECL 0.2 State delta audit`](reviews/2026/consistency/ecl-0.2-state-delta.md).

## Start here

- [`LICENSE`](LICENSE) — current working license text (ECL 0.2-DRAFT).
- [`schedules/`](schedules/) — versioned Restricted Parties Schedules. A schedule has licensing effect only when a software release expressly incorporates that exact schedule with the exact ECL version.
- [`spec/`](spec/) — principles, governance, terminology and designation standards.
- [`dossiers/`](dossiers/) — per-entity evidence records. Dossiers do not create licensing restrictions by themselves.
- [`reviews/`](reviews/) — adjudication, adversarial-review and consistency-audit history.
- [`registry/`](registry/) — machine-readable governance registry.
- [`versions/`](versions/) — immutable historical license/version snapshots.

## Normative hierarchy

ECL deliberately separates law-like terms from research and governance records:

1. **The exact ECL license text adopted by a software release** defines the operative license terms.
2. **The exact Schedule incorporated by that release** defines its Restricted Parties, Restricted Projects, classes and express exclusions.
3. **`spec/`** governs how future designations are reasoned, reviewed and interpreted, but does not silently create restrictions.
4. **`dossiers/`, `reviews/` and `registry/`** are evidence and governance records. They have no licensing effect unless a Schedule expressly adopts a designation.

No later ECL version or Schedule silently or retroactively changes rights attached to an earlier software release.

## Designation lifecycle

```text
proposal / evidence
        ↓
entity or project dossier
        ↓
adversarial review
        ↓
license-fit / consistency review
        ↓
reasoned governance determination
        ↓
versioned Restricted Parties Schedule
        ↓
explicit incorporation by a software release
        ↓
licensing effect
```

A designation concerns an institutional actor, project or materially participating entity. It does **not** impose guilt by nationality, ethnicity, religion, residence or remote association.

## 2026 State review

The repository contains an ECL-native review of **195 State entities**. Initial adjudication, whole-State adversarial review, scoped `S` review, full `U` review, original-`N` review, detailed dossier normalization and the ECL 0.2 State delta audit are complete.

**195 / 195 State dossiers are self-contained at the 2026-08-11 evidence cutoff.**

After the ECL 0.2 normative delta, the current provisional governance distribution is:

- **34 `R`**
- **86 `S`**
- **28 `U`**
- **47 `N`**
- **195 total**

The delta narrowed the United States and Israel from whole-apparatus `R` to scoped `S` under the narrowest-accurate-attribution rule, and narrowed Singapore's `S` by removing capital punishment/execution as a standalone ECL basis. The 28 `U` cases were all re-read and remained unresolved for factual/attribution reasons rather than merely because ECL 0.1 had narrower wording.

The canonical governance state is [`registry/states.yml`](registry/states.yml). These findings are **not** an operative Restricted Parties Schedule.

## Schedule status

[`schedules/ECL-RP-0.4-DRAFT.md`](schedules/ECL-RP-0.4-DRAFT.md) predates the completed State cycle and ECL 0.2 consistency work. It is historical/pre-0.2 draft material and should **not** be adopted with ECL 0.2-DRAFT.

The next Schedule candidate should be regenerated from the post-delta dossiers after State/organization/person/project reconciliation.

## Why exergism?

ECL uses *exergy* as a normative analogy for effective capacity: capacity that can actually be converted into meaningful, autonomous transformation. The project asks whether technology leaves people able to understand reality, coordinate, choose, dissent, contest decisions, exit systems and create alternatives — or whether those capacities are captured by opaque or coercive structures.

See [`spec/PRINCIPLES.md`](spec/PRINCIPLES.md).

## Legal status

This project is experimental and has not yet received formal legal review sufficient for production use. Ethical-use and actor-based restrictions raise enforceability and compatibility questions that conventional permissive and copyleft licenses do not. Obtain qualified intellectual-property advice before relying on ECL for consequential deployments.

## Versioning

```text
ECL 0.x  → experimental drafts
ECL 1.0  → first stable text after legal and governance review
```

Published license snapshots are immutable. Substantive legal changes require a new ECL version. Schedule changes are separately versioned and non-retroactive.

## Contributing

Legal criticism, contrary evidence, designation challenges, removal requests, adversarial examples and governance improvements are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
