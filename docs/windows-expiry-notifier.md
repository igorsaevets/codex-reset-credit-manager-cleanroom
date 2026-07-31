# Windows expiry notifier

## Purpose

The notifier answers one narrow question: **when will the nearest available Codex usage-limit reset activation expire?**

It performs one read-only Codex app-server observation per day and turns the nearest complete `expiresAt` into a local Windows Task Scheduler reminder. The reminder appears 12 hours before expiry by default and remains open until the interactive user selects **OK** or closes it.

The notifier has no reset-redemption implementation.

## Architecture

```text
DailyCheck (network, once/day)
  -> initialize
  -> account/read
  -> account/rateLimits/read
  -> validate complete available inventory
  -> hash opaque credit ID + expiry
  -> schedule one deterministic Notice task

Notice (local, once)
  -> verify fingerprint + saved expiry against local state
  -> refuse stale or expired notice
  -> show top-most modal
  -> record sanitized receipt after OK/close
```

The one-shot task never starts Codex and never performs a network request.

## State

The default installed root is:

```text
%LOCALAPPDATA%\CodexResetCreditNotifier
```

The state file contains:

- schema version
- last daily check time and result
- expiry, planned notice time, actual scheduled time, language, and task name
- a SHA-256 fingerprint derived from the opaque credit ID and expiry
- modal start and close timestamps
- a sanitized error class when display fails

It does not contain the raw credit ID, account email, token, API key, or idempotency key.

## Timing proof

For an expiry instant `E` and configured lead `L = 12 hours`:

```text
notification_target = E - L
E - notification_target = 12 hours
```

All subtraction occurs on timezone-aware UTC datetimes. Local formatting happens only for Task Scheduler XML and the visible message. This avoids DST arithmetic errors.

The app-server currently exposes expiry at one-second precision. The notifier preserves that value and does not inspect a private backend to obtain fractional seconds.

If the daily controller first discovers the credit after `E - L`, it cannot notify in the past. It schedules the notice for `now + 15 seconds`, provided that instant remains before `E`.

## Task Scheduler contract

The installer creates:

```text
CodexResetCreditNotifier-DailyCheck
```

The controller may create one deterministic child:

```text
CodexResetCreditNotifier-Notice-<16 hex characters>
```

Daily task:

- one `CalendarTrigger` with `DaysInterval = 1`
- `InteractiveToken`
- `LeastPrivilege`
- `StartWhenAvailable`
- `WakeToRun`
- `IgnoreNew`
- five-minute execution limit

Notice task:

- one `TimeTrigger`
- start boundary at the target or immediate late-discovery grace
- end boundary at expiry
- `InteractiveToken`
- `LeastPrivilege`
- `StartWhenAvailable`
- `WakeToRun`
- `IgnoreNew`
- no execution limit, so Windows does not close the modal automatically
- automatic deletion after its end boundary

Microsoft documents a default 10-minute queue delay when `StartWhenAvailable` catches up after a missed trigger. The exact T−12 claim therefore applies to a normally fired trigger, not a delayed wake or late catch-up.

## Installation preview

```powershell
pwsh -NoProfile -File .\install-notifier.ps1 `
  -Language ru `
  -LeadHours 12 `
  -DailyAt 09:00 `
  -WhatIf
```

The preview resolves Python and validates Tkinter, but does not copy files or register tasks.

## Installation

```powershell
pwsh -NoProfile -File .\install-notifier.ps1 `
  -Language ru `
  -LeadHours 12 `
  -DailyAt 09:00 `
  -Confirm:$false
```

Use `-PythonPath C:\absolute\path\python.exe` if automatic Python discovery selects the wrong installation.

## Verification

Inspect the daily task:

```powershell
Export-ScheduledTask -TaskName CodexResetCreditNotifier-DailyCheck
```

Inspect sanitized state from the source checkout:

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'src')
python -m codex_reset_credit_manager `
  --root "$env:LOCALAPPDATA\CodexResetCreditNotifier\state" `
  notifier-status `
  --json
```

List controller-owned tasks:

```powershell
Get-ScheduledTask |
  Where-Object TaskName -Like 'CodexResetCreditNotifier-*' |
  Select-Object TaskName, State
```

## Removal

Pause future checks and remove only this notifier's tasks:

```powershell
Get-ScheduledTask |
  Where-Object TaskName -Like 'CodexResetCreditNotifier-*' |
  Unregister-ScheduledTask -Confirm:$false
```

After verifying no notifier task is running, the installed files may be removed from:

```text
%LOCALAPPDATA%\CodexResetCreditNotifier
```

Removal does not affect `%LOCALAPPDATA%\CodexResetCredit` or the Codex CLI.

## Failure behavior

- App-server timeout or error: no new notice is scheduled.
- Environment identity mismatch: fail closed.
- Unlisted available credits: fail closed.
- Available-count mismatch: fail closed.
- Missing opaque ID, status, type, or expiry: fail closed.
- Naive or invalid timestamp: fail closed.
- Stale child task: exit without a dialog.
- Already-notified fingerprint: exit without a duplicate.
- Display failure: clear the scheduled claim and record only the exception class.
- PC unavailable through expiry: no stale dialog after expiry.

## Security boundary

Task registration is a local Windows state change explicitly requested during installation. It is not a Codex account mutation. The only account operation is `account/rateLimits/read`.

Any future reset-redemption feature must remain a separate project decision and must not be added to the notifier task or state machine implicitly.
