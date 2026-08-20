# Canonical Dossier Migration Contract

Status: normative repository curation specification.

## Supported non-State universe

Canonical per-entity dossier coverage applies to `Agency`, `Institution`, `Organization`, `Person`, `Project`, and `Deployment` ABox records stored as `.json` or `.jsonld` under `knowledge/entities/`. `Deployment` uses the `dossiers/projects/` surface, which is the repository home for project/program/deployment dossiers.

Every supported non-State identity must point to an existing type-appropriate dossier whose frontmatter `id` is exactly `ECL-<entity-id>`. When `entity` and `entity_type` frontmatter fields are present they must match the ABox name and type. This binding applies to the complete non-State universe, including identities that already had dedicated dossiers before the versioned migration ledger began.

## Append-only ledger

Migration manifests are named exactly `canonical-entity-dossier-migration-v<N>.json`, where `N` is a positive decimal integer with no sign, decimal point, leading-zero alias or alternate spelling. Payloads conform to `schemas/canonical-entity-dossier-migration.schema.json`.

The historical v1-v49 prefix is immutable. Later manifests append contiguously. A new supported non-State identity added after closure must arrive atomically with its dedicated dossier and a new manifest row. Existing identities may be migrated only from a non-dedicated pointer to a type-appropriate dedicated dossier, preserving the comparison-base source dossier and changing no ABox field except `dossier`.

## State-context snapshot semantics

`stateContext` is an **immutable migration-time snapshot** of the referenced State dossier's `provisional_outcome` when a manifest row is appended. It is provenance metadata, not a live alias for the State dossier.

A newly appended manifest row MUST match the referenced State dossier outcome at append time. Once that manifest becomes historical, later living-governance changes to the State dossier MUST NOT require rewriting the historical `stateContext` snapshot. Current governance is always read from the current State dossier; historical canonical visuals remain evidence of the migration snapshot and never propagate governance to the non-State identity.

This separation prevents a living State outcome change from deadlocking an immutable migration ledger.

## Canonical generated visuals

For every migration row `<ID>`, `visuals` is exactly:

- `dossiers/assets/generated/<ID>-status.svg`
- `dossiers/assets/generated/<ID>-evidence.svg`

No alternate path can satisfy the canonical visual contract. This ensures the assets referenced by dossiers are the same bytes regenerated and compared deterministically in CI.

Generated SVG semantics must be statically demonstrable. Text hidden by clipping, masks, filters, off-canvas positioning or unsupported indirection cannot satisfy required visual tokens.

## Source facsimiles

`dossiers/evidence-images/` is reserved for provenance-controlled **raster** source facsimiles. Allowed asset formats are PNG, JPEG and WebP. Each asset requires its sibling JSON metadata sidecar and must satisfy `schemas/evidence-image-metadata.schema.json` plus byte-hash checks.

SVG is intentionally excluded from the source-facsimile surface because SVG can reference active or remote resources whose rendered pixels are not fixed by hashing the wrapper bytes. Derived repository SVGs belong only under `dossiers/assets/generated/`.

Unknown image/media extensions in `dossiers/evidence-images/` fail closed rather than bypassing metadata validation.

## Adversarial testing

Canonical CI must exercise both the valid corpus and negative mutation fixtures. Tests cover at least:

- wrong baseline identity-to-dossier binding;
- `Deployment` inclusion;
- malformed manifest filenames and non-integer numeric fields;
- non-canonical visual paths;
- new-row State snapshot mismatch while allowing historical snapshot drift;
- unsupported/sidecarless source facsimiles;
- SVG facsimile rejection;
- clipped or otherwise non-verifiably-visible semantic text; and
- a complete post-v49 atomic-addition fixture crossing the base-relative ledger and provenance guards.
