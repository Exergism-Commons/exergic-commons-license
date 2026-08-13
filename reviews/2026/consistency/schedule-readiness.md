# ECL 0.2 Schedule Readiness Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / RELEASE-READINESS RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-13**

## 1. Current answer

Can the current post-ECL-0.2 governance records be converted directly into an adoptable Restricted Parties Schedule without vague or unknowable obligations?

**Not yet.** Substantive State review and Schedule translation are complete, but identity/project-boundary freeze is incomplete for part of the scoped `S` cohort.

The gate now separates two questions that Draft 0.4 incorrectly mixed together:

1. **Does the evidence support an ECL restriction?** — completed for the State corpus.
2. **Can a reasonable licensee determine exactly who/what is restricted from the Schedule text itself?** — complete for all State `R` candidates and only part of State `S` candidates.

## 2. State governance inventory

Post-ECL-0.2 State delta:

- `R`: **34**
- `S`: **86**
- `U`: **28**
- `N`: **47**
- total: **195**

Only `R`/`S` are potential Schedule inputs. `U` and `N` have no restriction effect.

## 3. State Schedule translation status

### `R` cohort

**34 / 34 identity freezes complete.**

`registry/schedule-state-r-freeze.yml` translates each current `R` dossier into a candidate governing/coercive apparatus class and carries common exclusions for:

- population/nationality;
- independent private actors;
- unrelated non-controlled entities; and
- qualifying Independent Remediation Activity.

The special de facto/military/transitional cases are frozen as those actual apparatuses rather than generic `Government of X` labels.

### `S` cohort

**86 / 86 Schedule Translation Records complete.**

The records are distributed across:

- `registry/schedule-state-s-translations.yml` — first 20;
- `registry/schedule-state-s-batches/batch-03-security-political.yml`;
- `batch-04-conflict-security.yml`;
- `batch-05-civic-security.yml`;
- `batch-06-detention-political.yml`;
- `batch-07-security-civic.yml`;
- `batch-08-conflict-detention.yml`; and
- `batch-09-final.yml`.

A direct status audit of those records yields:

- **18 `S` translations sufficiently knowable for draft Schedule rendering now**;
- **68 `S` translations requiring one or more additional identity/project freezes**.

The ready count is based on the actual record `status` values, not batch metadata. A prior intermediate aggregate overcounted the first two batches by one; this audit corrects that bookkeeping error before Schedule generation.

The 68 blocked/partial records are **not unresolved ECL outcomes**. Each remains `S`; the remaining problem is contract engineering such as the exact:

- agency/unit legal name;
- detention facility;
- prosecution/case;
- statutory provision and implementing authority;
- public-order operation;
- surveillance deployment;
- controlled proxy relationship; or
- project/temporal boundary.

## 4. Examples of State `S` entries already sufficiently knowable

Current ready translations include examples such as:

- Denmark — Udbetaling Danmark / ATP implicated welfare-profiling workflows;
- France — national algorithmic video-surveillance experiment in its qualifying capacity;
- Serbia — BIA/Interior units only in evidenced repressive spyware/mobile-forensic deployments;
- Armenia — Police biometric/facial-recognition surveillance capacity;
- Dominican Republic — DGM/CESFRONT only in qualifying deportation/detention operations;
- Lithuania — State Border Guard Service only in qualifying pushback/protection-access operations;
- Poland — Border Guard / Interior administration only in the frozen Belarus-border protection-access project;
- Angola — Rapid Intervention / National Police units only in frozen qualifying operations;
- Benin — HAAC/CRIET only in exact protected-expression enforcement processes;
- DRC — FARDC / specifically State-backed proxy project only where support/control is frozen;
- Ecuador — named `Exterminio Total` operation subject to final participating-unit freeze on rendering;
- Guatemala — Ministerio Público/FECI only in exact arbitrary-criminalisation cases;
- Haiti — Security Task Force / materially participating PNH or contractors only in the frozen unlawful-drone/summary-execution project;
- Jordan — State Security Court/security-prosecution, Media Commission and governor detention functions only in the frozen qualifying capacities;
- Lesotho — Lesotho Correctional Service only in the defined coercive detention/conditions project;
- Nigeria — Imo State Police Anti-Kidnapping Unit (`Tiger Base`) in the documented detention/torture/disappearance project;
- Singapore — POFMA/public-order project class with independent judicial review and capital punishment expressly excluded; and
- Sudan — SAF only through the synchronized cross-entity scoped organization record.

Final legal drafting can still narrow any of these further; `ready` means identity/boundary is sufficiently knowable to render a candidate, not that the entry is legally approved.

## 5. Non-State inventory

### Organizations

Current canonical registry:

- `R`: Al-Qaida; ISIL/Da'esh; Izz al-Din al-Qassam Brigades; Rapid Support Forces.
- `S`: NSO Group; Candiru; Intellexa/Predator network; Hamas; Sudanese Armed Forces; SDF/RADA.
- `U`: Palantir Technologies Inc.

Several scoped organization candidates still require exact legal-entity, alias or organizational-boundary freeze before Schedule rendering.

### Projects

- `R`: Mitiga Prison / SDF-RADA detention apparatus.
- `S`: Operation Epic Fury — Minab school targeting chain.
- `U`: ICE ICM/Investigative Analytics; Maven Smart System.

The Minab record intentionally does **not** infer Palantir/Maven participation absent project-specific evidence.

### Persons

No person is currently `R` or `S`. Osama Elmasry Njeem remains `U` under the heightened person-level standard. The old blanket ICC-warrant class is not carried forward.

## 6. External-list rule

The replacement Schedule will **not** dynamically import:

- the full UN ISIL/Al-Qaida sanctions list; or
- all public ICC warrant subjects.

UN/ICC records are authoritative evidence/identity inputs, but ECL makes its own substantive/scope decision. If an external identifier is used, the exact named entry/reference must be frozen as of Schedule adoption rather than incorporating a mutable third-party list by reference.

## 7. Supplier/project rule

Sensitive contracting is not guilt by procurement graph.

Current examples:

- Palantir Technologies Inc. remains `U` at organization level;
- ICE ICM/IA remains `U` at project level;
- Maven Smart System remains `U` at project level; and
- Minab's targeting chain is independently `S` without attributing that strike to Palantir/Maven absent evidence.

A supplier becomes restricted only through an exact entity designation or the operative Material Participation / Covered Associate rules for a qualifying project.

## 8. Schedule generation gate

A fresh post-0.2 Schedule should be rendered as **adoptable** only after:

- State `R` identity freeze — **complete 34/34**;
- State `S` translation — **complete 86/86**;
- State `S` identity/project freeze — **18 ready / 68 still to freeze**;
- scoped non-State legal identities/aliases are frozen;
- State↔organization↔project overlaps are deduplicated;
- candidate controlled classes pass objective-membership/knowability review; and
- the resulting Schedule explicitly declares compatibility with **ECL 0.2-DRAFT only**, unless later re-audited.

`ECL-RP-0.4-DRAFT` remains historical/pre-0.2 draft material and must not be patched into apparent readiness.

## 9. Current executable work queue

The machine-readable source of truth is `registry/schedule-translations.yml`.

The next work is no longer `translate all S dossiers`; that phase is complete. The current queue is **resolve the 68 explicit State-`S` freeze blockers plus the remaining scoped non-State identity blockers**. Only after those blockers are resolved should a fresh Schedule be rendered from the registries.
