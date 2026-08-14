# ECL Evidence Valuation Standard

> **Status: Draft governance methodology.** This standard evaluates evidence quality and analytical use. It does not itself create licensing restrictions.

## 1. Why evidence valuation is separate from Exergism

Formal Exergism evaluates the structure and effects of a defined object. It must not also be asked to decide whether the underlying evidence is trustworthy.

ECL therefore separates:

```text
source -> evidence qualification -> accepted/disputed claim -> Exergism analysis -> ECL criterion fit -> governance
```

A weak source cannot become strong merely because it produces an extreme Exergism result. Likewise, strong evidence does not automatically create an ECL restriction unless the exact operative criterion is satisfied.

## 2. Evidence item versus claim

An **EvidenceItem** is a document, decision, dataset, statement, technical record, investigation or other source artifact.

A **Claim** is a proposition that the evidence item is asserted to support or contradict.

One source may support several claims. Several independent sources may support one claim. Claims must remain narrower than the documents from which they are derived.

## 3. Minimum provenance

An evidence item intended to support a material governance decision should record, where applicable:

- stable `evidence_id`;
- publisher / issuing body;
- title or identifying description;
- canonical locator/URL;
- publication date;
- retrieval date;
- content/document hash where technically practical;
- source type;
- language;
- exact actor/object identifiers implicated;
- temporal period addressed;
- whether the evidence is primary, authoritative finding, independent analysis, secondary reporting or lead-only;
- any known correction, withdrawal, supersession or dispute.

A URL without an identified proposition is not a claim.

## 4. Two-stage gate

### 4.1 Admissibility

Before weight is considered, ask whether the evidence is usable at all.

Material evidence should normally satisfy:

1. **Attribution** — the source/publisher can be identified;
2. **Traceability** — reviewers can locate or reproduce the material relied upon;
3. **Subject specificity** — it concerns the actor/object actually under review;
4. **Temporal applicability** — it can be located in time and is not silently treated as current if historical;
5. **Semantic specificity** — the proposition relied upon can be stated precisely;
6. **Integrity** — there is no known reason to treat the artifact as altered, fabricated or materially misquoted.

If these fail, retain the item as a lead if useful, but do not use it as a material basis for an accepted claim.

### 4.2 Weight

Admissible evidence is then evaluated across independent dimensions:

- **Authority** — institutional competence/standing regarding the proposition;
- **Directness** — whether the source directly establishes the proposition or reports multiple inferential steps away;
- **Specificity** — whether it identifies the exact actor, project, conduct and time period;
- **Method transparency** — whether methods/data/reasoning are inspectable enough to evaluate;
- **Currentness** — whether the evidence remains temporally relevant to the proposition being asserted;
- **Independence / corroboration** — whether materially independent evidence supports the claim;
- **Counter-evidence resilience** — whether credible contrary evidence has been considered and the claim still holds at the stated confidence.

These dimensions are not summed into an automatic truth percentage.

## 5. Evidence grades

ECL uses ordinal grades to avoid pseudoprecision.

### `E3 — high-weight material evidence`

Examples may include, depending on the proposition:

- final or directly relevant judicial decisions;
- original statutes, orders, contracts, procurement or technical records;
- official or independent oversight findings based on direct investigation;
- authoritative international/treaty findings with sufficiently specific factual grounding;
- reproducible technical evidence directly establishing deployment/function;
- first-party admissions against interest where identity and context are verifiable.

`E3` does not mean infallible. It means the item can carry substantial analytical weight without requiring ordinary secondary corroboration for every proposition it directly establishes.

### `E2 — material corroborating evidence`

Examples may include:

- peer-reviewed or technically reproducible research with a clear evidentiary chain;
- high-quality investigative reporting supported by documents, multiple named sources or independently checkable artifacts;
- credible NGO/institutional investigations with transparent methodology and specific attribution;
- multiple materially independent credible reports converging on the same proposition.

`E2` can support a material claim, particularly through corroboration, but important contested propositions should seek stronger/direct evidence where reasonably available.

### `E1 — contextual / limited-weight evidence`

Examples may include:

- credible secondary summaries;
- reporting with limited access to underlying records;
- historical material relevant primarily to persistence/background;
- official or partisan statements primarily asserting a position rather than establishing the underlying facts.

`E1` may shape uncertainty and research direction but should rarely carry a consequential designation by itself.

### `E0 — lead only`

Examples include:

- anonymous or unverifiable social-media allegations;
- unattributed screenshots;
- unsourced lists;
- ideological characterizations without material facts;
- search snippets or summaries where the underlying source has not been inspected.

`E0` may create a research lead or ticket but cannot establish a material accepted claim by itself.

## 6. Source categories do not have automatic grades

The same publisher can produce differently weighted items. An official press release may be `E1` for a contested factual claim while an official contract or court record may be `E3` for a narrow proposition.

Similarly, a news organization is not assigned a permanent numerical reliability score. Evaluate the evidentiary artifact and proposition actually being relied upon.

## 7. Corroboration and independence

Ten articles repeating one wire report are one evidentiary chain, not ten independent confirmations.

Review should identify dependency where known:

```text
original record -> wire service -> ten republications
```

counts primarily as one originating chain.

Corroboration is stronger when sources have materially independent access, methods, data or institutional bases.

## 8. Positive and negative evidence

Evidence valuation must be symmetrical.

The system must actively preserve evidence that:

- a project stopped;
- a court blocked or invalidated conduct;
- an affected person gained an effective remedy;
- independent oversight became effective;
- a previously alleged relationship was disproved;
- a source corrected or withdrew a relied-upon claim;
- a program was narrowed or redesigned;
- current conduct no longer supports an older finding.

Removal and narrowing evidence is not secondary to restriction evidence.

## 9. Temporal validity

Every material claim should distinguish at least:

- `observed_at` — when ECL learned/recorded it;
- `valid_from` — when the proposition became true, if known;
- `valid_to` — when it ceased or is expected to cease, if known;
- `publication_date` — when the evidence item was published.

These are different dates.

A 2026 article describing a 2014 program does not, without more, establish current 2026 deployment.

## 10. From evidence to Exergism variables

Evidence is **not numerically averaged into variable scores**.

Instead, accepted claims are mapped to operational questions for each variable. Example:

```text
Claim: an independent court can suspend deployment P and has done so effectively.
Potential effects: A up, L up, O up, C down, R down.
```

The reviewer then re-applies the formal variable rubric to the total current claim set and chooses defensible `low/central/high` intervals.

Evidence grade affects how narrow the defensible interval can be and how robust a conclusion may be, not by multiplying the variable by a hidden article weight.

## 11. Claim confidence

Claim confidence is categorical:

- `established` — direct/high-weight evidence with no material unresolved contradiction;
- `well-supported` — substantial evidence and/or independent corroboration, with limited uncertainty;
- `reasonable-inference` — inferential but materially supported;
- `disputed` — credible evidence materially conflicts;
- `insufficient` — not enough admissible evidence to rely on the proposition;
- `rejected` — evidence review affirmatively defeats the proposition.

An accepted governance record must distinguish observed fact from reasonable inference.

## 12. Analytical value of a new evidence item

For ticket triage, ask sequentially:

1. **Is it new?** If duplicate, attach and close/dedupe.
2. **Is it admissible?** If not, lead-only.
3. **Does it change an accepted claim?** If no, contextual refresh.
4. **Does it change temporal validity?** A current-status confirmation can matter even when substantive content is similar.
5. **Does it change scope/identity/control?** If yes, scope review.
6. **Does it affect a formal variable?** If yes, partial/full Exergism review.
7. **Does it affect exact ECL criterion fit?** If yes, criterion review.
8. **Does it fire a removal/remediation trigger?** If yes, mandatory governance review.
9. **Could it make a Schedule entry inaccurate?** If yes, Schedule revalidation.

This sequence defines what the evidence is *worth operationally* without pretending that moral/legal significance is a single number.

## 13. Evidence-cutoff rule

Every formal assessment and governance decision must state its evidence cutoff.

An update case after that cutoff does not silently rewrite the older decision. It creates a new review event that either:

- leaves the prior decision intact;
- supersedes the assessment with a new version;
- narrows/removes/changes the governance finding; or
- remains unresolved pending evidence.

The old record remains historically auditable.

## 14. A posteriori use

After a claim has been accepted or rejected, the result should be used to:

1. update the canonical claim/evidence graph;
2. update temporal state (`valid_to`, suspension, supersession, etc.);
3. recalculate only affected formal variables first;
4. compare the new assessment against the previous version;
5. document whether the formal conclusion became stronger, weaker, reversed or uncertainty-sensitive;
6. re-test exact ECL criteria independently;
7. trigger adversarial review if scope/criterion/remediation/outcome implications exist;
8. update the dossier and canonical decision;
9. regenerate registry views; and
10. revalidate a future Schedule candidate where necessary.

Evidence acceptance never edits a released historical Schedule retroactively.
