# Repository Guide

## Overview

`codex-reset-credit-manager-cleanroom` is a Windows-first, safety-first planning and environment isolation toolkit for Codex reset-credit workflows.

This repository represents a public read-only MVP (Minimum Viable Product). It is designed to establish strong safety boundaries, deterministic planning, and environment sanitization before any live consumption or mutation path is considered.

## What This Repository Currently Does

- **Isolated State Management**: Resolves an isolated draft root under `%LOCALAPPDATA%\CodexResetCreditDraft`, keeping all state separate from existing local installations.
- **Strict Environment Scrubbing**: Generates sanitized child process environments containing only a minimal allowlist of necessary system variables (`PATH`, `SYSTEMROOT`, `TEMP`, etc.) and sets explicit `CODEX_HOME` and `CODEX_SQLITE_HOME` paths.
- **Selective Secret Value Access**: Only reads environment values for allowlisted variables. Ambient non-allowlisted secrets (e.g., `OPENAI_API_KEY`, `HF_TOKEN`) are observed strictly by key name when diffing environment state and are never read into memory for forwarding, logged, or sent anywhere.
- **Deterministic Expiry Checkpoint Planning**: Calculates warmup, validation, and dispatch windows relative to a target UTC expiry timestamp without requiring live network or account state.
- **Scheduled Task XML Preview**: Renders valid, inspectable Windows Task Scheduler XML for preview and audit purposes without registering or scheduling any background tasks.
- **Read-Only CLI Toolkit**: Provides `doctor`, `env-preview`, `plan`, `preview-task`, and `dry-run` commands for diagnostic and verification workflows.

## What This Repository Does NOT Do

- **No Live Credit Consumption**: Does not call `account/rateLimitResetCredit/consume` or any live reset endpoint.
- **No Scheduler Registration**: Does not register, modify, or enable Windows Scheduled Tasks automatically.
- **No Private Endpoint Usage**: Does not interact with private or undocumented API endpoints (such as `/backend-api/wham/*`).
- **No Auth Scraping**: Does not scrape local browser storage, tokens, or credential files.
- **No Legacy Installation Mutation**: Intentionally leaves any pre-existing legacy installation at `%LOCALAPPDATA%\CodexResetCredit` untouched.
- **No Secret Transmission**: Does not send API keys, credentials, or token values anywhere.

## Differences from Legacy Implementations

If you are familiar with older legacy repositories or installed legacy reset helpers, note the structural and operational differences:

| Feature / Aspect | Legacy Implementation | Cleanroom Read-Only MVP (This Repository) |
| --- | --- | --- |
| **Architecture** | Manager, guard, auto-installer, and task runner modules | Read-only CLI toolkit with modular single-responsibility helpers |
| **Child Environment** | Forwarded ambient shell environment (potentially leaking tokens) | Minimal allowlist; non-allowlisted secret values are never read or forwarded |
| **Scheduler** | Active installation and execution of Windows Scheduled Tasks | XML preview generation for inspection only |
| **Execution Surface** | Direct consumption / private backend interactions | Read-only planning transforms; future plans prioritize documented app-server endpoints |
| **Legacy Install Handling** | Modified local state directly | Strictly treated as external and untouched |

## Repository Structure

Key directories and files:

- `src/codex_reset_credit_manager/`: Core Python package modules
  - `cli.py`: Command-line interface definition and command dispatch
  - `config.py`: Resolves draft root paths, legacy install root, and local binaries
  - `sanitized_env.py`: Environment allowlisting and diffing logic
  - `planner.py`: Pure timestamp planning calculations for expiry checkpoints
  - `task_preview.py`: Windows Task Scheduler XML rendering
  - `models.py`: Dataclass models for diagnostic reports and planning windows
- `tests/`: Unit test suite verifying environment scrubbing, planning logic, task preview XML, and isolation
- `docs/`: Comprehensive technical and policy documentation
  - `architecture.md`: System design, threat model, and trust boundaries
  - `provenance.md`: Cleanroom provenance context and derivative-risk notes
  - `roadmap.md`: Phased roadmap from read-only MVP to potential future gated features
  - `upstream-differences.md`: Detailed comparison with legacy reset tools
  - `strategic-review-2026-07-26.md`: Initial strategic review snapshot
  - `repository-guide.md`: This orientation guide
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
