# Exergic Commons License (ECL)

> **Status: Draft 0.1 — not yet recommended for production licensing.**

The **Exergic Commons License (ECL)** is an experimental **source-available ethical software license** grounded in exergist principles: preserving and expanding human agency, truthful understanding, reversibility, distributed capacity, and the ability of people and communities to shape their own futures.

ECL is designed for authors who want to publish source code broadly while withholding permission for uses, projects, or actors that materially contribute to coercive capture, systemic domination, deceptive manipulation, repressive surveillance, or comparable reductions of human agency.

## Important classification

ECL is **not an Open Source Initiative (OSI) approved license and is not intended to satisfy the Open Source Definition**. Its ethical restrictions discriminate between uses and, in some cases, actors or projects. Projects using ECL should describe themselves as **source-available**, not OSI open source.

## Repository structure

- [`LICENSE`](LICENSE) — current working license text.
- [`versions/ECL-0.1.md`](versions/ECL-0.1.md) — immutable draft snapshot of version 0.1.
- [`EXERGIC-PRINCIPLES.md`](EXERGIC-PRINCIPLES.md) — philosophical principles that inform the license.
- [`EXERGIC-GOVERNANCE.md`](EXERGIC-GOVERNANCE.md) — procedure for evaluating prohibited uses, restricted parties, associates, and projects.
- [`RESTRICTED-PARTIES.md`](RESTRICTED-PARTIES.md) — versioned schedule of specifically designated parties.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to propose changes to the license and governance documents.

## Design goals

ECL aims to make restrictions **specific, knowable, reviewable, and non-retroactive**. The license therefore separates:

1. **Prohibited Uses** — conduct that is incompatible with the license regardless of who performs it.
2. **Restricted Parties** — specifically designated entities or individuals.
3. **Covered Associates** — persons or entities materially acting for, controlled by, or providing material support to a Restricted Party in the relevant project or use.
4. **Restricted Projects** — projects materially involving, serving, or benefiting a Restricted Party or Covered Associate.

Designation of a Restricted Party is governed by a documented process. A later schedule does not retroactively change the rights attached to a previously released software version unless that software version expressly incorporated the later schedule.

## Why exergism?

In this project, *exergy* is used as a normative analogy for effective capacity: not merely stored potential, but potential that can actually be converted into meaningful, autonomous action. Exergist software ethics therefore focuses on whether technology expands or captures the capacity of people and communities to understand reality, coordinate, choose, dissent, exit, and create alternatives.

See [`EXERGIC-PRINCIPLES.md`](EXERGIC-PRINCIPLES.md) for the working philosophical model.

## Legal status

This repository contains an experimental license draft, not legal advice. Software licensing and enforceability vary by jurisdiction, and ethical-use restrictions create questions that conventional permissive and copyleft licenses do not. Before relying on ECL for consequential software, obtain review from a qualified intellectual-property lawyer in the relevant jurisdictions.

## Versioning

The intended format is:

```text
Exergic Commons License 0.x   -> experimental drafts
Exergic Commons License 1.0   -> first stable text after legal/community review
```

License text already attached to a software release should remain immutable. Substantive changes produce a new ECL version.

## Contributions

Discussion, legal criticism, adversarial review, examples, and proposed wording are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
