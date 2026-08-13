# ECL Global License-Fit Consistency Audit — 2026

> **Status: PROVISIONAL GOVERNANCE / DRAFTING RECORD — NO LICENSING EFFECT BY ITSELF.**

Evidence cutoff for State dossiers: **2026-08-11**  
Audit date: **2026-08-13**

## 1. Scope

This audit begins after completion of detailed normalization for all 195 State dossiers. It tests a different layer from the country-by-country factual review: whether the governance vocabulary, dossier scopes, draft Schedule and operative working license text actually describe the same normative rule.

Current pre-audit governance distribution is `R 36 / S 84 / U 28 / N 47 = 195`.

The audit applies the repository hierarchy strictly:

1. the current working `LICENSE` is the operative legal text if adopted by a release;
2. an exact incorporated Schedule determines Restricted Parties/Projects for that release;
3. `spec/` explains governance but cannot silently add prohibitions missing from the license;
4. dossiers/reviews/registry are evidence and governance records only.

## 2. Critical finding A — ECL 0.1 under-expresses the intended non-domination rule

`spec/PRINCIPLES.md` §2.5 states that ECL rejects technology materially serving **persecution, unlawful political repression, torture, collective punishment, arbitrary detention, or comparable destruction of fundamental agency**.

`spec/GOVERNANCE.md` §3 likewise permits designation where an actor materially and systematically participates in conduct substantially matching ECL categories, expressly including **persecution or unlawful political repression**, coercive targeting connected to serious rights violations, and systematic discriminatory domination.

The working ECL 0.1 text does not fully carry that rule into Section 5. In particular:

- §5.1 reaches arbitrary detention/political repression only when tied to **surveillance/tracking/profiling**;
- §5.2 reaches torture, disappearance, collective punishment and unlawful violence through **targeting/operational support**, but does not directly state arbitrary detention, forced labour, forced displacement or political repression as a general coercive project;
- §5.3 is limited to **automated or data-driven** discrimination;
- §5.5 is limited to technological dependence/informational control/decision asymmetry.

This creates a drafting gap: a dossier can faithfully implement the principles/governance standard while still citing conduct that is not cleanly expressed by the operative §5 wording.

**Conclusion:** the correct first response is not to mass-downgrade factually supported dossiers to fit an under-specified 0.1 draft. A new draft must translate the intended non-domination criterion into operative text, then the dossiers must be rechecked against that text.

## 3. Critical finding B — Scheduled Restricted Projects are not independently expressible cleanly in ECL 0.1

ECL 0.1 defines a `Restricted Project` almost entirely by participation, direction, benefit or circumvention involving an already Restricted Party/Covered Associate.

The draft Schedule, however, sometimes intends to identify a project independently and then follow its material participants. The current definition does not state clearly that an exact Schedule may itself designate a named project/program/deployment as a Restricted Project.

**Required correction:** a future draft should define `Restricted Project` as either:

1. a project expressly designated by the incorporated Schedule; or
2. a project becoming restricted through material participation/direction/benefit involving a Restricted Party or relevant Covered Associate.

This preserves knowability while supporting project-first attribution.

## 4. Critical finding C — Accountability and Remediation Exception is missing

The State adversarial review repeatedly found real rights-protective State functions inside otherwise implicated institutional structures: courts, ombuds/NPM bodies, prosecutors investigating official abuse, auditors, inspectors, legal defence and other remedial functions.

ECL 0.1 says that no rights are granted to a Restricted Party, but provides no sufficiently explicit functional exception for a genuinely independent unit/person using ECL-covered software solely to investigate, challenge, audit, prosecute, defend against, remedy or disclose the conduct that caused the restriction.

This creates two opposite risks:

- **overbreadth:** software needed for accountability could be blocked merely because the remedial institution sits formally inside a designated apparatus;
- **loophole:** a Restricted Party could relabel ordinary operational work as `compliance` or `accountability`.

**Required correction:** define a narrow `Independent Remediation Activity` safe harbour requiring genuine operational independence from the underlying prohibited conduct, no material participation in that conduct, a strictly remedial purpose and no material enablement of the Restricted Project.

## 5. Critical finding D — designation basis is governance-defined but not sufficiently visible in the operative license

`spec/DESIGNATION-STANDARD.md` correctly requires material/systematic conduct substantially matching operative ECL criteria, scope discipline, counter-evidence and adversarial review. `spec/GOVERNANCE.md` contains the substantive designation grounds.

But those files expressly have no independent licensing effect. ECL 0.1 §8 requires a governance procedure and reasoned evidence but does not itself state the minimum substantive basis for a Restricted Party/Project designation.

A future draft should therefore make two things simultaneously clear:

- maintainers must use the ECL substantive criteria when creating a Schedule; and
- for **licensee knowability**, an express designation in the exact incorporated Schedule controls until that Schedule is superseded, amended or legally invalidated — downstream users are not required to re-litigate the evidence underlying every listed party.

## 6. State-dossier impact screen

### 6.1 Strong direct fit already visible under ECL 0.1

A substantial part of the current `R`/`S` corpus already rests on conduct that fits the existing categories without relying on the drafting gap: repressive spyware/surveillance, algorithmic welfare profiling, biometric political surveillance, disappearance/torture targeting, civilian-targeting systems, coercive cyber/information-control systems and comparable projects.

Representative examples include Serbia (spyware), France (AI/video surveillance plus public-order use), Denmark and Netherlands (automated welfare-risk systems), Kenya (surveillance plus disappearance/torture/protest repression), Morocco (surveillance/repression), Mexico (disappearance/torture plus conditional biometric scope), Pakistan (surveillance/disappearance), Haiti (state-linked armed-drone targeting) and the conflict-targeting components of Sudan/Russia/other armed apparatus findings.

### 6.2 Findings materially dependent on the missing general non-domination clause

The principal gap-sensitive families are:

- political imprisonment/prosecution and suppression of peaceful civic activity where no surveillance layer is necessary to the finding;
- arbitrary or secret detention not itself produced by surveillance;
- systematic torture/ill-treatment in detention where the scope is the detention apparatus rather than a targeting system;
- coercive forced displacement/collective expulsion and severe pushback/refoulement projects;
- forced labour or coercive labour systems;
- severe non-automated discriminatory domination/persecution;
- coercive public-order systems materially suppressing peaceful assembly; and
- severe forced-eviction/territorial coercion projects.

Current `S` dossiers materially touching one or more of those families include, among others, Algeria, Angola, Bahrain, Bhutan, Bolivia, Bosnia and Herzegovina, Bulgaria, Cameroon, Central African Republic, Chad, Côte d'Ivoire, Croatia, Cyprus, Dominican Republic, Germany, Georgia, Guatemala, Hungary, Iceland, Italy, Kazakhstan, Kyrgyzstan, Laos, Lesotho, Libya, Lithuania, Malta, North Macedonia, Panama, Paraguay, Poland, Qatar, Republic of the Congo, Slovakia, Somalia, Ukraine, Uzbekistan, Yemen, Zambia and Zimbabwe.

The evidence in those dossiers is not thereby rejected. The issue is whether the operative license text states the same normative rule that the dossiers were applying.

### 6.3 Immediate scope-cleanup cases independent of the broader drafting fix

Some scope language should still be narrowed because it is not sufficient **by itself**, even under the intended ECL model:

- **Singapore:** POFMA/information-control and qualifying public-order repression can independently sustain scoped review; `capital punishment/execution` should not be treated as ECL-prohibited merely because an execution occurs. Any execution-related scope must independently satisfy unlawful targeting, persecution, discriminatory domination or another operative criterion.
- **Ukraine:** ordinary lawful conscription/recruitment is excluded. Only substantiated unlawful violence, torture/ill-treatment, arbitrary confinement or independently qualifying political-repression/security projects may remain in scope.
- **Border/migration dossiers generally:** asylum restriction, immigration administration, detention or return is not automatically ECL-prohibited. The project must materially involve arbitrary detention, persecution, collective/summary forced transfer without meaningful protection, unlawful violence, discriminatory domination, repressive surveillance or another operative criterion.
- **Capital punishment generally:** retention or use of the death penalty is not, without more, a standalone ECL category. Japan's current `U` treatment is therefore an important consistency comparator.

## 7. U/N delta risk if the operative rule is broadened

Aligning the license with the principles may change the evidentiary threshold for some current `U` cases. The most obvious recheck candidates are cases where `U` was retained specifically because the 0.1 technology/use nexus was too narrow despite evidence of serious current coercion.

Priority rechecks after a new draft include:

- Australia — severe youth-detention projects and jurisdiction-specific attribution;
- Japan — prolonged pre-indictment detention / `hostage justice` and whether current practice reaches systematic arbitrary detention under the revised criterion;
- Nauru — offshore asylum/detention regime with Australia/Nauru attribution split;
- South Africa — State-linked coercive migration operations versus non-State xenophobic violence;
- Austria — actual return/detention implementation versus policy capacity;
- Samoa — whether religious coercion remains prospective or becomes materially deployed persecution.

No automatic tier change follows from changing the draft language. Each case still requires evidence, attribution, persistence, counter-institutions and the narrowest accurate scope.

## 8. Schedule drift

`ECL-RP-0.4-DRAFT.md` predates completion of the 195-State adversarial cycle and the present normative audit. It also contains stale repository-path references such as `EXERGIC-GOVERNANCE.md` rather than `spec/GOVERNANCE.md`.

The schedule should therefore remain **non-adoptable draft material** until:

1. the new operative draft is fixed;
2. the R/S/U/N delta review under that draft is complete;
3. State/organization/project overlap is reconciled;
4. exact legal entities/classes and exclusions are made knowable; and
5. a new Schedule version is generated from the final audited determinations rather than patched ad hoc from Draft 0.4.

## 9. Legal-drafting issues outside the State evidence audit

Before ECL 1.0, specialist legal review should separately address at least:

- whether and how to add an explicit patent grant;
- treatment of moral rights and contributor authority where relevant;
- enforceability/interpretation of actor- and use-based conditions across jurisdictions;
- cure/reinstatement mechanics after termination;
- Schedule incorporation mechanics and notice;
- the boundary between copyright-controlled acts and hosted/service uses;
- conflicts between mandatory law and license restrictions; and
- whether governing-law/forum language would improve or reduce portability.

These are deliberately not resolved by the empirical State review.

## 10. Decision from this audit

The repository should proceed to an **ECL 0.2 working draft** rather than silently mutating ECL 0.1. The immutable `versions/licenses/ECL-0.1.md` snapshot remains unchanged.

ECL 0.2 should, at minimum:

1. add an operative systematic-coercive-domination / unlawful-political-repression criterion consistent with `PRINCIPLES §2.5`;
2. make independent Scheduled Restricted Projects expressible;
3. add a tightly bounded Independent Remediation Activity exception;
4. make the designation standard visible in the operative text while preserving Schedule knowability;
5. preserve explicit dual-use/ordinary-government safeguards; and
6. correct repository-path/version references.

After that text exists, run a delta audit of all 195 dossiers against **that exact draft** before generating a new Restricted Parties Schedule.
