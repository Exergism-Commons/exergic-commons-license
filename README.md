# Exergic Commons License (ECL)

> **Status: Draft 0.1 — experimental source-available ethical software license.**

The **Exergic Commons License (ECL)** is a source-available software license designed to preserve and expand human agency, truthful understanding, reversibility, distributed capacity, and the ability of people and communities to shape their own futures.

ECL grants broad software rights while withholding permission from defined prohibited uses, Restricted Parties and Restricted Projects that materially contribute to coercive capture, systemic domination, deceptive population manipulation, repressive surveillance, unlawful coercive targeting or comparable destruction of meaningful agency.

ECL is **not OSI-approved Open Source** and is not intended to satisfy the Open Source Definition.

## Start here

- [`LICENSE`](LICENSE) — current working license text.
- [`schedules/`](schedules/) — versioned Restricted Parties Schedules. A schedule has licensing effect only when a software release expressly incorporates that exact schedule.
- [`spec/`](spec/) — principles, governance, terminology and designation standards.
- [`dossiers/`](dossiers/) — per-entity evidence records. Dossiers do not create licensing restrictions by themselves.
- [`reviews/`](reviews/) — adjudication and adversarial-review history.
- [`registry/`](registry/) — machine-readable governance registry.
- [`versions/`](versions/) — immutable historical license/version snapshots.

## Normative hierarchy

ECL deliberately separates law-like terms from research and governance records:

1. **`LICENSE`** defines the operative license terms.
2. **The exact Schedule incorporated by a software release** defines its Restricted Parties.
3. **`spec/`** governs how future designations are reasoned, reviewed and interpreted, but does not silently create restrictions.
4. **`dossiers/`, `reviews/` and `registry/`** are evidence and governance records. They have no licensing effect unless a later Schedule expressly adopts a designation.

No later Schedule silently or retroactively changes rights attached to an earlier software release.

## Designation lifecycle

```text
proposal / evidence
        ↓
entity dossier
        ↓
adversarial review
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

The repository contains an ECL-native review of 195 State entities. The current governance status is provisional and remains subject to adversarial review. See [`reviews/2026/`](reviews/2026/) and the per-State records in [`dossiers/states/`](dossiers/states/).

These findings are **not** the operative Restricted Parties Schedule.

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