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
reviewed_at: "<timestamp/date>"
conclusion: compatible
sources:
  - path: "<exact renderer-consumed source path>"
    sha256: "<exact source SHA-256>"
```

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
