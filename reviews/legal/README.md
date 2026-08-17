# ECL legal-review workspace

This directory separates **internal/adversarial pre-review material** from the immutable records that may eventually satisfy the ECL 1.0 qualified legal-review gate.

## Status boundary

Files such as the Codex pass logs in this directory are maintainer/AI-assisted pre-review evidence only. They do **not** count toward the independent qualified-review minimum in `spec/LEGAL-ADVERSARIAL-REVIEW.md`.

A completed legal-review gate record may exist only at:

```text
reviews/legal/records/<review_id>.json
```

and must conform to `schemas/legal-review-record.schema.json`. That schema intentionally accepts only `status: complete`; do not create a placeholder record there before the qualified review is actually complete.

## Prepare immutable reviewer inputs

For each new external review or required delta review, choose a new immutable `review_id` and explicitly identify the exact candidate License file:

```bash
python tools/prepare_legal_review.py \
  ECL-1.0-RC1-review-a \
  --license versions/licenses/ECL-1.0-RC1.md
```

The command freezes byte-for-byte copies of the three non-License mechanism inputs required by the review specification:

```text
reviews/legal/inputs/<review_id>/
  LEGAL-ADVERSARIAL-REVIEW.md
  VERSIONING.md
  bundle.schema.json
```

It prints a deterministic JSON preparation descriptor containing:

- `status: prepared-not-reviewed`;
- the exact candidate License path and SHA-256;
- the path and SHA-256 of each frozen input;
- the future completed-record path; and
- an explicit warning that the preparation is **not** a legal review record.

The tool never creates `reviews/legal/records/<review_id>.json`, never attests reviewer competence, and never increments qualified-review counts.

## Secure runtime boundary

Snapshot preparation is an identity/security boundary, not a convenience copy command. The helper therefore requires filesystem primitives that let it bind validation, reads, writes and publication to pinned file/directory descriptors without following symbolic links. The current implementation requires a Linux/POSIX environment providing `dir_fd` operations, `O_NOFOLLOW`, `O_DIRECTORY` and atomic no-replace `renameat2` publication.

If those primitives are unavailable, the command **fails closed**. There is intentionally no insecure pathname-based fallback. Run preparation in a supported environment such as the repository's Linux CI runner, Linux host or compatible WSL environment. Manual copying/hashing is not an equivalent substitute for the content-addressed preparation path and must not be presented as satisfying this mechanism.

## Fail-closed rules

- `--license` is mandatory; there is no implicit `LICENSE` or `latest` candidate.
- Paths must be repository-relative POSIX paths and must not traverse symlinks.
- A `review_id` is permanently consumed once either `reviews/legal/inputs/<review_id>/` **or** `reviews/legal/records/<review_id>.json` exists. Deleting one side must never permit the ID to be rebound to later canonical bytes.
- Preparation reads canonical inputs and the candidate License through pinned descriptors and publishes a fully written private snapshot with atomic no-replace semantics.
- The tool refuses to overwrite an existing snapshot even if the bytes are identical.
- If a material candidate or review-mechanism input changes, prepare a **new** review ID/delta-review snapshot. Do not mutate the old snapshot.
- A preparation failure must not be worked around by manually pointing a completed record at mutable canonical files.

## What qualified reviewers must still do

The preparation helper does not answer any legal question. Independent qualified reviewers must still cover the required jurisdiction tracks and `LAR-01` through `LAR-16`, record competence/independence/conflicts, preserve material findings and dissent, and disposition all release-blocking findings as required by `spec/LEGAL-ADVERSARIAL-REVIEW.md`.

Only after that substantive work is complete should the project create `reviews/legal/records/<review_id>.json`, bind it to the exact License and frozen-input hashes, and allow an operative Bundle to reference that immutable record.
