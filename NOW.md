# NOW — Codex Reseter (state layer)
Updated: 2026-10-30 (B-01+B-02+B-03+B-05 data-layer DONE; B-05 escalation residual OR B-07 env recommended next; B-04/B-06 after 11-06)
Single writer: main session

## Current state (what runs now)
Four patches applied to both installed managers under `C:\Users\igors\AppData\Local\CodexResetCredit\runners\`:
- v2.6.1 `codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` (ManagerSync — scheduled task action)
- v2.7.4 `codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` (UI — `manager-ui-ready.json`)

Patches:
1. **B-01 (persist cleared block)**: `_save_policy` immediately after `_clear_block` in `_sync_locked`, before `_quarantine_barrier`/`_create_child`. Breaks the 2026-10-22 deadlock cycle (installer no longer sees a stale `blocked` on disk).
2. **B-02 (preserve on transient)**: `_mutating_operation` has `_TRANSIENT_PROBE_CODES = {TIME_NOT_SYNCHRONIZED, TASK_ENUMERATION_FAILED}` and preserves a single armed one-shot (`len(active)==1`) on those codes — fail-closed intact (`_block+_save_policy` still writes the block, only the already-pinned armed job survives).
3. **B-03 (child-install codes + safe diagnostics)**: `_classify_installer_stderr` maps 4 distinct installer-throw classes to `CHILD_ADMISSION_REFUSED` / `CHILD_TIME_UNVERIFIED` / `CHILD_PWSH_FAILED` / `CHILD_TASK_REG_FAILED` (generic fallback `CHILD_INSTALL_FAILED` kept); `create_child` writes raw stderr + stdout tail to `<install_root>\logs\child-install-<UTC>.log`; `_block` preserves `firstCode` across code changes; `_validate_policy` and `_log` accept the new field.
4. **B-05 data layer (coverage-gap observability)**: `_block` tracks `streak` on `policy.blocked` (fresh=1, +1 on same-code re-block, reset to 1 on code transition; same-code re-block PRESERVES original `atUtc` so `blockedAgeSeconds` measures age of the problem, not age of last probe). `_status_from` exposes four new fields: `firstCode`, `blockedStreak`, `blockedAgeSeconds` (now - blocked.atUtc, computed), `coverageGap` (bool: blocked AND (no job OR terminal OR not armed) — NOT via the derived `reservation` string which gets masked to "attention" by the block itself). `_validate_policy` and `_log` whitelist `streak`. `ERROR_MESSAGES` extended with human strings for all five child-install codes.

All four verified by scripted repros under `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B0{1,2,3,5}-*\` — each PASSes on both patched files and FAILs on unpatched control `026abae` (B-03 raises AttributeError; others fail with explicit diagnostic). Full repo pytest 64/64 after each patch (run four times in sequence). Branch main, HEAD 876da44, repo code untouched; all fixes live in `%LOCALAPPDATA%\CodexResetCredit`.

Current live reservation: `jobId 5a818daf-2ee6-4c2b-bbe8-bd52f68d5b2d`, `expiresAtUtc 2026-11-06T23:24:29Z`, `triggerAtUtc 23:07:29Z` ≈ 16:07 PT. External risks NOT fixed by code (user action required): `powercfg SUB_SLEEP RTCWAKE DC=0` → on battery laptop cannot wake into the 5-min dispatch window; `notifications.delivered: false` → the toast channel is dead so any future popup system needs its own delivery verification.

## Next action (one task per prompt)
Recommended trigger: `Начни B-05 escalation` (continuation of B-05 — the data layer is in, now wire the attention logic + re-notification)
Alternative trigger: `Начни B-07` (environment: w32tm trigger-start + pwsh absolute path at install — self-contained)
Context: `D:\Gemini Projects\Codex Reseter\docs\backlog.md`

What to change (if B-05 escalation):
- `doctor`: when `coverageGap=true` AND `freeResetExpiresAtUtc` is within N days (propose 2) → return `ATTENTION` regardless of `blocked_code` being set already (today it's blocked anyway; the point is explicit `coverageGap:true` field in the JSON so operators and future diagnostics see the dedicated signal).
- Re-notify logic in `_block`: today `_notify_once(f"block:{code}")` deduplicates per-code so 538 same-code reblocks produce ONE toast. New rule: ALSO re-notify when `streak>=2` AND age-since-last-notify > 2h, under a SEPARATE key `f"block:{code}:streak"` so dedup doesn't swallow it. CAVEAT: `notifications.json delivered:false` — build this ONLY after B-12 roots-causes the delivery channel; otherwise the re-notify fires into the void. Alternative: just WRITE the escalation event to `manager.jsonl` without touching toasts.
- Primary button Pause→Start/Repair when `blocked && enabled`: EXPLICITLY out of scope (UI widget, lives with B-08/B-09).
- N-days window: hardcode N=2 as a module constant, NOT a policy field (keep policy schema stable; constant can be tuned without a schema bump).

Expected outcome: `doctor` prints `coverageGap=true blockedStreak=538 blockedAgeSeconds=~1.1M firstCode=TIME_NOT_SYNCHRONIZED` as it already does post-B-05, AND operator sees a renewed toast / log entry when streak crosses 2 or age crosses 7200s.

Problem (independent thought): the data layer is in but the system still won't REACT without the escalation wiring. Current `_block` writes a toast exactly once per code transition. Under a 10-22-style loop (538 same-code), after the first toast the system is silent. The right trigger for re-notification is "something is still wrong and nothing has moved" — i.e. `streak>=2 AND age-since-last-notify>N`. Secondarily, if `notifications.delivered` is lying (B-12 open question), the toast path is a mirage. A manager.jsonl `escalation` event is cheaper, auditable, and doesn't depend on the toast channel. Consider doing that FIRST (free, no risk), and the toast re-notify only after B-12 confirms delivery works.

## Deferred until after 2026-11-06 23:24:29Z dispatch
- **B-04** (truthful disarm reason) — touches guard-ffe58504 which owns the live Consume task; interface change on a running binary risks the 11-06 dispatch.
- **B-06** (manager hash pin + ManagerSync re-register) — requires rewriting ManagerSync task XML; any mistake breaks the next sync. Current post-B05 hashes recorded in `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B05-coverage-assertion\post-b05.sha256.txt`.
- Both are safe to run on 2026-11-07 or later.

## Files edited this session (re-Read before Edit)
- `D:\Gemini Projects\Codex Reseter\docs\backlog.md` — B-01, B-02, B-03 rows removed; B-05 narrowed to escalation residual
- `D:\Gemini Projects\Codex Reseter\docs\backlog-done.md` — B-01, B-02, B-03, B-05 data-layer entries with dates + results
- `D:\Gemini Projects\Codex Reseter\NOW.md` — this file
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B01-clearblock-save\` — pre-fix copies + .sha256 + `repro_b01.py` + `scan_all.py`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B02-preserve-transient\` — pre-fix copies + .sha256 + `post-b02.sha256.txt` + `repro_b02.py`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B03-distinct-child-codes\` — pre-fix copies + `pre-b03.sha256.txt` + `post-b03.sha256.txt` + `repro_b03.py`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B05-coverage-assertion\` — pre-fix copies (`be2578.pre-b05.py`, `fdf16668.pre-b05.py`) + `pre-b05.sha256.txt` + `post-b05.sha256.txt` + `repro_b05.py`
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` — B-01 + B-02 + B-03 + B-05
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` — same four fixes
- `D:\Gemini Projects\Codex Reseter\POST-COMPACT-PROMPT.md` — ready-to-paste prompt for the next session after `/compact`

## Hashes (for recovery if a copy drifts)
- Pre-B01 recorded in `backup/2026-10-30-B01-clearblock-save/*.sha256` (be2578: `bba850f3...`; fdf16668: `fdf16668...` matches filename, pristine)
- Pre-B02 → `backup/2026-10-30-B02-preserve-transient/pre-*.sha256` (be2578: `3c59b1b8...`; fdf16668: `74ded99d...`)
- Pre-B03 → `backup/2026-10-30-B03-distinct-child-codes/pre-b03.sha256.txt` (be2578: `e1213b45...`; fdf16668: `1ab061f6...`)
- Post-B03 → `backup/2026-10-30-B03-distinct-child-codes/post-b03.sha256.txt` (be2578: `6358802d...`; fdf16668: `1da142ea...`)
- Pre-B05 → `backup/2026-10-30-B05-coverage-assertion/pre-b05.sha256.txt` (be2578: `6358802d...`; fdf16668: `1da142ea...` — identical to post-B03, confirms no drift)
- Post-B05 → `backup/2026-10-30-B05-coverage-assertion/post-b05.sha256.txt` (be2578: `e8c9fbd0...`; fdf16668: `73890834...`)
- Guard runtime (pinned, UNCHANGED): `codex_reset_guard-ffe58504b28e552e9fdde359555ad16a94b5b184c39dd559ce25d2a6a60243fa.py` — SHA matches filename
- Installer (pinned, UNCHANGED): `install-7816d620e47a73d81aefbeead05dbe2810475737318c00930a504a57be4ae7dd.ps1` — SHA matches filename

## Open decisions
- Gray bypasses (auto-enable, SYSTEM UI, stored-password task) remain rejected.
- `powercfg RTCWAKE DC=1` left as user-decision: being on AC in 16:00-16:30 PT on 2026-11-06, OR `powercfg /setdcvalueindex SCHEME_BALANCED SUB_SLEEP RTCWAKE 1 && powercfg /S SCHEME_BALANCED` (shared-system setting).
- B-05 escalation re-notify path: toast (depends on B-12 delivery fix) vs. jsonl-only escalation event (free, immediate). Lean jsonl-first.

## Open backlog (pointers only)
- B-04 P0 (deferred until after 11-06) → docs/backlog.md
- B-05 escalation residual (P1 observability) → docs/backlog.md
- B-06 P1 pin (deferred until after 11-06) → docs/backlog.md
- B-07 P2 env (anytime, low-risk) → docs/backlog.md
- B-08..B-09 self-check popup → docs/backlog.md
- B-10..B-12 verify-before-build → docs/backlog.md
