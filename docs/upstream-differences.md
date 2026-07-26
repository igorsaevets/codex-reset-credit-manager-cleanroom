# Intentional Differences From The Legacy Third-Party Direction

## Strategic differences

| Topic | This draft |
| --- | --- |
| Publication | Starts private |
| Legal posture | Assumes no reuse rights from an unlicensed public repo |
| Existing machine state | Explicitly leaves the current paused install alone |
| Live behavior | Deferred |
| Scheduler integration | Preview-only XML, no registration |
| Secrets | Allowlist-based child environment |
| Release gate | Provenance + terms + security review |

## Product differences

- Read-only by default and by design
- Separate isolated root: `%LOCALAPPDATA%\\CodexResetCreditDraft`
- No attempt to mirror the legacy installer's runtime layout
- No direct dependence on a real reset-credit response schema yet

