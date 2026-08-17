# Formal Exergism assessments

This directory contains **ECL-specific machine-readable governance inputs** for the Exergism application layer defined in [`spec/EXERGIC-ANALYSIS.md`](../spec/EXERGIC-ANALYSIS.md). It is not the canonical home of the Metafísica emergentista de la liberación.

## Canonical upstream

The canonical repository is **[`Exergism-Commons/exergism`](https://github.com/Exergism-Commons/exergism)**. ECL pins **[Exergism `v0.1.0`](https://github.com/Exergism-Commons/exergism/releases/tag/v0.1.0)** at exact commit `4ca5207244f30060c486ca342f2f0af0d2a80fa2`.

The machine-readable contract is [`upstream.json`](upstream.json). The canonical formal source within that pinned release is `formal/sistema_analitico_exergico.json`.

This is a lineage/reproducibility dependency, not an automatic normative import. Later Exergism releases do not alter ECL until ECL explicitly updates the pin and reviews downstream impact. ECL does not `owl:imports` the upstream ontology.

> Exergism assessments have **no licensing effect by themselves**. They do not replace evidence review, exact ECL criterion fit, attribution, adversarial review or Schedule incorporation.

## Calculator

The calculator implements the canonical static formulas and temporal integration from pinned Exergism `v0.1.0`. It requires an **explicit context profile**; ECL does not guess one.

Example:

```bash
python tools/exergic_analysis.py \
  exergism/assessments/PRK.json \
  --profile exergism/profiles/upstream-transition-v0.1.0.json \
  --pretty
```

Pinned upstream context profiles:

- [`upstream-transition-v0.1.0.json`](profiles/upstream-transition-v0.1.0.json)
- [`upstream-liberated-society-v0.1.0.json`](profiles/upstream-liberated-society-v0.1.0.json)
- [`upstream-mundane-interaction-v0.1.0.json`](profiles/upstream-mundane-interaction-v0.1.0.json)

CI runs every committed assessment against all three profiles as a **mechanical sensitivity/regression check**. That does not assert that every context is normatively appropriate to every assessed object.

[`reference-balanced-v2.json`](profiles/reference-balanced-v2.json) is retained only as a deprecated legacy ECL regression profile from before the canonical upstream formal model was recovered. It is not an Exergism-canonical profile and is not a default.

## Canonical completeness

The early ECL pilot assessments contain the original core variables:

`P`, `A`, `V_ep`, `L`, `O`, `U`, `C`, `S`, `R`, `Ecol`, `D_p`.

Pinned Exergism `v0.1.0` also requires evidence for `D_a`, `I`, `Lz`, `G` and `Rj` to compute the non-compensatory/imputability layer:

```text
P_atr
E_i_adj
M_f
```

The calculator therefore labels legacy scorable records without those variables as **`core-only`**. It does not manufacture missing values. A static assessment becomes `canonical-static-complete` only when the complete advanced set is supplied.

The upstream temporal model additionally requires an explicit timeline, `lambda`, persistence weights and irreversibility. No temporal score is fabricated where those inputs do not exist.

## Assessment states

- `scorable` — the exact object is sufficiently defined for at least the supplied formal layer.
- `insufficient_evidence` — assigning the required variables would manufacture precision.
- `not_applicable` — no current ECL-relevant object exists at the required scope.

Missing evidence must never be silently converted to `0.5`.

## Current pilot

The initial five-record pilot still spans distinct ECL governance situations:

- [`PRK.json`](assessments/PRK.json) — scoped coercive State apparatus, currently core-only.
- [`USA.json`](assessments/USA.json) — scoped federal project set, currently core-only.
- [`NLD.json`](assessments/NLD.json) — narrow probation-tool scope, currently core-only.
- [`JPN.json`](assessments/JPN.json) — insufficiently defined object, deliberately unscored.
- [`NZL.json`](assessments/NZL.json) — no current object at the required scope, deliberately unscored.

Historical numerical envelopes produced with the deprecated balanced profile are no longer presented as the current Exergism baseline. Recompute explicitly against one or more pinned upstream context profiles and interpret the sensitivity, rather than treating one profile as universally correct.

## Next analytical gate

Before treating the 195-State corpus as **formal-exergism-complete**, each dossier should either:

1. provide a canonical-complete assessment with evidence-backed intervals, explicit context and sensitivity review;
2. document exactly which canonical variables remain unsupported and why; or
3. document `not_applicable` because no current ECL-relevant object exists.

That gate is separate from factual/adversarial normalization. Its purpose is to test whether ECL genuinely implements Exergism rather than borrowing its vocabulary.
