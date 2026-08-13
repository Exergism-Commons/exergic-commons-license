# Exergic Commons License (ECL)

> **Status: ECL 0.2-DRAFT — experimental source-available license.**

ECL is an experimental software-license project focused on preserving human agency, contestability, reversibility and distributed capacity. It is **not OSI-approved Open Source** and is not intended to satisfy the Open Source Definition.

## Canonical sources

- [`LICENSE`](LICENSE) — current working license text.
- [`spec/`](spec/) — principles, governance, terminology and designation standard.
- [`dossiers/`](dossiers/) — canonical evidence/governance records.
- [`reviews/`](reviews/) — adjudication, adversarial-review and consistency history.
- [`registry/`](registry/) — machine-readable governance, Schedule translation and freeze data.
- [`schedules/`](schedules/) — exact versioned Schedules; only an exact Schedule expressly incorporated with an exact license version can have licensing effect.
- [`versions/`](versions/) — immutable historical snapshots.

The immutable ECL 0.1 snapshot is [`versions/licenses/ECL-0.1.md`](versions/licenses/ECL-0.1.md). The root `LICENSE` is ECL 0.2-DRAFT.

## 2026 State corpus

The factual/adversarial review, dossier normalization and ECL 0.2 State delta are complete for **195 / 195** State dossiers at the 2026-08-11 evidence cutoff.

Current provisional governance distribution:

- **34 `R`**
- **86 `S`**
- **28 `U`**
- **47 `N`**

The canonical machine-readable source is [`registry/states.yml`](registry/states.yml). These are governance outcomes only.

## Schedule engineering

Draft [`schedules/ECL-RP-0.4-DRAFT.md`](schedules/ECL-RP-0.4-DRAFT.md) is historical/pre-0.2 material and is not synchronized with ECL 0.2-DRAFT.

Current State Schedule-engineering status:

- **34 / 34 `R`** identity freezes complete;
- **86 / 86 `S`** translation records complete;
- **19 `S`** fully frozen;
- **18 additional `S`** have at least one precise renderable subset;
- **3 `S`** require current-status/remediation revalidation; and
- **46 `S`** still require an exact identity/project-boundary freeze.

Therefore **37 / 86 State `S` dossiers currently have at least one Schedule-renderable entry**.

Live sources:

- [`registry/schedule-translations.yml`](registry/schedule-translations.yml)
- [`registry/schedule-state-r-freeze.yml`](registry/schedule-state-r-freeze.yml)
- `registry/schedule-state-s-freezes/`
- [`registry/schedule-project-freezes.yml`](registry/schedule-project-freezes.yml)
- [`reviews/2026/consistency/schedule-readiness.md`](reviews/2026/consistency/schedule-readiness.md)

A future Schedule may render a precisely frozen subset while leaving residual dossier scope non-operative. This is intentional: evidence language is not automatically contract language.

## Non-State records

Canonical organization, project and person records now have dedicated schemas, dossiers and registries:

- [`registry/organizations.yml`](registry/organizations.yml)
- [`registry/projects.yml`](registry/projects.yml)
- [`registry/persons.yml`](registry/persons.yml)

External lists may be used as evidence or identity anchors but are not automatically imported as mutable ECL classes.

## Release model

```text
evidence → dossier → adversarial review → consistency review
        → Schedule translation → identity/project freeze
        → versioned Schedule → explicit release incorporation
```

No dossier, review or registry entry has licensing effect by itself. Published license snapshots and incorporated Schedules are versioned and non-retroactive.

## Legal status

ECL remains experimental and has not yet received specialist legal review sufficient for production use. Obtain qualified intellectual-property advice before relying on it for consequential deployments.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for challenges, contrary evidence and governance contributions.
