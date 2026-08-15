# ECL Legal Adversarial Review

> **Status: Draft pre-1.0 release-gate specification.** This document has no licensing effect and is not a legal opinion. It defines the evidence and process required before the project may represent an exact ECL release as having completed its legal-review gate.

## 1. Purpose

The project premise is that ECL is intended to operate as a public software/copyright license whose permissions are deliberately limited by its operative conditions. The pre-1.0 legal review must not assume that premise is legally successful. It must try to falsify it.

The controlling question is:

> **Does the exact candidate text grant, withhold, condition and terminate rights as intended, with defensible notice, scope, remedies and statutory compatibility in each required jurisdiction?**

This review is separate from actor/project governance review. A well-supported Schedule designation does not cure a defective licensing mechanism, and a sound licensing mechanism does not validate a weak designation.

## 2. Immutable review inputs

A legal-review record MUST bind itself to immutable inputs, at minimum:

- exact candidate `LICENSE` SHA-256 or equivalent content hash;
- exact Schedule/incorporation mechanism reviewed, including its schema or format where applicable;
- exact version/hash of this review specification;
- review date and jurisdictional scope;
- reviewer identity, competence scope, independence and conflict disclosure; and
- every material amendment made in response to findings.

Review of a moving branch is insufficient for the stable-release gate.

Any material change to the grant, restrictions, definitions, Schedule incorporation, notice, termination, remedies, governing-law model, contributor-rights model or statutory-rights savings language invalidates the affected portion of prior review and requires recorded delta review.

## 3. Review principle

Reviewers are not asked whether they approve of ECL's politics or whether ECL satisfies the Open Source Definition. They are asked to identify credible legal failure modes.

At minimum, attempt the strongest plausible adverse-user arguments that:

- the complained-of act is outside rights controlled by the Licensor;
- a term is contractual only and no enforceable contract was formed;
- a term is a covenant rather than a condition limiting the copyright grant;
- a statutory exception, exhaustion rule or mandatory/non-waivable right applies;
- the exact incorporated Schedule was not objectively knowable;
- the defendant is not the actor/project captured by the operative words;
- notice, cure, termination or reinstatement did not work as claimed;
- the claimant lacks title, standing or authority over the relevant grant;
- the requested remedy is unavailable against this defendant;
- a sovereign/statutory substitution regime changes the enforcement path;
- the term is too uncertain, overbroad or contrary to mandatory/public-policy rules; or
- a cross-border choice-of-law/forum rule defeats the assumed result.

The goal is not universal enforceability. The goal is to expose exactly where ECL depends on copyright, contract, incorporation by reference, statutory defaults, ownership and remedies, and make those dependencies deliberate rather than accidental.

## 4. Mandatory attack surfaces

Every surface `LAR-01` through `LAR-16` MUST receive a recorded disposition for the exact release candidate.

### LAR-01 — Copyright hook and scope of grant

For every operative verb in Sections 3, 5 and 6 of `LICENSE`, identify whether the conduct:

1. normally implicates a Licensor-controlled exclusive software/copyright right;
2. does so only when particular technical facts such as reproduction are present;
3. requires a separate contractual theory; or
4. may lawfully occur without Licensor permission.

Test at least `use`, `execute`, `study`, `inspect`, `reproduce`, `modify`, `adapt`, `translate`, derivative works, `distribute`, combine/integrate, service provision, `deploy`, `train`, hosted functionality, models, dataset transformations and indirect/circumvention theories.

A restriction MUST NOT be assumed to become copyright infringement merely because ECL labels the underlying activity a `Prohibited Use`.

### LAR-02 — Conditions, covenants and remedies

For each material restriction, determine whether it is drafted and treated as:

- a limitation/condition on granted rights;
- an independent contractual covenant; or
- both under an intentionally designed theory.

Record the remedy consequences of that characterization in every required jurisdiction.

### LAR-03 — Formation, assent, notice and incorporation

Test realistic receipt/distribution modes including source repositories, registries, binaries, containers, vendored dependencies, mirrors, archives, forks, derivative distributions and SaaS/service deployments.

The exact License and exact incorporated Schedule/Bundle MUST be objectively identifiable without relying on mutable `latest`, registry pages, branches or channels.

Distinguish:

1. notice sufficient to delimit a copyright permission; and
2. assent sufficient for any independent contractual obligation on which ECL intends to rely.

### LAR-04 — Statutory limitations, exceptions and mandatory rights

Test program loading/execution copies, backup copies, observation/study/testing, interoperability/decompilation, fair use/fair dealing, maintenance/repair/essential-step copies, exhaustion/first-sale effects and relevant non-waivable consumer/mandatory-law protections.

The review MUST decide whether ECL 1.0 requires an explicit savings clause stating that the License does not restrict conduct for which applicable law does not require Licensor permission and cannot override rights that applicable law makes non-waivable.

### LAR-05 — Exhaustion and downstream copies

Determine what control, if any, remains after exhaustion/first sale of a particular lawfully transferred copy and separately identify later reproduction, adaptation, redistribution or deployment that still requires permission.

Cover Sections 4, 6 and 10 explicitly.

### LAR-06 — SaaS, remote execution and service-provider reach

Test the case where a provider holds/runs the ECL copy while a remote user receives only functionality/output and no copy.

Identify which obligations attach to the provider's exercise of licensed rights, which could attach to the remote user, and which cannot safely be grounded in copyright alone.

If ECL regulates service provision, the operative text MUST identify the obligated party and legal hook rather than relying on `use` as a catch-all.

### LAR-07 — Restricted Party / Project certainty

Test `Restricted Party`, `Covered Associate`, `Material Participation`, `Restricted Project`, class designations, knowledge standards and anti-circumvention language for:

- objective knowability;
- attribution and control precision;
- temporal scope;
- indirect-benefit scope;
- affiliates, contractors and employees;
- overbreadth; and
- predictable application to real transactions.

This legal review does not re-decide factual designation merits, but it MUST test whether a compliant recipient can determine whether the operative designation applies.

### LAR-08 — Schedule incorporation and non-retroactivity

Attack Sections 8, 9 and 16 and the exact-bundle model in `VERSIONING.md`.

Test:

- exact Schedule identity and redistribution propagation;
- disappeared URLs/repository moves;
- immutable hashes/content-addressed artifacts;
- mirrors, vendoring, archives, binaries and containers;
- later facts/governance changes;
- correction without rewriting historical grants; and
- any intended/disclaimed rescission theory.

No mutable governance state may silently become the operative Schedule of an older release.

### LAR-09 — Termination, cure, authority and reinstatement

Test:

- cure within and after the notice period;
- vague/wrong-recipient notice;
- deliberate circumvention;
- continuing breach after termination;
- later cessation of a Restricted Project;
- reinstatement;
- downstream recipients before upstream termination;
- derivative works containing multiple rightsholders' material; and
- whether one Licensor can terminate only its own grant or has authority over other Licensors' grants.

Termination scope MUST be objectively determinable as to affected rights, material, copy/release/Bundle and enforcing Licensor.

### LAR-10 — Chain of title, contribution rights and enforcement authority

Review whether every Licensor has authority to grant and, where claimed, enforce/terminate the relevant rights.

Distinguish repository/maintainer ownership, individual contributors, employee/employer ownership, joint ownership, third-party code and material lacking sublicensing authority.

The stable project MUST document its contributor/inbound-rights model; a copyright header alone is insufficient evidence of chain of title or enforcement authority.

### LAR-11 — Patent rights

ECL 0.2 contains no express patent license.

The review MUST recommend one of:

- retain no patent grant and state that clearly;
- add an express patent grant with defined scope/termination; or
- ship an explicit stable limitation explaining the omission.

### LAR-12 — Sovereigns, government actors and available remedies

Because ECL may designate governmental/military bodies, do not assume private-defendant remedies apply unchanged.

For each required jurisdiction review sovereign immunity/statutory substitution, forum/cause-of-action restrictions, injunction availability, damages/compensation, procurement-specific effects and government possession/use of copies.

A restriction and the remedy available to enforce it are separate questions.

### LAR-13 — Choice of law, forum and cross-border enforcement

Review the current absence of an express governing-law/forum clause against at least:

- neutral no-choice model;
- Licensor/home-jurisdiction choice;
- territorial copyright law plus chosen contract law; and
- forum-selection variants.

Record conflicts/recognition consequences for a worldwide multi-Licensor public license.

### LAR-14 — Warranty, liability and non-excludable rights

Review Sections 12 and 13 for businesses and consumers, including mandatory warranties/remedies, gross negligence/intentional misconduct and any liability that cannot lawfully be excluded.

`TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW` is a limiter, not a substitute for review.

### LAR-15 — Severability and judicial modification

Review Section 14 in every required jurisdiction and determine whether the forum recognizes the proposed narrowing/reformation approach and whether any provisions are interdependent/non-severable.

### LAR-16 — Independent regulation

Confirm that ECL permission is not represented as authorization under sanctions, export-control, procurement, criminal, human-rights, privacy or other independent regulation, and that absence from an ECL Schedule is not represented as legal clearance under those regimes.

Do not accidentally design ECL as a shadow sanctions list unless a future operative version deliberately chooses and legally reviews that role.

## 5. Required jurisdiction matrix

The following are all mandatory for the ECL 1.0 legal-review gate:

| Track | Required scope |
| --- | --- |
| EU software copyright | Directive 2009/24/EC mechanics, exhaustion and mandatory/limited exceptions |
| Spain | Spanish software-copyright implementation plus relevant contract/mandatory-law issues |
| United States | Federal copyright, software limitations, condition/covenant/remedies, sovereign-use issues and a reasoned contract/assent track selected from actual contacts |
| United Kingdom | Software copyright, contract/assent, mandatory exceptions and remedies |
| Cross-border | Choice-of-law, forum, conflicts and practical enforcement synthesis |

**Every track above MUST be covered. Any missing required track is itself release-blocking and the gate MUST remain incomplete.** Merely documenting that a gap exists does not satisfy the gate.

Additional jurisdictions SHOULD be added when adoption, a Restricted Party, a material Licensor or a known enforcement scenario makes them important.

A required jurisdiction may conclude that a mechanism is weaker than elsewhere. That weakness may be narrowed or accepted as a documented risk where this specification permits; required coverage itself cannot be waived by calling the omission a risk.

## 6. Reviewer independence and competence

The ECL 1.0 minimum requires:

1. at least **two substantive independent qualified legal reviews** of the exact candidate text;
2. at least **one reviewer competent in software copyright/public licensing**;
3. meaningful EU/Spain and US expertise, whether from the same reviewers or separate specialists;
4. at least **one explicit adversarial/falsification pass** whose task is to defeat enforcement assumptions rather than improve prose; and
5. disclosure of material conflicts of interest.

A maintainer self-review, AI review, automated check, community comment or non-specialist approval may identify useful issues but **does not count** toward the independent qualified legal-review minimum.

External practising counsel is preferred where obtainable; a suitably qualified independent academic or specialist may also provide substantive review if competence, independence, scope and limitations are recorded.

## 7. Findings and severity

**Every material legal finding MUST be recorded.** A known material finding that is omitted from the gate record, lacks a disposition, or cannot be linked to the reviewed immutable input is itself release-blocking.

Material findings MUST use one of:

- **BLOCKER** — credible failure could defeat a core grant/restriction or make stable claims materially misleading; fix/remove before 1.0.
- **MAJOR** — material uncertainty/jurisdictional weakness; fix, narrow or explicitly accept with reasoned limitation/risk before 1.0.
- **MINOR** — clarity/drafting issue unlikely alone to defeat the intended model.
- **NOTE** — optional hardening or documented limitation with no present gate effect.

Severity follows legal consequence, not ease of editing.

Each material finding MUST identify at least:

```text
id:
status: open | resolved | accepted-risk | not-applicable
severity: BLOCKER | MAJOR | MINOR | NOTE
license_sha256_or_blob:
provision:
jurisdiction:
attack:
authority:
consequence:
proposed_mitigation:
resolution:
reviewer:
review_date:
```

Where reviewers disagree, preserve dissent. A contested material issue MUST NOT be marked resolved merely because the maintainer prefers one interpretation.

## 8. Machine-verifiable immutable legal-review record

A stable operative Bundle MUST contain a content-addressed reference to an immutable legal-review record.

Tooling is responsible only for machine-verifiable integrity/state. It MUST NOT pretend to determine whether a lawyer is competent, whether an authority is correctly interpreted or whether the substantive legal analysis is true.

The record consumed by release tooling MUST, at minimum, attest:

- `status: complete`;
- the exact candidate License SHA-256 it reviewed;
- all five required jurisdiction tracks are `complete`;
- all `LAR-01` through `LAR-16` surfaces are dispositioned;
- qualified independent review count is at least 2;
- adversarial qualified review count is at least 1;
- unresolved `BLOCKER` count is 0;
- unresolved/undispositioned material-finding count is 0; and
- required delta review is complete for the shipped candidate.

The Bundle manifest MUST content-address that record. Release tooling MUST refuse `operative: true` when the record is absent, its hash fails, its reviewed License hash differs from the Bundle License hash, or its machine-verifiable gate state is incomplete.

Non-operative draft/candidate artifacts may exist without a completed legal-review record, but tooling MUST NOT surface them as stable/operative merely because a user allows draft resolution.

## 9. Gate closure

The ECL 1.0 legal-review gate is complete only when all of the following are true:

- exact release-candidate `LICENSE` is frozen/content-addressed;
- all LAR-01 through LAR-16 have recorded dispositions;
- **all five required jurisdiction tracks are complete**;
- reviewer-independence/competence minimum is satisfied;
- every material finding is recorded and dispositioned;
- no `BLOCKER` remains unresolved;
- every `MAJOR` is resolved, narrowed or explicitly accepted as a documented jurisdictional limitation/risk with reasoned decision;
- every material amendment triggered by review has received required delta review;
- the reviewed Schedule-incorporation mechanism is the one actually shipped;
- remaining limitations and dissent are preserved;
- an immutable machine-verifiable review record reflects those results; and
- the exact operative Bundle content-addresses that review record and passes release-tool validation.

Completion means **reviewed against a defined threat model**, not `guaranteed enforceable everywhere`.

## 10. Current ECL 0.2 pre-review hypotheses

These are attack hypotheses, not legal conclusions. Qualified reviewers must confirm, reject, narrow or replace them.

### H-01 — Broad operative verbs may outrun Licensor-controlled rights

`use`, `execute`, `deploy`, `train`, hosted functionality and similar verbs do not necessarily map one-to-one to copyright-exclusive rights in every jurisdiction.

**Initial candidate severity:** `BLOCKER` where a core restriction depends solely on conduct outside controlled rights and lacks an enforceable alternative hook.

### H-02 — Statutory-rights savings language may be needed

Current `applicable law`/severability language may not be sufficiently explicit about acts that require no permission or rights that cannot be waived.

**Initial candidate severity:** `MAJOR`.

### H-03 — Hosted-service reach needs provider/user decomposition

A provider may exercise ECL-controlled rights while a remote user receives functionality without receiving/copying the Software.

**Initial candidate severity:** `MAJOR`.

### H-04 — Exhaustion must be reconciled with downstream restrictions

Schedule restrictions cannot simply be assumed to recreate a distribution right that applicable law has exhausted; independent reproduction/adaptation rights require separate analysis.

**Initial candidate severity:** `MAJOR`.

### H-05 — Government restrictions may have remedy asymmetry

A restriction may be meaningful while sovereign/statutory rules substitute forum or remedy.

**Initial candidate severity:** `MAJOR`.

### H-06 — Patent silence must be intentional

No express patent grant exists today.

**Initial candidate severity:** `NOTE` to `MAJOR` depending actual exposure.

### H-07 — Termination/reinstatement and multi-Licensor authority need review

Section 10 does not expressly define post-termination reinstatement and may be ambiguous about whether notice from one Licensor can affect grants made by other rightsholders.

**Initial candidate severity:** `BLOCKER` or `MAJOR` depending the final contributor/enforcement model.

### H-08 — Choice of law/forum remains an open design decision

Omission is not treated here as invalidity; reviewers must compare alternatives and record the intended tradeoff.

**Initial candidate severity:** `NOTE` to `MAJOR`.

### H-09 — Exact Schedule identity may be lost on redistribution

ECL 0.2 §4 requires preservation/reference to the exact ECL version but does not expressly require the exact incorporated Schedule/Bundle identity to travel with redistributed copies, even though §§2, 8 and 16 make that Schedule operative.

**Initial candidate severity:** `BLOCKER`.

## 11. Initial primary authorities for specialist review

The first qualified review should start from current primary authorities and expand jurisdiction by jurisdiction. At minimum:

- Directive 2009/24/EC on the legal protection of computer programs, especially Arts. 4–6 and 8;
- Spain, Real Decreto Legislativo 1/1996, especially Arts. 95–104;
- United States, 17 U.S.C. §§ 106 and 117;
- *Jacobsen v. Katzer*, 535 F.3d 1373 (Fed. Cir. 2008), for the US condition/covenant/copyright-remedy analysis of a public software license;
- CJEU, *UsedSoft GmbH v Oracle International Corp.*, C-128/11, for EU software-distribution exhaustion; and
- United States, 28 U.S.C. § 1498(b), for federal-government copyright-remedy review.

These are a starting map, not a substitute for current qualified research or jurisdiction-specific advice.

## 12. Relationship to other ECL review systems

```text
actor/project evidence review
  -> asks whether a designation is justified

formal Exergism review
  -> asks whether the analytical model supports/narrows/challenges that conclusion

legal adversarial review
  -> asks whether the exact legal mechanism grants, withholds and terminates rights as intended

release review
  -> asks whether the exact reviewed artifacts are the artifacts being shipped
```

None of these layers may silently substitute for another.
