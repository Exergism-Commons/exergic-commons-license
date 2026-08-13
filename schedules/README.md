# Restricted Parties Schedules

This directory contains exact, versioned ECL Schedule artifacts.

A dossier, review or registry record has no licensing effect by itself. Only an exact Schedule expressly incorporated with an exact ECL version can affect a release.

## Current artifacts

- `ECL-RP-0.4-DRAFT.md` — historical pre-ECL-0.2 draft; do not treat it as synchronized with the current root license.
- `ECL-RP-0.5-PARTIAL-DRAFT.md` — non-operative post-0.2 rendering test; deliberately incomplete and not adoption-ready.

## Current Schedule sources

Use the current machine-readable sources under `../registry/`, in particular:

- `state-outcome-overrides.yml`
- `schedule-progress-overrides.yml`
- `schedule-status-overrides.yml`
- `schedule-state-r-freeze.yml`
- `schedule-state-s-freezes/`
- `schedule-organization-freezes.yml`
- `schedule-armed-organization-freezes.yml`
- `schedule-project-freezes.yml`

`../tools/render_schedule.py` renders a non-operative candidate from frozen records. Unfrozen or factual-review scope must remain omitted.

Schedules are separately versioned from the license text and are non-retroactive.
