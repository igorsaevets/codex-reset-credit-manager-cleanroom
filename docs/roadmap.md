# Roadmap

## Guiding rule

This roadmap is intentionally conservative. Each phase must earn the right to exist. The repository should not jump from a read-only planning draft to a live auto-reset tool just because that is the emotionally attractive destination.

## Phase 0 — Hardening foundation

Status: current

### Scope

- separate draft root under `%LOCALAPPDATA%\CodexResetCreditDraft`
- explicit `CODEX_HOME` and `CODEX_SQLITE_HOME` isolation
- allowlist-based child-process environment
- deterministic expiry planning
- Scheduled Task XML preview only
- unit tests for current guarantees

### Exit criteria

- no writes to the legacy `%LOCALAPPDATA%\CodexResetCredit` install
- no live consume path in code or tests
- environment preview clearly demonstrates stripped variables
- docs explain current non-goals without ambiguity

## Phase 1 — Read-only observability

Status: proposed

### Objective

Add optional, documented-surface read-only visibility through `codex app-server` without introducing any live mutation path.

### Candidate features

- opt-in `account/rateLimits/read` adapter over `codex app-server --stdio`
- normalized parsing of available reset-credit counts and detail rows when the backend provides them
- local audit artifact showing what was observed and what was intentionally not inferred
- version and capability probe for the local `codex` binary

### Non-goals

- no `account/rateLimitResetCredit/consume`
- no retry logic for redemption outcomes
- no scheduler registration

### Exit criteria

- strictly read-only tests with no live side effects
- clear fallback behavior when detailed reset-credit rows are unavailable
- docs explain the difference between `availableCount` and any returned detail rows

## Phase 2 — Operator-in-the-loop planning artifacts

Status: proposed

### Objective

Move from static timestamp planning to richer, auditable planning artifacts while remaining non-mutating.

### Candidate features

- planning ledger format for a chosen expiry target
- explicit timezone rendering and local/UTC comparison helpers
- structured dry-run reports
- preview bundle for a future scheduled action without performing registration

### Non-goals

- no automatic task installation
- no live reset attempt
- no background daemon

### Exit criteria

- dry-run artifacts are reproducible from the same inputs
- no dependence on auth scraping or private endpoints
- documentation explains exactly what remains hypothetical

## Phase 3 — Decision gate for any live action

Status: not approved

### Objective

Decide whether a user-initiated live path should exist at all.

### Questions that must be answered first

- Is publication posture resolved enough for a public release?
- Is there a terms-compliant way to present live redemption without implying rate-limit bypass?
- Is the supported app-server contract stable enough for a local tool?
- Can the repository separate read-only and mutating capabilities cleanly?

### If the answer is “no”

The repository remains a planning and observability toolkit. That is still a legitimate product outcome.

### If the answer is “yes”

Only then should the team design a live path with:

- explicit operator intent
- supported app-server methods only
- durable idempotency handling
- read-after-action reconciliation
- tests that do not consume real credits

## Phase 4 — Optional scheduler activation

Status: deferred

### Objective

Consider whether task registration or last-chance execution should exist as an explicit, separate capability.

### Guardrails

- never enabled by default
- no silent activation during install
- separate documentation from the read-only workflow
- activation flow must be obvious and reversible

### Why this is late

Scheduler activation multiplies the blast radius. It interacts with sleep/wake timing, battery state, missed windows, and user expectations. That work should not happen before the read-only and operator-controlled layers are solid.

## Release gates that apply to every future phase

1. provenance decision for publication
2. terms and policy review for newly introduced behavior
3. secret-handling review
4. documentation update before code is presented as a new capability
5. explicit regression tests for the guarantees that the phase depends on

## Strategic position

The repository is strongest when described as:

- a private draft
- a fresh reimplementation
- a Windows-first planning and isolation toolkit
- a repository that earns future capability step by step

It is weakest when described as:

- a quota bypass
- a guaranteed auto-reset manager
- a finished public replacement for every existing tool
