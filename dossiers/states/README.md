# State dossiers

This directory contains one canonical dossier for each of the 195 State entries assessed by ECL governance.

Files use ISO 3166-1 alpha-3 codes. `PSE.md` is used for the State of Palestine and `VAT.md` for the Holy See.

`R`, `S`, `U` and `N` are provisional governance outcomes only; they are not operative license restrictions.

## Current sources

All State dossiers are normalized and self-contained.

For current aggregate State outcomes, read `../../registry/states.yml` and then apply every `../../registry/state-outcome-overrides*.yml` in lexical order.

For Schedule preparation, use:

- `../../registry/schedule-progress-overrides.yml`
- `../../registry/schedule-status-overrides.yml`
- `../../registry/schedule-state-r-freeze.yml`
- `../../registry/schedule-state-s-freezes/`

A Schedule entry may be narrower than its supporting dossier. Residual unfrozen scope remains governance-only.

Use `_TEMPLATE.md` for dossier structure. Historical review records remain immutable procedural history; later completed review/override records control current governance state.
