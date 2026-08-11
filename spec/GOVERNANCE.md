# Exergic Governance

This document defines the draft governance process for the Exergic Commons License (ECL), especially the designation and removal of Restricted Parties.

> **Status: Draft 0.1.** Governance is not a substitute for the operative license text. A designation affects a software release only when that release expressly incorporates the relevant Restricted Parties Schedule.

## 1. Goals

The governance process exists to make ethical restrictions:

- evidence-based;
- reasoned rather than arbitrary;
- reviewable;
- knowable by users;
- non-retroactive;
- resistant to circumvention; and
- applicable under the same substantive criteria regardless of ideology or geopolitical alignment.

## 2. Designation categories

A proposal may seek to designate:

1. a legal entity;
2. a governmental body or agency;
3. a military or security body;
4. a specifically named individual;
5. a controlled group of entities; or
6. a narrowly defined class whose membership can be determined with reasonable certainty.

Broad classes should be avoided where membership is unknowable or would require unlimited investigation.

## 3. Grounds for restriction

A party may be designated only where the available evidence supports a reasoned conclusion that the party materially and systematically participates in, directs, enables, or derives substantial benefit from conduct substantially matching one or more ECL prohibited-use categories, including:

- repressive surveillance;
- persecution or unlawful political repression;
- coercive targeting connected to unlawful violence or serious violations of protected rights;
- systematic discriminatory domination;
- deliberate population-scale deception intended to remove meaningful agency;
- irreversible coercive capture; or
- deliberate circumvention of ECL restrictions.

Mere political disagreement, controversial speech, commercial scale, military status, nationality, ethnicity, religion, or ideological identity is insufficient by itself.

## 4. Evidence

A designation proposal should identify verifiable sources and distinguish fact from inference.

Relevant evidence may include:

- final judicial decisions;
- official investigations or findings;
- reports by international organizations;
- corporate filings, contracts, procurement records, or technical documentation;
- credible investigative journalism supported by documented evidence;
- peer-reviewed or technically reproducible research;
- public statements by the party itself; and
- multiple independent sources whose accounts materially corroborate one another.

Anonymous allegations, unsupported social-media claims, guilt by association, or ideological characterization alone should not be sufficient.

## 5. Proposal process

A designation proposal should be opened publicly and contain:

1. the exact party or class proposed;
2. the ECL criteria allegedly satisfied;
3. a concise statement of the material conduct;
4. supporting evidence;
5. known counter-evidence or material uncertainty;
6. the proposed scope of restriction; and
7. whether the proposal concerns the party itself, associated projects, or both.

## 6. Adversarial review

Before incorporation into a stable Restricted Parties Schedule, a proposal should receive a reasonable period for public criticism and contrary evidence.

Where practical, the affected party may be notified or given a reasonable opportunity to submit a response. Failure to respond does not itself establish the allegations.

## 7. Decision record

A designation decision should publish a short reasoned record containing:

- the scope of the designation;
- the material facts relied upon;
- the applicable ECL criteria;
- important uncertainty or dissent;
- the date of adoption;
- the first Schedule version containing the designation; and
- a suggested review date where appropriate.

## 8. Threshold

For a stable designation, the evidence should establish more than speculative or incidental involvement. The conduct should be material, systematic, or sufficiently severe to justify withholding software rights under the ECL framework.

Where evidence is significant but not yet sufficient, the party may be listed as **Under Review** rather than Restricted.

"Under Review" has no licensing effect unless an operative ECL version expressly states otherwise.

## 9. Associates and projects

Governance should avoid permanent personal restrictions based merely on proximity.

A person or entity may be treated as a Covered Associate for a specific project when there is a material connection to a Restricted Party through control, direction, contracting, material collaboration, service provision, financing, or material benefit.

A project may be treated as restricted when a Restricted Party or relevant Covered Associate has Material Participation, when the project materially benefits a Restricted Party, or when an intermediary structure materially circumvents the license.

Association is not recursively transitive without limit. A collaborator of a collaborator is not restricted merely because a social or professional path can be drawn to a Restricted Party.

## 10. Corporate relationships

When a legal entity is restricted, its controlled subsidiaries may be included through an express class designation where control is reasonably ascertainable.

Passive ownership alone should not automatically restrict every shareholder or investment fund. Individuals or entities exercising Control, or specifically designated major beneficial owners, may be separately included where justified by evidence.

## 11. Service users and customers

Use of a Restricted Party's products or services does not automatically and permanently convert every customer, employee, or end user into a Restricted Party.

However, a project materially using a Restricted Party's services may itself be a Restricted Project where the Restricted Party, a Covered Associate, or the service materially participates in the project's design, operation, targeting, decision-making, outputs, or material benefit.

This distinction is intended to restrict relevant projects without producing an unknowable chain of permanent association.

## 12. Removal and review

A Restricted Party may request review or removal based on:

- factual error;
- material change in conduct;
- organizational restructuring;
- cessation of the relevant activity;
- new evidence; or
- an overbroad or ambiguous designation.

Removal should use the same evidence-based process as designation.

## 13. Non-retroactivity

Changes to governance or the Restricted Parties Schedule do not rewrite licenses already attached to earlier software releases.

Each software release should identify the exact ECL version and exact Schedule version it incorporates.

Example:

```text
License: ECL-1.0
Restricted Parties Schedule: ECL-RP-2027-02
```

A later schedule applies only to releases that expressly incorporate it.

## 14. Emergency designation

A provisional emergency designation may be appropriate where there is strong evidence of imminent severe harm and ordinary review would materially undermine the purpose of the restriction.

An emergency designation should:

- state that it is provisional;
- identify the evidence and urgency;
- expire automatically unless ratified through ordinary review; and
- never retroactively alter previously released software licenses.

## 15. Maintainer power and anti-capture

No governance system can eliminate discretion, but ECL should avoid concentrating unreviewable power in a single maintainer.

Before ECL 1.0, this repository should define a stable decision mechanism, conflict-of-interest rules, minimum review requirements, and a process for documenting dissent.

The governance of an anti-capture license should itself be designed to resist arbitrary capture.
