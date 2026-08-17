# Formal Exergism Analysis

> **Status: Draft analytical specification.** This document formalizes the Exergism model used to interrogate ECL governance records. It does **not** create licensing restrictions, replace the operative ECL text, or map a numerical score directly to `R`, `S`, `U`, or `N`.

## 0. Pinned upstream lineage

The canonical philosophical/formal upstream currently adopted by this ECL analytical profile is **Exergism `v0.1.0`**, exact Git commit `4ca5207244f30060c486ca342f2f0af0d2a80fa2`. The machine-readable pin is [`exergism/upstream.json`](../exergism/upstream.json), including the SHA-256 identities of the upstream release manifest and source archive.

This specification is an **ECL application profile**, not a byte-for-byte mirror of the upstream corpus. ECL-specific scope discipline, evidence rules, uncertainty requirements and governance boundaries remain explicit here. A later Exergism release does not change this ECL profile without an explicit ECL repository change and downstream-impact review. This repository does not import the upstream OWL ontology, and the pin itself does not create licensing restrictions, Schedule entries or governance outcomes.

## 1. Purpose

ECL uses exergy both as a normative concept and, in governance, as a formal multicriteria analysis. The formal layer is intended to make hidden assumptions visible and testable before a designation decision is translated into legal scope.

The analytical chain is:

```text
evidence
  -> scorable object and scope
  -> normalized exergism variables + uncertainty
  -> immediate / strategic / structural / temporal analyses
  -> causal interpretation and sensitivity review
  -> exact ECL criterion fit
  -> attribution / exclusions / adversarial review
  -> provisional R/S/U/N governance outcome
  -> Schedule translation
```

The model is deliberately **multilayer**. A high strategic-historical value may never by itself cancel severe immediate harm, and no aggregate score substitutes for legal or evidentiary analysis.

## 2. Scope discipline before scoring

An assessment MUST identify the object being scored: a project, system, deployment, agency function, apparatus, institution, action, process, or event.

A whole State MUST NOT be scored merely because evidence exists about one project or agency. The object must follow the narrowest accurate attribution rule in `DESIGNATION-STANDARD.md`.

If the object is not sufficiently defined, the correct analytical state is `insufficient_evidence`, not an invented midpoint score. If no current ECL-relevant object exists, the correct state is `not_applicable`.

## 3. Normalized variables

All operational variables are normalized to `[0,1]`. Each value MUST be recorded as an uncertainty interval (`low`, `central`, `high`) with a rationale and evidence references.

### Positive / capacity variables

- `P` — **real transformative power**: capacity of the assessed object to materially transform conditions rather than merely exist formally.
- `A` — **effective autonomy**: practical ability of affected persons to choose, refuse, contest and act.
- `V_ep` — **epistemic truth access**: access to material reality, inspectability, freedom from systematic deception, and ability to distinguish evidence from manipulation.
- `L` — **liberation capacity**: capacity to reduce domination, restore agency, remedy prior capture, or create conditions for emancipation.
- `O` — **openness**: availability of exit, alternatives, interoperability, dissent, reversibility and non-captured future pathways.
- `U` — **exergic utility**: useful capability delivered to affected persons or communities without defining usefulness solely from the viewpoint of the dominant actor.

### Penalty / destruction variables

- `C` — **demiurgic capture**: concentration of effective capacity in a structure that disables others' autonomy, knowledge, bargaining power, alternatives or ability to exit.
- `S` — **structural suffering / damage**: material human or morally relevant harm produced or maintained by the object.
- `R` — **relapse / reproduction risk**: probability and structural propensity that the object reproduces, entrenches or restores the pattern of domination being evaluated.
- `Ecol` — **ecological cost**: destruction or degradation of ecological conditions that support durable human and collective capacity.

### Moral-domain coefficient

- `D_p` — **moral-domain coefficient**, normalized to `[0,1]`, used only where an analysis genuinely spans different moral domains. For ordinary ECL State/project assessments concerning human beings, `D_p = 1` unless the record states a defensible reason otherwise.

`D_p` MUST NOT be used to discount the moral standing of populations on the basis of nationality, ethnicity, religion, disability, class, citizenship or political status.

## 4. Core formulas

### 4.1 Base exergy

The v2 formal model uses a geometric mean so that a near-zero collapse in one constitutive capacity cannot be hidden by a very high value elsewhere:

```text
Ex_b = (P * A * V_ep * L * O * U)^(1/6)
```

### 4.2 Penalty term

```text
Pen = p_c * C^q_C + p_r * R + p_e * Ecol
```

where `p_c`, `p_r`, `p_e >= 0` are explicit contextual weights and `q_C > 0` controls the non-linearity of capture.

### 4.3 Relative exergy

```text
Ex_r = Ex_b / (1 + Pen)
```

`Ex_r` is a comparative structural indicator, not a moral verdict.

### 4.4 Immediate ethics

```text
E_i = D_p * [
    a1 * (A * V_ep)
  + a2 * (L * O * U)
  - a3 * S^q_S
  - a4 * C^q_C
  - a5 * Ecol
]
```

`E_i` asks what the object is doing to affected beings **now**. Strategic promise is not a defence to severe immediate harm.

### 4.5 Strategic-historical potential

```text
X_h = (P * O * A * U)^(1/4) / (1 + Pen)
```

`X_h` measures transformative potential under conditions of autonomy, openness and utility, discounted by capture, relapse and ecological cost.

### 4.6 Structural balance

```text
B_0 =
    b1 * Ex_b
  + b2 * L
  - b3 * C^q_C
  - b4 * S^q_S
  - b5 * R
  - b6 * Ecol
```

`B_0` is an explicit balance of liberating capacity against structural destruction. It is secondary to the decomposed variables and must always be read with `E_i` and `X_h`.

## 5. Temporal balance

Where a defensible time series exists, use the temporal layer inherited from the formal model:

```text
B_acc = sum_t [
  (Ex_b_t + O_t + A_t * V_ep_t)
  * exp(-lambda * t)
  * gamma_t
]

D_acc = sum_t [
  (S_t + Ecol_t + C_t)
  * exp(-lambda * t)
  * delta_t
]

N_t = B_acc - D_acc
```

- `lambda >= 0` is an explicit temporal discount/decay parameter.
- `gamma_t` and `delta_t` are explicit confidence/relevance multipliers and MUST NOT be silently defaulted in a governance assessment.
- `N_t > 0` means accumulated capacity dominates under the stated assumptions; `N_t < 0` means accumulated destruction dominates. The sign is not an ECL tier mapping.

A dossier without a defensible time series MUST leave `N_t` uncomputed rather than fabricate historical observations.

## 6. Parameters are not universal constants

The original formal system did not canonize universal numerical values for `p_*`, `q_*`, `a*`, `b*`, `lambda`, `gamma_t` or `delta_t`.

Therefore:

1. every composite calculation MUST identify the parameter profile used;
2. governance conclusions MUST be sensitivity-tested against plausible alternative profiles before claiming robustness;
3. a parameter profile may be published for mechanical regression testing, but it MUST be labelled non-normative until independently calibrated and adopted through governance; and
4. no maintainer may tune weights after seeing a target actor merely to force a desired tier.

## 7. Uncertainty and traceability

For every variable, record:

- `low`, `central`, `high` in `[0,1]`;
- a concise operational rationale;
- evidence references;
- whether the value is primarily `observed`, `inferred`, or `mixed`;
- the reviewer and review date where available.

The interval is epistemic uncertainty, not statistical confidence unless the underlying evidence supports a statistical interpretation.

When interval arithmetic is used, the analysis SHOULD report conservative bounds: low positive capacities with high penalties for the lower bound, and high positive capacities with low penalties for the upper bound.

## 8. Interpretation rules

The following rules are mandatory:

- **No score-to-tier function.** `R/S/U/N` remains a governance/legal outcome based on evidence, exact ECL criteria, attribution and Schedule knowability.
- **No moral laundering.** A high `X_h`, `P` or `U` cannot automatically absolve severe `E_i` harm, capture or suffering.
- **No midpoint fabrication.** Missing evidence is `insufficient_evidence`, not `0.5`.
- **No whole-State inflation.** A project score does not become a State score without evidence of cross-institutional scope.
- **No pseudoprecision.** Two decimal places do not make weak evidence strong. Ranges and rationales are primary.
- **No partisan parameterization.** The same scoring definitions and parameter profiles must be available for ideologically opposed actors.
- **Counter-institutions matter.** Courts, auditors, ombuds institutions, inspectors, remediation and meaningful exit must affect `A`, `V_ep`, `L`, `O`, `C` and/or `R` where the evidence supports it.
- **Ecology is not optional in the model.** If `Ecol` cannot be estimated responsibly, mark it uncertain and test sensitivity rather than silently setting it to zero.

## 9. Relationship to ECL criteria

Formal exergism analysis is an **upstream diagnostic layer**. It can reveal why an object is exergically destructive or liberating, but ECL restriction still requires exact normative fit with the operative license.

Examples of conceptual bridges include:

- low `A`/`O` + high `C` -> possible irreversible coercive capture;
- low `V_ep` + high `C` -> possible deceptive manipulation or information-control capture;
- high `S` + high `C` + low `A` -> possible coercive domination;
- high `P` with low `A`/`O` -> powerful but exergically captured capability;
- high `L`/`O` with falling `C`/`R` -> evidence of remediation or narrowing.

These are diagnostic relationships, not replacements for Section 5 elements.

## 10. Required place in the dossier workflow

Before a dossier can be treated as analytically complete for ECL 1.0 readiness, it should contain or link:

1. the exact scorable object;
2. formal exergism assessment status;
3. variable intervals and rationales where scorable;
4. parameter profile(s) used;
5. `Ex_b`, `Ex_r`, `E_i`, `X_h`, `B_0`, and `N_t` where data permit;
6. sensitivity / disagreement notes;
7. explanation of how the formal result does or does not support the exact ECL criterion;
8. counter-institutions and exclusions; and
9. the adversarial determination.

The formal analysis may confirm, weaken, narrow, or expose an inconsistency in a prior governance result. It does not retroactively create licensing restrictions.
