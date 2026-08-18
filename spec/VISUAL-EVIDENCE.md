# Visual Evidence and Dossier Rendering

Status: normative repository curation specification.

## Purpose

ECL dossiers may contain visual material to make provenance, scope, evidence gaps and governance context easier to audit. Visuals are subordinate to the cited record: they do not create facts, Claims, relations, Material Participation, or governance outcomes.

## Evidence classes

### 1. Source facsimile

A screenshot, scan, photograph, map, chart or figure copied from an external evidentiary source.

A source facsimile may be committed only when repository storage/reuse is permitted and the asset has a sidecar metadata record containing at least:

- `sourceUrl`
- `capturedAt`
- `contentSha256`
- `licenseBasis` or a documented repository-use basis
- `propositions` or dossier sections the image supports
- `transformation` (`none`, `crop`, `redaction`, or another precisely described change)

Cropping or redaction must never change the evidentiary meaning. A remote image must not be hot-linked from dossier Markdown as a substitute for provenance control.

If storage/reuse is not justified, keep the external citation and describe the visual evidence in text; do not copy the image into the repository.

### 2. Derived evidence diagram

A repository-generated diagram that visualizes already-curated dossier content, for example:

`source surface -> curated proposition -> entity identity -> attribution boundary`

Derived diagrams MUST:

- say that they are derived;
- preserve a textual equivalent in the dossier;
- identify source granularity as direct, partial or otherwise explicit;
- never manufacture a Claim/EvidenceItem record;
- never imply `partOf`, control, operation, participation, supply, command, membership, culpability or Material Participation by graphical adjacency.

### 3. Derived chart

A chart generated from versioned repository data.

A derived chart MUST identify its data source and generation method. Ordinal position, bar length, area, saturation or other visual magnitude must not be used as an undocumented proxy for culpability or severity.

## State-context palette

The canonical machine-readable palette is `../knowledge/generated/dossier-visual-palette-v1.json`.

| State | Meaning | Color |
|---|---|---|
| `R` | Restricted | `#B42318` |
| `S` | Scoped restriction | `#E67E22` |
| `U` | Under review / unresolved | `#D4A017` |
| `N` | No restriction | `#2E7D32` |
| unknown | Insufficient information | `#667085` |

The palette is a rendering vocabulary, **not a severity or culpability scale**.

Color MUST NOT be the sole carrier of meaning. Every state color must be accompanied by the state letter and a human-readable label.

For a non-State entity, an `R/S/U/N` color may represent a referenced State dossier only when the visual labels it as **State dossier context**. It must also state that there is **no entity-level governance inheritance**. A State outcome is never copied into a non-State dossier's frontmatter `provisional_outcome`.

## Accessibility

Committed SVG evidence visuals must include:

- `<title>`
- `<desc>`
- meaningful Markdown alt text
- a textual equivalent in the dossier

Visual interpretation must remain possible in monochrome or for readers who cannot distinguish the palette colors.

## Layout bounds and text overflow

Dynamic SVG text MUST remain inside the visual region that owns it. It must never rely on an assumed browser font metric or be allowed to paint into a later column, arrow, badge or annotation.

The canonical renderer therefore uses two independent protections:

1. **deterministic wrapping** with conservative font-width estimates and bounded line counts; and
2. **hard SVG `clipPath` guards** around every dynamic name, source, proposition, identity, boundary and palette-label region.

The clip is the fail-closed guarantee: even if a browser substitutes a font whose glyph metrics are wider than the renderer's estimate, text cannot render beyond the owning box. Wrapping is the readability layer above that hard bound.

If bounded content cannot fit within the permitted line count, the rendered line may be ellipsized. The full text MUST remain available in the dossier or versioned manifest and, for entity names, in SVG metadata.

`tools/check_dossier_visual_layout.py` validates the committed and regenerated SVGs in CI, including clip geometry, clip assignment and maximum wrapped-line counts. A generated asset that loses its hard overflow guard fails CI.

## AI-generated and decorative imagery

AI-generated, reconstructed or decorative imagery is not evidence and MUST NOT be placed in an evidence section or stored under a path that implies evidentiary status.

Illustrative imagery may be used elsewhere only when explicitly labeled non-evidentiary and when it cannot reasonably be mistaken for a source photograph, document, chart or event record.

## Deterministic generation

`tools/render_dossier_visuals.py` renders the canonical derived SVGs from versioned migration manifests and the palette file.

CI regenerates those assets and compares them byte-for-byte with the committed versions. Manual edits to generated SVGs are therefore rejected.

## Canonical dossier boundary

A State dossier may be provenance for an Agency, Institution, Organization, Person or Project, but it is not that entity's canonical per-entity dossier.

The migration ratchet in `knowledge/generated/canonical-entity-dossier-migration-v*.json` measures dedicated dossier coverage. `tools/check_canonical_entity_dossiers.py` validates migrated entities, dossier paths, visual requirements, frontmatter and the no-inheritance boundary.
