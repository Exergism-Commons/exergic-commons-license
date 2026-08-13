# Exergic Governance

This document defines the draft governance process for the Exergic Commons License (ECL), especially the designation, narrowing and removal of Restricted Parties and Restricted Projects.

> **Status: Draft 0.2 alignment.** Governance is not a substitute for the operative license text. A designation affects a software release only when that release expressly incorporates the relevant exact ECL version and Restricted Parties Schedule.

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
5. a controlled group of entities;
6. a narrowly defined class whose membership can be determined with reasonable certainty; or
7. a specifically identified project, program, deployment, contract, product or coordinated activity.

Broad classes should be avoided where membership is unknowable or would require unlimited investigation.

## 3. Grounds for restriction

A party or project may be proposed for designation only where the available evidence supports a reasoned conclusion that it materially and systematically participates in, directs, enables, or derives substantial benefit from conduct substantially matching one or more operative ECL prohibited-use categories.

Under ECL 0.2-DRAFT those categories include:

- repressive surveillance;
- coercive targeting connected to unlawful violence, torture, enforced disappearance, collective punishment or intentional attacks on protected persons;
- automated/data-driven systematic discriminatory domination;
- deliberate population-scale deception intended to remove meaningful agency;
- irreversible coercive technological/informational capture;
- systematic coercive domination or unlawful political repression, including qualifying persecution, arbitrary detention, forced labour, forced displacement/expulsion, severe discriminatory domination and comparably severe treatment where the exact §5.6 elements are met; and
- deliberate circumvention of ECL restrictions.

Mere political disagreement, controversial speech, commercial scale, military status, nationality, ethnicity, religion, ideology or remote association is insufficient by itself.

A serious human-rights concern is an evidence input, not an automatic designation rule. The proposal must still identify the operative ECL criterion and the material connection between the actor/project and the qualifying conduct.

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

1. the exact party, project or class proposed;
2. the exact ECL criterion allegedly satisfied;
3. a concise statement of the material conduct;
4. supporting evidence;
5. known counter-evidence or material uncertainty;
6. the proposed scope of restriction;
7. narrower alternatives considered; and
8. whether any court, ombuds, audit, legal-defence or other remedial function should be expressly excluded.

## 6. Adversarial review

Before incorporation into a stable Restricted Parties Schedule, a proposal should receive a reasonable period for public criticism and contrary evidence.

Where practical, the affected party may be notified or given a reasonable opportunity to submit a response. Failure to respond does not itself establish the allegations.

Reviewers must actively test both factual sufficiency and normative fit against the exact operative ECL text. Principles and governance documents may expose a drafting defect, but they do not silently add legal prohibitions.

## 7. Decision record

A designation decision should publish a short reasoned record containing:

- the scope of the designation;
- the material facts relied upon;
- the applicable ECL criteria;
- important uncertainty or dissent;
- material counter-institutions/exclusions;
- the date of adoption;
- the first Schedule version containing the designation; and
- a suggested review date where appropriate.

## 8. Threshold

For a stable designation, the evidence should establish more than speculative or incidental involvement. The conduct should be material, systematic, or sufficiently severe to justify withholding software rights under the ECL framework.

Where evidence is significant but not yet sufficient, the party or project may be listed as **Under Review** rather than Restricted.

"Under Review" has no licensing effect unless an operative ECL version expressly states otherwise.

## 9. Associates and projects

Governance should avoid permanent personal restrictions based merely on proximity.

A person or entity may be treated as a Covered Associate for a specific project when there is a material connection to a Restricted Party through control, direction, contracting, material collaboration, service provision, financing, or material benefit.

Under ECL 0.2-DRAFT, a project may also be designated directly by the exact Schedule. Separately, a project becomes Restricted through the participation/direction/benefit/circumvention rules in the operative license.

Association is not recursively transitive without limit. A collaborator of a collaborator is not restricted merely because a social or professional path can be drawn to a Restricted Party.

## 10. Corporate relationships

When a legal entity is restricted, its controlled subsidiaries may be included through an express class designation where control is reasonably ascertainable.

Passive ownership alone should not automatically restrict every shareholder or investment fund. Individuals or entities exercising Control, or specifically designated major beneficial owners, may be separately included where justified by evidence.

## 11. Service users and customers

Use of a Restricted Party's products or services does not automatically and permanently convert every customer, employee, or end user into a Restricted Party.

However, a project materially using a Restricted Party's services may itself be a Restricted Project where the operative license's project rules are satisfied.

This distinction is intended to restrict relevant projects without producing an unknowable chain of permanent association.

## 12. Accountability and remediation

Governance should distinguish ordinary operations from genuine remediation.

Where a broader institutional designation would otherwise capture a court, ombuds/NPM function, inspector, auditor, prosecutor investigating official abuse, independent legal defence function or comparable body that is materially independent from the underlying prohibited conduct, reviewers should:

1. consider an express Schedule exclusion where that is the clearest solution; and
2. assess whether the function can satisfy the operative `Independent Remediation Activity` definition.

The remediation rule must not become a self-certifying loophole for ordinary intelligence, military, police, detention, immigration, surveillance, targeting, procurement or administrative operations.

## 13. Removal and review

A Restricted Party or Restricted Project may request review or removal based on:

- factual error;
- material change in conduct;
- organizational restructuring;
- cessation of the relevant activity;
- new evidence; or
- an overbroad or ambiguous designation.

Removal should use the same evidence-based process as designation.

## 14. Non-retroactivity

Changes to governance or the Restricted Parties Schedule do not rewrite licenses already attached to earlier software releases.

Each software release should identify the exact ECL version and exact Schedule version it incorporates.

Example:

```text
License: ECL-1.0
Restricted Parties Schedule: ECL-RP-2027-02
```

A later schedule applies only to releases that expressly incorporate it.

## 15. Emergency designation

A provisional emergency designation may be appropriate where there is strong evidence of imminent severe harm and ordinary review would materially undermine the purpose of the restriction.

An emergency designation should:

- state that it is provisional;
- identify the evidence and urgency;
- identify the exact operative ECL criterion;
- expire automatically unless ratified through ordinary review; and
- never retroactively alter previously released software licenses.

## 16. Schedule knowability

The evidentiary process may be complex; application of the final license should not be.

A stable Schedule should use exact legal names, identifiers, named projects or reasonably determinable classes and should state material exclusions. Licensees should be able to rely on the exact incorporated Schedule rather than independently reconstructing the entire governance record.

## 17. Maintainer power and anti-capture

No governance system can eliminate discretion, but ECL should avoid concentrating unreviewable power in a single maintainer.

Before ECL 1.0, this repository should define a stable decision mechanism, conflict-of-interest rules, minimum review requirements, and a process for documenting dissent.

The governance of an anti-capture license should itself be designed to resist arbitrary capture.
