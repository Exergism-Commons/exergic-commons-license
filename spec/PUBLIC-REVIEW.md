# ECL Public Adversarial Review

> **Status: Draft governance specification.** This process has no licensing effect by itself. Only an exact Schedule incorporated with an exact ECL version can affect a software release.

## 1. Purpose

GitHub State issues are the public review surface for canonical ECL dossiers. They are not the canonical evidence record and must not become a second mutable source of governance truth.

The separation is:

```text
dossier                     = canonical current synthesis
GitHub review issue         = public scrutiny / evidence / objections
GovernanceDecision record   = reviewed conclusion and dissent record
ScheduleRelease             = immutable legal artifact
```

A dossier being internally complete does **not** mean its public governance review is complete.

## 2. Review must be symmetric

Reviewers must test the current conclusion rather than seek evidence for a predetermined direction.

The same process applies to:

- proposed `R` outcomes;
- proposed scoped `S` outcomes;
- proposed `N` outcomes;
- narrowing or removal of an existing finding;
- transitions into or out of `U`;
- remediation/exclusion findings.

Evidence capable of weakening, narrowing or removing a restriction must be sought and handled with the same seriousness as evidence capable of creating or expanding one.

## 3. Canonical State review issue

Each State dossier may have one long-lived public review issue. The issue should link the canonical dossier and expose at least:

- current provisional outcome and scope;
- evidence cutoff;
- formal-Exergism status/assessment where available;
- identity/scope review checklist;
- supporting-evidence review checklist;
- counter-evidence/falsification checklist;
- exact ECL-criterion-fit review;
- attribution and narrower-alternative review;
- remediation/removal-trigger review;
- open objections and documented dissent;
- independent-review gate; and
- resulting GovernanceDecision once adopted.

The issue remains a discussion surface. Substantive accepted evidence must be normalized into the dossier/claim/evidence layer rather than existing only in comments.

## 4. Review lifecycle

A State review issue moves conceptually through:

```text
external-review-needed
  -> active-review
  -> objections-open
  -> objections-resolved | documented-dissent
  -> governance-ready
  -> decision-recorded
  -> review-closed
```

A review issue may reopen whenever material new evidence, counter-evidence, a scope change, remediation, identity change, model change or Schedule mismatch creates a new governance question.

Closing an issue means the current review cycle is complete. It does not make the dossier or historical issue immutable and it does not prevent future re-review.

## 5. Independent reviewer

For purposes of the minimum review gate, an **independent reviewer** is a person who:

1. did not author the substantive conclusion being reviewed;
2. is not reviewing their own prior determination as the independent check;
3. discloses any material relationship, employment, financial interest, direct advocacy role or other conflict reasonably capable of affecting the review; and
4. performs a substantive evidence/criterion review rather than merely expressing agreement or disagreement.

A conflicted participant may still provide valuable evidence, argument or corrections. Their contribution is retained and considered, but it does not satisfy the independent-review minimum for the affected question.

The primary author/maintainer may answer objections, update the dossier and make provisional determinations, but cannot count themselves as an independent reviewer.

## 6. Minimum review gate

A final `R`, `S` or `N` GovernanceDecision intended to support ECL 1.0 readiness or a stable Schedule must have:

- **at least two substantive independent reviews**;
- **at least one adversarial/falsification review** explicitly trying to identify material contrary evidence, attribution error, overbreadth or a narrower defensible result;
- all material objections either resolved or explicitly documented as dissent;
- exact ECL criterion fit checked separately from formal Exergism; and
- scope/exclusions/remediation conditions reviewed.

`U` is the appropriate unresolved state where evidence, scope, reviewer independence or material objections do not yet support a final determination.

The numerical minimum is a floor, not a voting rule. Two weak approvals do not outweigh a well-supported unresolved material objection.

## 7. Review submissions are not votes

ECL governance is reasoned review, not popularity voting.

A review submission should state one of:

- `support-current-conclusion`;
- `support-with-narrowing`;
- `challenge-current-conclusion`;
- `insufficient-evidence`;
- `conflict-disclosed / evidence-only`.

The submission should identify what was checked, source/counter-source references, material uncertainty and any unresolved objection.

Maintainers must resolve arguments by evidence, attribution and operative ECL criteria, not by counting reactions or comments.

## 8. Material objection

An objection is material when, if true, it could reasonably change:

- exact actor/project identity;
- temporal applicability;
- evidence admissibility/grade in a relied-upon proposition;
- an Exergism variable interval or robustness conclusion;
- exact ECL criterion fit;
- attribution/control/participation;
- scope, exclusion or remediation;
- `R/S/U/N` outcome; or
- Schedule knowability.

A material objection may be closed as:

- `accepted`;
- `resolved-by-evidence`;
- `resolved-by-narrowing`;
- `superseded`;
- `not-material`, with reasons; or
- `documented-dissent` where reasonable reviewers still disagree.

Material dissent must not be deleted merely to manufacture consensus.

## 9. Conflict-of-interest declarations

A reviewer who wants their review to satisfy the independent gate should include a short declaration such as:

```text
Independence: I did not author the dossier conclusion and I have no material
relationship with the reviewed actor/project or the proposal that I believe
would affect this review.
```

Where a conflict exists, disclose it concisely. A disclosed conflict does not invalidate factual evidence; it changes whether the contribution counts toward the minimum independent-review gate.

## 10. What issue comments can change

A GitHub comment may:

- supply evidence/counter-evidence;
- identify a factual or attribution error;
- challenge criterion fit;
- propose narrowing/remediation/removal;
- submit an independent review;
- document dissent.

A comment does **not** by itself change the dossier, GovernanceDecision, registry or Schedule.

Accepted material changes are normalized through a repository change with provenance.

## 11. Closure criteria

A State review cycle may close only when:

1. the canonical dossier reflects the evidence cutoff used for the decision;
2. the minimum independent-review gate is met for a final `R`, `S` or `N` result, or the unresolved result is `U`;
3. supporting and contrary evidence have both been actively tested;
4. material objections are resolved or documented as dissent;
5. exact ECL criterion fit and scope have been reviewed;
6. the formal Exergism layer is reviewed or explicitly `insufficient_evidence` / `not_applicable` where appropriate;
7. a GovernanceDecision record identifies the review issue and material dissent; and
8. the next review/removal trigger is recorded where applicable.

Closure has no retroactive licensing effect.

## 12. Emergency exception

The emergency-designation mechanism in `GOVERNANCE.md` may temporarily bypass the ordinary independent-review minimum only when its stated urgency conditions are actually met.

Such an emergency result remains provisional, must expire automatically unless ratified under ordinary review, and must never be represented as having completed the normal public-review gate.

## 13. Migration of historical State issues

Existing `[STATE DOSSIER]` issues are historical evidence-gathering threads and should not be discarded. They should be migrated in place to `[STATE REVIEW]` surfaces by:

- preserving the existing issue number and comments;
- linking the canonical dossier;
- prepending the current review checklist and provisional state;
- preserving the pre-migration body as historical context;
- adding public-review labels; and
- leaving the issue open unless the review gate is actually complete.

Migration is an organizational change only. It must not silently change `R/S/U/N` or Schedule content.
