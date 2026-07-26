You are an independent reviewer, not the author. Find errors and hidden risks.

CONTEXT
We are planning a new Windows-first local automation tool for an existing Codex weekly reset credit. The tool must never create quota, bypass plan limits, or perform any live reset during design and test. An earlier third-party repository exists, but it is public with no license declared. We therefore need a clean-room implementation strategy that preserves useful ideas while avoiding unsafe code reuse and avoiding any mutation of the currently installed local setup.

MATERIALS
- Goal: create a brand-new repository and implementation beside an existing local installation, without changing the installed runtime already present on the user's laptop.
- Existing local installation remains out of scope for edits. It is currently paused and must stay paused.
- Upstream third-party repo status:
  - public GitHub repo
  - no LICENSE file
  - no SECURITY.md
  - no releases
  - minimal community reputation
- Known safe design constraints for the new implementation:
  - local-only by default
  - no hosted backend
  - no direct HTTP calls to private Codex backend endpoints
  - use official Codex app-server or other official local interface for authenticated account/rate-limit reads
  - tests must not call the live consume RPC
  - automation disabled by default
  - exact credit identity checks
  - stable idempotency key per logical attempt
  - bounded retries only for read-only initialization or reconciliation
  - fail closed on ambiguous execution
  - strong environment scrubbing so unrelated API keys/tokens are never inherited by child processes
  - Windows Task Scheduler support is desired
- Candidate clean-room direction:
  1. Observe required behavior and public contracts.
  2. Re-implement from scratch without copying source text or repo-specific structure.
  3. Ship a read-only MVP first: status/doctor/planning/dry-run.
  4. Add guarded scheduling only after environment and task-contract tests are complete.
- Omitted from this brief:
  - source code of the unlicensed upstream repo
  - any user secrets, emails, account identifiers, URLs, or local auth files

QUESTIONS
1. Is a clean-room reimplementation based on public behavior and independently written code the right publication path, given the upstream repo has no license?
2. Should the new GitHub repository start private or public, and why?
3. What architecture is most defensible for a Windows-first safe MVP that never mutates live account state during development?
4. What hidden legal, operational, or security risks are easy to miss here?
5. Which features should be explicitly deferred from v1 to reduce risk?

RESEARCH
Use web search for time-sensitive claims. Prefer primary sources and give direct URLs.
If search finds no confirmation, say exactly "my search found no confirmation"; do not infer non-existence without positive evidence of absence.

OUTPUT
Give findings by severity, accepted claims, rejected claims with proof, disagreements, unknowns, and recommended next steps. End with the following marker on its own final line:
REVIEW-COMPLETE-20260726-CLEANROOM-RESETTER
