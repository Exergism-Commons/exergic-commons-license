# ECL Living Update System

> **Status: Draft governance/data architecture.** This system has no licensing effect by itself. Automated signals and tickets are review inputs, never automatic designations.

## 1. Problem

ECL cannot remain credible if actor/project status is periodically rewritten by hand from a static list. A living governance system must answer, reproducibly:

1. what exact actor, project, deployment or institution is being discussed;
2. what new fact changed;
3. when the fact became true or ceased to be true;
4. which source establishes or disputes it;
5. which ECL criterion and formal-Exergism variables could be affected;
6. whether the change is material enough to require re-analysis;
7. what prior assessment/decision it supersedes or leaves intact; and
8. what downstream records must be updated.

GitHub Issues are useful for discussion, assignment and public review, but they are not a database. The canonical state must remain versioned, structured repository data.

## 2. Architecture

The living system uses five layers:

```text
external sources / scheduled review clocks
              |
              v
         Update Signal
      (machine detected)
              |
              v
         Update Case
   (deduped canonical event)
              |
              v
       Evidence Claims
(provenance + validity + grade)
              |
              v
 semantic graph / Exergism assessment
              |
              v
 governance decision -> dossier -> generated registry -> Schedule candidate
```

### 2.1 Semantic identity layer

Stable IDs represent entities and reviewable objects independent of names:

- `STATE-USA`
- `ORG-NSO-GROUP`
- `PERSON-...`
- `PROJECT-ICE-ICM-INVESTIGATIVE-ANALYTICS`
- `INSTITUTION-...`
- `DEPLOYMENT-...`

Names and aliases may change; IDs do not.

### 2.2 Claim layer

Facts are stored as atomic, temporally qualified claims rather than buried only in prose. A claim says, in effect:

```text
subject --predicate--> object/value
       valid during [from, to]
       supported/disputed by evidence items
```

Examples:

- project `P` **is suspended** from date `D`;
- organization `A` **controls** organization `B` during a stated period;
- agency `A` **deploys** project `P`;
- court `C` **invalidated** deployment `P`;
- oversight body `O` **found** a specified validation defect;
- project `P` **materially affects** a defined population.

Claims can be `candidate`, `accepted`, `disputed`, `rejected`, or `superseded`.

### 2.3 Update-case layer

An `UpdateCase` is the canonical equivalent of a ticket. GitHub Issues are a human-facing projection of this record.

An update case has a stable fingerprint and lifecycle:

```text
detected
  -> deduped
  -> triage
  -> evidence-qualified
  -> analysis-required | no-material-change
  -> analyzed
  -> governance-review-required | resolved
  -> applied | rejected | superseded
```

Closing a GitHub Issue does not delete the underlying historical event.

### 2.4 Analysis layer

Accepted claims may affect:

- formal Exergism variables;
- the object/scope being scored;
- exact ECL criterion fit;
- counter-institution/remediation analysis;
- attribution/control relationships;
- Schedule knowability.

The system performs **differential re-analysis**: re-evaluate only what the new evidence can materially change, then escalate to full review when necessary.

### 2.5 Output layer

Dossiers remain canonical human-readable governance records. Registries should increasingly become **generated materialized views** of accepted decisions rather than independently edited outcome stores.

Schedules remain separate, exact, versioned legal artifacts and are never rewritten automatically from a ticket.

## 3. Why a semantic model, but not an RDF-only database

ECL benefits from ontology semantics because restrictions and reviews depend on relationships: control, participation, operation, remediation, project scope, identity, evidence and temporal validity.

However, an RDF triplestore should not be required to edit or audit the repository. The canonical records should be small Git-friendly JSON/JSON-LD-compatible documents with stable IDs. A JSON-LD context / ontology vocabulary can give them graph semantics and permit later RDF export, SPARQL use or SHACL validation without making those technologies a prerequisite for ordinary contribution.

This hybrid approach provides:

- readable diffs;
- deterministic CI;
- provenance/history through Git;
- no mandatory database service;
- graph traversal when needed;
- future API/RDF export without migration of identifiers.

## 4. Core semantic classes

The minimum conceptual model is:

- `Actor`
  - `State`
  - `Organization`
  - `Person`
  - `Agency`
- `Project`
- `Deployment`
- `Institution`
- `EvidenceItem`
- `Claim`
- `ExergicAssessment`
- `GovernanceDecision`
- `UpdateSignal`
- `UpdateCase`
- `ScheduleEntry`

Core relationships include:

- `controls`
- `participatesIn`
- `operates`
- `deploys`
- `materiallyBenefits`
- `targetsOrAffects`
- `remediates`
- `reviews`
- `evidenceFor`
- `evidenceAgainst`
- `supersedes`
- `hasAssessment`
- `hasDecision`
- `triggersReviewOf`

A relationship may trigger review of a related actor but **must never propagate an ECL restriction automatically**. Graph reachability is not guilt by association.

## 5. Update triggers

An automatic update signal may be generated by:

### 5.1 Source change

A whitelisted source publishes or materially changes an item associated with a tracked actor/object.

Preferred adapters, in descending operational stability:

1. structured APIs / JSON feeds;
2. RSS / Atom feeds;
3. stable publication indexes;
4. explicit document URLs with content fingerprints;
5. narrowly scoped HTML watchers as a last resort.

A page changing is not evidence that the actor changed. It is only a signal to inspect the new content.

### 5.2 Scheduled review due

Each tracked entity/object may define a `next_review` date. Reaching it creates a deterministic review-due update case even if no external source changed.

### 5.3 Expiry / temporal boundary

A temporary suspension, emergency order, project contract, sanction, court stay, policy or other time-bounded fact reaching its stated end creates a review signal.

### 5.4 Relationship change

Merger, acquisition, dissolution, rename, new control relationship, contractor change, program transfer or successor entity creates an identity/scope review signal.

### 5.5 Remediation/removal trigger

A dossier's explicit removal/narrowing trigger is linked to monitorable facts. Evidence that a trigger may have fired gets priority because ECL must be able to remove restrictions as actively as it adds them.

### 5.6 ECL-model change

Changes to the operative working license, designation standard, formal Exergism model or accepted parameter profile can invalidate prior analytical assumptions. These create model-revalidation cases independently of actor behavior.

## 6. Update-case types

Allowed top-level types should include:

- `new-evidence`
- `counter-evidence`
- `remediation`
- `deployment-start`
- `deployment-stop`
- `identity-change`
- `control-change`
- `scope-change`
- `source-correction`
- `review-due`
- `temporal-expiry`
- `model-revalidation`

The type describes the event, not its moral direction.

## 7. Deduplication

Every detected signal receives a deterministic fingerprint constructed from stable fields such as:

```text
source_id + subject_id + normalized locator + event kind + content/event hash
```

For scheduled review:

```text
subject_id + review-due + due-date
```

A detector MUST search prior update cases / GitHub projections for the fingerprint before creating another ticket.

Multiple evidence items about the same event should normally attach to one update case rather than produce an issue storm.

## 8. GitHub Issue projection

An automatic issue should use a title such as:

```text
[ECL UPDATE] STATE-USA — review due — 2026-09-14
[ECL UPDATE] PROJECT-X — candidate suspension/remediation evidence
```

The issue body MUST contain a hidden stable fingerprint and link the canonical update-case record when one exists.

Suggested lifecycle labels:

- `ecl:update`
- `update:triage`
- `update:evidence`
- `update:analysis`
- `update:governance`
- `update:resolved`
- `impact:scope`
- `impact:exergism`
- `impact:schedule`

The Issue can be deleted, renamed or unavailable without losing the canonical governance history.

## 9. Priority is not a moral score

Ticket priority answers **how urgently review is needed**, not whether an actor is good/bad or restricted.

Priority should be an ordinal class derived from explicit factors:

- `P0`: credible evidence of an immediately material change that could make the current Schedule scope materially wrong or unsafe to rely on;
- `P1`: likely current change to a restricted/scoped project, remediation trigger, identity/control, or exact criterion fit;
- `P2`: material new evidence likely to change formal variables or confidence but not obviously scope;
- `P3`: routine review due / staleness / contextual evidence;
- `P4`: weak lead retained for traceability only.

Automatic systems may assign a provisional priority, but review may change it.

## 10. Determining the required re-analysis

After evidence qualification, classify impact:

### `none`

The new item is duplicate, immaterial, outside temporal scope, or does not alter any accepted claim.

### `claim-only`

A claim/provenance record changes, but no formal variable, criterion or scope is materially affected.

### `partial-exergism`

Only a known subset of variables needs re-estimation. Example: verified suspension may raise `O`/`L` and lower `C`/`R` for a particular deployment.

### `full-exergism`

The object's causal structure or several constitutive variables changed enough that the complete formal assessment should be recomputed.

### `criterion-review`

The evidence affects whether exact ECL Section 5 elements are met, regardless of aggregate formal score.

### `scope-review`

Attribution, control, participation, affected population or project boundaries changed.

### `schedule-review`

An accepted governance change could make a currently incorporated/frozen Schedule entry too broad, too narrow, stale or wrongly identified.

These flags are cumulative.

## 11. Differential formal Exergism procedure

For an accepted material update:

1. load the previous assessment and its exact evidence cutoff;
2. identify new/superseded claims since that cutoff;
3. identify which variables each claim can rationally affect;
4. re-apply the operational rubric to those variables, including counter-evidence;
5. produce new `low/central/high` intervals rather than averaging article scores;
6. recompute `Ex_b`, `Ex_r`, `E_i`, `X_h`, `B_0`, and `N_t` where applicable;
7. run parameter sensitivity using the same profiles as the previous assessment plus any newly adopted profile;
8. record a delta vector and whether prior qualitative conclusions remain robust;
9. separately re-test exact ECL criterion fit; and
10. escalate to adversarial governance review when criterion, scope, remediation, outcome or Schedule implications are material.

A useful machine-readable delta is:

```text
Delta = {
  P, A, V_ep, L, O, U, C, S, R, Ecol,
  Ex_b, Ex_r, E_i, X_h, B_0, N_t
}
```

The delta is diagnostic. There is still no score-to-tier function.

## 12. Material-change triggers

A governance re-review is mandatory when any of the following occurs:

- a previously satisfied ECL criterion may no longer be satisfied;
- a previously unsatisfied criterion may now be satisfied;
- a named remediation/removal trigger may have fired;
- the exact actor/project identity or control chain changed;
- the currently frozen Schedule scope no longer matches the reviewed object;
- an assessment changes from `scorable` to `insufficient_evidence` or vice versa;
- a key formal conclusion changes sign or becomes uncertainty-sensitive where it was previously robust;
- materially authoritative counter-evidence contradicts a relied-upon claim;
- evidence underlying a current finding is discovered to be false, withdrawn, superseded or materially outdated.

A numerical delta threshold alone is deliberately insufficient.

## 13. Downstream application

Once an update case is resolved:

```text
accepted evidence
  -> claim graph
  -> assessment delta (if applicable)
  -> dossier/review record
  -> governance decision
  -> generated registry view
  -> Schedule candidate/revalidation if required
```

Possible outcomes:

- **no material change:** close update case; preserve provenance;
- **evidence refresh:** update claims/evidence cutoff only;
- **formal change without legal change:** update assessment/dossier, retain tier/scope;
- **scope/criterion change:** adversarial review before registry change;
- **governance outcome change:** update canonical decision and regenerate registry views;
- **Schedule implication:** prepare a new Schedule version/candidate. Never retroactively mutate an incorporated older Schedule.

## 14. Registry migration direction

The current grouped registries and override files are useful transitional artifacts but encode current state rather than the causal history producing it.

Long term:

```text
accepted GovernanceDecision records -> generate registry/states.yml
                                     -> generate registry/organizations.yml
                                     -> generate registry/projects.yml
                                     -> generate registry/persons.yml
```

Overrides should then become unnecessary except during explicit migration windows.

## 15. Automation safety boundary

Automation MAY:

- detect source/review changes;
- create/update candidate tickets;
- deduplicate;
- attach source metadata and hashes;
- identify potentially affected objects/variables/criteria;
- compute formal analysis from already reviewed variable inputs;
- run staleness checks.

Automation MUST NOT:

- accept an accusation merely because a page changed;
- infer guilt through arbitrary graph distance;
- create a Restricted Party designation by itself;
- alter an incorporated Schedule automatically;
- turn weak or anonymous evidence into a high-confidence claim;
- tune Exergism parameters to reach a desired outcome.

## 16. Pre-195-dossier gate

Before scaling formal Exergism to all 195 State dossiers, ECL should have:

1. stable semantic identifiers for the objects being assessed;
2. claim/evidence schemas;
3. an evidence valuation standard;
4. a deterministic update-case format;
5. automatic review-due ticket generation;
6. a source-monitor adapter interface;
7. differential Exergism rules;
8. governance escalation rules; and
9. CI ensuring that accepted decisions, dossiers, assessments and generated registry views do not silently diverge.

Only then does mass formal analysis become maintainable rather than a one-time snapshot.
