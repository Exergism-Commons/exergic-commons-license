# Formal Exergism Analysis

> **Status: ECL application profile of pinned Exergism `v0.1.0`.** This specification applies the canonical formal Exergism model to ECL governance records. It does **not** create licensing restrictions, replace the operative ECL text, or map any numerical result directly to `R`, `S`, `U`, or `N`.

## 0. Canonical upstream

The canonical philosophical/formal upstream is `Exergism-Commons/exergism`. ECL pins Exergism `v0.1.0` at commit `4ca5207244f30060c486ca342f2f0af0d2a80fa2` through `exergism/upstream.json`.

The canonical formal source is `formal/sistema_analitico_exergico.json` in that pinned release. ECL MUST NOT silently replace an upstream formula with a locally invented one. ECL may add narrower evidence, uncertainty, scope and governance constraints required by the license workflow.

A later Exergism release has no effect on ECL until an explicit ECL change updates the immutable pin and reviews downstream impact. ECL does not `owl:imports` the upstream ontology.

## 1. Method boundary

The formal model is multicriteria, not a single moral score. ECL uses it as a diagnostic/falsification layer:

```text
evidence -> exact object -> normalized variables + uncertainty
         -> canonical Exergism analysis -> sensitivity/disagreement
         -> exact ECL criterion fit -> attribution/adversarial review
         -> governance outcome -> Schedule translation
```

No Exergism result has licensing effect by itself.

## 2. Scope and normalization

An assessment MUST identify the exact object being analysed. Whole-State scoring MUST NOT be inferred from a narrower project or apparatus.

Finite operational variables are normalized to `[0,1]` against ex-ante hypothetical minima/maxima or an explicit structured rubric. ECL records each value as an epistemic interval `low <= central <= high`, with rationale, evidence references, basis and uncertainty. Missing evidence remains missing; it is never silently replaced by a midpoint.

## 3. Canonical variables

Constitutive/capacity variables:

- `P` — real transformative power.
- `A` — effective autonomy.
- `V_ep` — partial epistemic truth orientation/access.
- `L` — non-manipulative liberating orientation.
- `O` — opening of possibilities.
- `U` — exergic utility.

Structural variables:

- `C` — demiurgic capture.
- `S` — structural suffering/damage.
- `R` — relapse/reproduction risk.
- `Ecol` — ecological impact.

Moral/imputability variables:

- `D_p` — moral-patient coefficient.
- `D_a` — imputable-agency coefficient.
- `I` — intentionality of domination/harm.
- `Lz` — agent lucidity.
- `G` — gratuitousness of harm.
- `Rj` — risk of justifying cruelty; a component of upstream relapse decomposition and an input to the atrocity penalty.

For ordinary ECL human-domain assessments, `D_p = 1` unless a defensible non-discriminatory reason says otherwise.

## 4. Upstream decompositions

The pinned model includes:

```text
A    = (Ai + Am + As + Ac) / 4
V_ep = (Co + Cr + Ce + Rs) / 4
L    = (Lm + Ln + La + Lt) / 4
C    = (Cp + Ci + Cs + Ct) / 4
R    = (Rh + Rj + Rp + Rc) / 4
Ecol = (Ed + El + Ep + Er) / 4
U    = Tr / (Tr + De + e)
```

The upstream suggested technical `e` is `0.01`. ECL may score aggregates directly when the evidence supports them, but component-level reasoning is preferred where it materially improves traceability.

## 5. Canonical formulas

```text
Ex_b = (P * A * V_ep * L * O * U)^(1/6)

Pen = pc * C^q_C + pr * R + pe * Ecol

Ex_r = Ex_b / (1 + Pen)

E_i = D_p * [
    a1 * (A * V_ep)
  + a2 * (L * O * U)
  - a3 * S^q_S
  - a4 * C^q_C
  - a5 * Ecol
]

X_h = (P * O * A * U)^(1/4) / (1 + Pen)

B_0 = b1 * Ex_b + b2 * L
    - b3 * C^q_C - b4 * S^q_S - b5 * R - b6 * Ecol
```

These metrics answer different questions and MUST NOT be collapsed into one ECL governance score.

## 6. Non-compensatory layer and imputability

Suggested upstream `v0.1.0` values:

```text
q_S = 2.0
q_C = 2.0
S_crit = 0.85
C_crit = 0.80
```

Canonical additional formulas:

```text
P_atr = r1 * max(0, S - S_crit)^2
      + r2 * max(0, C - C_crit)^2
      + r3 * Rj

E_i_adj = E_i - P_atr

M_f = D_p * D_a * (
    m1 * I + m2 * Lz + m3 * G + m4 * C + m5 * S
)
```

`M_f` distinguishes destructive effect from strong imputability. ECL MUST NOT invent `D_a`, `I`, `Lz`, `G` or `Rj` from outcome severity alone.

Existing pilots without the complete advanced variable set are explicitly `core-only`. The calculator does not emit `P_atr`, `E_i_adj` or `M_f` until all required advanced variables are evidenced.

## 7. Canonical context profiles

ECL stores exact pinned context-weight copies in `exergism/profiles/`.

`transicion`:

```text
a = [0.22, 0.18, 0.22, 0.16, 0.12]
b = [0.28, 0.12, 0.16, 0.16, 0.14, 0.14]
(pc, pr, pe) = (0.40, 0.30, 0.30)
m = [0.25, 0.20, 0.20, 0.20, 0.15]
r = [0.50, 0.30, 0.20]
```

Known upstream ambiguity: `a1..a5` sum to `0.90`. ECL preserves this exactly and does not silently renormalize it.

`sociedad_liberada`:

```text
a = [0.24, 0.16, 0.24, 0.18, 0.18]
b = [0.24, 0.14, 0.18, 0.18, 0.13, 0.13]
(pc, pr, pe) = (0.45, 0.30, 0.25)
m = [0.20, 0.20, 0.20, 0.20, 0.20]
r = [0.45, 0.35, 0.20]
```

`interaccion_mundana`:

```text
a = [0.26, 0.16, 0.24, 0.20, 0.14]
b = [0.26, 0.14, 0.18, 0.18, 0.12, 0.12]
(pc, pr, pe) = (0.40, 0.25, 0.35)
m = [0.25, 0.20, 0.25, 0.15, 0.15]
r = [0.50, 0.30, 0.20]
```

ECL does not guess a context. The CLI requires an explicit profile. CI evaluates committed assessments against all three pinned profiles as a mechanical sensitivity/regression check; that does not imply that every context is applicable to every object.

`reference-balanced-v2.json` is deprecated legacy ECL regression material, not canonical Exergism.

## 8. Canonical temporal integration

For a defensible timeline:

```text
D_acc = SUM_t [
    (S_t^q_S + Ecol_t + C_t^q_C + P_atr_t)
    * exp(-lambda * t) * delta_t * (1 + Irr_t)
]

B_acc = SUM_t [
    (Ex_b_t + O_t + A_t * V_ep_t + L_t)
    * exp(-lambda * t) * gamma_t
]

N_t = B_acc - D_acc
```

The pinned upstream does not provide a universal numeric `lambda`; ECL therefore requires it explicitly for temporal calculation. `gamma_t`, `delta_t` and irreversibility must also be explicit. A positive `N_t` is not automatic moral absolution.

## 9. Macroevents

The upstream model supports hierarchical subevents and macroevent aggregation. The current ECL calculator implements the canonical static formulas and canonical timeline integration but does **not** yet claim full macroevent aggregation support. ECL MUST NOT fabricate aggregate whole-State results while that layer remains unimplemented.

## 10. Mandatory ECL rules

- No score-to-tier function.
- No moral laundering between immediate, strategic, structural and temporal layers.
- No midpoint fabrication.
- No whole-State inflation.
- No pseudoprecision.
- No partisan parameter tuning.
- Counter-institutions and remediation matter when evidenced.
- Ecology remains explicit.
- Intent/imputability variables require their own evidence.
- Formula changes belong upstream in Exergism or require an explicit documented ECL application delta.

## 11. Dossier completeness gate

Before a dossier is `formal-exergism-complete` for ECL 1.0 readiness, it should contain or link:

1. exact object/scope;
2. assessment state;
3. normalization anchors/rubric;
4. evidence-backed intervals;
5. explicit context profile(s) and sensitivity review;
6. `Ex_b`, `Pen`, `Ex_r`, `E_i`, `X_h`, `B_0`;
7. `D_a`, `I`, `Lz`, `G`, `Rj`, `P_atr`, `E_i_adj`, `M_f` when evidence permits canonical-complete static analysis;
8. `B_acc`, `D_acc`, `N_t` where a defensible timeline exists;
9. counter-institutions, exclusions and disagreement notes;
10. explanation of exact ECL criterion relevance; and
11. adversarial determination.

Formal Exergism may confirm, weaken, narrow or expose an inconsistency in a governance result. It cannot create licensing restrictions by itself.
