### Compact Survival Summary
This review establishes Phase 1.5 as a non-mutating, documentation-first milestone ("Phase 1.5: Operator Planning Ledger & Posture Alignment"). It clarifies public repo posture, eliminates contradictions between historical pre-publication notes and current public visibility, introduces `docs/planning-ledger.md` as an explicit schema specification, and prepares the repository for auditability without introducing any live reset or automated mutation code.

---

### 1. Findings by Severity

#### Major Severity: Historical Document Posture Contradiction
* **Issue**: `docs/strategic-review-2026-07-26.md` contains active-sounding statements such as *"Start with a private repository"* and *"This repository stays private and read-only for now."*
* **Impact**: External readers and automated scanners may conclude the repository was published accidentally or contains unreviewed private information.
* **Resolution**: Add an explicit, standardized **Historical Context Banner** at the top of `strategic-review-2026-07-26.md` confirming the document is an unedited pre-publication record preserved solely for provenance.

#### Major Severity: Scope Ambiguity Between Read-Only Observability and Execution
* **Issue**: Transitioning directly from Phase 1 (observability) to Phase 2 (planning/preview features) creates ambiguity about whether dry-run previews include execution capabilities or live side-effects.
* **Impact**: Stakeholders might assume Task Scheduler previews or expiry targets execute mutations behind the scenes.
* **Resolution**: Formally introduce **Phase 1.5: Operator-in-the-Loop Planning Ledger Specification** as a non-mutating documentation bridge.

#### Minor Severity: Fragmented Architecture & Roadmap References
* **Issue**: `README.md`, `docs/roadmap.md`, and `docs/architecture.md` refer to planning concepts across scattered bullet points with slightly varying phase numbering and scope bounds.
* **Impact**: Inconsistent terminology for the planning ledger and operator review steps.
* **Resolution**: Harmonize phase definitions across all four core documentation files.

---

### 2. Accepted Claims
1. The repository is public, read-only, and operates under strict environment/auth boundary constraints.
2. Observability via `codex app-server --stdio` adapter behind `--allow-live-read` is complete (Phase 1).
3. The repo must remain documentation-first, non-mutating, with zero live reset flow or scheduler registration.
4. Local research artifacts and local legacy installs must remain uncommitted and unreferenced in public files.

---

### 3. Rejected Claims & Proof from Provided Materials
* **Claim**: *"The repo needs executable code for Phase 1.5 planning."*
  * **Proof**: Context states: *"keep all changes documentation-first and non-mutating"* and *"leave local research files uncommitted and untouched"*. Phase 1.5 is purely structural and analytical.
* **Claim**: *"Historical review documents should be deleted or retroactively modified."*
  * **Proof**: Context explicitly lists `docs/strategic-review-2026-07-26.md` as an intended pre-publication snapshot. Provenance integrity requires keeping original text intact while wrapping it in clear public disclaimer metadata.

---

### 4. Disagreements & Hidden Risks

1. **Risk of "Schema Illusion"**: Defining structured JSON/YAML schemas for the planning ledger in `docs/planning-ledger.md` might lead readers to assume a background daemon processes them.
   * *Mitigation*: Emphasize in `docs/planning-ledger.md` that all planning ledger artifacts are human-reviewed, static JSON files intended solely for manual operator evaluation.
2. **Timezone & Expiry Clock Divergence**: Planning expiry targets across UTC vs. local system time risks misinterpretation by operators.
   * *Mitigation*: Require explicit dual ISO-8601 timestamps (`expiry_utc` and `expiry_local`) in the ledger specification.
3. **External Verification Claim**: my search found no confirmation for external third-party compliance standards regarding this specific repository posture, so posture boundaries must remain self-contained.

---

### 5. Unknowns
* Final naming/formatting of future Phase 2 dry-run report outputs (outside Phase 1.5 scope).
* Specific operator environment OS defaults (Windows Task Scheduler vs. cron) for future non-registered preview bundles.

---

### 6. Answers to Specific Questions

#### Q1: What is the strongest Phase 1.5 documentation shape for a public read-only MVP?
The strongest shape is a **bridging milestone** ("Phase 1.5: Planning Ledger Specification & Posture Alignment") inserted between Phase 1 (Observability) and Phase 2 (Artifact Generation). This makes it explicit that data formats and safety boundaries are frozen before any generation logic is introduced.

#### Q2: Is a dedicated `planning-ledger.md` the right next artifact, or is that over-structuring?
A dedicated `docs/planning-ledger.md` is **the right next artifact**. It isolates the schema definitions, timezone rules, and operator verification procedures without inflating `architecture.md` or `roadmap.md`.

#### Q3: Which current public statements are most likely to confuse readers about repo status or scope?
1. `docs/strategic-review-2026-07-26.md`: Lines stating *"Start with a private repository"* / *"stays private"*.
2. `README.md` & `docs/roadmap.md`: Jumping from Phase 1 directly to Phase 2 without explicitly bounding Phase 1.5 as non-mutating design/documentation.

#### Q4: What minimal edit set gives the cleanest repo page and internal consistency?
A 6-file documentation update package:
1. `README.md`: Add Phase 1.5 to quick roadmap; clarify public posture.
2. `docs/roadmap.md`: Formalize Phase 1.5 milestone and deliverables.
3. `docs/architecture.md`: Insert Planning Ledger conceptual layer between App-Server Adapter and Future Action Gate.
4. `docs/repository-guide.md`: Update file index to include `docs/planning-ledger.md` and clarify cleanroom constraints.
5. `docs/strategic-review-2026-07-26.md`: Add standard Historical Context Disclaimer header.
6. `docs/planning-ledger.md` *(New)*: Specification for operator-in-the-loop ledger JSON format, schema, and human verification process.

#### Q5: What hidden risks or credibility problems remain even after those edits?
* Readers looking for automated reset solutions might misinterpret "planning ledger" as an active queued task engine.
* Clear security disclaimers must state that planning ledgers do **not** log authorization credentials, API keys, or raw local session tokens.

---

### 7. Concrete File-by-File Recommended Edit Plan

#### File 1: `README.md`
* **Changes**: Update the summary roadmap section to include Phase 1.5 explicitly. Clarify public posture.
* **Suggested Edit Block**:
```markdown
## Roadmap Summary

1. **Phase 0 (Foundation)**: Strict child environment scrubbing, isolated draft root, deterministic expiry planning. *(Completed)*
2. **Phase 1 (Observability)**: Read-only `codex app-server --stdio` adapter behind `--allow-live-read`. *(Completed)*
3. **Phase 1.5 (Planning Ledger & Posture Alignment)**: Operator-in-the-loop planning ledger specification (`docs/planning-ledger.md`) and public repository framing. *(Current)*
4. **Phase 2 (Planning & Preview Artifacts)**: Non-registering preview bundles, dry-run reports, and structured planning exports. *(Proposed)*
5. **Future Decision Gate**: User-initiated consume flow or scheduler registration (strictly subject to formal audit).
```

---

#### File 2: `docs/roadmap.md`
* **Changes**: Insert Phase 1.5 details; clarify that Phase 1.5 is documentation and schema definition only.
* **Suggested Edit Block**:
```markdown
### Phase 1.5: Operator Planning Ledger & Posture Alignment (Current)
- [x] Standardize public posture and auditability framing across all documentation.
- [x] Clarify historical pre-publication reviews vs. active public cleanroom status.
- [x] Specify `docs/planning-ledger.md` format (JSON schema for planned expiry actions).
- [x] Define operator review criteria and timezone display rules (UTC vs. local).
- [ ] Maintain 100% non-mutating design with zero live execution paths.

### Phase 2: Operator-in-the-Loop Artifact Generation (Proposed)
- Structure dry-run reports against frozen Phase 1.5 ledger schemas.
- Generate Task Scheduler XML preview bundles (without system registration).
```

---

#### File 3: `docs/architecture.md`
* **Changes**: Update component diagram/flow text to show the Planning Ledger as a read-only intermediate document produced after observability inspection and before any future decision gate.
* **Suggested Edit Block**:
```markdown
## System Data & Planning Flow

[ App-Server State / Read-Only Adapter ]
                   │
                   ▼
       [ Read-Only Observability ]
                   │
                   ▼
     [ Phase 1.5 Planning Ledger ]  <-- Static JSON Schema / Manual Review
                   │
                   ▼
  [ Phase 2 Preview & Dry-Run Reports ]
                   │
                   ▼ (Strict Manual Gate - No Auto-Execution)
       [ Future Action Decision ]
```

---

#### File 4: `docs/repository-guide.md`
* **Changes**: Add `docs/planning-ledger.md` to the document map; re-affirm public cleanroom guidelines.
* **Suggested Edit Block**:
```markdown
## Documentation Map

- `README.md`: Public project overview, boundaries, and quickstart.
- `docs/architecture.md`: System topology, boundaries, and data flow.
- `docs/roadmap.md`: Chronological milestone tracker (Phase 0 through Phase 2).
- `docs/planning-ledger.md`: Schema specification for operator-in-the-loop planning ledgers.
- `docs/strategic-review-2026-07-26.md`: Historical pre-publication review snapshot (archival).
- `SECURITY.md`: Auth scrubbing rules, local credential isolation, and threat model.
```

---

#### File 5: `docs/strategic-review-2026-07-26.md`
* **Changes**: Add an un-ambiguous historical disclaimer header at top of file.
* **Suggested Edit Block**:
```markdown
> [!NOTE]
> **HISTORICAL PRE-PUBLICATION SNAPSHOT**  
> This document represents an internal architectural review created on July 26, 2026, prior to making the repository public. Recommendations within this document regarding repository visibility ("keep private") reflect past decision-making steps and are preserved strictly for historical provenance. For current repository status and posture, consult [README.md](../README.md).
```

---

#### File 6: `docs/planning-ledger.md` *(NEW FILE)*
* **Purpose**: Create a clean, authoritative schema document for the non-mutating planning ledger.
* **Suggested Content Outline**:
```markdown
# Operator Planning Ledger Specification (Phase 1.5)

## Overview
The Planning Ledger is a static, structured JSON artifact format designed to record observed credit expiry targets and operator review decisions without executing mutations.

## Guiding Principles
1. **Non-Mutating**: Contains zero executable code or active trigger mechanisms.
2. **Explicit Timezones**: All timestamps must provide paired `ISO-8601` values for UTC and local system time.
3. **No Credential Persistence**: Auth tokens, cookies, or secrets must never appear in ledger outputs.

## Ledger Schema (v1.0)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CodexResetPlanningLedger",
  "type": "object",
  "properties": {
    "generated_at_utc": { "type": "string", "format": "date-time" },
    "target_expiry_utc": { "type": "string", "format": "date-time" },
    "target_expiry_local": { "type": "string" },
    "observed_credit_state": {
      "type": "object",
      "properties": {
        "status": { "type": "string" },
        "remaining_percent": { "type": "number" }
      }
    },
    "operator_review": {
      "type": "object",
      "properties": {
        "approved": { "type": "boolean", "default": false },
        "notes": { "type": "string" }
      }
    }
  },
  "required": ["generated_at_utc", "target_expiry_utc", "observed_credit_state"]
}
```

## Security & Provenance Notes
- Planning ledgers are strictly local, uncommitted artifacts unless sanitized for dry-run previews.
- File integrity can be validated using standard SHA-256 hashes for audit trails.
```

---

REVIEW-COMPLETE-PHASE15-20260727
