# Planning Ledger Specification

## Status

Phase 1.5 documentation artifact. This file defines the intended shape of future operator-reviewed planning artifacts. It does not introduce any execution path, scheduler registration, or live reset behavior.

Version 0.2's optional expiry notifier is a separate read-only subsystem. It does not consume this document or any planning-ledger file as a task queue.

## Why this document exists

Phase 0 and Phase 1 established isolation, deterministic checkpoint planning, and read-only observability. The next safe step is not automation. The next safe step is a canonical artifact shape that can be reviewed by a human before any future dry-run bundle or decision gate exists.

That artifact is called the planning ledger.

## Non-goals

- not a task queue
- not a daemon input file
- not an authorization artifact
- not a source of private credentials
- not a live action request

## What a planning ledger is

A planning ledger is a static, inspectable record that ties together:

- the expiry target an operator is reasoning about
- the checkpoint timestamps derived from that target
- any read-only observations that support the plan
- explicit operator notes about confidence, unknowns, or blockers

The planning ledger is intended to be reproducible from the same inputs. At Phase 1.5, this repository only documents the format and rules. It does not yet generate the ledger automatically.

## Required properties

Every future planning-ledger artifact should make the following information explicit:

| Property | Purpose |
| --- | --- |
| `generated_at_utc` | Shows when the artifact was created |
| `target_expiry_utc` | Canonical expiry target in UTC |
| `target_expiry_local` | Human-readable local rendering of the same target |
| `planning_offsets_seconds` | Warmup, validation, and dispatch offsets used to derive checkpoints |
| `derived_checkpoints_utc` | The computed UTC checkpoints |
| `observation_summary` | High-level read-only observation context, if any |
| `operator_review` | Human notes, approval state, and unresolved questions |

## Reference shape

The reference shape below is illustrative. It is a documentation contract for future dry-run artifacts, not an implemented runtime API.

```json
{
  "generated_at_utc": "2026-08-02T11:40:00Z",
  "target_expiry_utc": "2026-08-02T12:00:00Z",
  "target_expiry_local": "2026-08-02T05:00:00-07:00",
  "planning_offsets_seconds": {
    "warmup": 900,
    "validation": 240,
    "dispatch": 80
  },
  "derived_checkpoints_utc": {
    "warmup_at": "2026-08-02T11:45:00Z",
    "validation_at": "2026-08-02T11:56:00Z",
    "dispatch_at": "2026-08-02T11:58:40Z"
  },
  "observation_summary": {
    "source": "codex app-server --stdio",
    "mode": "read-only",
    "detailed_rows_available": false,
    "notes": "availableCount was present but no detailed reset-credit rows were returned"
  },
  "operator_review": {
    "approved_for_preview_generation": false,
    "notes": "Confirm local timezone rendering before any future preview bundle is produced."
  }
}
```

## Time rules

- UTC is canonical for comparison and reproducibility.
- Local time is required for operator readability and sanity-checking.
- The local rendering must correspond to the same instant as `target_expiry_utc`.
- Future dry-run outputs should make timezone offsets explicit rather than relying on ambiguous local strings.

## Security rules

- Planning ledgers must never include API keys, token values, cookies, auth-file contents, or unrelated environment-variable values.
- If read-only observations are included, they should be summarized rather than storing raw credential-bearing payloads.
- Account identifiers should be masked if they are displayed outside a strictly local review context.

## Operator review checklist

Before a planning ledger is treated as a trustworthy dry-run input, an operator should be able to answer:

1. Is the expiry target clearly stated in both UTC and local time?
2. Are the checkpoint offsets the expected ones?
3. If read-only observations were used, are they described without exposing secrets?
4. Are there unresolved unknowns that should block any future preview bundle?
5. Does the artifact remain non-mutating and purely informational?

## Relationship to later phases

- Phase 1 established read-only observability.
- Phase 1.5 defines the planning-ledger contract and public posture.
- Phase 2 may generate dry-run and preview artifacts that follow this contract.
- Any live action decision remains outside this document and behind a separate policy and design gate.
