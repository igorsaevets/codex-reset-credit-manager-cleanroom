# NOW — Codex Reseter (state layer)
Updated: 2026-10-30 (B-01+B-02+B-03+B-05 data-layer + B-10 research+fix DONE; **operator confirmed deliberate pause**; operator Start needed before 11-06; B-04/B-06 wait for post-11-06)
Single writer: main session

## 🟡 Operational state (observed 2026-10-30T10:36Z; operator confirmed deliberate)
- `policy.enabled = False` — **operator-paused** since 2026-10-30T09:43:48Z (confirmed by operator: deliberate pause for the dev session). Live reservation `5a818daf-...` is DISARMED on disk (`.cancel` marker on manifest; `state: "DISARMED"`, `armed: false`).
- **Required operator action BEFORE 2026-11-06T23:07:29Z**: click **Start** in the UI (or run `python manager.py sync` after `enable()`). `enable()` → `_clear_block` → `_save_policy` → `_sync_locked` → terminal-reconcile of 5a818daf → `_quarantine_barrier` (post-B10b: False since no quarantine matches the earliest live credit) → fresh enrollment on earliest live credit → new jobId + new Consume task registered + armed.
- The pause provides a safe window: `_sync_locked` early-returns on `if not policy["enabled"]:` before touching the barrier / `_create_child`, so patches deployed now do not perturb live state. B-10b landed in this window.
- Earlier concern "credit will burn automatically" (based on an incorrect unix-timestamp conversion) was **retracted**; all 3 live quarantine entries have `expiresAt` in the past, barrier returns False.

## Current state (what runs now)
Five patches applied to both installed managers under `C:\Users\igors\AppData\Local\CodexResetCredit\runners\`:
- v2.6.1 `codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` (ManagerSync — scheduled task action)
- v2.7.4 `codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` (UI — `manager-ui-ready.json`)

Patches:
1. **B-01 (persist cleared block)**: `_save_policy` immediately after `_clear_block` in `_sync_locked`, before `_quarantine_barrier`/`_create_child`. Breaks the 2026-10-22 deadlock cycle.
2. **B-02 (preserve on transient)**: `_mutating_operation` + `_TRANSIENT_PROBE_CODES = {TIME_NOT_SYNCHRONIZED, TASK_ENUMERATION_FAILED}` → preserves a single armed one-shot on those codes.
3. **B-03 (child-install codes + safe diagnostics)**: 4 distinct `CHILD_*` codes + logs/child-install-*.log + `_block` preserves `firstCode`.
4. **B-05 data layer**: `policy.blocked.streak`, `firstCode`, `blockedStreak`, `blockedAgeSeconds`, `coverageGap` (bool: blocked AND no armed non-terminal job). ERROR_MESSAGES + 5 CHILD_* strings.
5. **B-10b (quarantine barrier scope fix)**: `_quarantine_barrier` narrowed to per-credit scope. First pass preserves REAPPEARED / METADATA_CHANGED hard-raises + absentObservedAtUtc timestamping; final boolean checks only whether EARLIEST live credit itself is in an unresolved quarantine. Stops the latent 30-day lockout on next POST_DISPATCH_NOTHING_TO_RESET.

All verified by scripted repros under `backup/2026-10-30-B0{1,2,3,5}-*\` and `backup/2026-10-30-B10b-quarantine-scope-fix\` — each PASSes on both patched files; B-01..B-05 FAIL on control `026abae` as expected; B-10b PASSes on patched + fails on control in 3 groups matching the semantic delta; frozen research `backup/2026-10-30-B10-quarantine-scope-research/repro_b10.py` now has 2 FAILs on patched by design. Repo pytest 64/64 after every change. Branch main HEAD will be published this round as the next commit.

Current live reservation: `jobId 5a818daf-2ee6-4c2b-bbe8-bd52f68d5b2d`, `expiresAtUtc 2026-11-06T23:24:29Z`, `triggerAtUtc 2026-11-06T23:07:29Z`, **DISARMED**. External risks not fixed by code (user action required): operator Start before 11-06; `powercfg SUB_SLEEP RTCWAKE DC=0` → on-battery wake fails during dispatch; `notifications.delivered: true` for `paused` key observed today → the toast channel is **working** (contradicts earlier assumption of dead channel; B-12 scope on notifications narrows accordingly).

## Next action (one task per prompt)
Candidates while paused (operator safely blocked on `if not policy["enabled"]:` before any barrier/enrollment):
- **B-05 escalation** (jsonl-only OR toast — toast channel is confirmed working for the `paused` key, see below). Builds on existing data layer. Low risk.
- **B-07 env hardening** — resolve `pwsh` absolute path at install, `w32time` triggerinfo. Self-contained but touches shared service state.
- **B-12 subset** — orthogonal quarantine purge (`policy["quarantine"]` grows unboundedly; expired entries no longer block but still accumulate). Small, confined to `_sync_locked` or a dedicated maintenance call. Lowest risk.

Post-2026-11-06 (needed for live-task touches):
- **B-04** truthful disarm reason — removes the hardcoded `"user-requested"` lie in guard-ffe58504, which blocked diagnosis of the exact pause-origin ambiguity we just hit.
- **B-06** manager hash pin + ManagerSync re-register — closes the admission-check gap on manager content.
- **B-11** `nothingToReset` spend semantics — ❌ **FORBIDDEN** before 11-06 (requires a live reset-run).

## Deferred until after 2026-11-06 23:24:29Z dispatch
- **B-04** truthful disarm reason — touches guard-ffe58504 (live Consume task owner).
- **B-06** manager hash pin + ManagerSync re-register — rewrites live task XML.
- Both safe post-2026-11-07. Current post-B10b hashes in `backup/2026-10-30-B10b-quarantine-scope-fix/post-b10b.sha256.txt`.

## Files edited this session (re-Read before Edit)
- `D:\Gemini Projects\Codex Reseter\docs\backlog.md` — B-05 narrowed; B-10 moved to DONE; B-12 extended with quarantine purge
- `D:\Gemini Projects\Codex Reseter\docs\backlog-done.md` — B-01..B-03 + B-05 data layer + B-10 research + B-10b code fix
- `D:\Gemini Projects\Codex Reseter\NOW.md` — this file
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B01-clearblock-save\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B02-preserve-transient\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B03-distinct-child-codes\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B05-coverage-assertion\`
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B10-quarantine-scope-research\` — repro_b10.py (frozen pre-fix artifact)
- `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B10b-quarantine-scope-fix\` — `be2578.pre-b10b.py`, `fdf16668.pre-b10b.py`, `pre-b10b.sha256.txt`, `post-b10b.sha256.txt`, `repro_b10b.py`
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-be2578bf…py` — B-01+B-02+B-03+B-05+B-10b
- `C:\Users\igors\AppData\Local\CodexResetCredit\runners\codex_reset_manager-fdf1666889c0…py` — same five fixes
- `D:\Gemini Projects\Codex Reseter\.gitignore` — excludes `backup/*/*.pre*.py`, `backup/*/pre-*.py`, `backup/*/codex_reset_manager-*.py`, `backup/*/scan_all.py`, `POST-COMPACT-PROMPT.md`

## Hashes (for recovery if a copy drifts)
- Pre-B01 → `backup/2026-10-30-B01-clearblock-save/*.sha256` (be2578: `bba850f3…`; fdf16668: `fdf16668…` pristine)
- Pre-B02 → `backup/2026-10-30-B02-preserve-transient/pre-*.sha256` (be2578: `3c59b1b8…`; fdf16668: `74ded99d…`)
- Pre-B03 → `backup/2026-10-30-B03-distinct-child-codes/pre-b03.sha256.txt` (be2578: `e1213b45…`; fdf16668: `1ab061f6…`)
- Post-B03 → `backup/2026-10-30-B03-distinct-child-codes/post-b03.sha256.txt` (be2578: `6358802d…`; fdf16668: `1da142ea…`)
- Pre-B05 → identical to post-B03 (confirms no drift)
- Post-B05 → `backup/2026-10-30-B05-coverage-assertion/post-b05.sha256.txt` (be2578: `e8c9fbd0…`; fdf16668: `73890834…`)
- Pre-B10b → `backup/2026-10-30-B10b-quarantine-scope-fix/pre-b10b.sha256.txt` (identical to post-B05)
- Post-B10b → `backup/2026-10-30-B10b-quarantine-scope-fix/post-b10b.sha256.txt` (be2578: `ef10662d…`; fdf16668: `751bb1ab…`)
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
- B-11 instrumented reset probe (**FORBIDDEN before 11-06**) → docs/backlog.md
- B-12 hygiene (now includes quarantine purge from B-10b) → docs/backlog.md
