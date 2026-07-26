# Codex Reset Credit Manager (Private Draft)

This repository is a private, from-scratch draft for a Windows-first local tool
that plans and audits safe automation around an existing Codex reset credit.

The current milestone is intentionally read-only. It does not register
Scheduled Tasks, does not call a live consume/reset endpoint, and does not
change the existing paused third-party installation already present on the
author's laptop.

## Why this repository exists

- The previously studied third-party repository is public but has no license.
- Direct reuse, off-platform copying, or public derivative publication is not a
  safe default.
- A separate draft lets us redesign the project around stricter safety,
  isolation, and provenance rules.

## Current status

- Repository visibility: private
- Implementation status: read-only MVP
- Existing laptop installation: intentionally untouched
- Live consume support: out of scope for this milestone

## What this draft already does

- Builds a separate state root away from the existing `CodexResetCredit`
  install.
- Previews a sanitized child-process environment with explicit `CODEX_HOME`
  isolation.
- Computes planning checkpoints from an expiry timestamp without touching live
  account state.
- Emits a Windows Scheduled Task XML preview for a read-only command.
- Ships unit tests for environment scrubbing, planning windows, and XML preview
  generation.

## What this draft does not do

- It does not consume a reset credit.
- It does not register or enable a scheduled task.
- It does not read or write the existing third-party install root.
- It does not bypass plan limits, create quota, or use private HTTP calls.

## Quick start

```powershell
python -m pip install -e .[dev]
python -m codex_reset_credit_manager doctor
python -m codex_reset_credit_manager env-preview
python -m codex_reset_credit_manager plan --expires-at 2026-08-02T12:00:00Z
python -m codex_reset_credit_manager preview-task `
  --run-at 2026-08-02T11:58:40Z `
  --exec-command "python" `
  --arguments "-m codex_reset_credit_manager dry-run"
python -m unittest discover -s tests -v
```

## Repository map

- `src/codex_reset_credit_manager/`: read-only CLI and core helpers
- `tests/`: unit tests
- `docs/architecture.md`: system design and trust boundaries
- `docs/provenance.md`: current provenance and publication caveats
- `docs/upstream-differences.md`: how this draft intentionally differs from the
  legacy third-party approach
- `docs/strategic-review-2026-07-26.md`: synthesized strategic review

## Why this draft differs from the legacy tool

| Area | Legacy third-party direction | This draft |
| --- | --- | --- |
| Publication | Unclear license posture | Private draft first |
| Scope | End-to-end automation | Read-only MVP |
| Environment | Needed hardening against ambient secrets | Allowlist-based child env |
| Scheduling | Real task installation | XML preview only |
| Existing laptop state | Already installed | Explicitly untouched |
| Provenance | Third-party source | New code and fresh docs |

## Release gate before any public switch

1. Human review of provenance and license risk
2. Terms-risk review for the intended live behavior
3. Clear separation between read-only and live code paths
4. Secret-handling and scheduler audits
5. Fresh repo metadata: license, security policy, and public-facing disclaimers

This project is not affiliated with OpenAI or GitHub.
