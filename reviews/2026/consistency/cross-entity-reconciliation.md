# ECL 0.2 Cross-Entity Reconciliation — 2026

> **Status: PROVISIONAL GOVERNANCE / SCHEDULE-DESIGN RECORD — NO LICENSING EFFECT BY ITSELF.**

Audit date: **2026-08-13**  
Working license: **ECL 0.2-DRAFT**

## 1. Purpose

This audit begins after completion of the 195-State ECL 0.2 delta. Its purpose is to reconcile State, organization, person and project records before generating a replacement for the stale `ECL-RP-0.4-DRAFT` Schedule.

The old Schedule contained non-State Restricted Parties, classes and projects without canonical dossiers. That bypassed the repository lifecycle now required for ECL 1.0:

```text
evidence → canonical dossier → adversarial review → license-fit review → reasoned determination → versioned Schedule → release incorporation
```

No old Schedule entry is presumed correct merely because it already existed.

## 2. Structural findings

### 2.1 Non-State dossier vacuum

Before this reconciliation, `dossiers/organizations/`, `dossiers/persons/` and `dossiers/projects/` contained only README placeholders. Yet Draft 0.4 designated companies, armed organizations, natural-person classes and named projects.

**Decision:** no non-State entry may enter the next Schedule without a canonical dossier or an explicitly frozen determinable class whose members have received an equivalent ECL-native review.

### 2.2 Third-party lists are evidence, not automatic ECL law

The UN Security Council ISIL/Al-Qaida list and ICC warrant records are authoritative evidence sources for identity and conduct, but their listing criteria are not identical to ECL §5.

**Decision:** the next Schedule must not automatically import every UN-listed associate or every ICC warrant subject as an ECL Restricted Party. Maintainers may use frozen external records as evidence and identity anchors, but each entry/class must satisfy an ECL-specific rule.

### 2.3 State duplication

Draft 0.4 contains State sections that no longer match the canonical State registry, including blanket United States federal-government and State-of-Israel classes. The ECL 0.2 State delta narrowed both to `S`.

**Decision:** the next Schedule must be generated from canonical post-delta State dossiers rather than copying State sections from Draft 0.4.

### 2.4 Organization versus project attribution

Supplying technology to a sensitive customer is not by itself proof that every activity of a company is a Prohibited Use. Conversely, a company whose core product line is designed and distributed as invasive spyware and is officially documented as enabling repressive targeting may support an entity/business-line scoped finding.

The next Schedule should therefore distinguish:

- whole-organization Restricted Party candidates;
- scoped organization/business-line candidates;
- exact Restricted Projects;
- Material Participants / Covered Associates for a project; and
- ordinary/benign activity outside the project.

## 3. Palantir Technologies — old whole-company restriction does not survive

### Evidence

Official U.S. procurement records establish that Palantir provides ICE's Investigative Case Management / Investigative Analytics systems and that the software is deeply integrated into investigative case and subject management. DoD/Army records also establish substantial Maven Smart System and broader military software contracts.

Palantir's SEC filings show, however, that its business spans a very broad commercial and government customer base and many non-coercive sectors. The company also expressly disputes claims that it developed certain alleged automated targeting systems used by Israel and states that its ICE work is intended to improve data quality and reduce erroneous enforcement.

### Determination

**Organization level: `U`, not `R`.** The old whole-company Restricted Party entry is overbroad on the current record.

Specific ICE, Maven or other deployments may separately become Restricted Projects where evidence establishes that the exact deployment materially enables an ECL §5 Prohibited Use. Palantir may then be a Material Participant / Covered Associate for that exact project. Government contracting or defense work alone is insufficient.

## 4. Commercial spyware vendors

### NSO Group and Candiru

The U.S. Commerce Department states that NSO Group and Candiru developed and supplied spyware to foreign governments that used the tools to maliciously target officials, journalists, activists, academics, businesspeople and embassy workers and that the tools enabled transnational repression.

**Determination: `S` organization-level candidates**, scoped to development, supply, operation and material support of commercial spyware/surveillance projects that enable repressive surveillance, persecution or transnational repression under ECL §5.1/§5.6. This does not create permanent restriction for former employees or unrelated activity.

### Intellexa / Predator network

U.S. Treasury records identify Intellexa S.A., Intellexa Limited, Cytrox AD, Cytrox Holdings ZRT and Thalestris Limited as entities involved in developing, holding, reselling or distributing Predator spyware, and describe Predator as used to target government officials, journalists, policy experts and opposition politicians. Treasury separately identifies Aliada Group Inc. as a financial/network enabler.

**Determination: `S` scoped organization/network candidates.** Exact legal entities must be individually knowable in the Schedule; `Intellexa Consortium` is useful as a dossier/network label but is not a substitute for legal-entity identification.

## 5. ISIL and Al-Qaida

The UN Security Council maintains current named entries and narrative reasons for listing Al-Qaida and ISIL/Al-Qaida in Iraq, including participation in financing, planning, facilitating, preparing or perpetrating violent activities. The frozen UN list is valuable identity/evidence material, but contains hundreds of distinct people/entities under its own sanctions criteria.

**Determination:**

- **Al-Qaida — `R` organization candidate.**
- **ISIL/Da'esh — `R` organization candidate**, using exact current UN naming/aliases.
- **All other UN-listed associated actors — not automatically ECL Restricted.** Remove the blanket import rule from the next Schedule unless individual entries are ECL-reviewed or a narrow ECL-native class is separately justified.

## 6. Hamas and Izz al-Din al-Qassam Brigades

The UN Independent International Commission of Inquiry found that the 7 October 2023 attacks were led/coordinated by Hamas and implemented by the military wings of Hamas and other Palestinian armed groups, and found intentional attacks on civilians, murder, hostage-taking, torture/cruel treatment and other serious violations. Later Commission reporting found crimes against humanity/war crimes in the treatment of hostages by Hamas and other armed groups.

**Determination:**

- **Izz al-Din al-Qassam Brigades — `R` organization candidate** for its armed/hostage-taking/coercive operational apparatus.
- **Hamas — `S` organization candidate**, restricted only for armed-command, hostage/detention and other materially participating coercive structures/projects unless stronger evidence justifies treating every organizational function as the same prohibited apparatus.

Palestinians, Gaza residents, humanitarian/civil institutions and unrelated political/social activity are not restricted by identity or geography.

## 7. Sudan armed structures

Current OHCHR Special Procedures records contain serious allegations against the Rapid Support Forces, including arbitrary detention of approximately 9,000 persons at Shala Prison in 2026, torture/ill-treatment and life-threatening detention conditions, as well as broader patterns of killings, enforced disappearances, sexual violence and displacement. Separate State/SAF evidence already exists in the Sudan State dossier.

**Determination:**

- **RSF — `R` organization candidate**, subject to a dedicated dossier and current counter-evidence review.
- **SAF — do not duplicate blindly.** Create an organization dossier linked to `SDN.md`; any Schedule entry must align with the canonical Sudan `S` scope and avoid double-counting the same apparatus under inconsistent language.

## 8. Special Deterrence Forces / RADA and Osama Elmasry Njeem

The ICC states that its 18 January 2025 warrant for Osama Elmasry Njeem concerns alleged crimes at Mitiga Prison including imprisonment, torture, murder, rape/sexual violence and persecution, and states that the alleged crimes were committed personally, ordered by him or with his assistance by members of the Special Deterrence Forces / RADA.

**Determination:**

- **SDF/RADA — `S` organization candidate**, scoped to the Mitiga detention/security apparatus and any current materially continuous coercive structures established by evidence.
- **Osama Elmasry Njeem — `U` person candidate pending heightened person-level review.** An ICC warrant is powerful evidence but is not a conviction; the next ECL Schedule should not use a blanket `all ICC atrocity-warrant subjects` class without individualized ECL review and explicit due-process language.

## 9. Person-level class rule

The old `public ICC atrocity-warrant subjects` class is removed from the automatic-designation model.

A warrant may establish identity, alleged role and a judicial reasonable-grounds record. It does not establish criminal guilt and its legal threshold is not itself the ECL designation threshold.

**Decision:** person-level ECL designations require an individual dossier applying a heightened specificity standard. Where organization/project restriction adequately addresses the risk, prefer that narrower structural solution over personal restriction.

## 10. Schedule migration rule

The replacement Schedule must be generated from canonical dossiers and should not preserve Draft 0.4 numbering or categories merely for continuity.

Minimum requirements for each entry:

1. exact legal/organizational identity or exact named project;
2. current governance outcome and ECL 0.2 criterion;
3. scope / capacity limitation where `S`;
4. express material exclusions;
5. controlled-entity rule only where membership is reasonably knowable;
6. no recursive guilt by association;
7. remediation/safe-harbour relationship where relevant; and
8. exact source dossier identifier.

## 11. Remaining reconciliation queue

Before generating the new Schedule candidate, canonical dossiers should exist at minimum for:

- Palantir Technologies Inc.;
- NSO Group;
- Candiru;
- Intellexa/Predator legal entities and Aliada Group Inc.;
- Al-Qaida;
- ISIL/Da'esh;
- Hamas;
- Izz al-Din al-Qassam Brigades;
- Rapid Support Forces;
- Sudanese Armed Forces;
- Special Deterrence Forces / RADA;
- Osama Elmasry Njeem; and
- named project dossiers for any ICE, Maven/targeting, Mitiga-detention or other project proposed for direct Schedule designation.

Only after these records are normalized should a fresh post-0.2 Schedule candidate be created.
