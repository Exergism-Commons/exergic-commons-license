# State dossiers

This directory contains one canonical evidence dossier for each of the **195 State entries** assessed by ECL governance (193 UN Member States, the State of Palestine and the Holy See).

## Filename rule

Files use ISO 3166-1 alpha-3 codes (`USA.md`, `MAR.md`, `CHN.md`, etc.). `PSE.md` is used for the State of Palestine and `VAT.md` for the Holy See.

## Outcome codes

- `R` — State/governing apparatus provisionally Restricted by governance analysis.
- `S` — Restricted with defined scope; only specified organs/projects/systems are implicated.
- `U` — Under Review / evidence presently insufficient for stable restriction.
- `N` — No current State-level basis identified at the evidence cutoff.

These are **governance outcomes, not operative license restrictions**. The operative source is always an expressly incorporated Schedule under `../../schedules/`.

## Canonical schema

Use `_TEMPLATE.md`. A fully normalized dossier contains current determination, ECL criteria, supporting evidence, counter-evidence/exergic institutions, attribution/exclusions, adversarial result, review/removal triggers, sources and procedural history.

## Review precedence

Where historical records conflict, later completed adversarial review controls the dossier's current provisional governance outcome. Historical tranche files remain immutable procedural records and must not be silently rewritten to match later decisions.
