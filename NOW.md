# NOW — Codex Reseter (state layer)
Updated: 2026-10-30 (B-01+B-02+B-03+B-05 data-layer + B-10 research DONE; **URGENT**: live reservation 5a818daf is DISARMED, re-enable needed before 11-06; next code task after 11-06)
Single writer: main session

## 🔴 Urgent operational state (observed 2026-10-30T10:36Z)
- `policy.enabled = False` — system is **PAUSED** since 2026-10-30T09:43:48Z (user-requested).
- Live reservation `5a818daf-...` is **DISARMED** on disk (`.cancel` marker present at `manifests/reset-credit-20261029-191148Z.json.cancel`; manifest `state: "DISARMED"`, `armed: false`, `execution.result: "DISARMED"`, `terminalAt: 2026-10-30T09:43:34Z`, per-job log shows `event: disarmed, reason: "user-requested"`).
- If 11-06T23:07:29Z arrives with this state unchanged, the Consume scheduled task will fire but the guard will refuse (`.cancel` + DISARMED) and the credit expiring 2026-11-06T23:24:29Z burns.
- **Required operator action BEFORE 2026-11-06T23:07:29Z**: click **Start** in the UI (or run `python manager.py sync` after `enable()`). `enable()` → `_clear_block` → `_save_policy` → `_sync_locked` → terminal-reconcile of 5a818daf → fresh enrollment on earliest live credit → new jobId + new Consume task registered + armed. B-10 research confirms the quarantine barrier is currently **False** (all 3 quarantine entries have expiresAt in the past, see below), so re-enrollment is not blocked.
- Earlier concern "credit will burn automatically" was based on an incorrect unix-timestamp conversion; **retracted** after observing `expiresAt` values are seconds (quarantine[2].expiresAt = 1793300254 = 2026-10-29T18:57:34Z, in the past), not nanoseconds or Nov.

## Current state (what runs now)
Four patches applied to both installed managers under `C:\Users\igors\AppData\Local\CodexResetCredit\runners\`:
- v2.6.1 `codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` (ManagerSync — scheduled task action)
- v2.7.4 `codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` (UI — `manager-ui-ready.json`)

Patches:
1. **B-01 (persist cleared block)**: `_save_policy` immediately after `_clear_block` in `_sync_locked`, before `_quarantine_barrier`/`_create_child`. Breaks the 2026-10-22 deadlock cycle (installer no longer sees a stale `blocked` on disk).
2. **B-02 (preserve on transient)**: `_mutating_operation` has `_TRANSIENT_PROBE_CODES = {TIME_NOT_SYNCHRONIZED, TASK_ENUMERATION_FAILED}` and preserves a single armed one-shot (`len(active)==1`) on those codes — fail-closed intact.
3. **B-03 (child-install codes + safe diagnostics)**: `_classify_installer_stderr` maps 4 distinct installer-throw classes to `CHILD_ADMISSION_REFUSED` / `CHILD_TIME_UNVERIFIED` / `CHILD_PWSH_FAILED` / `CHILD_TASK_REG_FAILED` (generic fallback `CHILD_INSTALL_FAILED` kept); `create_child` writes raw stderr + stdout tail to `<install_root>\logs\child-install-<UTC>.log`; `_block` preserves `firstCode` across code changes.
4. **B-05 data layer (coverage-gap observability)**: `policy.blocked.streak` counter (fresh=1, +1 same-code, reset=1 on transition); same-code re-block preserves `atUtc`. `_status_from` exposes `firstCode`, `blockedStreak`, `blockedAgeSeconds` (now - blocked.atUtc), `coverageGap` (bool: blocked AND no armed non-terminal job — NOT via masked `reservation`). `ERROR_MESSAGES` + 5 CHILD_* strings.

B-10 research (no code change): claim confirmed in all 3 manager versions (be2578 patched / fdf16668 patched / control 026abae). `_quarantine_barrier` is global, not per-credit. Latent-bite scenario: a new `POST_DISPATCH_NOTHING_TO_RESET` after 11-06 locks all enrollments until that quarantine entry's expiresAt. Current live state: all 3 entries past expiresAt → barrier False → no current block. Code fix deferred until post-11-06.

All verified by scripted repros under `backup/2026-10-30-B0{1,2,3,5}-*\` and `backup/2026-10-30-B10-quarantine-scope-research\` — each PASSes on both patched files; B-01..B-05 FAIL on control `026abae` as expected; B-10 PASSes on all (pre-existing bug). Repo pytest 64/64 after every change. Branch main HEAD `be82731` (pushed), all fixes live in `%LOCALAPPDATA%\CodexResetCredit`.

Current live reservation: `jobId 5a818daf-2ee6-4c2b-bbe8-bd52f68d5b2d`, `expiresAtUtc 2026-11-06T23:24:29Z`, `triggerAtUtc 2026-11-06T23:07:29Z`, **DISARMED**. External risks not fixed by code (user action required): operator Start before 11-06; `powercfg SUB_SLEEP RTCWAKE DC=0` → on-battery wake fails during dispatch; `notifications.delivered: true` for `paused` key observed today → the toast channel is **working** (contradicts earlier assumption of dead channel; B-12 scope on notifications narrows accordingly).

## Next action (one task per prompt)
Recommended trigger: **(none — hold until Igor re-enables and 11-06 dispatch completes)**. If Igor wants progress before 11-06, lowest-risk candidate: **B-05 escalation jsonl-only path** (no live-install mutation beyond already-live patches, no toast dependency).

Alternative lower-risk candidates:
- **B-07 env hardening** — self-contained; touches `w32time` + resolves `pwsh` absolute path. Risk: w32time is a shared service. Benefit: closes the TIME_NOT_SYNCHRONIZED re-entry.
- **B-11 nothingToReset spend semantics** — ❌ **FORBIDDEN** before 11-06 (requires a live reset-run).

Post-11-06 priority order: **B-04** (truthful disarm reason) → **B-06** (manager hash pin + ManagerSync re-register) → **B-10 fix** (narrow barrier scope + optional quarantine purge).

## Deferred until after 2026-11-06 23:24:29Z dispatch
- **B-04** truthful disarm reason — touches guard-ffe58504 (live Consume task owner).
- **B-06** manager hash pin + ManagerSync re-register — rewrites live task XML.
- **B-10 code fix** — barrier scope + quarantine purge in `_sync_locked` enrollment path.
- Both B-04 and B-06 safe post-2026-11-07. Current post-B05 hashes in `backup/2026-10-30-B05-coverage-assertion/post-b05.sha256.txt`.

## Files edited this session (re-Read before Edit)
- `D:\Gemini Projects\Codex Reseter\docs\backlog.md` — B-05 narrowed; B-10 narrowed
- `D:\Gemini Projects\Codex Reseter\docs\backlog-done.md` — B-01..B-03 + B-05 data layer + B-10 research
- `D:\Gemini Projects\Codex Reseter\NOW.md` — this file
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B01-clearblock-save\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B02-preserve-transient\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B03-distinct-child-codes\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B05-coverage-assertion\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B10-quarantine-scope-research\` — repro_b10.py (research only; no manager snapshots, no SHA records needed)
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-be2578bf…py` — B-01+B-02+B-03+B-05
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-fdf1666889c0…py` — same four fixes
- `D:\Gemini Projects\Codex Reseter\.gitignore` — excludes `backup/*/*.pre*.py`, `backup/*/pre-*.py`, `backup/*/codex_reset_manager-*.py`, `backup/*/scan_all.py`, `POST-COMPACT-PROMPT.md`

## Hashes (for recovery if a copy drifts)
- Pre-B01 → `backup/2026-10-30-B01-clearblock-save/*.sha256` (be2578: `bba850f3…`; fdf16668: `fdf16668…` pristine)
- Pre-B02 → `backup/2026-10-30-B02-preserve-transient/pre-*.sha256` (be2578: `3c59b1b8…`; fdf16668: `74ded99d…`)
- Pre-B03 → `backup/2026-10-30-B03-distinct-child-codes/pre-b03.sha256.txt` (be2578: `e1213b45…`; fdf16668: `1ab061f6…`)
- Post-B03 → `backup/2026-10-30-B03-distinct-child-codes/post-b03.sha256.txt` (be2578: `6358802d…`; fdf16668: `1da142ea…`)
- Pre-B05 → identical to post-B03 (confirms no drift)
- Post-B05 → `backup/2026-10-30-B05-coverage-assertion/post-b05.sha256.txt` (be2578: `e8c9fbd0…`; fdf16668: `73890834…`)
- Guard runtime (pinned, UNCHANGED): `codex_reset_guard-ffe58504…py` — SHA matches filename
- Installer (pinned, UNCHANGED): `install-7816d620…ps1` — SHA matches filename

## Open decisions
- Gray bypasses (auto-enable, SYSTEM UI, stored-password task) remain rejected.
- `powercfg RTCWAKE DC=1` left as user-decision for the 11-06 window.
- Toast channel is confirmed WORKING for the `paused` key (`notifications.json delivered:true` observed today); B-12 "notifications.delivered root-cause" narrows to "verify delivery per-key over longer window", not "channel is broken".
- B-05 escalation re-notify path: previously assumed toast-dependent; with channel confirmed working, both toast and jsonl-only paths are viable.

## Open backlog (pointers only)
- B-04 P0 (deferred until after 11-06) → docs/backlog.md
- B-05 escalation residual (P1 observability) → docs/backlog.md
- B-06 P1 pin (deferred until after 11-06) → docs/backlog.md
- B-07 P2 env (anytime, low-risk) → docs/backlog.md
- B-08..B-09 self-check popup → docs/backlog.md
- B-10 code fix (deferred until after 11-06) → docs/backlog.md
- B-11 instrumented reset probe (**FORBIDDEN before 11-06**) → docs/backlog.md
- B-12 hygiene → docs/backlog.md
