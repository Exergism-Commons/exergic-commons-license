# ECL legal-review workspace

This directory separates **internal/adversarial pre-review material** from the immutable records that may eventually satisfy the ECL 1.0 qualified legal-review gate.

## Status boundary

Files such as Codex pass logs or maintainer notes in this directory are maintainer/AI-assisted pre-review evidence only. They do **not** count toward the independent qualified-review minimum in `spec/LEGAL-ADVERSARIAL-REVIEW.md`.

A completed legal-review gate record may exist only at:

```text
reviews/legal/records/<review_id>.json
```

and must conform to `schemas/legal-review-record.schema.json`. That schema accepts only `status: complete`; do not create a placeholder record before the qualified review is actually complete.

## Prepare immutable reviewer inputs

Preparation is based on an **exact Git commit**, not on mutable working-tree bytes. Start from an isolated clean checkout of the candidate commit and pass that full commit SHA explicitly:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)

python tools/prepare_legal_review.py \
  ECL-1.0-RC1-review-a \
  --license versions/licenses/ECL-1.0-RC1.md \
  --source-commit "$SOURCE_COMMIT"
```

The helper requires:

- `--source-commit` to be a full 40-hex commit SHA;
- that commit to equal the checkout's current `HEAD`; and
- a clean working tree before it writes anything.

The candidate License and canonical mechanism inputs are read from the immutable Git objects reachable from that commit. Their source paths in the preparation descriptor therefore mean **paths inside `source_commit`**, not whatever bytes a later working tree happens to expose at the same pathname.

The command materializes byte-for-byte copies of the three non-License mechanism inputs required by the review specification:

```text
reviews/legal/inputs/<review_id>/
  LEGAL-ADVERSARIAL-REVIEW.md
  VERSIONING.md
  bundle.schema.json
```

It prints a deterministic JSON preparation descriptor containing:

- `status: prepared-not-reviewed`;
- the exact `source_commit`;
- the candidate License path-in-commit and SHA-256;
- the path and SHA-256 of each frozen input;
- the future completed-record path; and
- an explicit warning that preparation is **not** a legal review record.

The tool never creates `reviews/legal/records/<review_id>.json`, never attests reviewer competence and never increments qualified-review counts.

## Trust boundary

The helper is an identity/reproducibility tool, **not a sandbox against a hostile process that already has write access to the same checkout or `.git` object database**. Run it in an isolated trusted checkout with no untrusted concurrent writer, such as a fresh CI job, dedicated worktree/container or otherwise controlled operator environment.

This boundary is deliberate. Earlier filesystem-hardening prototypes attempted to defend every pathname against arbitrary concurrent renames and replacement. That model cannot provide a meaningful final guarantee once an untrusted process has equivalent write authority over the repository. The current design instead makes source identity content-addressed by Git, requires a clean exact-HEAD checkout, and states the remaining local trust assumption explicitly.

After preparation, inspect and **commit the frozen snapshot before substantive qualified review is finalized**. The eventual legal-review record must hash the committed frozen copies. Git history plus the record hashes provide the historical identity; the preparer itself is not the legal attestation.

## Fail-closed rules

- `--license` is mandatory; there is no implicit `LICENSE` or `latest` candidate.
- `--source-commit` is mandatory and must be an exact full commit equal to current `HEAD`.
- The working tree must be clean before publication.
- Source files must be regular tracked Git blobs; committed symlinks are rejected.
- Paths must be repository-relative POSIX paths and may not traverse `..` or use absolute/backslash/colon forms.
- A `review_id` is permanently consumed once either `reviews/legal/inputs/<review_id>/` or `reviews/legal/records/<review_id>.json` exists in the source commit or current workspace.
- The tool refuses to overwrite an existing snapshot even if the bytes are identical.
- The output namespace itself must be a real directory, not a symlink.
- If a material candidate or mechanism input changes, use a **new review ID** and a new exact source commit. Do not mutate the old snapshot.
- A preparation failure must not be worked around by pointing a completed record at mutable canonical files.

## What qualified reviewers must still do

The preparation helper does not answer any legal question. Independent qualified reviewers must still cover the required jurisdiction tracks and `LAR-01` through `LAR-16`, record competence/independence/conflicts, preserve material findings and dissent, and disposition all release-blocking findings as required by `spec/LEGAL-ADVERSARIAL-REVIEW.md`.

Only after that substantive work is complete should the project create `reviews/legal/records/<review_id>.json`, bind it to the exact candidate License hash and committed frozen-input hashes, and allow an operative Bundle to reference that immutable record.
