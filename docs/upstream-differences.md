# Intentional Differences From The Legacy Third-Party Direction

## Strategic differences

| Topic | This draft |
| --- | --- |
| Publication | Public read-only notifier with explicit provenance caveat |
| Legal posture | Assumes no reuse rights from an unlicensed public repo |
| Existing machine state | Explicitly leaves the current paused install alone |
| Account behavior | Read-only observation; no reset activation or redemption |
| Scheduler integration | Optional daily read plus persistent local T−12 reminder |
| Secrets | Allowlist-based child environment |
| Release gate | Provenance + terms + security review |

## Product differences

- Read-only by default and by design
- One daily app-server observation and one deterministic local reminder task
- Reminder action performs no network request and contains no raw credit ID
- Separate isolated root: `%LOCALAPPDATA%\\CodexResetCreditDraft`
- No attempt to mirror the legacy installer's runtime layout
- Strict validation of app-server reset-credit type, status, count, and timezone-aware expiry
