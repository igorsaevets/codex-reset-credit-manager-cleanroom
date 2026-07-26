# Architecture

## Goals

The first milestone is a safe, read-only MVP. It is designed to prove the hard
parts we care about before any live reset behavior exists:

1. filesystem isolation from the legacy local install
2. deterministic planning windows
3. strict environment scrubbing for child processes
4. Windows Task Scheduler preview generation without registration

## Trust boundaries

- The legacy local installation under `%LOCALAPPDATA%\\CodexResetCredit` is an
  observed external system. This repository must not mutate it.
- Ambient shell environment is treated as hostile and overshared.
- Official Codex interfaces may be read-only inputs in future milestones, but
  the current MVP does not invoke them by default.

## Current components

- `config.py`
  Resolves isolated local roots and identifies the legacy install path.
- `sanitized_env.py`
  Produces a child-process environment using a small allowlist plus explicit
  `CODEX_HOME` isolation.
- `planner.py`
  Computes timing checkpoints from an expiry timestamp.
- `task_preview.py`
  Emits one-time Scheduled Task XML for a read-only command preview.
- `cli.py`
  Exposes `doctor`, `env-preview`, `plan`, `preview-task`, and `dry-run`.

## Non-goals for v0.1

- No live reset-credit consume behavior
- No task registration
- No direct backend HTTP
- No credential storage helper
- No auto-update or background daemon

## Future shape

If the project survives provenance and terms review, a later milestone can add
a separate read-only Codex adapter that speaks only to official local
interfaces. Any live mutation path should live behind a separate capability
boundary and remain disabled by default.

