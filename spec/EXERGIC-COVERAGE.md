# Formal Exergism coverage and ECL 1.0 release gate

Status: repository architecture / release-readiness specification. This document has no licensing effect and does not alter the pinned Exergism model.

## 1. Purpose

ECL must be able to prove how much of its actor corpus has actually passed Formal Exergism analysis. Actor identity, an accepted Claim, a dossier outcome, a Schedule freeze and a formal assessment are different records and MUST NOT be treated as synonyms.

Coverage is therefore a **derived audit property** of exact actor/scope dependencies. The canonical inputs remain the Git-native actor/Claim/Evidence records, dossiers, formal assessments, review clocks and governance/Schedule records. `tools/report_exergism_coverage.py` projects those inputs into a deterministic coverage matrix; the matrix is disposable and is not a new source of governance truth.

This architecture preserves the separation required by `KNOWLEDGE-MODEL.md` and `EXERGIC-ANALYSIS.md`:

- no score-to-tier or score-to-outcome rule;
- no whole-State inflation;
- no propagation through `partOf`, `controls`, `participatesIn`, `operates`, `tracks`, `deploys` or similar predicates;
- association is not attribution and attribution is not governance;
- missing evidence remains missing;
- intent/imputability variables require independent support;
- Formal Exergism remains diagnostic/falsificatory upstream of governance; and
- the assessment object/scope, not a convenient parent identity, is what is analysed.

## 2. Inventory boundary

The actor inventory is every Git-native ABox identity whose `type` is one of:

`State`, `Agency`, `Organization`, `Institution`, `Person`.

`Project` and `Deployment` are `TrackedObject`s, not `Actor`s. They are nevertheless first-class **material scopes** when a GovernanceDecision, Schedule freeze/entry or restriction depends directly on them. Coverage reporting therefore exposes both:

1. an `Actor × Coverage` matrix; and
2. a material governance-scope inventory.

This distinction prevents a project assessment from becoming a whole-parent assessment and prevents a parent assessment from laundering an unassessed project.

## 3. Coverage dimensions

Each dimension is a structured result with `status`, `reason`, `missing[]` and `provenance[]`; it is not a boolean. Allowed statuses are:

- `complete` — all machine-checkable invariants for the dimension are demonstrated;
- `incomplete` — the record exists but required proof is missing;
- `not-applicable` — applicability is explicitly absent or formal analysis is not yet required for a non-material actor;
- `insufficient-evidence` — the exact object is known but required evidence cannot defensibly bound the missing variables/layer;
- `blocked` — the dependency is known but a prerequisite record/process is absent or unresolved;
- `disputed` — a material disagreement prevents treating the layer as complete.

A future human-authored `coverage_disposition` may express only non-complete states and MUST include reason + provenance. `complete` is forbidden there: completeness is derived.

### 3.1 Identity complete

Derived from the canonical ABox identity. At minimum ID/IRI/type/name/dossier must resolve; State identities additionally require the State identity invariants already enforced by SHACL (ISO3 alignment and review provenance).

### 3.2 Evidence normalized

For an actor with active direct Claims, every active Claim must have the required Claim identity, status and provenance and every evidence link must resolve to a canonical EvidenceItem. A material actor with no direct normalized Claim/Evidence path is `incomplete`; a non-material actor with no active direct Claim is `not-applicable` for this dimension.

This means only that Claim/Evidence structure is normalized. It does **not** prove that the evidence is sufficient to score every Exergism variable.

### 3.3 Formal core complete

For a `scorable` assessment the reporter derives `complete` only when all of the following are present and valid:

- `actor_id` resolves to a canonical Actor;
- exact `object`/scope is explicit;
- normalization method, rubric and ex-ante anchors are explicit for every core variable;
- normalization provenance is explicit;
- one or more repository-resolving context profiles are explicit;
- sensitivity review is explicitly performed and described;
- evidence-backed low/central/high intervals exist for `P`, `A`, `V_ep`, `L`, `O`, `U`, `C`, `S`, `R`, `Ecol`, `D_p`;
- every interval is ordered and lies in `[0,1]`; and
- the pinned `tools/exergic_analysis.py` implementation can derive `Ex_b`, `Pen`, `Ex_r`, `E_i`, `X_h`, `B_0` from those inputs for every declared profile.

The reporter does not reimplement or normalize the upstream formulas. It calls the canonical ECL implementation bound to `exergism/upstream.json`.

### 3.4 Formal canonical complete

Requires `formal-core-complete` plus independently evidenced intervals for `D_a`, `I`, `Lz`, `G`, `Rj`, and successful derivability of `P_atr`, `E_i_adj`, `M_f` through the same pinned calculator.

Damage, capture or a severe outcome MUST NOT be used as substitute evidence for intention, lucidity, imputability or gratuitousness.

### 3.5 Temporal complete / temporal N/A

Temporal completeness requires a defensible timeline containing explicit:

- `lambda`;
- per-snapshot `t`, `gamma`, `delta`, irreversibility;
- evidence-backed snapshot variables; and
- derivable `B_acc`, `D_acc`, `N_t` through the pinned calculator.

Absence of a timeline is **not** automatic temporal N/A. `not-applicable` requires an explicit reason and provenance. If temporal evidence is needed but unavailable, the correct state is `insufficient-evidence` or `blocked`.

### 3.6 Adversarial reviewed

A formal assessment is reviewed only when a structured `adversarial_review` records `status: reviewed`, determination, date, reviewer-independence characterization and provenance. Historical prose can remain provenance, but a generic dossier review label does not silently become an assessment-specific formal review.

### 3.7 Governance ready

`governance-ready` is deliberately stronger than “the calculation runs”. A direct material actor dependency requires, at minimum:

- complete identity;
- normalized direct Claim/Evidence path;
- formal-core completeness for the exact material object/scope;
- exact ECL criterion relevance;
- explicit attribution boundary;
- counter-institutions/counter-evidence;
- exclusions;
- disagreement notes;
- structured adversarial review;
- dossier scope, evidence cutoff and last review; and
- an unexpired/valid review clock where a clock exists.

Canonical-advanced and temporal layers are additionally required when the governance rationale actually relies on imputability/intent/atrocity variables or accumulated temporal balance. Otherwise those layers must have a defensible explicit applicability disposition; they may never be filled with neutral values merely to satisfy a gate.

A score is never a governance-ready condition and can never produce `R/S/U/N`.

## 4. Priority tiers

Priorities are review workload, not culpability tiers:

- **P0** — direct material dependency: actor-level `R/S` governance outcome, exact Schedule actor/entity freeze, or future direct GovernanceDecision/Schedule dependency;
- **P1** — substantive non-P0 dossier/assessment/direct material Claim requiring formal follow-up;
- **P2** — attribution-review dependency connected to a material project/object by an accepted/disputed attribution Claim; P2 does not inherit the target's outcome;
- **P3** — identity-only remainder with no current material path. Formal analysis may correctly be `not-applicable` with reason `not-yet-required`.

`partOf` is never a priority-propagation edge. `tracks` alone is never a guilt or restriction edge. P2 is only a review obligation.

## 5. Material dependency gate

The repository invariant is:

> No actor or exact scope materially supporting a GovernanceDecision, Schedule entry/freeze or restriction may remain SILENT/UNKNOWN.

The reporter resolves every material dependency into a known state. A missing assessment for a known material actor/scope is therefore `blocked`, not UNKNOWN. `insufficient-evidence`, `blocked`, `disputed` and defensible `not-applicable` remain first-class findings; they must not be rewritten as scores.

### 5.1 Always-blocking integrity failures

CI fails immediately for:

- unresolved material identity/scope (UNKNOWN);
- duplicate or unresolved assessment IDs/actor bindings;
- a human-authored `complete` coverage disposition;
- malformed intervals or completeness claims that cannot be proved;
- score/tier or score/governance laundering fields;
- broken material Schedule identity mappings; or
- other deterministic integrity errors emitted by the reporter.

These are repository-integrity errors, not disagreements about the substantive outcome.

### 5.2 ECL 1.0 release blockers

`python tools/report_exergism_coverage.py --release-1-0-gate` additionally fails if any direct material dependency is:

- `blocked`;
- `insufficient-evidence`;
- `disputed`; or
- UNKNOWN.

The correct response to an evidence-insufficient restriction candidate is not to invent a score; it is to obtain the missing evidence, narrow/remove the material dependency, or keep the release gate closed.

Non-material P3 actors do not block 1.0 merely because they have never been scored.

## 6. Existing-assessment migration rule

Legacy pilots are migrated only by adding deterministic actor identity bindings. Existing values are not promoted to “complete”. In particular, legacy `scorable` pilots that contain core variable intervals but lack explicit normalization anchors, context-profile binding and sensitivity/adversarial metadata remain `formal-core: incomplete` until those records are genuinely supplied.

`insufficient_evidence` and `not_applicable` pilots remain exactly those states. No midpoint, inferred intent variable or fabricated temporal layer is introduced.

## 7. CLI and deterministic outputs

Human report:

```bash
python tools/report_exergism_coverage.py
```

Machine report and actor matrix:

```bash
python tools/report_exergism_coverage.py \
  --json build/exergism-coverage.json \
  --matrix build/exergism-actor-matrix.json
```

PR/integrity gate:

```bash
python tools/report_exergism_coverage.py --fail-on-unknown-material
```

ECL 1.0 gate:

```bash
python tools/report_exergism_coverage.py --release-1-0-gate
```

Outputs are sorted deterministically. Generated reports are projections and SHOULD NOT be hand-edited as governance sources.

## 8. RDF / SHACL / SPARQL boundary

Formal calculation completeness depends on Git files, profile files, assessment intervals and the pinned Python calculator; pretending that this is an OWL entailment would put governance/program logic in the wrong layer. The Python reporter is therefore authoritative for cross-file Formal Exergism coverage.

RDF checks remain useful for the graph-native boundary. `ontology/exergism-governance-coverage.shacl.ttl` and `sparql/integrity/material-governance-formal-links.rq` require future graph-native `R/S` GovernanceDecision records to identify a subject and a formal assessment link, and ScheduleEntry records to identify their decision. These checks do not infer that the linked assessment is complete; the reporter must prove that separately.

## 9. Adversarial failure modes explicitly rejected

The coverage system is designed to fail closed against:

- score laundering / score-to-tier mapping;
- whole-State inflation from a project or apparatus assessment;
- parent/subsidiary guilt propagation;
- association-as-imputation;
- missing evidence disguised as completeness;
- assessments whose actor binding does not resolve;
- direct project freezes covered only by a parent actor assessment;
- temporal calculations without complete time parameters;
- false temporal N/A without reason/provenance;
- advanced imputability variables inferred from harm alone;
- stale review clocks;
- manually asserted completeness;
- unresolved Claim/Evidence links;
- duplicate assessment IDs; and
- nondeterministic reporting.

The coverage matrix is evidence about repository process state. It is not itself an ECL restriction, moral verdict or legal effect.
