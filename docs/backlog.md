# Backlog — Codex auto-reset, incident 2026-10-22

Source: second-opinion round `D:\Reviews\codex-autoreset-fix` (cheap panel + `mimov26pro`), 7 verified reviews. All channels confirmed blocked-state deadlock as dominant cause (0.85–0.985).
Scope note: failing component is the installed legacy manager under `%LOCALAPPDATA%\CodexResetCredit` (`codex_reset_manager-*.py`, `codex_reset_guard-*.py`, `install-*.ps1`), not the read-only notifier in this repo. Fixes below apply to that component; this repo tracks them plus its own witness role.

Process: when a task is done, move its row to `docs/backlog-done.md` with date + one-line result. Do not delete rows.

## P0 — reliability (deadlock)

- [ ] **B-04 Truthful disarm reasons.** Thread `reason` through `disarm(job, reason)` into `.cancel` marker + `disarmed` event (`user:pause` vs `controller:error:<CODE>`). Acceptance: 20:27:27 case would read `controller:error:TIME_NOT_SYNCHRONIZED`, not `user-requested`. RISK: touches guard runtime that owns the live Consume task — defer until AFTER 2026-11-06 dispatch window.

## P1 — observability / ops

- [ ] **B-05 Coverage assertion ESCALATION layer** (data layer DONE 2026-10-30 — see `backlog-done.md`). The data layer surfaced four new status fields (`coverageGap`, `blockedStreak`, `blockedAgeSeconds`, `firstCode`) and five `ERROR_MESSAGES` entries for `CHILD_*` codes. STILL TO DO: (a) `doctor` returns `ATTENTION` with explicit `coverageGap:true` reason when `coverageGap=true` AND `freeResetExpiresAtUtc` within N=2 days — N as a module constant, NOT a policy field; (b) re-notify on `streak>=2 AND timeSinceLastNotify>7200s` under a SEPARATE `_notify_once` key (`f"block:{code}:streak"`) because the current `block:<code>` dedupes per-code — BUT this depends on B-12 root-causing `notifications.delivered:false`; alternative is to emit a jsonl-only `escalation` event (free, no toast dependency). Primary-button Pause→Start/Repair stays with B-08/B-09 UI task. Acceptance: 13-day silent loop impossible; 09-04 single CHILD would have alerted.
- [ ] **B-06 Pin manager runtime, re-register task.** Add `runtimeManager`+sha to policy, self-verify at startup; re-point `ManagerSync` action from `be2578` (hash mismatch `BBA850F3`, v2.6.1) to the shipped file (UI runs `fdf16668`, v2.7.4); test task XML hash == runner filename digest. Acceptance: scheduled and UI binaries identical and pinned.

- [ ] **B-13 Linux classifier coverage + test fidelity** (found in the v2.7.6 re-verification). (a) 74 of 133 distinct `install_linux.py` `InstallError` messages still fall back to `CHILD_INSTALL_FAILED` (full list: `backup/2026-10-30-B03-linux-twin/coverage-v2.7.6.txt`); first candidates: `A final, GIL-enabled base CPython 3.11+ installation is required.`, `User lingering must be disabled`, `A systemd scalar path must be absolute`, `Less than ten minutes remain before the one-shot trigger.`, `Child npm environment differs from the loaded ManagerSync pin.`, `Manager child mode requires an owned`, `command failed`. (b) `tests/test_linux_manager.py` fake `create_child` still maps `TimeoutExpired` to `CHILD_INSTALL_FAILED`; v2.7.6 real code maps it to `CHILD_PWSH_FAILED` (cleanup is code-agnostic, so cosmetic). (c) Upstream suite is not Linux-clean: 21 Windows-only tests error or fail on Linux on v2.7.5 and v2.7.6 alike. Acceptance: `verify_signatures_v276.py` coverage up, fake matches real, `unittest discover` on Linux skips Windows-only tests.

## P2 — environment

- [ ] **B-07 W32Time repair + unified health.** Apply KB2385818 trigger-start (`sc triggerinfo w32time start/networkon`); unify `Get-WindowsTimeHealth` and guard `_time_status` (w32tm → SNTP UDP, 5s cap); log `synchronized` vs `degraded_sntp_fallback`; resolve `pwsh` to absolute path at install (prefer `C:\Program Files\PowerShell\7\pwsh.exe`), reject 0-byte alias silently failing. Acceptance: `w32tm` healthy or health line says which path was used.

## P3 — self-verification popup (manual fallback)

- [ ] **B-08 Verify task + guard verification field.** Installer registers one-shot `\CodexResetCredit\Verify-<hash8>-<jobid8>` at `processAt-60s`, `EndBoundary=expiresAt`, `InteractiveToken`/`LeastPrivilege`, `StartWhenAvailable`+`WakeToRun`, `PT8M` limit; guard writes `execution.verification={checkedAtUtc,outcome,attempts,limitsState}`; ManagerSync sweeps unacknowledged alerts (covers signed-out/logon case via `LogonTrigger`). Name must stay auditable (note: `Consume-*` filter ignores `Verify-*` — add explicit cleanup in pause/uninstall). Acceptance: guard-never-started still produces an alert.
- [ ] **B-09 Popup UI + dedup + gating.** Reuse UI `show_request` (needs `schemaVersion:2` for fingerprint/reason fields) or tkinter topmost non-modal + `FlashWindowEx` (no `SYSTEMMODAL` focus steal); fingerprint `sha256(jobId|expiresAt|failureCode)` in `state/attention.json` (`firstShown/lastShown/count/snoozeUntil/acked`), ≤3 shows, 10-min re-show cap; fire at `process+90s` (≈expires-3:30) + `cutoff+0`, never at bare trigger; gate ACTION vs silent vs UNKNOWN on precondition (limit exhausted? `nothingToReset` → no ACTION page, else manual steps + Dismiss receipt + auto-close on RESOLVED). Acceptance: `NO_ACTION`/`INDETERMINATE`/`POST_DISPATCH_NOTHING_TO_RESET` and never-ran both surface exactly once per fingerprint.

## P4 — verify-before-build (research)

- [x] **B-10 DONE 2026-10-30** — see `backlog-done.md` (research + B-10b fix landed same day while system was operator-paused).
- [ ] **B-11 `nothingToReset` spend semantics.** Instrumented run: does `consume→nothingToReset` burn the banked credit? Log rate-limit state before/after. Decision gates B-09 wording. Acceptance: yes/no with log evidence.
- [ ] **B-12 Hygiene.** Purge stale `.cancel` on `enable()` + `cancel_file_exists` in `doctor`; purge past-expiry quarantine entries from `policy["quarantine"]` once `absentObservedAtUtc` is set AND `now() >= expiresAt` (prevents unbounded growth; orthogonal cleanup from B-10b); add `entryPoint` to mutating `manager.jsonl` events; cap/rotate `logs/child-install-*.log` (one file per failed attempt since v2.7.5 Windows / v2.7.6 Linux, up to ~48/day on the 30-min Linux timer; two failures in the same UTC second overwrite one file); **narrow** `notifications.json delivered:false` root-cause (channel confirmed working for `paused` key 2026-10-30 → not fully dead; verify per-key delivery over longer window); audit 16 runner copies in install root. Acceptance: each item closed with one line.

## Done this round (now in docs/backlog-done.md)

- [x] B-03 Linux twin — shipped as v2.7.6 (2026-10-30). The former "Linux twin for B-03 — v2.7.6 candidate" pointer is CLOSED.

## Out of scope (rejected)

- Blind auto-`enable()`/auto-clear of `blocked` outside controller lock; installer ignoring `blocked`; `SYSTEM+CreateProcessAsUser` UI bypass; stored-password task; `nssm` loop. Reasons: break fail-closed, credential/session risk, ToS/account-policy risk.
