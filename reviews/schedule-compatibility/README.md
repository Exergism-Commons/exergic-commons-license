# Schedule compatibility evidence

This directory stores immutable, content-addressed evidence records used by the
Schedule renderer. It is separate from qualified legal-review records.

A completed `registry/schedule-license-compatibility.yml` pointer must reference
exactly:

`reviews/schedule-compatibility/<sha256>.yml`

where `<sha256>` is the lowercase SHA-256 of that evidence file's exact bytes.
The renderer rejects any path/ID/content mismatch.

Each evidence record must contain:

```yaml
schema_version: 1
target_license: "ECL-0.3-DRAFT"
target_license_artifact:
  path: "versions/licenses/ECL-0.3-DRAFT.md"
  sha256: "<exact target License SHA-256>"
reviewer: "<identity of compatibility reviewer>"
reviewed_at: "2026-08-15T00:00:00Z"
conclusion: compatible
sources:
  - path: "<exact renderer-consumed source path>"
    sha256: "<exact source SHA-256>"
```

`reviewed_at` must be either a valid ISO calendar date (`YYYY-MM-DD`) or a
valid RFC 3339 timestamp with an explicit timezone (`Z` or `±HH:MM`). Unquoted
YAML date/timestamp scalars are also accepted when PyYAML materializes them as
`date` or timezone-aware `datetime` values. The renderer validates the original
YAML scalar lexically **before** PyYAML timestamp construction, including
explicit clock/offset field ranges, so malformed inputs such as `24:00:00Z`,
`+01:60`, or `+00:99` cannot be normalized into apparently valid values.
Malformed dates, arbitrary strings, out-of-range clock/offset fields, and
timezone-less timestamps are rejected. This parsing rule is part of the
compatibility gate itself and is regression-tested through the same
content-addressed evidence path used by a future `complete` state.

The `sources` set must exactly equal every frozen clause source consumed by
`tools/render_schedule.py`: no missing, extra, duplicate or stale bindings are
accepted. The evidence target-License binding must also exactly match the
current mutable pointer and the frozen License bytes, while root `LICENSE` must
remain byte-identical to that frozen artifact.

Changing the License or any consumed source therefore requires a new review and
a new evidence file with a new content hash. Reusing an old evidence ID after
refreshing mutable claims is rejected.

These records prove repository-level compatibility-review identity and input
binding only. They do not by themselves constitute qualified independent legal
review or satisfy #207.
