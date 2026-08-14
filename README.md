# Exergic Commons License (ECL)

> **Status: ECL 0.2-DRAFT — experimental source-available license.**

ECL is an experimental software-license project focused on human agency, contestability, reversibility and distributed capacity. It is **not OSI-approved Open Source** and is not intended to satisfy the Open Source Definition.

## Canonical sources

- [`LICENSE`](LICENSE) — current working license text.
- [`spec/`](spec/) — principles, governance, terminology and designation standard.
- [`dossiers/`](dossiers/) — canonical evidence/governance records.
- [`reviews/`](reviews/) — adjudication, adversarial-review and consistency history.
- [`registry/`](registry/) — machine-readable governance, translation, freeze and override data.
- [`schedules/`](schedules/) — exact versioned Schedules.
- [`versions/`](versions/) — immutable historical snapshots.

The immutable ECL 0.1 snapshot is [`versions/licenses/ECL-0.1.md`](versions/licenses/ECL-0.1.md). The root `LICENSE` is ECL 0.2-DRAFT.

## 2026 State corpus

Detailed review and normalization are complete for **195 / 195** State dossiers.

Current provisional governance after applying the State outcome override layers:

- **34 `R`**
- **80 `S`**
- **34 `U`**
- **47 `N`**
- **195 total**

Read `registry/states.yml`, then apply all `registry/state-outcome-overrides*.yml` in lexical order. The override layer has precedence until the next consolidated snapshot.

## Schedule engineering

Draft [`schedules/ECL-RP-0.4-DRAFT.md`](schedules/ECL-RP-0.4-DRAFT.md) is historical/pre-0.2 material. [`schedules/ECL-RP-0.5-PARTIAL-DRAFT.md`](schedules/ECL-RP-0.5-PARTIAL-DRAFT.md) is a non-operative rendering test.

Current State Schedule status:

- **34 / 34 `R`** identity freezes complete;
- all **80 active `S`** dossiers have completed Schedule translation;
- **79 / 80 active `S`** have at least one Schedule-renderable frozen entry;
- **1 `S`** remains in current-status / public-knowability review (`LAO`); and
- **0 `S`** remain blocked merely because identity/project translation is unfinished.

The 2026-08-14 five-gate revalidation froze narrow current projects for Iraq (`IRQ`) and the Philippines (`PHL`), downgraded Bulgaria (`BGR`) and Colombia (`COL`) from `S` to `U` rather than inferring continuing restrictability, and left Laos (`LAO`) as the sole active-`S` factual/knowability gate because the fresh public evidence deliberately withholds the identity needed for a defensible Schedule entry.

Canonical progress sources:

- [`registry/schedule-progress-overrides.yml`](registry/schedule-progress-overrides.yml)
- [`registry/schedule-status-overrides.yml`](registry/schedule-status-overrides.yml)
- [`registry/schedule-state-r-freeze.yml`](registry/schedule-state-r-freeze.yml)
- `registry/schedule-state-s-freezes/`
- [`registry/schedule-organization-freezes.yml`](registry/schedule-organization-freezes.yml)
- [`registry/schedule-armed-organization-freezes.yml`](registry/schedule-armed-organization-freezes.yml)
- [`registry/schedule-project-freezes.yml`](registry/schedule-project-freezes.yml)

`tools/render_schedule.py` renders a non-operative candidate from frozen records, and Schedule CI validates the current State coverage before producing the artifact.

A Schedule entry may be narrower than the dossier supporting it. Residual unfrozen scope remains governance-only.

## Non-State records

Canonical organization, project and person sources:

- [`registry/organizations.yml`](registry/organizations.yml)
- [`registry/projects.yml`](registry/projects.yml)
- [`registry/persons.yml`](registry/persons.yml)

External lists may serve as evidence or identity anchors but are not automatically imported as mutable ECL classes.

## Release model

```text
evidence → dossier → adversarial review → consistency review
        → Schedule translation → identity/project freeze
        → generated Schedule candidate → legal/internal review
        → explicit release incorporation
```

No dossier, review or registry entry has licensing effect by itself. Only an exact Schedule expressly incorporated with an exact ECL version can have licensing effect for a release.

## Legal status

ECL remains experimental and has not yet received specialist legal review sufficient for production use. Obtain qualified intellectual-property advice before relying on it for consequential deployments.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for challenges, contrary evidence and governance contributions.
