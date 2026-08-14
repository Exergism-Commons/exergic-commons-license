# ECL source monitoring

Source monitoring exists to create **review signals**, not automatic factual or legal conclusions.

## Adapter contract

A monitor record conforming to `../schemas/source-monitor.schema.json` identifies:

- a stable monitor ID;
- the exact source locator;
- the tracked subject/object IDs;
- an adapter type;
- the purpose of monitoring;
- expected predicates/events;
- a cadence;
- an authority hint used only for triage.

The first implemented automation is the deterministic `review-due` sweep. External source adapters should be added incrementally, beginning with structured/official feeds where change detection is reproducible.

## Preferred order

1. JSON/API feeds;
2. RSS/Atom;
3. stable publication indexes;
4. document hash/change checks;
5. narrowly configured HTML watchers.

A generic web crawler over actor names is intentionally **not** the default architecture: it would maximize noise, duplicate reporting chains and ideological/source-selection bias.

## Source change output

A source adapter should emit a normalized `UpdateSignal` containing at least:

```json
{
  "sourceId": "MON-...",
  "subject": "STATE-...",
  "detectedAt": "...",
  "locator": "...",
  "eventHash": "...",
  "candidateType": "remediation | deployment-stop | new-evidence | ...",
  "candidatePredicates": ["..."],
  "rawSummary": "..."
}
```

The signal is deduplicated by fingerprint. It may create a GitHub Issue for triage. It becomes a canonical `UpdateCase` only after the change is materialized into structured, reviewable evidence/claims.

## Removal symmetry

Every monitor plan for a restricted/scoped object should deliberately include, where available, sources capable of surfacing **remediation, suspension, judicial invalidation, oversight and cessation**. Monitoring only sources that can add restrictions would structurally bias the system toward permanent accumulation.
