# NOW — Codex Reseter (state layer)
Updated: 2026-10-30 (post-compact: B-03 Linux twin landed as **v2.7.6**; v2.7.5 Windows fixes already shipped; operator pause deliberate; next step waits for 11-06)
Single writer: main session

## 🟢 Public releases on `igorsaevets/codex-usage-limit-auto-reset`

### v2.7.6 (just landed 2026-10-30, post-compact)
- Commit `3c5fbca` on `main` (fast-forward from `be3e849`), tag `v2.7.6` pushed.
- GitHub Releases page entry **NOT YET CREATED** — `gh release create` was blocked by Claude Code auto-mode classifier ("Create Public Surface"). Operator needs to approve or create it manually. Code + tag are public.
- Change: Linux twin for B-03. New `_LINUX_INSTALLER_SIGNATURES` + `_classify_linux_installer_stderr` at module scope; `LinuxServices.create_child` now classifies `install_linux.py` stderr into the 4 CHILD_* codes and writes `logs/child-install-*.log` via the inherited `_record_child_install_failure`. `ERROR_MESSAGES[CHILD_PWSH_FAILED]` reworded to platform-neutral ("could not start its native runtime"). APP_VERSION 2.7.5 → 2.7.6; `tests/test_manager_console.py:102` updated from stale "2.7.4" assert to "2.7.6".
- Pre-SHA256 of `codex_reset_manager.py` (disk form, CRLF): `2bdb56064dd3028ef6f84ba979429795e5fc35084ff44e13b013d7313aac31a7`
- Post-SHA256 of `codex_reset_manager.py` (disk form, CRLF): `70248853bb7951eab23dfaa4a8c2de392b2636d540e753a2b8b2f061fdbface2`
- Verified: upstream `pytest tests/` 315 passed (3 pre-existing failures all `OSError:[Errno 22]` from pathlib on the Cyrillic path `C:\Users\igors\OneDrive\Документы\...`); new Linux repro PASS; all 5 prior B-NN repros still PASS.

### v2.7.5 (earlier same day)
- URL: https://github.com/igorsaevets/codex-usage-limit-auto-reset/releases/tag/v2.7.5
- Published 2026-10-30T22:14:18Z. First GitHub release for this repo.
- `main` fast-forwarded `3d02aa8` (v2.5.0) → `be3e849` (v2.7.5). Nine previously-unpublished commits (v2.6.0 through v2.7.4) became public for the first time in this push.
- Source of the release: `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\codex_reset_manager.py` (APP_VERSION="2.7.5", HEAD-blob SHA256 `4cd3fdcfd16256207d03acc7765b2b8b5f42b2ea32e0da4770c215db8f715aca`; disk-form with CRLF normalization was `2bdb56064dd3028e…` — git-managed, status clean).
- All five fixes (B-01, B-02, B-03, B-05 data layer, B-10b) baked into the release source.
- Backup of the pristine v2.7.4 pre-overwrite source: `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-v2.7.5-release\codex_reset_manager.pristine-v2.7.4.py` (SHA256 `fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729` — matches installed-filename and the pre-B01 backup, confirms source WAS byte-identical to deployed before patches).

## 🟡 Live operational state (operator-paused, deliberate)
- `policy.enabled = False` since 2026-10-30T09:43:48Z. Confirmed by operator: deliberate pause for the dev session.
- Live reservation `5a818daf-...` on disk: `state: "DISARMED"`, `armed: false`, `.cancel` marker on manifest `reset-credit-20261029-191148Z.json`.
- Installed runtime files in `%LOCALAPPDATA%\CodexResetCredit\runners\` are **still at APP_VERSION="2.7.4"** string but content has all 5 fixes inline (SHA256 be2578: `ef10662d…`, fdf16668: `751bb1ab…`). UI window title will say v2.7.4; released GitHub source says v2.7.5. Cosmetic gap; identical behaviour.
- **Required operator action BEFORE 2026-11-06T23:07:29Z**: click **Start** in the Reset Manager UI. `enable()` → `_clear_block` → `_save_policy` → `_sync_locked` → terminal-reconcile of 5a818daf → `_quarantine_barrier` (post-B10b: False — none of the 3 current quarantine entries match the earliest live credit; all three expire in the past) → fresh enrollment → new jobId + new armed Consume-* task.
- **DO NOT reinstall** via `pwsh install.ps1` before 2026-11-06 dispatch — reinstall renames content-addressed files, re-registers Scheduled Tasks under new SHA names, and the current paused reservation (5a818daf) would become orphan.

## Current state (what runs now)
Five patches applied to both installed managers under `C:\Users\igors\AppData\Local\CodexResetCredit\runners\`:
- v2.6.1 `codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` (ManagerSync — scheduled task action; filename hash from original pre-patch content)
- v2.7.4 `codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` (UI — `manager-ui-ready.json`; filename hash matches OneDrive pristine source pre-overwrite)

Patch summary:
1. **B-01** `_save_policy` after `_clear_block` in `_sync_locked`
2. **B-02** `_TRANSIENT_PROBE_CODES` preserved-reservation branch in `_mutating_operation`
3. **B-03** `_classify_installer_stderr` + 4 distinct CHILD_* codes + raw-stderr log file + `_block` firstCode preservation
4. **B-05 data layer** `policy.blocked.streak` + atUtc preserve + four new status fields (`firstCode`, `blockedStreak`, `blockedAgeSeconds`, `coverageGap`) + ERROR_MESSAGES extended
5. **B-10b** `_quarantine_barrier` per-credit scope — stale entries no longer block fresh enrollment

All verified by scripted repros under `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B0{1,2,3,5,10b}-*\` and B-10 research record at `D:\Gemini Projects\Codex Reseter\backup\2026-10-30-B10-quarantine-scope-research\`. Repo pytest 64/64 after every change.

cleanroom repo (`codex-reset-credit-manager-cleanroom`) branch main HEAD = `15ce7f9` (last audit commit on 2026-10-30). This session's audit upload after v2.7.5 release goes on top.

## Antigravity memory layout (confirmed via deep-research subagent, 2026-10-30)
- **Project memory**: Antigravity reads `GEMINI.md` and `AGENTS.md` at project root, recursive walk upward. Per-file cap 24 KB, aggregate 20 K-token budget. Also `.agents/rules/*.md` with YAML `trigger:` frontmatter.
- **This project has NO project memory** — neither `D:\Gemini Projects\Codex Reseter\GEMINI.md` nor `AGENTS.md` exists. Antigravity's next session will see no project-level context. Working example on same disk: `D:\Gemini Projects\Webpage2pdf\GEMINI.md` and `AGENTS.md`.
- **Session-to-project link**: `C:\Users\igors\.gemini\antigravity\conversation_summaries.db` → table `conversation_summaries` → fields `workspace_uris` (JSON array of `file://` URIs), `project_id`, `last_user_input_time`. For this project only ONE session recorded: 2026-09-04 05:26 UTC, 2156 steps, workspace `D:\Gemini Projects\Codex Reseter` — likely the v0.3.4 notifier build (date matches commits `c8934c4` and `876da44`). ZERO Antigravity sessions in `OneDrive\...\codex-usage-limit-auto-reset\` — the v2.6.0..v2.7.4 manager commits were made with another tool (Claude Code? Codex? manual?).
- **brain/** = per-trajectory UUID subdirs with media artifacts (screenshots, browser recordings); not a vector store.
- **No cloud sync confirmed** — all memory under `~/.gemini/` is local.
- **Create project memory for next session**: write a 24 KB-max `GEMINI.md` or `AGENTS.md` at `D:\Gemini Projects\Codex Reseter\` with instructions for Antigravity, or `.agents/rules/<name>.md` with `trigger: always_on` frontmatter.

## Next action (one task per prompt)
**Default path — WAIT.** Operator clicks **Start** at a convenient time before 2026-11-06T23:07:29Z; dispatch happens; after 11-06 the deferred backlog (B-04, B-06) becomes safe.

**Alternative code tasks that are safe NOW while paused:**
- **~~Linux twin for B-03~~ DONE as v2.7.6.** B-10b barrier was already shared, so Linux twin was only needed for the B-03 classifier + log; shipped 2026-10-30 post-compact.
- **B-05 escalation residual** (jsonl-only, now that notification channel is confirmed working — `notifications.delivered: true` for `paused` key today): `_block` emits an `escalation` event when `streak >= 2 AND timeSinceLastNotify > 7200s`. Pure data layer, no live reservation risk.
- **~~GEMINI.md / AGENTS.md~~ DONE** at `D:\Gemini Projects\Codex Reseter\GEMINI.md` (3.6 KB) — Antigravity's next session has project-level context.
- **GitHub Release page for v2.7.6**: tag + code are public but Releases-page entry still needs operator approval (classifier blocked `gh release create`).

**Deferred until after 2026-11-06T23:24:29Z dispatch:**
- **B-04** truthful disarm reason — guard-side change on live Consume task.
- **B-06** manager runtime hash pin + ManagerSync re-register — rewrites live task XML.

## Files edited this session (re-Read before Edit after /compact)

In cleanroom repo (`D:\Gemini Projects\Codex Reseter\`):
- `NOW.md` — this file
- `.gitignore` — extends with `backup/*/*.pristine*.py`
- `docs\backlog.md` — B-05 narrowed; B-10 → DONE; B-12 extended with quarantine purge
- `docs\backlog-done.md` — B-01..B-03 + B-05 data layer + B-10 research + B-10b code fix + v2.7.5 release entry
- `backup\2026-10-30-B01-clearblock-save\` — repro + SHA records (manager snapshots ignored)
- `backup\2026-10-30-B02-preserve-transient\` — repro + pre/post SHA
- `backup\2026-10-30-B03-distinct-child-codes\` — repro + pre/post SHA
- `backup\2026-10-30-B05-coverage-assertion\` — repro + pre/post SHA
- `backup\2026-10-30-B10-quarantine-scope-research\repro_b10.py` — frozen pre-fix artifact
- `backup\2026-10-30-B10b-quarantine-scope-fix\` — repro + pre/post SHA + patch backups (gitignored)
- `backup\2026-10-30-v2.7.5-release\codex_reset_manager.pristine-v2.7.4.py` — pristine source backup (gitignored)
- `POST-COMPACT-PROMPT.md` — handoff for next session (gitignored)

In installed runtime (`C:\Users\igors\AppData\Local\CodexResetCredit\runners\`):
- `codex_reset_manager-be2578bf1da55f5e9f8c2aa73d004fee6b08ef950cef383537cbef5fd97bb94d.py` — B-01+B-02+B-03+B-05+B-10b
- `codex_reset_manager-fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729.py` — same five fixes

In upstream fork OneDrive clone (`C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\`):
- `codex_reset_manager.py` — v2.7.5 content (B-01..B-10b) in commit `be3e849`; v2.7.6 content (B-03 Linux twin) in commit `3c5fbca` on main. Pushed to origin; tags `v2.7.5` and `v2.7.6` published; v2.7.5 Release page live, v2.7.6 Release page pending operator approval.
- `tests/test_manager_console.py` — line 102 assertion unlocked from "2.7.4" (stale after v2.7.5) → "2.7.6".

## Hashes (for recovery if a copy drifts)
- Pre-B01 → `backup\2026-10-30-B01-clearblock-save\*.sha256` (be2578: `bba850f3…`; fdf16668: `fdf16668…` matches filename, pristine)
- Pre-B02 → `backup\2026-10-30-B02-preserve-transient\pre-*.sha256` (be2578: `3c59b1b8…`; fdf16668: `74ded99d…`)
- Pre-B03 → `backup\2026-10-30-B03-distinct-child-codes\pre-b03.sha256.txt` (be2578: `e1213b45…`; fdf16668: `1ab061f6…`)
- Post-B03 → `backup\2026-10-30-B03-distinct-child-codes\post-b03.sha256.txt` (be2578: `6358802d…`; fdf16668: `1da142ea…`)
- Post-B05 → `backup\2026-10-30-B05-coverage-assertion\post-b05.sha256.txt` (be2578: `e8c9fbd0…`; fdf16668: `73890834…`)
- Post-B10b → `backup\2026-10-30-B10b-quarantine-scope-fix\post-b10b.sha256.txt` (be2578: `ef10662d…`; fdf16668: `751bb1ab…`)
- v2.7.5 release source (OneDrive HEAD blob) → SHA256 `4cd3fdcfd16256207d03acc7765b2b8b5f42b2ea32e0da4770c215db8f715aca` (differs from installed `751bb1ab…` by exactly one line: `APP_VERSION = "2.7.5"` vs still-`"2.7.4"` on disk)
- Pre-B03-linux (OneDrive disk form) → `backup\2026-10-30-B03-linux-twin\pre-b03-linux.sha256.txt` (`2bdb56064dd3028e…`)
- Post-B03-linux / v2.7.6 (OneDrive disk form) → `backup\2026-10-30-B03-linux-twin\post-b03-linux.sha256.txt` (`70248853bb7951ea…`); test file: `533552b2098ad164…`
- Pristine v2.7.4 pre-overwrite → `backup\2026-10-30-v2.7.5-release\codex_reset_manager.pristine-v2.7.4.py` SHA256 `fdf1666889c047cee6e3151417e9e7f61c3ad93b83d1498f9c0b8511045be729`
- Guard runtime (pinned, UNCHANGED): `codex_reset_guard-ffe58504…py` — SHA matches filename
- Installer (pinned, UNCHANGED): `install-7816d620…ps1` — SHA matches filename

## Open decisions
- Gray bypasses (auto-enable, SYSTEM UI, stored-password task) remain rejected.
- `powercfg RTCWAKE DC=1` left as user-decision for the 11-06 window.
- Toast channel confirmed WORKING for the `paused` key (`notifications.json delivered:true` observed today). B-12 scope narrows accordingly.
- B-05 escalation re-notify path: previously assumed toast-dependent; both toast and jsonl-only are viable.
- GitHub release scope: v2.7.5 shipped Windows-only versions of B-03 and B-10b. **v2.7.6 (2026-10-30 post-compact) added the Linux twin for B-03** — barrier (B-10b) was already shared so Linux has had that fix since v2.7.5. GitHub Releases-page entry for v2.7.6 pending operator approval.

## Open backlog (pointers only)
- B-04 P0 (deferred until after 11-06) → `docs\backlog.md`
- B-05 escalation residual (P1 observability) → `docs\backlog.md`
- B-06 P1 pin (deferred until after 11-06) → `docs\backlog.md`
- B-07 P2 env (anytime, low-risk) → `docs\backlog.md`
- B-08..B-09 self-check popup → `docs\backlog.md`
- B-11 instrumented reset probe (**FORBIDDEN before 11-06**) → `docs\backlog.md`
- B-12 hygiene (now incl. quarantine purge from B-10b) → `docs\backlog.md`
- Linux twin for B-03 — DONE in v2.7.6 (see Public releases above)
