# Contributing to the Exergic Commons License

ECL is an experimental license project. Contributions are welcome, especially legal criticism, adversarial examples, ambiguity reports, governance proposals, contrary evidence, designation challenges and improvements that make the license more precise without abandoning its exergist purpose.

## Repository layers

Keep changes in the correct layer:

- `LICENSE` — operative license text.
- `spec/` — principles, terminology and governance standards.
- `schedules/` — exact versioned Restricted Party designations.
- `dossiers/` — entity-specific evidence, counter-evidence and determinations.
- `reviews/` — historical adjudication/adversarial-review records.
- `registry/` — machine-readable mirrors of governance status.
- `versions/` — immutable historical snapshots.

Do not place new research or designation records in the repository root.

## Proposed workflow

For substantive changes:

1. Open or use the relevant issue/dossier.
2. State the exact problem or proposed designation.
3. Give concrete evidence and distinguish fact from inference.
4. Include material counter-evidence and uncertainty.
5. Apply the standards in [`spec/GOVERNANCE.md`](spec/GOVERNANCE.md), [`spec/PUBLIC-REVIEW.md`](spec/PUBLIC-REVIEW.md) and [`spec/DESIGNATION-STANDARD.md`](spec/DESIGNATION-STANDARD.md).
6. Keep operative `LICENSE` changes separate from evidence changes where practical.
7. A stable designation must be adopted in an exact versioned file under `schedules/`; a dossier finding alone has no licensing effect.
8. A substantive license change must produce a new immutable snapshot under `versions/licenses/` before being declared stable.

## Restricted Party proposals and challenges

Designation, removal and narrowing proposals must identify:

- the exact party, project or class;
- the ECL criteria allegedly satisfied or no longer satisfied;
- material conduct and attribution;
- supporting evidence;
- contrary evidence and uncertainty;
- proposed scope;
- remediation/removal conditions where appropriate; and
- whether the proposal concerns the party itself, associated projects, or both.

Do not use ECL designations for harassment, nationality-based exclusion, ideological blacklisting, unsupported accusations or recursively expanding guilt by association.

## State dossiers and public review

Each State has a canonical entry point under `dossiers/states/`. The corresponding GitHub State issue is a **public governance-review surface**: it exists so contributors other than the primary author can scrutinize identity, evidence, counter-evidence, attribution, exact ECL criterion fit, scope, remediation and formal Exergism.

The issue is not a second canonical dossier. Accepted material evidence or conclusions should be normalized into repository records with provenance.

A State issue should remain open while the current review cycle still needs external scrutiny. Internal completion of a dossier does not by itself satisfy independent review.

For a review intended to count toward the minimum independent-review gate in [`spec/PUBLIC-REVIEW.md`](spec/PUBLIC-REVIEW.md), reviewers should:

1. state a disposition: `support-current-conclusion`, `support-with-narrowing`, `challenge-current-conclusion`, `insufficient-evidence`, or `conflict-disclosed / evidence-only`;
2. identify what they actually checked;
3. provide supporting and contrary evidence;
4. identify material objections or uncertainty; and
5. disclose relevant authorship, employment, financial, advocacy or other material conflicts.

Reviews are not votes. Reactions and raw approval counts do not resolve a substantive evidence or attribution objection.

The same scrutiny applies to `R`, `S` and `N`, and to narrowing/removal. Review must test the current conclusion rather than assume restriction is the desired direction.

## Independent-review minimum

A final `R`, `S` or `N` GovernanceDecision intended to support ECL 1.0 readiness or a stable Schedule requires at least **two substantive independent reviews**, including at least one adversarial/falsification review, plus resolution or explicit documentation of material dissent.

The primary author or maintainer may respond, revise and make provisional determinations but cannot count their own work as an independent review. Where the review gate cannot yet be satisfied, `U` remains the appropriate unresolved governance state.

See [`spec/PUBLIC-REVIEW.md`](spec/PUBLIC-REVIEW.md) for independence, conflicts, material objections and closure criteria.

## Contribution rights

By intentionally submitting text, code, examples or documentation for inclusion, you represent that you have the right to submit it and grant the maintainers and downstream recipients a perpetual, worldwide, royalty-free, non-exclusive, irrevocable copyright license to reproduce, modify, publish, distribute, sublicense and incorporate the contribution into current or future versions of ECL and related documentation.

This contribution term remains a draft and should receive legal review before ECL 1.0.

## Style

Prefer defined terms over rhetoric, behavior over ideology, material participation over remote association, objective triggers where possible, explicit knowledge standards, evidence/counter-evidence, versioned schedules and non-retroactivity.

Avoid undefined moral labels such as “evil” or “enemy” in operative text. The project should improve by trying to falsify its own conclusions before downstream users must rely on them.
