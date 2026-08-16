<p align="center">
  <img src="assets/app_icon.png" width="128" height="128" alt="Codex Reset Credit Manager Icon" />
</p>

<h1 align="center">Codex Reset Credit Manager & Live Usage Monitor</h1>

<p align="center">
  <b>Read-only Windows monitor and notifier for OpenAI Codex rate-limit usage, reset credits, and expiry reminders.</b>
</p>

---

Read-only Windows monitor and notifier for OpenAI Codex usage-limit reset expiry and real-time rate limit tracking. It queries the local Codex app-server, inspects live primary and secondary quota usage (`usedPercent`, `windowDurationMins`, `resetsAt`), reads available reset credits, and schedules one persistent modal reminder for 12 hours before a reset expires.

> **Short answer:** this tool shows you live Codex rate-limit usage and tells you the exact local date and time when the nearest saved Codex usage-limit reset expires. It does not activate, redeem, consume, create, or extend a reset.

Version **0.3.2** introduces:
- **ChatGPT-Inspired App Icon**: Custom cyan/emerald cyclic vortex icon across Desktop, Start Menu, Window headers, and Taskbar.
- **Monthly Repository Update Checker**: Automatic background check (throttled to 1/month) with in-app banner to easily update.
- **Interactive Desktop GUI Monitor**: Live usage gauges, real-time quota inspection, and Russian/English toggle.
- **`usage` CLI Command**: ASCII progress bars and countdowns directly in terminal.

## What it does

- queries `codex app-server --stdio` through read-only RPCs only
- reads `account/read` and `account/rateLimits/read`
- verifies that the detailed available-credit inventory is complete
- selects the earliest available Codex rate-limit reset (`codexRateLimits`, including its snake-case wire equivalent)
- converts its timezone-aware `expiresAt` to the PC's local date, time, timezone, and UTC offset
- runs one network check per day with Windows Task Scheduler
- schedules one local, one-shot reminder at **T−12 hours**
- displays days, hours, minutes, and seconds remaining when the window opens
- keeps the top-most modal visible until **OK** or the window's close button is selected
- stores only a SHA-256 fingerprint, timestamps, task name, and sanitized status

The daily controller and the one-shot reminder have different jobs:

1. `CodexResetCreditNotifier-DailyCheck` performs the single daily read.
2. `CodexResetCreditNotifier-Notice-<hash>` performs no network request. It only opens the already-planned modal at T−12 hours.

This split is how one daily check can still produce an exact 12-hour reminder.

## What it never does

- no reset activation or automatic redemption
- no `account/rateLimitResetCredit/consume` call
- no direct `/backend-api/wham/*` HTTP request
- the manager never directly opens or parses `auth.json`; authentication remains inside the user's normal Codex app-server session
- no API-key, access-token, email-address, raw credit-ID, or idempotency-key logging
- no modification of another Codex reset manager installation
- no quota bypass, additional usage, or extension of an existing expiry

If the inventory is incomplete, the account environment changes, a timestamp is invalid, or an available-count invariant fails, the notifier stops without scheduling a dialog.

## Install on Windows

Requirements:

- Windows 10 or Windows 11
- CPython 3.11 or later with `pythonw.exe` and Tkinter
- a signed-in Codex CLI available on `PATH`
- PowerShell with the Windows ScheduledTasks module

Preview the installation without changing the PC:

```powershell
pwsh -NoProfile -File .\install-notifier.ps1 `
  -Language auto `
  -LeadHours 12 `
  -DailyAt 09:00 `
  -WhatIf
```

Install and activate the daily read-only check:

```powershell
pwsh -NoProfile -File .\install-notifier.ps1 `
  -Language auto `
  -LeadHours 12 `
  -DailyAt 09:00 `
  -Confirm:$false
```

For a Russian modal:

```powershell
pwsh -NoProfile -File .\install-notifier.ps1 `
  -Language ru `
  -LeadHours 12 `
  -DailyAt 09:00 `
  -Confirm:$false
```

The installer performs one initial read-only check, then runs once per day. Pass `-SkipInitialCheck` if the first check should wait until the daily trigger.

`-Language auto` is the default. It selects Russian for a Windows UI culture beginning with `ru` and English for the United States and every other currently unsupported language. Use `-Language ru` or `-Language en` to override it. The resolved language is stored during installation; reinstall after changing the Windows display language.

## Inspect without installing

Install the package in editable mode:

```powershell
python -m pip install -e .[dev]
```

Display current rate-limit usage, progress bar, and reset countdown:

```powershell
# In Russian
python -m codex_reset_credit_manager usage --allow-live-read --language ru

# In English
python -m codex_reset_credit_manager usage --allow-live-read --language en

# In JSON
python -m codex_reset_credit_manager usage --allow-live-read --json
```

Launch the interactive desktop status monitor:

```powershell
python -m codex_reset_credit_manager gui --allow-live-read
```

Read full observation report (account, rate-limits, reset-credits inventory):

```powershell
python -m codex_reset_credit_manager observe-rate-limits `
  --allow-live-read `
  --json
```

Preview what the notifier would schedule:

```powershell
python -m codex_reset_credit_manager notifier-sync `
  --allow-live-read `
  --lead-hours 12 `
  --language en `
  --dry-run `
  --json
```

Inspect sanitized notifier state:

```powershell
python -m codex_reset_credit_manager notifier-status --json
```

## Timing behavior and edge cases

- **Normal case:** when the daily check sees a reset more than 12 hours before expiry, the local one-shot runs exactly at `expiresAt − 12 hours`.
- **Late discovery:** if a reset is first discovered inside the 12-hour window, the reminder is scheduled immediately after a short controller-exit grace period. Software cannot retroactively notify at T−12.
- **PC asleep:** the one-shot has `WakeToRun` and `StartWhenAvailable`. Firmware, battery policy, or disabled wake timers can prevent an exact wake, and Microsoft documents a default 10-minute queue delay for a late `StartWhenAvailable` run.
- **User signed out:** the modal requires the same interactive Windows user. It is not shown on the secure desktop or to another account.
- **Dialog left open:** its task has no execution time limit; the dialog remains until OK or close is selected.
- **Remaining time:** the modal shows days, hours, minutes, and seconds remaining at the instant it opens. It is an accurate snapshot, not a live ticking counter.
- **Timestamp precision:** the notifier displays the one-second precision exposed by `account/rateLimits/read`; it does not scrape a private backend for fractional seconds.
- **Expired before display:** the child checks the saved UTC expiry locally and exits without showing stale information.
- **Duplicate daily runs:** a lock, deterministic fingerprint, and deterministic task name prevent duplicate reminders for the same credit.
- **Credit changes:** the next daily check replaces only the notifier's own stale one-shot task.

## Safety model

The notifier passes the validated path of the current signed-in `CODEX_HOME` to the official app-server, without parsing its credential files, and uses a sanitized child-process environment. It requires:

- explicit `--allow-live-read`
- `mode == "read-only"`
- `live_consume_allowed == false`
- an exact match between available count and available detail rows
- status `available`
- the app-server Codex rate-limit reset type, normalized across camel-case and snake-case forms
- an opaque ID used only as input to a local SHA-256 fingerprint
- a timezone-aware future `expiresAt`

The one-shot action contains the fingerprint and expiry, not the raw credit ID. Its Task Scheduler XML uses `InteractiveToken`, `LeastPrivilege`, `StartWhenAvailable`, `WakeToRun`, `IgnoreNew`, and no execution-time limit for the modal.

## Frequently asked questions

### When does a Codex reset credit disappear?

The authoritative time for an individual available reset is its server-provided `expiresAt`. The notifier displays that instant in both local time and UTC.

### Does this program automatically reset my Codex limit?

No. It is an expiry monitor and reminder only. There is no redemption implementation in the Python source or scheduled-task actions.

### Why not poll every few minutes?

The controller intentionally checks once per day to minimize background activity. It turns the observed expiry into one local T−12 Task Scheduler trigger, so frequent network polling is unnecessary.

### Will the notification disappear by itself?

No. The Windows dialog is modal and stays open until you select OK or close the window.

### Which language will the notification use?

The installer defaults to `auto`: Russian Windows UI uses Russian; American English and all other currently unsupported UI languages use English. Explicit `-Language ru` and `-Language en` settings always win. The project currently ships two translations, not arbitrary machine translation.

### Is this an official OpenAI tool?

No. This is an independent open-source project and is not affiliated with or endorsed by OpenAI or GitHub.

## Other read-only tools in this repository

- `doctor` checks isolation and local prerequisites
- `env-preview` shows which environment-variable names are kept or stripped
- `observe-rate-limits` performs an explicitly authorized read-only observation
- `plan` computes deterministic planning checkpoints from a supplied expiry
- `preview-task` renders Task Scheduler XML without registering it
- `dry-run` prints the earlier planning-only workflow

## Development and verification

The test suite uses fake app-server fixtures and fake schedulers. It never contacts a real account and never opens a real modal.

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'src')
python -m unittest discover -s tests -v
git diff --check
```

Tests cover exact 12-hour arithmetic, localized remaining-time rendering, nearest-credit selection, incomplete inventory, late discovery, idempotent scheduling, stale-task replacement, expired notices, modal deduplication, state redaction, Task Scheduler XML, CLI opt-in, and a source-level absence check for reset-redemption RPCs.

## Repository map

- [docs/windows-expiry-notifier.md](docs/windows-expiry-notifier.md) — notifier architecture, installation, recovery, and threat model
- [docs/repository-guide.md](docs/repository-guide.md) — codebase orientation
- [docs/architecture.md](docs/architecture.md) — original isolation and planning design
- [docs/planning-ledger.md](docs/planning-ledger.md) — planning-ledger specification
- [docs/provenance.md](docs/provenance.md) — publication and derivative-risk caveats
- [docs/upstream-differences.md](docs/upstream-differences.md) — differences from previously studied tools
- `src/codex_reset_credit_manager/` — CLI, read-only app-server transport, and notifier
- `tests/` — fake-only unit and contract tests

## Provenance and responsible use

This repository is independently written but does not claim formal legal clean-room certification. Earlier evaluation work included reading an unlicensed third-party repository; the read-only notifier code and its tests are new work in this repository. See [docs/provenance.md](docs/provenance.md).

This software must not be described or used as a rate-limit bypass. It does not promise unlimited Codex usage and cannot change an OpenAI plan, quota, or server-side expiry.

## License

MIT. See [LICENSE](LICENSE).
