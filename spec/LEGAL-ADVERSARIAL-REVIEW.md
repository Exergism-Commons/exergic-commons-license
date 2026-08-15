# ECL Legal Adversarial Review

> **Status: Draft pre-1.0 release-gate specification.** This document has no licensing effect by itself and is not a legal opinion. It defines how ECL's operative legal text must be attacked, reviewed and evidenced before a stable 1.0 release may be represented as having completed the project's legal-review gate.

## 1. Purpose

ECL does not need external permission to exist as a copyright license. The relevant pre-1.0 question is narrower and harder:

> **Does the exact operative text create the intended permissions and restrictions, with defensible notice, scope, remedies and statutory compatibility in the jurisdictions in which ECL expects to be used?**

The legal adversarial review exists to try to falsify that proposition.

It is intentionally separate from actor/project governance review. A State dossier may be perfectly researched while the license mechanism used to implement a Schedule is legally defective; conversely, a sound licensing mechanism does not validate a weak designation.

## 2. Objects under review

A legal-review record MUST bind itself to immutable inputs, at minimum:

- the exact `LICENSE` content hash / Git blob or release hash;
- the exact Schedule format/version being reviewed, where Schedule mechanics are in scope;
- the exact version of this review specification;
- the review date and jurisdictional scope; and
- all amendments made in response to findings.

A review of a moving branch is not sufficient for the stable-release gate. Any material change to the grant, restrictions, definitions, incorporation mechanics, termination, remedies, governing-law model or statutory-rights savings language invalidates the affected portion of the prior legal review and requires delta review.

## 3. Review principle

Reviewers are not asked whether they like ECL's politics or whether it satisfies the Open Source Definition. They are asked to identify legal failure modes.

A useful review should attempt to construct the strongest plausible compliant/adverse-user arguments against enforcement, including:

- `this act is outside copyright exclusivity`;
- `this term is contractual at most and no contract was formed`;
- `the condition is a covenant rather than a limitation on the license grant`;
- `a statutory exception or mandatory right applies`;
- `the incorporated Schedule was not reasonably knowable`;
- `the relevant copy was distributed after exhaustion/first sale`;
- `the defendant is not the actor or project captured by the words used`;
- `termination or notice did not occur as the Licensor claims`;
- `the requested remedy is unavailable against this defendant`;
- `the provision is too uncertain, overbroad or contrary to mandatory/public-policy rules in this forum`; or
- `the claimant did not own or control the rights it purported to license`.

The goal is not to guarantee universal enforceability. No private license can do that. The goal is to expose where ECL relies on copyright, contract, incorporation by reference, statutory default rules or remedies, and to make those dependencies deliberate rather than accidental.

## 4. Mandatory attack surfaces

### LAR-01 — Copyright hook and scope of grant

For every operative verb in Sections 3, 5 and 6 of `LICENSE`, reviewers MUST identify whether the conduct normally implicates an exclusive copyright/software right in each reviewed jurisdiction, requires a separate contractual theory, or may fall outside both without additional facts.

The review MUST specifically test at least:

- `use` and `execute`;
- `study` and `inspect`;
- `reproduce`;
- `modify`, `adapt`, `translate` and derivative works;
- `distribute`;
- `combine` / integrate;
- `provide services using the Software`;
- `deploy`;
- `train`;
- `hosted functionality`;
- `model` and `dataset transformation`; and
- indirect provision / circumvention theories.

A restriction must not be assumed to become copyright infringement merely because the license labels the underlying activity a `Prohibited Use`.

### LAR-02 — Conditions, covenants and remedies

Review whether each material restriction is drafted as a limitation/condition on the granted rights, a contractual promise, or both, and what remedies follow from that characterization.

The review MUST test whether the operative wording sufficiently connects prohibited conduct to the scope of the permission granted and whether breach can support the remedy ECL expects in the relevant jurisdiction.

### LAR-03 — Formation, assent, notice and incorporation by reference

Review how a recipient becomes bound or loses permission under realistic distribution modes, including:

- source repositories;
- package registries;
- binary distribution;
- containers and images;
- vendored dependencies;
- mirrors and archives;
- forks and derivative distributions; and
- service/SaaS deployments.

The exact Schedule incorporated by a release MUST be objectively identifiable without depending on a mutable `latest`, registry page, branch or channel.

The review MUST distinguish:

1. notice sufficient to delimit a copyright permission; and
2. assent sufficient to support any independent contractual obligation on which ECL intends to rely.

### LAR-04 — Statutory limitations, exceptions and mandatory rights

Review all terms against applicable statutory rights that do not require the Licensor's permission or cannot validly be contracted away.

At minimum, test:

- program loading/execution copies;
- backup copies;
- observation/study/testing;
- interoperability/decompilation where applicable;
- fair use/fair dealing and other copyright exceptions;
- maintenance/repair and essential-step copies;
- exhaustion/first-sale effects; and
- non-waivable consumer or mandatory-law protections where relevant.

The review MUST decide whether ECL 1.0 should contain an explicit savings clause stating that the License does not restrict conduct for which applicable law does not require the Licensor's permission, while preserving restrictions to the maximum lawful extent.

### LAR-05 — Exhaustion and downstream copies

Review whether first-sale/exhaustion doctrines can limit ECL's ability to control later distribution or use of particular lawfully transferred copies, and which independent rights remain implicated by later reproduction, adaptation, redistribution or deployment.

This review MUST cover the interaction between exhaustion and Section 4 distribution conditions, Section 6 downstream provision, and Section 10 downstream-license survival.

### LAR-06 — SaaS, remote execution and service-provider reach

Test the strongest case in which:

- a provider lawfully obtains an ECL copy;
- a third party receives only remote functionality and no copy; and
- the prohibited result occurs through the hosted service.

Review which ECL obligations attach to the provider, which could attach to the remote user, and which cannot safely be grounded in copyright alone.

If ECL intends to regulate service provision, the operative text MUST make the legal hook and obligated party clear rather than relying on the word `use` as a catch-all.

### LAR-07 — Restricted Party / Project certainty

Review `Restricted Party`, `Covered Associate`, `Material Participation`, `Restricted Project`, knowledge standards, class-based designations and anti-circumvention language for:

- objective knowability;
- attribution precision;
- control thresholds;
- temporal scope;
- indirect-benefit scope;
- treatment of affiliates, contractors and employees;
- overbreadth; and
- predictable application to real transactions.

The legal review does not re-decide the factual merits of a designation, but it MUST test whether a compliant recipient can determine whether the designation legally applies.

### LAR-08 — Schedule incorporation and non-retroactivity

Attack the exact-bundle model in `VERSIONING.md` and Sections 8, 9 and 16 of `LICENSE`.

Review at least:

- whether an exact Schedule is unambiguously incorporated;
- what happens when a Schedule URL disappears or a repository moves;
- whether hashes / immutable artifacts are sufficient evidence of the incorporated text;
- whether later governance facts can accidentally alter an older grant;
- how corrections are published without rewriting history; and
- whether any rescission theory is intended or expressly disclaimed.

No reviewer should infer dynamic retroactivity from ECL's living-governance system unless the operative text expressly creates it.

### LAR-09 — Termination, cure and reinstatement

Review Section 10 against at least these scenarios:

- knowing prohibited use followed by cure before 30 days;
- notice that is vague or reaches the wrong entity;
- deliberate circumvention with no cure period;
- continuing breach after termination;
- later cessation of the prohibited project;
- a terminated user seeking reinstatement;
- downstream recipients who received copies before upstream termination; and
- derivative works containing both terminated-party contributions and ECL-covered material.

The review MUST determine whether an explicit reinstatement mechanism is desirable and whether termination is scoped to the affected rights/copy/release with sufficient precision.

### LAR-10 — Chain of title and contributor authority

Review whether every Licensor has authority to grant the rights ECL purports to grant.

The project MUST distinguish:

- copyright owned by the repository/project maintainer;
- copyright owned by individual contributors;
- employer-owned contributions;
- third-party code under compatible/incompatible terms; and
- material for which the purported Licensor has no sublicensing authority.

A future stable release SHOULD document the contributor-rights model separately rather than relying on a copyright header to solve chain-of-title questions.

### LAR-11 — Patent rights

ECL 0.2 grants copyright/software permissions but contains no express patent license.

Review whether that omission is intentional and whether patents controlled by Licensors could make the stated `broad rights` materially incomplete. The review MUST recommend one of:

- retain no patent grant and state that clearly;
- add an express patent grant with defined scope and termination; or
- defer patent coverage with an explicit 1.0 limitation.

### LAR-12 — Sovereigns, government actors and available remedies

Because ECL expressly contemplates governmental and military bodies as potential Restricted Parties, the legal review MUST not assume private-defendant remedies apply unchanged to sovereign defendants.

For each priority jurisdiction, review:

- sovereign immunity / statutory substitution regimes;
- forum and cause-of-action restrictions;
- availability of injunctions;
- damages or compensation regimes;
- procurement-specific terms; and
- whether a government's possession or use of a copy changes the practical enforcement path.

Reduced or substituted remedies do not necessarily invalidate a restriction; they may materially change what enforcement can achieve.

### LAR-13 — Choice of law, forum and cross-border enforcement

ECL 0.2 contains no express governing-law or forum clause.

Review whether that omission should remain deliberate. Compare at least:

- a neutral no-choice model;
- Licensor/home-jurisdiction choice;
- copyright-law-by-territory plus chosen contract law; and
- forum-selection variants.

The review MUST consider whether a single clause would improve predictability or create unacceptable conflicts for a multi-licensor worldwide public license.

### LAR-14 — Warranty, liability and non-excludable rights

Review Sections 12 and 13 for enforceability against:

- businesses;
- consumers where ECL distribution can reach them;
- gross negligence / intentional misconduct rules;
- death/personal-injury exclusions where relevant; and
- mandatory statutory warranties or remedies.

`TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW` is a useful limiter but is not a substitute for jurisdiction-specific review.

### LAR-15 — Severability and judicial modification

Review whether Section 14's instruction to interpret or limit an unenforceable provision to the minimum extent necessary is recognized in each priority jurisdiction, and whether any non-severable dependency between provisions should be stated expressly.

### LAR-16 — Export controls, sanctions and independent regulation

ECL designation is not a substitute for sanctions, export-control, procurement, criminal, human-rights, privacy or other regulatory compliance.

Review whether the stable documentation should expressly state that:

- ECL permission does not authorize conduct prohibited by law; and
- absence from an ECL Schedule does not mean a transaction is lawful under independent regulation.

The legal review MUST avoid designing ECL as a shadow sanctions list unless the operative project intentionally chooses that role.

## 5. Priority jurisdiction matrix

ECL 1.0 MUST NOT be described as having completed the project's legal-review gate merely because one jurisdiction was reviewed.

Minimum stable-gate coverage:

| Track | Required scope |
| --- | --- |
| EU software copyright | Directive 2009/24/EC mechanics, exhaustion and mandatory/limited exceptions |
| Spain | Spanish software-copyright implementation plus applicable contract/mandatory-law issues relevant to the Licensor/release |
| United States | Federal copyright, computer-program limitations, condition/covenant/remedy analysis, sovereign-use issues and at least one reasoned contract-law/assent track selected on actual contacts rather than arbitrarily |
| United Kingdom | Software copyright, contract/assent, mandatory exceptions and remedies |
| Cross-border | Choice-of-law, forum, conflicts and practical enforcement synthesis |

Additional jurisdictions SHOULD be added when adoption, a Restricted Party, a material Licensor or a known enforcement scenario makes them important.

A jurisdiction may conclude that a particular ECL mechanism is weaker than elsewhere. The gate requires that the weakness be understood and addressed or accepted explicitly; it does not require fictional worldwide uniformity.

## 6. Reviewer independence and competence

For ECL 1.0, the minimum legal-review gate requires:

1. **at least two substantive independent legal reviews** of the exact candidate text;
2. **at least one reviewer competent in software copyright/public licensing**;
3. **meaningful EU/Spain and US coverage**, whether by the same reviewers or separate specialists;
4. **at least one explicit adversarial/falsification pass** whose task is to defeat enforcement assumptions rather than improve prose; and
5. disclosure of material conflicts of interest.

A maintainer self-review, AI review, community comment or non-specialist approval can identify useful issues but **does not count as an independent qualified legal review** for this gate.

External practising counsel is preferred where the project can obtain it; a suitably qualified independent academic or specialist may also provide a substantive review, with their scope and limitations recorded.

## 7. Finding severity

Every material legal finding SHOULD be recorded as one of:

- **BLOCKER** — a credible failure mode could defeat a core ECL restriction/grant or make the stable text materially misleading; must be fixed or the affected feature removed before 1.0.
- **MAJOR** — material uncertainty or jurisdictional weakness; must be fixed, narrowed, or explicitly accepted with rationale before 1.0.
- **MINOR** — drafting/clarity issue unlikely by itself to defeat the intended legal model; resolve where practical.
- **NOTE** — observation, optional hardening or jurisdiction-specific limitation with no current release-gate effect.

Severity is based on legal consequence, not on how easy the prose is to patch.

## 8. Finding record

Each finding SHOULD identify:

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

Where reviewers disagree, preserve the dissent. Do not convert a contested MAJOR issue into `resolved` merely because the maintainer prefers one interpretation.

## 9. Gate closure

The ECL 1.0 legal-review gate is complete only when all of the following are true:

- the exact release-candidate `LICENSE` is frozen and content-addressed for review;
- all LAR-01 through LAR-16 attack surfaces have a recorded disposition;
- the minimum jurisdiction matrix has been covered or an explicit release-blocking gap remains;
- the reviewer-independence minimum is satisfied;
- no `BLOCKER` remains unresolved;
- every `MAJOR` is resolved, narrowed, or explicitly accepted as a documented jurisdictional limitation/risk with a reasoned decision;
- every material amendment triggered by review has received delta review;
- the Schedule-incorporation mechanism reviewed is the one actually shipped;
- the final review record identifies remaining limitations and dissent; and
- `VERSIONING.md`'s stable/operative release gate points to the completed immutable review record.

Completion means **reviewed against a defined threat model**, not `guaranteed enforceable everywhere`.

## 10. Current ECL 0.2 pre-review hypotheses

The following are **issues to attack**, not legal conclusions. They are recorded now so formal reviewers do not start from a blank page.

### H-01 — Broad operative verbs may outrun copyright exclusivity

ECL 0.2 grants and restricts `use`, `execute`, `deploy`, `train`, hosted functionality and other conduct. Some legal systems connect execution to protected reproduction in common technical circumstances; others enumerate exclusive rights without creating a freestanding copyright right over every kind of `use`.

Formal review must determine which restrictions are copyright-license conditions, which require a contractual hook, and which need narrower drafting.

**Initial severity candidate:** `BLOCKER` for any core restriction that depends solely on an act outside the Licensor's exclusive rights and lacks an enforceable alternative hook.

### H-02 — Statutory-rights savings language may be needed

The current text says rights are subject to applicable law but does not contain a focused statement that ECL does not restrict acts for which copyright permission is not required or rights that cannot be waived.

Formal review should test whether adding such a clause reduces overclaiming without weakening the intended restrictions on acts that do require permission.

**Initial severity candidate:** `MAJOR`.

### H-03 — Hosted-service reach needs a provider/user split

The current text prohibits providing hosted functionality in circumvention scenarios, but the relationship between the provider's licensed copy and a remote user's conduct is not fully decomposed.

Formal review should test whether Section 6 sufficiently binds the party actually exercising ECL rights and avoids pretending that every remote recipient is directly exercising copyright rights in the Software.

**Initial severity candidate:** `MAJOR`.

### H-04 — Exhaustion must be reconciled with downstream restrictions

The exact effect of exhaustion/first sale on a lawfully transferred copy differs from the continuing control available over reproduction, adaptation and other protected acts.

Formal review should verify that Sections 4, 6 and 10 do not claim more post-transfer control than applicable law supplies.

**Initial severity candidate:** `MAJOR`.

### H-05 — Government-targeted restrictions may have remedy asymmetry

ECL intentionally contemplates sovereign actors. At least some jurisdictions alter the forum or remedy when copyrighted material is used by government.

Formal review must distinguish `the license condition is valid` from `the Licensor can obtain the same injunction/damages available against a private defendant`.

**Initial severity candidate:** `MAJOR`.

### H-06 — Patent silence should be intentional

A broad software permission can be operationally incomplete if a Licensor also controls patent claims necessary to exercise the software rights and the license says nothing about them.

Formal review should decide rather than accidentally inherit this omission.

**Initial severity candidate:** `MAJOR` or `NOTE`, depending on actual patent exposure and intended scope.

### H-07 — Termination has no explicit post-termination reinstatement path

Section 10 provides cure before termination for most breaches, but does not expressly define reinstatement after termination.

Formal review should determine whether permanent termination is intended, whether reinstatement may be discretionary, or whether an automatic/provisional reinstatement model would improve proportionality and downstream predictability.

**Initial severity candidate:** `MINOR` to `MAJOR` depending on jurisdiction and intended policy.

### H-08 — No governing-law/forum clause is a deliberate decision still waiting to be made

Omission is not itself invalidity, but it leaves cross-border contract and remedy questions to conflicts rules.

Formal review should compare alternatives and preserve the omission only if that tradeoff is intentional.

**Initial severity candidate:** `NOTE` to `MAJOR`.

## 11. Initial authorities for specialist review

The first legal review should start from primary authorities and then expand jurisdiction by jurisdiction. At minimum:

- Directive 2009/24/EC on the legal protection of computer programs, especially Articles 4–6;
- Spain, Real Decreto Legislativo 1/1996 (Ley de Propiedad Intelectual), especially Articles 95–102;
- United States, 17 U.S.C. §§ 106 and 117;
- *Jacobsen v. Katzer*, 535 F.3d 1373 (Fed. Cir. 2008), for the US condition/copyright-remedy analysis of a public software license;
- CJEU, *UsedSoft GmbH v Oracle International Corp.*, C-128/11, for EU software-distribution exhaustion analysis; and
- United States, 28 U.S.C. § 1498(b), when reviewing federal-government copyright remedies.

These authorities are a starting map, not a substitute for current specialist research or jurisdiction-specific advice.

## 12. Relationship to other ECL review systems

```text
actor/project evidence review
  -> asks whether a designation is justified

formal Exergism review
  -> asks whether the analytical model supports/narrows/challenges that conclusion

legal adversarial review
  -> asks whether the exact legal mechanism actually grants, withholds and terminates rights as intended

release review
  -> asks whether the exact reviewed artifacts are the artifacts being shipped
```

None of these layers may silently substitute for another.
