# ECL Redistribution Identity and Self-Contained Bundle Profile

> **Status: Draft release/tooling specification.** This document does not replace or modify the operative duties in `LICENSE`. It defines one strict, machine-verifiable packaging profile for preserving exact Bundle identity during redistribution.

## 1. Purpose

ECL Section 4 requires a distributor exercising Licensed Rights to preserve, for each affected Licensor grant and material:

- the exact ECL License;
- the exact Schedule governing that grant and material; and
- immutable Bundle metadata identifying both exact components.

A hash, Bundle identifier, lock file, mutable registry entry, branch or channel is not a substitute for the Schedule where Section 4(c) requires the Schedule to accompany the copy. Section 4 separately permits a demonstrably retrievable immutable content-addressed Schedule reference in the circumstances stated by the License.

This specification defines a **self-contained local-accompaniment profile** so mirrors, vendored dependencies, binary packages, containers and archives can preserve an objective resolution path without consulting mutable project state.

It is a sufficient machine-verifiable packaging profile. It is **not a declaration that every legally compliant redistribution must use this layout**, and the verifier does not adjudicate the alternative immutable-retrieval route allowed by Section 4.

## 2. Canonical self-contained envelope

A profile-v1 envelope is a real directory containing at least:

```text
ECL-DISTRIBUTION.json
ECL-BUNDLE.json
LICENSE
ECL-SCHEDULE
```

Additional application/package files may exist outside or alongside the envelope. For software containing multiple Licensor grants or multiple exact ECL Bundles, preserve one independently verifiable envelope per affected Bundle/material scope, for example under a package-specific namespace such as:

```text
ecl/
  ECL-1.0.0@RP-2026.08.18.1/
    ECL-DISTRIBUTION.json
    ECL-BUNDLE.json
    LICENSE
    ECL-SCHEDULE
  ECL-1.0.0@RP-2026.09.01.1/
    ...
```

The directory name is convenience metadata. The authoritative identity inside each envelope is the descriptor plus exact hashed bytes.

## 3. `ECL-DISTRIBUTION.json`

The descriptor conforms to `schemas/distribution.schema.json` and binds:

- the exact immutable Bundle identifier;
- whether that Bundle manifest declares itself operative;
- SHA-256 of the exact copied `ECL-BUNDLE.json`;
- exact License ref, local path `LICENSE`, and SHA-256;
- exact Schedule ref, local path `ECL-SCHEDULE`, and SHA-256; and
- a mandatory notice that packaging verification is not legal advice, legal review or a compliance determination.

JSON object member names MUST be unique in both `ECL-DISTRIBUTION.json` and `ECL-BUNDLE.json`, including nested objects. The canonical tools reject duplicate member names rather than inheriting parser-dependent first-wins/last-wins behavior for legal identity metadata.

The local paths are deliberately fixed. Profile v1 does not permit a descriptor to redirect the License, Schedule or Bundle manifest through `..`, an absolute path, a symlink, a mutable URL, a branch, a channel or another external namespace.

`ECL-BUNDLE.json` is the byte-for-byte immutable Bundle manifest from the ECL release source. Its repository-relative component paths are provenance for the source repository; within this redistribution envelope, the fixed local paths in `ECL-DISTRIBUTION.json` identify the accompanying copies.

## 4. Semantic Bundle identity invariant

The Bundle identifier is not an independent label. For every Bundle, tooling enforces:

```text
bundle == license.ref + "@" + schedule.ref with the leading "ECL-" removed
```

For example:

```text
license.ref  = ECL-1.0.0
schedule.ref = ECL-RP-2026.08.18.1
bundle       = ECL-1.0.0@RP-2026.08.18.1
```

A manifest named or labelled as one Bundle while carrying different License or Schedule refs is invalid even if every individual file hash is internally consistent. This invariant also applies before `ecl.lock` is rendered, preventing contradictory lock metadata.

The Canonical Empty Schedule fallback remains subject to its additional exact registered identity rules in `tools/ecl_resolve.py` and `schemas/bundle.schema.json`.

## 5. Building an envelope

The builder deliberately **does not create missing parent directories**. The output parent must already exist as a real, non-symlink-resolved directory; this keeps parent-path trust explicit instead of silently creating a hierarchy through an unexpected namespace. Create the intended packaging parent first, then ask the builder to create only the final envelope directory.

For an operative Bundle:

```bash
mkdir -p dist/ecl
python tools/ecl_distribution.py build \
  --repo-root . \
  --bundle ECL-1.0.0@RP-2026.08.18.1 \
  --output dist/ecl/ECL-1.0.0@RP-2026.08.18.1
```

The builder subsequently verifies that `dist/ecl` resolves exactly as that path and rejects a parent path that traverses a symlink. Therefore `mkdir -p` is only the explicit parent-creation step; it does not relax the builder's namespace check.

Before copying bytes, the builder invokes the repository Bundle validator. Therefore an operative source Bundle must already satisfy its machine-verifiable completed legal-review gate.

Non-operative/draft Bundles are refused by default. They may be packaged only for testing with explicit opt-in:

```bash
python tools/ecl_distribution.py build \
  --repo-root . \
  --bundle ECL-0.3-DRAFT@RP-EMPTY-1 \
  --output /tmp/ecl-draft-envelope \
  --allow-draft
```

The resulting descriptor preserves `operative: false`. Packaging a draft does not promote it to an operative release.

The builder refuses to overwrite an existing output directory. It writes the descriptor last, so an interrupted build lacking `ECL-DISTRIBUTION.json` cannot verify as a complete profile-v1 envelope.

## 6. Verifying a redistributed copy

Verification is repository-independent:

```bash
python tools/ecl_distribution.py verify \
  --root dist/ecl/ECL-1.0.0@RP-2026.08.18.1
```

The verifier fails closed if, among other cases:

- `LICENSE`, `ECL-SCHEDULE`, `ECL-BUNDLE.json` or `ECL-DISTRIBUTION.json` is missing;
- any exact byte hash is corrupted or substituted;
- either JSON identity document contains duplicate object member names;
- the descriptor attempts to redirect one of the fixed local paths;
- a required local file is a symlink;
- the Bundle identifier contradicts the License/Schedule refs;
- descriptor and Bundle manifest disagree on Bundle identity or operative state;
- the local License or Schedule ref/hash disagrees with the frozen Bundle manifest; or
- an operative manifest omits immutable legal-review metadata.

A successful result means only that the self-contained identity envelope is internally exact and reconstructible. It does **not** determine whether a particular distribution implicates Licensed Rights, whether every Section 4 obligation for every Licensor/material scope has been met, whether a reviewer was legally qualified, or whether ECL is enforceable in a jurisdiction.

## 7. Failure disposition

If the verifier reports a missing or corrupted Schedule/Bundle component, **do not repair the copy by resolving `latest`, a branch, a mutable registry view, a channel, or a later Schedule**. Those sources cannot retroactively identify the earlier exact Bundle.

For the self-contained profile, repair means restoring the exact bytes whose immutable refs/hashes are bound by the affected Bundle and rebuilding or re-verifying the envelope. If the distributor instead relies on the alternative immutable content-addressed retrieval route allowed by Section 4, that route must independently satisfy the operative License; this local verifier intentionally returns no opinion on that legal/factual question.

Failure for one Bundle envelope does not manufacture an empty Schedule, broaden the recipient's rights, or alter another Licensor's otherwise distinct Bundle. Scope remains grant-, material- and Bundle-specific as stated by `LICENSE`.

## 8. Threat boundary

The builder and verifier reject symlink-based local substitution and unsafe descriptor paths, but they are not sandboxes against a hostile process with equivalent write authority mutating the same directory while verification is executing. Run them against a stable package/envelope. For archival or supply-chain authenticity beyond internal identity, separately use signatures, trusted release provenance or another authenticated distribution mechanism.

## 9. Relationship to `ecl.lock`

`ecl.lock` remains exact publisher/release resolution metadata under `spec/VERSIONING.md`. It is useful and SHOULD be retained with a software release where applicable, but a correct lock alone does not prove that the exact Schedule actually accompanies a redistributed copy.

The profile-v1 envelope closes that distinction by binding and carrying the exact Schedule and License bytes locally together with their exact Bundle manifest. No mutable channel movement can change those already packaged bytes or their recorded hashes.
