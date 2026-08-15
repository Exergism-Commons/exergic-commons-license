# Claim / EvidenceItem curation contract

> **Status: Draft semantic-data specification.** Claim and evidence records are review inputs and provenance. They do not create licensing restrictions, governance outcomes or Schedule entries by themselves.

## 1. Canonical graph-native records

A material proposition is a first-class `Claim` individual under `knowledge/claims/`. A source artifact is a first-class `EvidenceItem` individual under `knowledge/evidence/`.

A Claim has a stable `CLAIM-*` ID and matching `urn:ecl:CLAIM-*` IRI, exactly one subject and predicate, exactly one object IRI **or** literal value, a claim status, optional temporal qualification, supporting and/or contrary EvidenceItem links, and repository provenance. `candidate`, `accepted` and `disputed` Claims must have an evidence link; an `accepted` Claim must have at least one supporting EvidenceItem identity.

An EvidenceItem has a stable `EVIDENCE-*` ID and matching `urn:ecl:EVIDENCE-*` IRI, a source locator and repository provenance. Publisher, title, publication/retrieval time, source type, language, content hash and `E0-E3` grade are optional unless actually known and reviewed. Absence is preserved as absence.

`asOf` means the date for which the proposition was explicitly curated as applicable. `validFrom` / `validTo` describe the proposition's real-world validity interval only when the record supports those boundaries. `observedAt`, publication date and retrieval time are different concepts and must not be substituted for one another.

## 2. Machine extraction boundary

Automation MAY copy or derive only deterministic structure already explicit in canonical repository material, for example:

- a stable ID / IRI from an existing structured record;
- an exact canonical repository locator;
- an already structured relationship or timestamp;
- exact source metadata copied from a reviewed structured field; and
- deterministic file/IRI/ID integrity facts.

Automation MUST NOT infer from free-form prose or a bare URL:

- `candidate` / `accepted` / `disputed` / `rejected` / `superseded` status;
- an `E0-E3` evidence grade;
- claim confidence;
- a validity boundary or `asOf` date that is not explicit in the reviewed record;
- control, participation, operation, deployment, benefit or attribution;
- an affected Exergism variable;
- ECL criterion fit;
- supersession; or
- a governance outcome, tier, restriction status or Schedule consequence.

If a field is not supported, omit it. Do not manufacture precision to satisfy a schema.

## 3. Human curation boundary

Human/reviewed curation is required for claim status, evidence grade, claim confidence, attribution-sensitive relationships, temporal interpretation not already structured, affected variables/criteria, and supersession unless the canonical reviewed record states the relationship explicitly.

Evidence grading follows `EVIDENCE-VALUATION.md` and is proposition-specific. A publisher never receives a permanent grade. Repository dossiers used as provenance are not assigned an `E0-E3` grade merely because they are canonical ECL synthesis.

Contradictory material states are retained as distinct Claims. Do not overwrite an accepted proposition in place to hide disagreement: represent a live conflict as `disputed`, or use an explicit `supersedes` relationship when a reviewed later Claim replaces an earlier one.

## 4. Governance separation

Claims describe propositions; they do not execute their predicate as a hidden rule. A Claim about `tracks`, `controls`, `participatesIn`, `operates`, `deploys` or a similar relationship can create a review/dependency edge only through explicit tooling. It must never imply a State's or actor's ECL outcome, culpability, tier or inherited restriction.

No Claim may assert `ecl:outcome` or a governance/tier/restriction-status predicate as its proposition. No Claim object may be a `GovernanceOutcome`. Governance remains in the reviewed dossier / GovernanceDecision process, and only an exact incorporated Schedule has licensing effect.

## 5. Pilot policy

The first normalized cohort is intentionally bounded to the USA, NLD and LBY State-review pilots. It is curated from facts and relationships already explicit in canonical dossiers, project identities and review material. The pilot is a schema/graph validation exercise, not a bulk NLP migration of the 195 State dossiers.

The 195-State identity architecture from the State ABox migration remains unchanged. Expansion beyond the pilots should happen only after the Claim/EvidenceItem contract, SHACL, SPARQL and review workflow prove stable under adversarial review.
