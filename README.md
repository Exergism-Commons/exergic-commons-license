# Exergic Commons License (ECL)

> **Status: ECL 0.3-DRAFT — experimental source-available license.**

ECL is an experimental software-license project focused on human agency, contestability, reversibility and distributed capacity. It is **not OSI-approved Open Source** and is not intended to satisfy the Open Source Definition.

## Canonical sources

- [`LICENSE`](LICENSE) — current working license text.
- [`spec/`](spec/) — principles, governance, terminology, designation standard, evidence valuation, formal Exergism, knowledge-model, living-update, versioning and legal-adversarial-review specifications.
- [`knowledge/`](knowledge/) — Git-native JSON-LD ABox records.
- [`ontology/`](ontology/) — OWL TBox, JSON-LD context and SHACL shapes.
- [`monitoring/`](monitoring/) — source-monitor contracts and change-detection policy.
- [`exergism/`](exergism/) — ECL-specific machine-readable Exergism assessments, pinned upstream context profiles and immutable upstream binding.
- [`dossiers/`](dossiers/) — canonical human-readable evidence/governance records during migration.
- [`reviews/`](reviews/) — adjudication, adversarial-review and consistency history.
- [`registry/`](registry/) — transitional machine-readable governance, translation, freeze and override views; intended to become generated from accepted decisions.
- [`schedules/`](schedules/) — exact versioned Schedules.
- [`versions/`](versions/) — immutable historical license snapshots.
- [`channels/`](channels/) — mutable convenience pointers; never authoritative over an exact bundle.

The immutable ECL 0.1 snapshot is [`versions/licenses/ECL-0.1.md`](versions/licenses/ECL-0.1.md). The root `LICENSE` is the ECL 0.3-DRAFT legal-hardening candidate; earlier drafts remain available through Git history.

## Formal Exergism layer

The canonical philosophical and formal upstream for ECL is **[Exergism](https://github.com/Exergism-Commons/exergism)**, maintained separately in `Exergism-Commons/exergism`. ECL currently pins **[Exergism `v0.1.0`](https://github.com/Exergism-Commons/exergism/releases/tag/v0.1.0)** at exact commit `4ca5207244f30060c486ca342f2f0af0d2a80fa2`; [`exergism/upstream.json`](exergism/upstream.json) records the immutable release and artifact identities.

ECL distinguishes the philosophical/normative use of exergy from the **formal Exergism analysis** applied to ECL governance records in [`spec/EXERGIC-ANALYSIS.md`](spec/EXERGIC-ANALYSIS.md). That application now follows the pinned canonical formal source `formal/sistema_analitico_exergico.json` rather than a locally invented universal profile.

The formal layer evaluates a precisely attributed object through normalized, evidence-backed intervals for transformative power, autonomy, epistemic truth access, liberation capacity, openness, exergic utility, capture, structural harm, relapse risk and ecological cost. Where evidence supports the canonical advanced layer, it also evaluates imputable agency, intentionality, lucidity, gratuitous harm, justification-of-cruelty risk, non-compensatory atrocity and strong moral imputation. Immediate-ethical, strategic-historical, structural, imputability and temporal outputs remain distinct.

There is deliberately **no numerical score-to-tier mapping**. Formal Exergism is an upstream diagnostic and falsification layer; restriction still requires exact ECL criterion fit, evidence, attribution, adversarial review, Schedule knowability and explicit incorporation. A later Exergism release does not alter ECL unless ECL explicitly updates its immutable pin and reviews downstream impact.

The pinned profiles, pilot and calculator are documented in [`exergism/README.md`](exergism/README.md).

## Knowledge model and living updates

Before the formal model is scaled to all 195 State dossiers, ECL is adopting a semantic maintenance architecture:

```text
OWL 2 TBox
    +
JSON-LD ABox in Git
    +
SHACL validation
    ↓
derived RDF dataset
    ↓
SPARQL integrity/dependency queries
    ↓
UpdateSignal -> UpdateCase -> evidence/claim delta
    ↓
differential Exergism -> exact ECL review -> GovernanceDecision
```

[`spec/KNOWLEDGE-MODEL.md`](spec/KNOWLEDGE-MODEL.md) defines the OWL/JSON-LD/SHACL/RDF/SPARQL separation. [`spec/LIVING-UPDATE-SYSTEM.md`](spec/LIVING-UPDATE-SYSTEM.md) defines change detection, automatic tickets, evidence qualification, differential re-analysis and governance escalation. [`spec/EVIDENCE-VALUATION.md`](spec/EVIDENCE-VALUATION.md) keeps evidence quality separate from formal Exergism scoring.

GitHub Issues are the public ticket/projection layer, not the database. The canonical editable knowledge state remains versioned in Git. Any RDF store/triplestore is a disposable index and must be reconstructible from the repository.

The OWL ontology deliberately does **not** infer restriction from association, graph reachability or Exergism scores. Such relationships can trigger review only through explicit governance procedure.

The RDF tooling is pinned reproducibly in `requirements-ontology.txt`. It currently uses the exact upstream RDFLib commit containing the JSON-LD internal `ConjunctiveGraph` warning fix, rather than falsely claiming that fix exists in the older RDFLib 7.6.0 release.

The first implemented automation is a deterministic review-due sweep: `tools/update_ticket_sweep.py` and `.github/workflows/living-review-sweep.yml`. The current five-State pilot exercises different review classes without changing any tier automatically.

## Versioning and exact ECL Bundles

ECL separates mutable living knowledge from immutable released legal artifacts. [`spec/VERSIONING.md`](spec/VERSIONING.md) defines:

```text
KnowledgeSnapshot
    -> GovernanceDecision
    -> immutable ScheduleRelease

immutable LicenseRelease + immutable ScheduleRelease
    = exact ECLBundle
```

A software release should resolve an exact bundle such as:

```text
ECL-1.0.0@RP-2026.10.02.1
```

and retain hashes/lock metadata for reproducibility.

Publisher policy is separate from the exact resolved bundle. Planned modes are:

- `pinned` — exact bundle never moves;
- `follow-stable` — each **new software release** resolves the newest compatible stable bundle;
- `latest-stable` — follows the newest stable line, with explicit confirmation required before crossing a legal MAJOR boundary.

`tools/ecl_resolve.py` implements the resolution boundary and writes an exact `ecl.lock`. It refuses non-operative/draft channels by default. An `operative: true` Bundle must also content-address a completed immutable legal-review record bound to the exact License and reviewed incorporation mechanism. `channels/draft.json` exists only as a development pointer: ECL currently has **no fabricated stable 1.0 bundle**.

This preserves both continuous governance improvement and non-retroactivity: later knowledge or Schedules do not silently rewrite already published software releases.

## 2026 State corpus

Detailed factual review and normalization are complete for **195 / 195** State dossiers.

Current provisional governance after applying the State outcome override layers:

- **34 `R`**
- **80 `S`**
- **34 `U`**
- **47 `N`**
- **195 total**

Read `registry/states.yml`, then apply all `registry/state-outcome-overrides*.yml` in lexical order. The override layer has precedence until the next consolidated snapshot.

The 195 dossiers are **not yet formal-exergism-complete** merely because factual/adversarial normalization is complete. Before ECL 1.0 readiness, each dossier should either link an evidence-backed scorable assessment, document why the object remains insufficiently defined, or document why no current ECL-relevant object exists.

The full formal pass should start only after the living knowledge/versioning architecture is adopted, so those assessments remain maintainable rather than becoming another static snapshot.

## Schedule engineering

Draft [`schedules/ECL-RP-0.4-DRAFT.md`](schedules/ECL-RP-0.4-DRAFT.md) is historical/pre-0.2 material. [`schedules/ECL-RP-0.5-PARTIAL-DRAFT.md`](schedules/ECL-RP-0.5-PARTIAL-DRAFT.md) is a non-operative rendering test.

Current State Schedule status:

- **34 / 34 `R`** identity freezes complete;
- all **80 active `S`** dossiers have completed Schedule translation;
- **79 / 80 active `S`** have at least one Schedule-renderable frozen entry;
- **1 `S`** remains in current-status / public-knowability review (`LAO`); and
- **0 `S`** remain blocked merely because identity/project translation is unfinished.

The 2026-08-14 five-gate revalidation froze narrow current projects for Iraq (`IRQ`) and the Philippines (`PHL`), downgraded Bulgaria (`BGR`) and Colombia (`COL`) from `S` to `U` rather than inferring continuing restrictability, and left Laos (`LAO`) as the sole active-`S` factual/knowability gate because the fresh public evidence deliberately withholds the identity needed for a defensible Schedule entry.

Canonical progress sources:

- [`registry/schedule-progress-overrides.yml`](registry/schedule-progress-overrides.yml)
- [`registry/schedule-status-overrides.yml`](registry/schedule-status-overrides.yml)
- [`registry/schedule-state-r-freeze.yml`](registry/schedule-state-r-freeze.yml)
- `registry/schedule-state-s-freezes/`
- [`registry/schedule-organization-freezes.yml`](registry/schedule-organization-freezes.yml)
- [`registry/schedule-armed-organization-freezes.yml`](registry/schedule-armed-organization-freezes.yml)
- [`registry/schedule-project-freezes.yml`](registry/schedule-project-freezes.yml)

`tools/render_schedule.py` renders a non-operative candidate from frozen records, and Schedule CI validates the current State coverage before producing the artifact.

A Schedule entry may be narrower than the dossier supporting it. Residual unfrozen scope remains governance-only.

## Non-State records

Canonical organization, project and person sources currently include:

- [`registry/organizations.yml`](registry/organizations.yml)
- [`registry/projects.yml`](registry/projects.yml)
- [`registry/persons.yml`](registry/persons.yml)

External lists may serve as evidence or identity anchors but are not automatically imported as mutable ECL classes.

## Release model

```text
source/change detection -> EvidenceItem/Claim -> KnowledgeSnapshot
        -> scoped formal Exergism analysis -> exact ECL criterion fit
        -> adversarial/consistency review -> GovernanceDecision
        -> generated current registry view
        -> Schedule translation/freeze -> immutable ScheduleRelease
        -> exact LicenseRelease + ScheduleRelease = ECLBundle
        -> qualified legal adversarial review of exact candidate artifacts
        -> content-addressed legal-review record
        -> operative software release records exact bundle/lock
```

Formal Exergism may confirm, weaken, narrow or expose an inconsistency in a governance result. It cannot create a restriction absent operative ECL fit.

No signal, GitHub ticket, claim record, dossier, Exergism assessment, review, ontology inference, registry entry or mutable channel has licensing effect by itself. Only exact legal artifacts expressly incorporated for a software release can have that effect.

## Legal status

ECL remains experimental. The project now defines a machine-enforced pre-1.0 adversarial legal-review gate in [`spec/LEGAL-ADVERSARIAL-REVIEW.md`](spec/LEGAL-ADVERSARIAL-REVIEW.md), but ECL 0.3-DRAFT has **not** completed that gate and no automated, maintainer, AI or community review counts as the required qualified independent legal review. Obtain qualified intellectual-property advice before relying on ECL for consequential deployments.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for challenges, contrary evidence and governance contributions.
