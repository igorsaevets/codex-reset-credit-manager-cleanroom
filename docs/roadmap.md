# Roadmap

## Guiding rule

This roadmap is intentionally conservative. Each phase must earn the right to exist. The repository should not jump from a read-only planning draft to a live auto-reset tool just because that is the emotionally attractive destination.

## Current release — 0.2.0 read-only expiry notifier

Status: completed

Version 0.2.0 adds an optional, reversible Windows reminder layer:

- one read-only `account/rateLimits/read` observation per day
- one local one-shot dialog at `expiresAt − 12 hours`
- no reset redemption, private backend request, or quota mutation
- task registration restricted to the `CodexResetCreditNotifier-*` namespace
- persistent modal display until OK or close

## Phase 0 — Hardening foundation

Status: completed

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

Status: completed

### Objective

Add optional, documented-surface read-only visibility through `codex app-server` without introducing any live mutation path.

### Implemented features

- `observe-rate-limits` CLI command behind an explicit `--allow-live-read` opt-in flag
- `account/rateLimits/read` and `account/read` adapter over `codex app-server --stdio`
- normalized parsing of available reset-credit counts and detail rows when the backend provides them
- timestamp flexible parsing (supporting Unix seconds/ms, numeric strings, ISO strings)
- raw account email masking (`g***@example.com`)
- child process environment drift detection (`codexHome` vs expected `CODEX_HOME`)
- deterministic fake app-server test suite for all edge cases

### Non-goals

- no `account/rateLimitResetCredit/consume`
- no retry logic for redemption outcomes
- no scheduler registration

### Exit criteria

- strictly read-only tests with no live side effects (achieved)
- clear fallback behavior when detailed reset-credit rows are unavailable (achieved)
- docs explain the difference between `availableCount` and any returned detail rows (achieved)

## Phase 1.5 — Operator planning ledger and posture alignment

Status: completed

### Objective

Freeze the documentation shape for operator-reviewed planning artifacts and remove ambiguity between historical pre-publication notes and the current public read-only repository posture.

### Scope

- canonical planning-ledger specification for a chosen expiry target
- explicit UTC and local-time rendering rules for future artifacts
- public wording alignment across the repository front page and core documentation
- historical-context framing for pre-publication review notes

### Non-goals

- no new executable workflow
- no background processing of planning ledgers
- no automatic task installation
- no live reset attempt
- no background daemon

### Exit criteria

- a canonical `docs/planning-ledger.md` exists
- public documentation no longer implies the repository is still private
- the operator planning-ledger concept is described without implying automation
- security documentation states that planning-ledger artifacts must not contain credentials or token values

## Phase 2 — Operator-in-the-loop planning artifacts

Status: proposed

### Objective

Move from static timestamp planning to richer, reproducible, non-mutating artifacts that follow the Phase 1.5 planning-ledger model.

### Candidate features

- structured dry-run reports derived from the planning-ledger shape
- preview bundle for a future scheduled action without performing registration
- explicit timezone rendering and local/UTC comparison helpers in generated artifacts
- inspectable operator summary outputs for a chosen expiry target

### Non-goals

- no automatic task installation
- no live reset attempt
- no background daemon

### Exit criteria

- dry-run artifacts are reproducible from the same inputs
- no dependence on auth scraping or private endpoints
- documentation explains exactly what remains hypothetical

The v0.2 notifier is deliberately separate from this proposed planning-ledger generator. It reads the current account inventory directly and never treats a planning ledger as an execution queue.

## Phase 3 — Decision gate for any live action

Status: not approved

### Objective

Decide whether a user-initiated live path should exist at all.

### Questions that must be answered first

- Is publication posture resolved enough for broader claims or wider adoption?
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

## Phase 4 — Optional scheduled reset action

Status: not approved

### Objective

Consider whether scheduled redemption or last-chance reset execution should exist as an explicit capability separate from the read-only notifier.

### Guardrails

- never enabled by default
- no silent activation during install
- separate documentation from the read-only workflow
- activation flow must be obvious and reversible

### Why this is late

Scheduling a mutating account action multiplies the blast radius. It interacts with sleep/wake timing, battery state, missed windows, idempotency, and user expectations. A local read-only reminder does not imply approval for that capability.

## Release gates that apply to every future phase

1. provenance decision for publication
2. terms and policy review for newly introduced behavior
3. secret-handling review
4. documentation update before code is presented as a new capability
5. explicit regression tests for the guarantees that the phase depends on

## Strategic position

The repository is strongest when described as:

- a public read-only expiry notifier
- a fresh reimplementation
- a Windows-first observability, reminder, planning, and isolation toolkit
- a repository that earns future capability step by step

It is weakest when described as:

- a quota bypass
- a guaranteed auto-reset manager
- a finished public replacement for every existing tool
