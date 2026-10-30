# Codex Reseter — project context for Antigravity

This is a project-level memory file for Antigravity, auto-loaded from the project root on next session (confirmed via live Antigravity docs 2026-10-30: `antigravity.google/docs/rules`).

## Scope of this folder

`D:\Gemini Projects\Codex Reseter\` is a **git clone of the cleanroom notifier repo** `igorsaevets/codex-reset-credit-manager-cleanroom` — a read-only Windows observer for Codex rate-limit usage. It ships Python package `codex_reset_credit_manager` with CLI and GUI. **It does not perform resets** — see `docs/upstream-differences.md` and `docs/provenance.md`.

The companion **upstream manager** (which actually consumes reset credits automatically) is a **separate repo**: `igorsaevets/codex-usage-limit-auto-reset` (operator's fork of `godxxy1229/codex-usage-limit-auto-reset`). Its source lives locally at `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\`. Latest release: **v2.7.5** (2026-10-30), with five reliability fixes landed from the audit done in this cleanroom repo. Any change to manager runtime behaviour goes there, not here.

## Operational constraints (hard rules)

- **DO NOT touch guard runtime** `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_guard-ffe58504b28e552e9fdde359555ad16a94b5b184c39dd559ce25d2a6a60243fa.py` until after 2026-11-06T23:24:29Z — guard owns the live Consume task armed for that window.
- **DO NOT reinstall** via `pwsh install.ps1` before 2026-11-06 dispatch — reinstall renames content-addressed files and orphans the current paused reservation.
- **DO NOT re-register ManagerSync** or any Scheduled Task under `\CodexResetCredit\*`.
- **DO NOT touch `policy.json` directly** at `C:\Users\igors\AppData\Local\CodexResetCredit\state\policy.json` — only through controller writes.
- **DO NOT touch `powercfg` SUB_SLEEP RTCWAKE** — shared-system setting; operator decision for the 11-06 wake window.
- **DO NOT trigger a reset** — no `schtasks /run /tn \CodexResetCredit\*`, no `enable()`, no `python manager.py sync` with `enabled=true`.

## Current state as of 2026-10-30

- Operator deliberately paused the auto-reset manager (`policy.enabled=False`) at 2026-10-30T09:43:48Z for the dev session; live reservation `5a818daf-...` on 2026-11-06T23:07:29Z is DISARMED on disk but will re-arm when operator clicks Start before that time.
- Installed manager runtime files in `C:\Users\igors\AppData\Local\CodexResetCredit\runners\` carry B-01..B-05 + B-10b fixes applied inline (content hash differs from filename-encoded hash — that is intentional; admission check does not pin manager content).
- Full audit: `D:\Gemini Projects\Codex Reseter\NOW.md`, `D:\Gemini Projects\Codex Reseter\docs\backlog.md`, `D:\Gemini Projects\Codex Reseter\docs\backlog-done.md`.
- Deferred post-11-06: B-04 (truthful disarm reason, guard-side), B-06 (manager runtime hash pin + ManagerSync re-register).

## For code work in this folder

Repo tests: `python -m pytest tests/ -q --tb=line` must stay 64 passed.

The `backup/` folder is the audit trail: pre/post-patch SHA records and standalone repro scripts for every B-NN item. Repros load the manager under test via `importlib.util.spec_from_file_location`; they do not touch the live install. Pattern model for new audit items.

The cleanroom repo does **not** carry the installed-manager source (that is in the companion `codex-usage-limit-auto-reset` repo). The audit here references its function names, which is a known caveat from `docs/provenance.md` — the cleanroom claim is already softened to "independently written public preview with provenance caveat".
