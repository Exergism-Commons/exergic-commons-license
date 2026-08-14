# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-14**

## Current answer

A post-ECL-0.2 Schedule candidate **can be generated from frozen records**, but it is **not yet ready for adoption**. State identity/project translation and the identity-freeze queue are complete. After the five-gate current-status review, only one active-`S` State remains non-renderable: Laos (`LAO`), where fresh evidence preserves `S` but public source protection prevents an objectively knowable Schedule identity.

## State inventory

Current State governance after applying all `registry/state-outcome-overrides*.yml` in lexical order is:

- `R`: **34**
- `S`: **80**
- `U`: **34**
- `N`: **47**
- total: **195**

The outcome overlays have precedence over the base State registry until the next consolidated snapshot. Cyprus (`CYP`), Bulgaria (`BGR`) and Colombia (`COL`) are no longer active `S` records after current-status revalidation carried their `S -> U` decisions into machine-readable outcome overlays.

## Schedule engineering status

### `R`

**34 / 34 identity freezes complete.**

Source: `registry/schedule-state-r-freeze.yml`.

### `S`

All **80 active `S`** dossiers have completed Schedule translation.

Current freeze/readiness status:

- **19** fully frozen;
- **60** additional active `S` records with at least one precise renderable subset;
- **79 / 80** active `S` States therefore have at least one Schedule-renderable frozen entry;
- **1** active `S` State remains behind a current-status/public-knowability gate; and
- **0** remain blocked merely because identity or project-boundary translation is unfinished.

The sole remaining factual/status queue is: `LAO`.

Canonical aggregate counts are maintained in `registry/schedule-progress-overrides.yml`, which supersedes stale aggregate State-`S` progress numbers in `registry/schedule-translations.yml`. Explicit renderer blocking is maintained in `registry/schedule-status-overrides.yml`.

## Narrowed-subset rule

A Schedule entry may be narrower than its governance dossier. A precise frozen subset can be rendered while residual scope remains governance-only.

A renderable subset requires:

1. objectively knowable identity or project boundary;
2. explicit capacity limitation;
3. explicit exclusions;
4. Material Participation as the connection rule; and
5. no silent incorporation of residual dossier scope.

## Revalidation rule

Solved identity does not prove current restrictability. If a system, measure, facility or project may have been suspended, invalidated, remediated or materially changed, current-status review must complete before Schedule rendering. Conversely, current concern alone is insufficient where the public identity needed for a Schedule entry is intentionally redacted or otherwise unknowable.

ECL does not infer continuing abuse, non-investigation or non-remediation merely because a later public update cannot be found.

## Five-gate current-status revalidation — 2026-08-14

### Bulgaria (`BGR`) — `S -> U`

The 2025 Zaharna Fabrika eviction and Bulgaria-Türkiye border record remain serious governance evidence. However, Zaharna Fabrika was a completed event followed by material accommodation/remediation measures, and the current 2026 record does not identify a sufficiently narrow new Bulgarian border operation/unit with present abusive attribution. Preserving `S` would therefore require inferring continuity from earlier evidence. `BGR` is downgraded to `U` and remains monitored for re-escalation.

### Colombia (`COL`) — `S -> U`

The 2025 398-conflict dataset remains strong evidence that military-jurisdiction claims can interfere with ordinary accountability. Official 2026 Constitutional Court records confirm recurring jurisdiction disputes, but the exact cases reviewed are constitutionally corrected, procedurally supervised or lack a sufficiently authoritative later public status establishing a currently unremediated obstruction. A generic Military Criminal Justice restriction would over-include lawful judicial functions. `COL` is therefore downgraded to `U` pending a fresh named obstruction project or case-level current-status mapping.

### Iraq (`IRQ`) — narrow renderable freeze

The 2025-26 cohort transferred from northeast-Syrian detention facilities provides a finite project boundary. Iraqi Supreme Judicial Council records identify the Karkh First Investigation Court and a designated investigation site; contemporary human-rights evidence raises project-specific torture, coercive-interrogation and safeguard concerns. `registry/schedule-state-s-freezes/batch-22b-irq-freeze.yml` freezes only the materially participating abusive custodial/interrogation capacities of that Al-Karkh transferred-detainee project. Lawful custody, prosecution, courts, juvenile protection, medical care, defence, review and unrelated Iraqi detention/security functions are excluded.

### Philippines (`PHL`) — narrow renderable freeze

Official 2026 NAPOLCOM material identifies six Station Drug Enforcement Unit personnel from Malate Police Station 9 arrested after a 28 January 2026 Barangay San Isidro, Makati incident involving an allegedly unauthorized anti-drug operation, armed threats, restraint and robbery. `registry/schedule-state-s-freezes/batch-22a-phl-freeze.yml` freezes only that incident and its materially participating alleged abusive functions. It is not a finding of individual criminal guilt and does not restrict PNP, MPD, the station, SDEUs or anti-drug enforcement generally. Dismissal, acquittal or material attribution changes trigger review.

### Laos (`LAO`) — sole remaining gate

Fresh reporting from 29 June 2026 states that six young Christians remained detained after December 2025 arrests in northern Laos and were being pressured to renounce Christianity. That preserves a current `S` governance concern. The source deliberately withholds the village, district and detainees' identities for their safety. ECL will not reverse-engineer or guess those protected identities, and therefore cannot produce an objectively knowable Schedule freeze from that record.

The separate Sisay Luangmonda/Bao Mor Khaen disappearance/death case remains relevant, but no sufficiently authoritative post-March public update was found establishing that the reported lack of investigation remains current. Silence is not treated as proof of continuing non-remediation.

## Current freeze registries

State `S` freeze records are maintained under `registry/schedule-state-s-freezes/`. Direct-project freezes are maintained in `registry/schedule-project-freezes.yml`. Organization and armed-organization freezes are maintained in their dedicated Schedule registries.

`registry/schedule-translations.yml` is a base index/work-queue snapshot, not the current aggregate source of truth once later progress/status overlays apply.

## Direct-project rule

ECL 0.2 may designate an exact Restricted Project directly without converting its entire parent institution into a Restricted Party. This is preferred where project identity is more precise than institutional identity.

## Schedule generation gate

`tools/render_schedule.py` renders a deterministic, non-operative Schedule candidate from frozen registries. The renderer applies all `state-outcome-overrides*.yml` in lexical order so later outcome layers cannot be silently ignored.

A generated candidate is not adoption-ready until every included entry passes:

- identity/project knowability;
- overlap and duplicate-scope reconciliation;
- controlled-class membership review;
- remediation/exclusion synchronization;
- internal legal-consistency review; and
- exact ECL-version compatibility review.

Schedule CI independently validates active `R`/`S` coverage against the canonical progress overlays before rendering the candidate.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 material. `ECL-RP-0.5-PARTIAL-DRAFT` remains non-operative test material.

## Current queue

Immediate State work is now **1 factual/public-knowability review and 0 identity/project-freeze translations**: `LAO`.

If that gate can be resolved with a precise public identity, it should be frozen narrowly. If reliable remediation or contrary evidence instead defeats the current `S`, it should be narrowed or downgraded. The Schedule remains non-operative and non-adoptable until the broader consistency, deduplication, controlled-class, remediation, legal/internal and exact-version release gates also pass.
