You are an independent reviewer, not the author. Find errors and hidden risks.

CONTEXT
We are continuing a public cleanroom repository named `codex-reset-credit-manager-cleanroom`.
The repository is now public and already has a read-only Phase 1 app-server observability layer.
The next narrow task is Phase 1.5:

1. add a clear operator-in-the-loop planning ledger concept and public-facing documentation for it;
2. clean up residual public wording so the repo no longer looks accidentally private or internally contradictory;
3. keep all changes documentation-first and non-mutating;
4. leave local research files uncommitted and untouched as local-only artifacts.

This matters because the repo page is meant to be a credible public read-only MVP, not a vague draft and not a live reset bot. We want clearer public positioning and a visible planning-ledger layer before any future live-action gate is even discussed.

MATERIALS
Repository state summary as of 2026-07-27:

- Public repo: `igorsaevets/codex-reset-credit-manager-cleanroom`
- Current milestone: read-only MVP
- Existing code already includes:
  - strict child environment scrubbing
  - isolated draft root
  - deterministic expiry planning
  - Task Scheduler XML preview only
  - read-only `codex app-server --stdio` adapter behind `--allow-live-read`
- Explicit non-goals still include:
  - no live consume path
  - no scheduler registration
  - no private endpoints
  - no auth scraping

Important file snapshots:

1. `README.md`
- Describes repo as a public read-only MVP and public preview.
- Says roadmap short version is:
  1. keep current milestone read-only and auditable
  2. add optional read-only observability
  3. add operator-in-the-loop planning artifacts
  4. only then decide whether user-initiated consume path or scheduler registration should exist

2. `docs/roadmap.md`
- Phase 0 hardening foundation: current foundations
- Phase 1 read-only observability: completed
- Phase 2 operator-in-the-loop planning artifacts: proposed
- Candidate features include:
  - planning ledger format for a chosen expiry target
  - timezone rendering and local/UTC comparison helpers
  - structured dry-run reports
  - preview bundle for a future scheduled action without registration

3. `docs/architecture.md`
- Future order currently says:
  1. read-only observability
  2. planning ledger and audit artifacts
  3. only then a decision about whether a user-initiated `consume` path should exist

4. `docs/repository-guide.md`
- Repo guide is public-facing and currently accurate about read-only scope.

5. `docs/strategic-review-2026-07-26.md`
- This file is explicitly described as a historical pre-publication snapshot.
- It still includes the historical recommendation:
  - “Start with a private repository.”
  - “This repository stays private and read-only for now.”
- The first line already says it is a historical pre-publication snapshot from July 26, 2026, before the repository was made public.

Constraints:

- Do not rely on or mention any unlicensed third-party source code.
- Do not add or imply a live reset flow.
- Do not add scheduler activation.
- Do not introduce private or undocumented API use.
- Do not assume any local auth artifacts are available.
- Do not touch or reference any local legacy install outside the cleanroom repo.
- Do not request browser, shell, file, or command tools. Reason from the supplied materials only.
- Keep the task advisory and read-only.

Requested deliverable:

Produce a concrete recommended edit set for Phase 1.5. The best answer will:

- decide whether Phase 1.5 should be represented as a distinct doc milestone between Phase 1 and Phase 2, or whether Phase 2 should be reframed;
- propose the smallest coherent public documentation package;
- identify any wording that still confuses “historical snapshot” with “current repo posture”;
- recommend whether to create a new doc such as `docs/planning-ledger.md`, and if so what sections it should contain;
- suggest exact file-by-file edits for:
  - `README.md`
  - `docs/roadmap.md`
  - `docs/architecture.md`
  - `docs/repository-guide.md`
  - `docs/strategic-review-2026-07-26.md`
- mention whether any SECURITY or provenance wording should also be updated.

QUESTIONS
1. What is the strongest Phase 1.5 documentation shape for a public read-only MVP?
2. Is a dedicated `planning-ledger.md` the right next artifact, or is that over-structuring?
3. Which current public statements are most likely to confuse readers about repo status or scope?
4. What minimal edit set gives the cleanest repo page and internal consistency?
5. What hidden risks or credibility problems remain even after those edits?

RESEARCH
Use only the materials above. If you believe a claim requires external verification, say exactly "my search found no confirmation", but do not ask for tools or browsing because this review is intentionally evidence-bounded.

OUTPUT
Give findings by severity, accepted claims, rejected claims with proof from the provided materials, disagreements, unknowns, and recommended next steps.
Then provide a file-by-file recommended edit plan with suggested wording blocks or section outlines.
End with the following marker on its own final line:
REVIEW-COMPLETE-PHASE15-20260727

Additional task-specific guidance:
- Keep a compact-survival summary of what you are doing and why.
- Prefer bounded, explicit, read-only-safe framing.
- Be alert for contradictions between “historical document” language and “current public repo” language.
