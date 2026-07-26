





Reviewing your clean-room plan for Codex reset automation. I’ll audit legal, security, and operational risks with primary sources to validate the safe MVP constraints.I’ve confirmed the upstream licensing trap and the official local interface. Now I’ll pull primary sources to document risks and finalize the review.Independent Review – Windows-first Codex weekly reset tool

### Summary
The proposed safe constraints are directionally correct. The biggest risks are copyright (unlicensed upstream), ToS automation, and accidental live state mutation / credential leakage via Task Scheduler.

### Findings by Severity

**CRITICAL**
- **C1 Legal reuse:** Upstream public repo with no LICENSE is NOT free to reuse. Default copyright applies. GitHub ToS only grants view+fork on GitHub. Off-platform copy/modify/share is prohibited and . Direct copying of source or repo structure = infringement risk.
- **C2 Private backend calls:** Proposal correctly bans direct HTTP to private Codex backend. Bypassing plan limits or creating quota would likely violate upstream ToS and Service Terms. The only defensible read path is the documented official interface: Codex app-server is the interface Codex uses to power rich clients and implementation is open source in openai/codex.
- **C3 Live mutation in tests:** Any test calling live consume RPC risks real quota burn / duplicate consume. Must be banned in CI as proposed.

**HIGH**
- **H1 Existing install mutation:** Requirement “must stay paused” – new repo beside it risks collision via %USERPROFILE%\.codex, %APPDATA%, config.yaml, auth.json, PATH. Need explicit root isolation and read-only probe of existing install.
- **H2 Task Scheduler attack surface:** Task Scheduler can run under SYSTEM context. If tasks store tokens or use highest-privilege, credential theft / persistence abuse. Windows stores credentials differently than Linux cron; error “credentials cannot be stored” is known failure mode. Need no-secret-in-task-definition, DPAPI or Credential Manager, LogonType=S4U or Interactive-only for MVP dry-run.
- **H3 Idempotency misunderstanding:** Stable idempotency key per logical attempt only helps if server honors it. If server does not, client key alone does NOT prevent double spend. Must fail closed on ambiguous execution as proposed.

**MEDIUM**
- **M1 Env scrubbing on Windows:** Requirement is good but incomplete. Windows CreateProcess inherits parent environment block by default; PowerShell child also gets user secrets. Must scrub OPENAI_API_KEY, CODEX_, GH_*, AWS_*, etc., and blocklist via allowlist env, not denylist.
- **M2 Clean-room documentation:** Clean room = method to develop material in isolated environment to ensure work is authentic and not copied and in IP context means developing from room from which all trade secrets, licensed know-how, or copyrighted material have been excluded. Current plan describes re-implement but does not require audit log of what public behavior was observed, who observed, separation list. Without that, contamination claim fails.
- **M3 Publish timing:** No LICENSE, no SECURITY.md, no releases, minimal reputation upstream – increases risk that upstream itself may be ToS-violating or malicious. Re-publishing similar functionality publicly day-1 amplifies legal/reputational risk.

**LOW**
- **L1 Bounded retries:** Limit to read-only init/reconciliation as proposed is correct, but need jitter/backoff spec referencing App Server overloaded error -32001 pattern.
- **L2 Exact credit identity check:** Good, but identity source must be from official account/rate-limit reads, not scraped HTML.

### Accepted Claims
- Local-only by default, no hosted backend – defen­sible for least privilege.
- No direct HTTP calls to private Codex backend – correct, reduces ToS bypass risk.
- Use official app-server/local interface for account reads – correct, primary source confirms app-server is official interface.
- Tests must not call live consume RPC – correct.
- Automation disabled by default, fail closed on ambiguous execution, bounded retries read-only only, exact credit identity checks, stable idempotency key – all accepted as safety best practices.
- Read-only MVP first: status/doctor/planning/dry-run before scheduling – accepted.
- Windows Task Scheduler support desired but after contract tests – accepted.
- Need strong env scrubbing – accepted.

### Rejected Claims With Proof
- **Claim: “Public GitHub repo = free to reuse if no license.” Rejected.**
  Proof: Without a license, default copyright laws apply, meaning you retain all rights and no one may reproduce, distribute, or create derivative works. For users, if you find software without license you have no permission; GitHub allow to view/fork does not imply permission to use/modify/share.
- **Claim: “Fork implied license to reuse elsewhere.” Rejected.**
  Proof: ToS grant is to view and fork your repository and license to reproduce solely on GitHub as permitted through functionality (for example, through forking) – not off-platform reuse.

### Disagreements / Nuances
- Clean-room reimplementation is right publication path *if* strict isolation is documented. The brief’s 2-step “observe behavior + rewrite” is insufficient without written specification firewall and no access to upstream source for implementers.
- Starting public is higher risk than private despite open-source intent. Private-first allows security review, ToS review, and documentation of clean-room sources before any facilitating-use argument.

### Facts / Inferences / Unknowns Separation
**Facts (with primary sources):**
- Default no-license = all rights reserved; view+fork on GitHub only; no permission to copy/distribute/modify.
- Clean room definition: isolated environment ensuring authentic, not copied; excluding trade secrets/know-how/copyrighted material.
- Codex app-server is official rich-client interface, open source impl.
- Task Scheduler can run as SYSTEM.

**Inferences:**
- Weekly reset credit automation, even using official app-server, may still be discouraged under OpenAI Codex product policy if it automates a benefit intended for interactive use.
- Env scrubbing on Windows needs explicit allowlist; otherwise child `codex app-server` may inherit unrelated tokens.
- Stable idempotency key mitigates retry duplication only if persisted atomically and checked before any state change.

**Unknowns:**
- Does official app-server expose weekly reset credit identity and remaining quota as stable typed fields? my search found no confirmation.
- Does consume RPC have server-side idempotency? my search found no confirmation.
- Exact OpenAI Terms language on automating ChatGPT Plus/Pro plan-based Codex credits: my search found no confirmation in retrieved docs – requires legal check of current Terms of Use / Service Terms.
- Upstream third-party repo provenance of its knowledge of private endpoints – unknown without source review (out of scope).

### Q&A

1. **Clean-room right path?** Yes, given no license, only clean-room from public contracts/behavior without copying expression is defensible. Requires documented isolation, specification doc, and no copy of source text or repo-specific structure. Copyright law clean room is process guaranteeing independent design and foreclosing possibility of copying.

2. **Private or public?** Start PRIVATE. Reasons: avoid premature distribution of potentially ToS-sensitive automation, allow SECURITY.md/threat model, avoid facilitating violations, preserve ability to re-license under MIT/Apache-2.0. Switch to public after read-only MVP passes audit and license file added.

3. **Defensible Windows-first MVP architecture:** 
   - Binary/script with zero network except spawning `codex app-server --listen stdio://` (default) to read account/rate-limit.
   - Config root override (e.g., CODEX_HOME_NEW) – never touch existing `%USERPROFILE%\.codex`.
   - Commands: `status`, `doctor` (checks install isolation, no live auth), `plan` (shows next reset UTC), `dry-run` (logs what would happen, no RPC).
   - Persistence: local JSON state with stable attemptId = hash(account_id + credit_id + reset_week) + local monotonic counter, fsync, file lock.
   - Scheduler adapter: generates Task Scheduler XML but does NOT register by default; `schedule --dry-run` prints XML + principal = limited user, LogonType=S4U, no stored password.
   - Strong scrub: spawn with env = {PATH=clean, SystemRoot, TEMP, plus explicit CODEX_?}. No parent env inheritance.

4. **Hidden risks:**
   - Legal: implied copyright, contributor liability if you accept contributions under no license.
   - Operational: clock skew (Windows sleep/hibernate), DST, Task Scheduler miss on laptop closed, double trigger after resume.
   - Security: token leakage via Task Scheduler `Actions` argument visible in Registry/Schtasks query, logs containing account IDs, DPAPI scope mismatch.
   - Compatibility: existing paused installation must stay paused – auto-start of app-server may unpause or upgrade.

5. **Defer from v1:**
   - Any code path that actually calls consume/execute credit.
   - Auto-registration of scheduled task (require explicit `schedule --install --allow-write`).
   - Direct HTTP fallback, headless browser, credential storage helpers, hosted backend, auto-update, multi-user/machine sync, wake-to-run.

### Recommended Next Steps
1. Create private GitHub repo with LICENSE (MIT/Apache-2.0) + SECURITY.md + clean-room policy doc (sources allowed: developers.openai.com/codex/app-server, openai/codex repo).
2. Implement read-only MVP in new directory, env scrub tests, isolation test ensuring existing install untouched.
3. Add idempotency store unit tests + fail-closed property tests (ambiguous = no write).
4. Add Task Scheduler contract tests that parse generated XML, assert no secrets, Principal = limited, LogonType.
5. Legal review of ToS for automating reset credit; document decision; add disclaimer and opt-in flag.
6. Only after audit, open-source publicly with SBOM and threat model.

REVIEW-COMPLETE-20260726-CLEANROOM-RESETTER