# Formal Exergism assessments

This directory contains machine-readable governance inputs for the formal Exergism layer defined in [`spec/EXERGIC-ANALYSIS.md`](../spec/EXERGIC-ANALYSIS.md).

> These records have **no licensing effect by themselves**. They do not replace evidence review, exact ECL criterion fit, attribution, adversarial review or Schedule incorporation.

## Run the calculator

The calculator uses only the Python standard library:

```bash
python tools/exergic_analysis.py exergism/assessments/PRK.json --pretty
```

A different explicit parameter profile may be supplied:

```bash
python tools/exergic_analysis.py \
  exergism/assessments/PRK.json \
  --profile path/to/profile.json \
  --pretty
```

The committed [`reference-balanced-v2.json`](profiles/reference-balanced-v2.json) profile is **mechanical-reference-only**. Its weights are deliberately non-canonical because the original formal system did not define universal numerical constants. Governance conclusions require sensitivity analysis before ECL 1.0 readiness.

## Assessment states

- `scorable` — a sufficiently defined object exists and all formal variables can be bounded from evidence.
- `insufficient_evidence` — the object or evidence is not yet strong enough to assign values without manufacturing precision.
- `not_applicable` — no current ECL-relevant object exists at the required scope.

Missing evidence must never be silently converted to `0.5`.

## Initial cross-tier pilot

The first pilot intentionally spans distinct governance outcomes:

- [`PRK.json`](assessments/PRK.json) — `R`, scoped coercive State apparatus, scorable.
- [`USA.json`](assessments/USA.json) — `S`, only the defined federal project scope, scorable.
- [`NLD.json`](assessments/NLD.json) — `S`, narrow probation risk-algorithm scope, scorable.
- [`JPN.json`](assessments/JPN.json) — `U`, insufficiently defined Software/project nexus, therefore deliberately unscored.
- [`NZL.json`](assessments/NZL.json) — `N`, no current ECL-relevant object after adversarial review, therefore deliberately unscored.

Using the non-normative reference profile, the current pilot produces the following mechanical envelopes:

| Case | `Ex_r` | `E_i` | `B_0` | Formal reading |
| --- | --- | --- | --- | --- |
| PRK | `0.0241–0.0854` (`0.0526`) | `-0.8564–-0.6455` (`-0.7551`) | `-0.8626–-0.6163` (`-0.7436`) | robustly destructive under the pilot assumptions |
| USA scoped projects | `0.1381–0.3684` (`0.2373`) | `-0.6648–-0.2655` (`-0.4746`) | `-0.5463–-0.0046` (`-0.2818`) | negative across the current interval, but materially less captured than PRK |
| NLD probation tools | `0.2980–0.5906` (`0.4334`) | `-0.2662–0.2867` (`-0.0168`) | `-0.0864–0.4513` (`0.1853`) | composite balance is uncertainty-sensitive; exact ECL criterion and remediation evidence remain decisive |
| JPN | not computed | not computed | not computed | insufficiently defined ECL-relevant technology/project object |
| NZL | not computed | not computed | not computed | no current object to score at the required scope |

Values in parentheses are central estimates. The ranges are epistemic envelopes, not statistical confidence intervals.

The pilot deliberately demonstrates why there is no score-to-tier mapping. The Netherlands can remain a narrowly scoped `S` governance case because exact algorithmic conduct may satisfy an operative criterion even though aggregate formal balances cross zero under plausible variable bounds. Conversely, a negative formal score without exact ECL Section 5 fit cannot create a restriction.

## Next analytical gate

Before treating the 195-State corpus as **formal-exergism-complete**, each dossier should either:

1. link a `scorable` assessment with evidence-backed intervals and sensitivity review;
2. document `insufficient_evidence` and the exact missing facts; or
3. document `not_applicable` because no current ECL-relevant object exists.

That gate is separate from the already completed factual/adversarial normalization. It is intended to test whether the ECL corpus actually implements the Exergism theory rather than merely borrowing its vocabulary.
