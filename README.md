# Codex Reset Credit Manager (Private Draft)

Windows-first, safety-first planning and isolation toolkit for Codex reset-credit workflows.

This repository is a fresh private draft for a read-only MVP. It does not consume a reset credit, does not register a Scheduled Task, does not call private backend endpoints, and does not modify the paused third-party installation already present on the author's laptop.

## Status

- Repository visibility: private
- Milestone: read-only MVP
- Existing laptop installation: intentionally untouched
- Live `consume` support: not implemented
- Scheduler registration: not implemented

## Why this repository exists

This draft exists to solve the parts that are easy to get wrong before any live reset behavior is even considered:

- filesystem isolation from a legacy local install
- strict child-process environment scrubbing
- deterministic expiry planning
- inspectable Windows Task Scheduler XML preview instead of silent task registration
- provenance-first documentation before any public release

It also deliberately avoids the path taken by many public experiments: calling private reset-credit endpoints directly or reading local auth state in ad hoc ways. The long-term intent, if the project ever grows beyond this MVP, is to stay on documented Codex surfaces such as [`codex app-server`](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md).

## What the MVP already does

- builds an isolated root under `%LOCALAPPDATA%\CodexResetCreditDraft`
- forces a separate `CODEX_HOME` and `CODEX_SQLITE_HOME` for child processes
- keeps only a small allowlist of ambient environment variables
- computes warmup, validation, and dispatch checkpoints from an expiry timestamp
- renders one-time Scheduled Task XML for inspection only
- ships unit tests for environment scrubbing, planning windows, and XML preview generation

## What this MVP does not do

- no live `account/rateLimitResetCredit/consume`
- no automatic credit redemption
- no Scheduled Task registration
- no direct `/backend-api/wham/*` calls
- no auth-file scraping helper
- no writes into the existing `%LOCALAPPDATA%\CodexResetCredit` install

## Why this draft is different

This is not positioned as a “quota bypass” tool or a full auto-reset manager. Right now it is a hardening and planning foundation.

| Area | Typical public reset helper direction | This private draft |
| --- | --- | --- |
| Scope | End-to-end reset flow | Read-only planning and isolation only |
| Child environment | Often inherits ambient shell state | Small allowlist plus explicit `CODEX_HOME` isolation |
| Scheduler behavior | Real registration or background automation | XML preview only |
| Existing local install | May reuse or mutate it | Explicitly treated as external and untouched |
| Backend surface | Private endpoints are common | Future work is intended to stay on documented app-server surfaces |
| Publication posture | Public-first | Private draft first, with provenance gate |

More detail: [docs/upstream-differences.md](docs/upstream-differences.md), [docs/provenance.md](docs/provenance.md)

## Repository map

- [docs/architecture.md](docs/architecture.md) — current design, trust boundaries, and threat model
- [docs/roadmap.md](docs/roadmap.md) — phased plan from read-only MVP to any future gated capabilities
- [docs/provenance.md](docs/provenance.md) — publication and derivative-risk caveats
- [docs/upstream-differences.md](docs/upstream-differences.md) — intentional differences from the previously studied legacy direction
- [docs/strategic-review-2026-07-26.md](docs/strategic-review-2026-07-26.md) — prior strategic review snapshot
- `src/codex_reset_credit_manager/` — CLI and core helpers
- `tests/` — unit tests

## Quick start

```powershell
python -m pip install -e .[dev]
python -m codex_reset_credit_manager doctor
python -m codex_reset_credit_manager env-preview
python -m codex_reset_credit_manager plan --expires-at 2026-08-02T12:00:00Z
python -m codex_reset_credit_manager preview-task `
  --run-at 2026-08-02T11:58:40Z `
  --exec-command "python" `
  --arguments "-m codex_reset_credit_manager dry-run --expires-at 2026-08-02T12:00:00Z"
python -m unittest discover -s tests -v
```

## Safety and compliance notes

- This repository does not promise unlimited Codex usage and must not be described as a rate-limit bypass.
- Any future live mutation path would need to use documented app-server methods such as `account/rateLimits/read` and `account/rateLimitResetCredit/consume`, with explicit user intent and idempotent behavior.
- OpenAI's Terms of Use prohibit users from circumventing rate limits, restrictions, or protective measures. That boundary is one of the release gates for any future live feature.
- Historical ecosystem pressure around reset-credit tooling is real: for example, issue [#29618](https://github.com/openai/codex/issues/29618) asked for detailed reset-credit rows through supported Codex surfaces so local tools would not need private endpoints.

## Provenance note

This repository is best described as a fresh private reimplementation draft, not yet as a formally isolated legal clean-room deliverable. Earlier evaluation work included reading an unlicensed third-party repository, so publication still requires an explicit provenance decision. That is why this repository remains private today.

See [docs/provenance.md](docs/provenance.md) for the exact caveat and release options.

## Roadmap

The short version:

1. keep the current milestone read-only and auditable
2. add optional read-only observability through supported app-server interfaces
3. add operator-in-the-loop planning artifacts before any live action exists
4. only then decide whether a user-initiated consume path or scheduler registration should exist at all

Full plan: [docs/roadmap.md](docs/roadmap.md)

## Non-affiliation

This project is an independent draft and is not affiliated with OpenAI or GitHub.
