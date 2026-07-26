### Executive Summary & Review Overview

This independent review evaluates the clean-room reimplementation strategy for a Windows-first local automation tool targeting Codex weekly reset credits. Based strictly on the provided brief and design constraints, the proposed direction is architecturally sound and safety-focused, but contains critical legal and operational blind spots that must be addressed prior to implementation.

---

### Findings by Severity

#### 1. CRITICAL: Clean-Room Contamination Risk (Single-Author Pitfall)
* **Description**: Simply writing "new code from scratch" does not constitute a legal clean-room implementation if the same engineer inspects the unlicensed upstream source code and subsequently writes the new implementation. Standard copyright law ("All Rights Reserved" for unlicensed public repos) protects code structure, sequence, and organization.
* **Impact**: Potential copyright infringement claims from the original upstream author if non-trivial structural or procedural similarities persist.

#### 2. HIGH: Platform Terms of Service (ToS) & Account Suspension Risk
* **Description**: Automating weekly credit resets or manipulating quota reset workflows—even locally—may violate the Codex platform's Terms of Service regarding automated account management or unauthorized client automation.
* **Impact**: Risk of account flagging, rate-limiting, or permanent account ban by the service provider, regardless of local tool safety.

#### 3. HIGH: Shared State & Process Contention Risk
* **Description**: Running a new local tool beside a paused existing local installation risks race conditions, file lock contention (e.g., SQLite/JSON state databases), or double-execution if the paused runtime resumes or shares local configuration paths.
* **Impact**: Corrupted local account state or unintended runtime side effects.

#### 4. MEDIUM: Scheduled Task Context & Token Leaks
* **Description**: Windows Task Scheduler tasks often execute under non-interactive user tokens or system contexts. Standard environment variable inheritance or unencrypted temp logs can expose authentication tokens to local event logs or low-privilege users.
* **Impact**: Local privilege escalation or credential exposure on the host machine.

#### 5. LOW: System Sleep & Clock Drift Edge Cases
* **Description**: Windows desktop hibernation and sleep cycles interrupt scheduled tasks and skew relative timer calculations.
* **Impact**: Missed reset windows or unexpected burst retries upon waking from sleep.

---

### Accepted Claims

* **Read-only MVP as initial milestone**: Limiting initial releases strictly to `status`, `doctor`, `planning`, and `dry-run` guarantees zero live account mutations during early testing.
* **Local-only execution & Environment scrubbing**: Explicitly scrubbing child process environments and refusing hosted backends eliminates external data telemetry and accidental token propagation.
* **Official app-server IPC for reads**: Using official local interfaces (app-server / IPC) rather than scraping or reverse-engineering private REST endpoints ensures compliance with local contract boundaries.
* **Fail-closed on ambiguous state**: Halting execution whenever credit identity or state verification is unclear prevents unauthorized or duplicate reset attempts.

---

### Rejected Claims with Rationale

* **Claim**: *"Observing public behavior and re-implementing without copying source text is automatically a safe clean-room implementation."*
  * **Proof / Rationale**: Legal clean-room design requires strict isolation between the **Specification Team** (who analyzes public behavior or unlicensed source code) and the **Implementation Team** (who writes code strictly based on written functional specifications without ever viewing the original source). If a single developer reads the upstream repo and writes the new repo, clean-room defense is compromised.

---

### Disagreements

* **Direct inclusion of Windows Task Scheduler in initial test phases**:
  * *Disagreement*: Integrating Task Scheduler before the core CLI state machine is fully verified in interactive mode adds process-level non-determinism (environment variances, background context execution). Task Scheduler integration should be isolated into a standalone helper script after core CLI stability is achieved.

---

### Unknowns

* **Codex Platform Policy on Local Reset Automation**: Whether automated reset triggers via official app-server IPC are explicitly permitted under current Codex ToS.
* **Shared Storage Directory Paths**: Whether the existing paused local installation uses locked local files or standard directory locations that the new tool might inadvertently access.
* *(Note on external verification)*: As no external web queries were performed per execution constraints, my search found no confirmation regarding specific upstream repository updates or third-party license additions.

---

### Answers to Detailed Questions

#### 1. Is a clean-room reimplementation based on public behavior and independently written code the right publication path, given the upstream repo has no license?
**Yes, but with strict clean-room governance.**
Since the upstream repo has no license, default copyright ("All Rights Reserved") applies. You cannot fork, copy, or adapt its source code. A clean-room approach is the only legally defensible path. To make it defensible:
1. Document the functional spec derived strictly from public documentation or black-box observations.
2. Ensure the developer implementing the code does not reference or look at the unlicensed upstream source files.

#### 2. Should the new GitHub repository start private or public, and why?
**Start Private.**
* **Security & Safety**: Prevents premature distribution of unverified automation logic before dry-run safety guards and environment scrubbing tests are verified.
* **Legal Hygiene**: Allows the project to establish clear clean-room provenance documentation, open-source licensing (e.g., MIT/Apache-2.0), and a `SECURITY.md` before public visibility.

#### 3. What architecture is most defensible for a Windows-first safe MVP that never mutates live account state during development?
**Hexagonal Architecture (Ports & Adapters) with a Hard-Coded Policy Engine**:
* **Domain / Policy Engine**: Pure, deterministic logic that parses credit identity, reset windows, and idempotency keys. Zero network or OS dependencies. Tested via pure unit tests.
* **Codex IPC Adapter (Read-Only)**: Interfaces exclusively with the official local app-server via local IPC/JSON-RPC.
* **Execution Guard Adapter**: Wraps all side-effect calls. In MVP mode, the mutation interface is a hard-coded stub (`NoOpExecutor`) that throws an error if a write/consume RPC is invoked.
* **Environment & Config Adapter**: Reads configuration via Windows DPAPI or isolated user-scoped config files, explicitly scrubbing unrelated environment variables (`OPENAI_API_KEY`, `AZURE_*`, `HEX_KEY`).

```
 +-------------------------------------------------------+
 |                     CLI / Runner                      |
 +---------------------------+---------------------------+
                             |
 +---------------------------v---------------------------+
 |               Pure Domain Policy Engine               |
 |         (Idempotency, Credit Identity, Rules)         |
 +-------------+---------------------------+-------------+
               |                           |
 +-------------v-------------+ +-----------v-------------+
 | Codex IPC Read Adapter    | | Read-Only Guard Adapter |
 | (Official App-Server IPC) | | (NoOp / Mock Execution) |
 +---------------------------+ +-------------------------+
```

#### 4. What hidden legal, operational, or security risks are easy to miss here?
* **Single-Developer Contamination**: Reading unlicensed code before writing new code undermines clean-room defense.
* **Account ToS Violations**: Automated quota manipulation triggering automated abuse detection systems.
* **Windows Task Context Leaks**: Scheduled tasks storing plain-text tokens in logs or inheriting system-wide environment variables.
* **Hibernate / Clock Skew**: Windows laptops waking from sleep triggering mass retry loops due to stale time deltas.

#### 5. Which features should be explicitly deferred from v1 to reduce risk?
* **Live Credit Mutation / Reset Execution**: Keep v1 strictly read-only (`doctor`, `status`, `dry-run`).
* **Automated Task Scheduler Registration**: Require manual PowerShell/Task Scheduler configuration initially.
* **Daemon / Background Service Mode**: Force manual interactive CLI invocations.
* **Multi-Account / Key Switching**: Limit to single authenticated local session context.

---

### Recommended Next Steps

1. **Establish Clean-Room Spec**: Draft a standalone specification document describing input/output schemas and public IPC contracts without pasting or copying upstream code.
2. **Initialize Private Repository**: Create a private GitHub repository containing `LICENSE` (e.g., MIT), `README.md`, `SECURITY.md`, and the functional specification.
3. **Build Read-Only Core**: Implement the Hexagonal Architecture with hard-coded read-only guards.
4. **Implement Environment Scrubbing**: Add suite-level unit tests verifying child processes inherit zero sensitive ambient environment variables.
5. **Verify Against Paused Setup**: Validate that the new tool operates in complete isolation without reading or writing files in the paused installation directory.

REVIEW-COMPLETE-20260726-CLEANROOM-RESETTER
