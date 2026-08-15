# ECL Versioning, Channels and Exact Bundles

> **Status: Draft governance/release specification.** This document does not modify the operative `LICENSE`. ECL remains experimental and requires specialist legal review before production reliance.

## 1. Core rule

ECL separates a continuously maintained knowledge/governance system from immutable legal artifacts.

```text
mutable world
  -> Evidence / Claims
  -> KnowledgeSnapshot
  -> ExergicAssessment
  -> GovernanceDecision
  -> ScheduleRelease
  -> ECLBundle = exact LicenseRelease + exact ScheduleRelease
```

The governing invariant is:

> **Knowledge may change; decisions are versioned; released Schedules and license texts are immutable; a software release resolves an exact ECL Bundle.**

A later fact, assessment, decision, Schedule or license version MUST NOT silently rewrite the terms attached to an already released copy of software.

## 2. Four meanings of "current"

Do not collapse these states:

1. **Knowledge state** — latest accepted facts/claims and their temporal validity.
2. **Analytical state** — latest formal Exergism assessment for a scoped object.
3. **Governance state** — latest accepted `R/S/U/N` decision and scope.
4. **Operative state** — exact Schedule entry incorporated by the exact ECL Bundle attached to a software release.

Accordingly, `currentGovernance(actor)` and `operativeStatus(actor, bundle)` may legitimately differ.

## 3. KnowledgeSnapshot

A `KnowledgeSnapshot` freezes the exact input state used for governance/release reproducibility. It MUST identify at least:

- exact Git commit;
- canonical SHA-256 over the Git-native ABox source records;
- OWL TBox SHA-256;
- evidence cutoff date; and
- creation timestamp.

The generated RDF serialization is disposable. Snapshot identity binds canonical Git sources and hashes, not a particular Turtle blank-node serialization.

## 4. GovernanceDecision

A governance decision records a reviewed conclusion for an exact subject and scope. It SHOULD identify:

- subject/object;
- outcome (`R`, `S`, `U`, `N` through named ontology individuals);
- exact scope and exclusions;
- relied-upon assessment(s) and claims;
- rationale;
- review/adoption date;
- decision it supersedes, if any.

A `GovernanceDecision` changes the **current governance view** after adoption. It does not retroactively mutate any released Schedule.

## 5. LicenseRelease

A `LicenseRelease` is an immutable exact legal text artifact.

For stable ECL releases, use semantic versioning discipline:

- `MAJOR`: materially incompatible change to grant, obligations, restrictions, definitions or legal model;
- `MINOR`: compatible normative addition/clarification that is still legally substantive;
- `PATCH`: non-substantive editorial/corrective change only.

Because legal compatibility can be ambiguous, any substantive uncertainty SHOULD be treated conservatively as at least a MINOR change and reviewed before release.

Every released license artifact MUST be content-addressable by SHA-256 and retained immutably.

## 6. ScheduleRelease

A `ScheduleRelease` is an immutable exact Restricted Parties/Projects Schedule.

Schedules are versioned independently from the core license. Prefer calendar versioning:

```text
ECL-RP-YYYY.MM.DD.N
```

where `N` is an optional same-day sequence number.

A Schedule release MUST identify the `KnowledgeSnapshot` from which it was prepared and the exact accepted decisions supporting its entries.

A later Schedule never edits an older Schedule in place.

## 7. ECLBundle

An `ECLBundle` is the exact pair that a software release actually incorporates:

```text
ECLBundle = LicenseRelease + ScheduleRelease
```

Canonical display form SHOULD be similar to:

```text
ECL-1.0.0@RP-2026.10.02.1
```

Every Bundle manifest MUST contain immutable identifiers and SHA-256 hashes for its License and Schedule components.

An `operative: true` Bundle MUST additionally content-address the immutable completed legal-review record required by [`LEGAL-ADVERSARIAL-REVIEW.md`](LEGAL-ADVERSARIAL-REVIEW.md). That review record binds the exact candidate License plus the exact reviewed incorporation/versioning model and Bundle schema. A non-operative draft/candidate MAY omit the legal-review component, but it remains explicitly non-operative.

This Bundle identity is the unit that downstream tooling, SBOMs, archives and compliance records should resolve.

## 8. Publisher policy versus resolved legal state

ECL distinguishes a **publisher policy file** from an **exact lock file**.

### `ecl.toml`

Declares what the publisher wants to follow.

Example:

```toml
mode = "follow-stable"
license = "1.x"
schedule = "latest-compatible"
channel = "stable-1"
```

### `ecl.lock`

Records exactly what was resolved for a particular software release, including whether that resolved Bundle is operative.

Example of an operative lock:

```toml
bundle = "ECL-1.0.2@RP-2026.10.02.1"
operative = true
license = "ECL-1.0.2"
license_sha256 = "..."
schedule = "ECL-RP-2026.10.02.1"
schedule_sha256 = "..."
legal_review = "ECL-1.0.2-legal-review-1"
legal_review_sha256 = "..."
resolved_at = "2026-10-03T09:10:00Z"
```

A lock produced through an explicit draft-resolution path MUST carry `operative = false`; omitting a completed legal-review record does not turn that draft into a stable/operative Bundle.

A published software release SHOULD preserve its exact lock information or equivalent immutable metadata.

## 9. Resolution modes

### 9.1 `pinned`

The publisher selects an exact immutable bundle.

```toml
mode = "pinned"
bundle = "ECL-1.0.0@RP-2026.08.20.1"
```

Nothing moves automatically.

### 9.2 `follow-stable`

Recommended rolling policy for publishers that want current ECL governance.

At the time a **new software release is prepared**, tooling resolves the newest compatible stable bundle and writes an exact `ecl.lock`.

An already published software release remains bound to its previous exact bundle.

### 9.3 `latest-stable`

Resolves the newest stable ECL line. A change across an ECL MAJOR version MUST require explicit opt-in/confirmation; tooling MUST NOT silently cross a major legal boundary.

### 9.4 Draft/candidate channels

Draft or candidate channels are explicitly non-operative unless and until a particular artifact is formally released and incorporated. Tooling MUST refuse to present a draft/candidate bundle as stable. If tooling provides an explicit draft-resolution escape hatch for testing, the resulting lock MUST preserve `operative = false`.

## 10. Mutable channels, immutable targets

Channels are convenience pointers:

```text
stable
stable-1
candidate
draft
```

A channel MAY move. The artifact to which it points MUST NOT.

For example:

```text
stable-1 -> ECL-1.0.0@RP-2026.09.01.1
stable-1 -> ECL-1.0.0@RP-2026.09.14.1
```

is valid over time, while both exact bundle manifests remain immutable and retrievable.

Before ECL 1.0, the repository MUST NOT fabricate a `stable` channel merely for convenience.

## 11. `or-later` is not `follow-stable`

These concepts are deliberately separate:

- `follow-stable` is a **publisher tooling policy**: resolve the latest acceptable bundle when preparing a new software release.
- `or-later` would be a **license grant option** allowing a licensee to elect a later ECL version.

ECL does not acquire `or-later` semantics merely because tooling supports `follow-stable`. Any future `or-later` mechanism requires explicit operative-license language and legal review.

## 12. Update propagation

When accepted evidence changes the living system:

```text
new EvidenceItem / Claim
  -> affected assessment(s)
  -> GovernanceDecision if review changes outcome/scope
  -> generated current registry view
  -> Schedule revalidation ticket if operative scope may be stale
```

If a new Schedule is approved, a new immutable `ScheduleRelease` is created. Existing bundles remain unchanged.

Projects using `follow-stable` adopt the new Schedule only when they next resolve a software release.

## 13. Emergency corrections

A materially wrong current Schedule is a high-priority governance event, not permission to rewrite history.

Emergency handling SHOULD:

1. mark the current channel target as superseded/withdrawn for future resolution;
2. publish a corrected new immutable Schedule release;
3. move relevant mutable channel pointers;
4. preserve the flawed historical artifact and provenance;
5. notify downstream users where practicable.

Whether legal rescission or other remedies are possible for previously granted rights is a legal question outside automated ontology inference and requires qualified review.

## 14. Source-of-truth hierarchy

For living knowledge/governance:

```text
Git-native ABox + OWL TBox + accepted decision records
    -> generated RDF/SPARQL views
    -> generated registry views
```

For an exact software release:

```text
exact ECLBundle manifest
    -> exact LicenseRelease
    -> exact ScheduleRelease
    -> immutable legal-review record when operative
```

No mutable channel, registry, dossier, ticket or current Web view may override the exact immutable artifacts recorded in an already resolved bundle.

## 15. Release gate

A bundle may be marked `operative: true` only when all required release gates are satisfied, including:

- immutable license artifact exists;
- immutable Schedule artifact exists;
- hashes match;
- Schedule provenance resolves to reviewed governance decisions;
- required CI/integrity checks pass;
- the legal adversarial review required by [`LEGAL-ADVERSARIAL-REVIEW.md`](LEGAL-ADVERSARIAL-REVIEW.md) is complete for the exact release-candidate text and Schedule-incorporation mechanism;
- the Bundle content-addresses that completed immutable legal-review record;
- the legal-review record binds the exact License hash, exact reviewed `VERSIONING.md` incorporation model and exact reviewed Bundle schema;
- no unresolved legal-review `BLOCKER` remains, and every `MAJOR` finding is resolved, narrowed or explicitly accepted as a documented jurisdictional limitation/risk under that review process;
- every required minimum jurisdiction track and every mandatory legal attack surface has a recorded disposition;
- any separate internal release review required by project policy is complete; and
- the bundle manifest is itself immutable/versioned.

Release tooling MUST reject `operative: true` when the legal-review record is absent, its content hash fails, it targets a different License or reviewed incorporation artifact, or its machine-verifiable gate state is incomplete.

A maintainer self-review, AI review, automated check or general community approval does not by itself satisfy the independent qualified legal-review minimum defined by `LEGAL-ADVERSARIAL-REVIEW.md`.

Until those conditions are met, the artifact remains draft/candidate and MUST NOT be surfaced as stable by ECL tooling.
