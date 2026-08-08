# Repository Guide

## Overview

`codex-reset-credit-manager-cleanroom` is a Windows-first, safety-first expiry-observation and reminder toolkit for Codex reset-credit workflows.

Version 0.2.0 remains read-only with respect to the Codex account. Its optional Windows notifier registers only local reminder tasks; it has no credit-redemption or quota-mutation implementation.

The current focus is a once-daily observation that schedules one local modal reminder for 12 hours before the nearest available reset credit expires.

## What This Repository Currently Does

- **Isolated State Management**: Resolves an isolated draft root under `%LOCALAPPDATA%\CodexResetCreditDraft`, keeping all state separate from existing local installations.
- **Strict Environment Scrubbing**: Generates sanitized child process environments containing only a minimal allowlist of necessary system variables (`PATH`, `SYSTEMROOT`, `TEMP`, etc.) and sets explicit `CODEX_HOME` and `CODEX_SQLITE_HOME` paths.
- **Selective Secret Value Access**: Only reads environment values for allowlisted variables. Ambient non-allowlisted secrets (e.g., `OPENAI_API_KEY`, `HF_TOKEN`) are observed strictly by key name when diffing environment state and are never read into memory for forwarding, logged, or sent anywhere.
- **Deterministic Expiry Checkpoint Planning**: Calculates warmup, validation, and dispatch windows relative to a target UTC expiry timestamp without requiring live network or account state.
- **Planning-Ledger Specification**: Defines a static Phase 1.5 artifact shape for operator-reviewed expiry planning, timezone comparison, and future dry-run reporting without introducing any execution engine.
- **Scheduled Task XML Preview**: Renders valid, inspectable Windows Task Scheduler XML for the original planning-only workflow.
- **Read-Only App-Server Observability**: Provides Phase 1 live read-only observation (`observe-rate-limits`) over `codex app-server --stdio` using documented read methods (`initialize`, `initialized`, `account/read`, `account/rateLimits/read`) behind an explicit `--allow-live-read` opt-in flag.
- **Optional Expiry Notifier**: Installs one daily local observation task and one deterministic one-shot modal reminder at `expiresAt − 12 hours`.
- **Persistent Local Dialog**: Shows the already-planned time without a network request and stays visible until the user selects OK or closes it.
- **Read-Only CLI Toolkit**: Provides diagnostic, observation, planning, notifier preview/status, and local reminder commands.

## What This Repository Does NOT Do

- **No Live Credit Consumption**: Does not call `account/rateLimitResetCredit/consume` or any live reset endpoint.
- **No Scheduled Reset Action**: Registered notifier tasks only read expiry metadata or display a local dialog; they never activate or redeem a reset.
- **No Unrelated Task Mutation**: The notifier creates, replaces, and removes tasks only inside its own `CodexResetCreditNotifier-*` namespace.
- **No Private Endpoint Usage**: Does not interact with private or undocumented API endpoints (such as `/backend-api/wham/*`).
- **No Auth Scraping**: The manager does not directly open or parse local browser storage, tokens, or credential files; authentication remains inside Codex app-server.
- **No Legacy Installation Mutation**: Intentionally leaves any pre-existing legacy installation at `%LOCALAPPDATA%\CodexResetCredit` untouched.
- **No Secret Transmission**: Does not send API keys, credentials, or token values anywhere.
- **No Ledger Execution Engine**: Does not watch, process, or execute planning-ledger artifacts in the background.

## Differences from Legacy Implementations

If you are familiar with older legacy repositories or installed legacy reset helpers, note the structural and operational differences:

| Feature / Aspect | Legacy Implementation | This Repository |
| --- | --- | --- |
| **Architecture** | Manager, guard, auto-installer, and reset task runner modules | Read-only observer plus local expiry-reminder controller |
| **Child Environment** | Forwarded ambient shell environment (potentially leaking tokens) | Minimal allowlist; non-allowlisted secret values are never read or forwarded |
| **Scheduler** | Tasks capable of reset execution | Only a once-daily read and a local modal reminder; no redemption action |
| **Execution Surface** | Direct consumption / private backend interactions | Documented `codex app-server --stdio` read-only RPCs (`account/rateLimits/read`, `account/read`) |
| **Legacy Install Handling** | Modified local state directly | Strictly treated as external and untouched |

## Repository Structure

Key directories and files:

- `src/codex_reset_credit_manager/`: Core Python package modules
  - `cli.py`: Command-line interface definition and command dispatch
  - `config.py`: Resolves draft root paths, legacy install root, and local binaries
  - `sanitized_env.py`: Environment allowlisting and diffing logic
  - `app_server.py`: Read-only transport and normalization client for `codex app-server --stdio`
  - `notifier.py`: Nearest-credit selection, state machine, Task Scheduler XML, and persistent modal
  - `planner.py`: Pure timestamp planning calculations for expiry checkpoints
  - `task_preview.py`: Windows Task Scheduler XML rendering
  - `models.py`: Dataclass models for diagnostic reports, observation reports, and planning windows
- `tests/`: Unit test suite verifying environment scrubbing, planning logic, app-server read-only adapter, task preview XML, and isolation
- `docs/`: Comprehensive technical and policy documentation
  - `architecture.md`: System design, threat model, and trust boundaries
  - `planning-ledger.md`: Phase 1.5 planning-ledger specification and artifact rules
  - `windows-expiry-notifier.md`: Notifier design, installation, recovery, and timing caveats
  - `provenance.md`: Cleanroom provenance context and derivative-risk notes
  - `roadmap.md`: Completed read-only milestones and future gated features
  - `upstream-differences.md`: Detailed comparison with legacy reset tools
  - `strategic-review-2026-07-26.md`: Initial strategic review snapshot
  - `repository-guide.md`: This orientation guide
- `install-notifier.ps1`: Previewable installer for the optional daily notifier
- `pyproject.toml`: Package setup, metadata, and dependency specifications
- `SECURITY.md`: Security policies and environment scrubbing guarantees
- `README.md`: Public entry point and quick start instructions

## How to Run and Test

### Setup
Install the package in editable mode with development dependencies:
```powershell
python -m pip install -e .[dev]
```

### Running CLI Commands
Check local isolation and prerequisites:
```powershell
python -m codex_reset_credit_manager doctor
```

Preview kept vs. stripped environment variable names:
```powershell
python -m codex_reset_credit_manager env-preview
```

Calculate planning checkpoints for a given expiry timestamp:
```powershell
python -m codex_reset_credit_manager plan --expires-at 2026-08-02T12:00:00Z
```

Render Task Scheduler XML preview:
```powershell
python -m codex_reset_credit_manager preview-task `
  --run-at 2026-08-02T11:58:40Z `
  --exec-command "python" `
  --arguments "-m codex_reset_credit_manager dry-run --expires-at 2026-08-02T12:00:00Z"
```

Execute a read-only dry run:
```powershell
python -m codex_reset_credit_manager dry-run --expires-at 2026-08-02T12:00:00Z
```

### Running Tests
Execute the unit test suite:
```powershell
python -c "import sys; sys.path.insert(0, 'src'); import unittest; unittest.main(module=None, argv=['unittest', 'discover', '-s', 'tests', '-v'])"
```
Or if installed in editable mode (`pip install -e .`):
```powershell
python -m unittest discover -s tests -v
```
