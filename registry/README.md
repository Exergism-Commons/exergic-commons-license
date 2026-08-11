# Machine-readable registry

`states.yml` mirrors the current **provisional governance outcomes** for all 195 State dossiers using ISO 3166-1 alpha-3 identifiers.

It is designed for tooling, validation, documentation generation and future APIs. It is **not a Restricted Parties Schedule** and has no licensing effect.

Each ISO3 entry resolves to `../dossiers/states/{ISO3}.md`. The exact human-readable dossier and the exact versioned Schedule remain authoritative for their respective purposes.

The registry is currently grouped by outcome to keep the file compact and auditable. Counts must equal the number of ISO3 identifiers in each group and the four groups must be mutually exclusive.