# Phase 1 app-server read-only adapter — implementation brief

Date: 2026-07-27

## Why this exists

The repository is currently a public read-only MVP. Phase 1 should add optional observability through documented Codex app-server read methods without introducing any live consume path, scheduler activation, auth scraping, or mutation of the paused legacy installation on this laptop.

This brief is intended for a bounded local implementation pass inside the cleanroom repository only.

## Hard safety boundaries

- Do not add `account/rateLimitResetCredit/consume` anywhere in cleanroom code or tests.
- Do not add retry logic for redemption or any mutating RPC.
- Do not register a Windows Scheduled Task.
- Do not touch the existing paused legacy runtime under `%LOCALAPPDATA%\\CodexResetCredit`.
- Do not read or forward unrelated secret environment variables into child processes.
- Do not run any live consume/reset action during development or tests.
- Keep all tests deterministic and side-effect free by using local fakes/stubs.

## Official surface we are targeting

Documented Codex app-server read-only surface:

- `initialize`
- `initialized` notification
- `account/read`
- `account/rateLimits/read`

Primary official reference:

- [OpenAI codex app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)

Important observations from the official docs:

1. `codex app-server --stdio` uses newline-delimited JSON-RPC-like JSONL.
2. The connection must send `initialize`, then `initialized`.
3. `account/rateLimits/read` is a documented read method.
4. `rateLimitResetCredits` may be `null`.
5. `rateLimitResetCredits.credits` may be `null`, empty, or capped below `availableCount`.
6. `availableCount` is authoritative when detail rows are fewer than the count.

## Cleanroom files to inspect first

- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\README.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\SECURITY.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\architecture.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\roadmap.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\repository-guide.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\cli.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\config.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\sanitized_env.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\tests\test_sanitized_env.py`

## Legacy reference files to inspect for ideas only

Do not copy code mechanically. Use only for clean-room architectural comparison and edge-case discovery.

- `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\codex_reset_guard.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\tests\fake_app_server.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\tests\test_transport.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-usage-limit-auto-reset\tests\test_validation.py`

## Recommended implementation shape

Keep the design intentionally small and inspectable.

Suggested modules:

- a tiny JSONL app-server client for one request/response session
- a read-only observation layer that:
  - spawns `codex app-server --stdio` with the sanitized child environment
  - performs the initialize handshake
  - calls `account/read`
  - calls `account/rateLimits/read`
  - normalizes the response into a report that explicitly separates:
    - observed facts
    - safe summaries
    - not-inferred / unknown fields
- CLI integration with an explicit opt-in command for live read-only observation

## Strong recommendation on CLI shape

Add a new explicit command instead of silently changing existing commands.

Example direction:

- `observe-rate-limits`

Recommended guardrail:

- require an explicit flag such as `--allow-live-read`

Reason:

- this command is still read-only, but it does talk to the user's actual local Codex app-server and account read surface, so it should never happen accidentally.

## Hidden edge cases to handle

1. `rateLimitResetCredits` can be missing or `null`.
2. `credits` can be `null` even when `availableCount > 0`.
3. `availableCount` can be greater than the number of detail rows.
4. timestamp fields may arrive as Unix seconds or strings depending on backend/client layer shape.
5. `account/read` may include an email; do not expose the full raw email in normal human-readable output unless there is an explicit reason. Prefer redaction or omission in normalized output.
6. `initialize` reports `codexHome`; compare it against the isolated child `CODEX_HOME` to detect environment isolation drift.
7. Do not assume retry behavior. Phase 1 should be single-attempt and fail closed.
8. Ignore server notifications for now unless they are required for transport correctness.

## Good acceptance criteria for this pass

1. Cleanroom gains a read-only app-server adapter that uses only documented read methods.
2. No consume/mutation path is introduced anywhere in cleanroom.
3. Tests use a fake local app-server and do not contact the real network/account.
4. CLI output clearly distinguishes:
   - `availableCount`
   - detail row count
   - unknown / omitted detail rows
5. Documentation is updated to reflect that the repository is still read-only, but now has an explicit opt-in live read-only observation command.
6. The child process still inherits only the allowlisted environment plus explicit cleanroom variables.

## Nice-to-have if it stays bounded

- optional JSON output for machine-readable audit
- optional audit file output
- codex binary version capture if it can be done read-only and simply
- a compact handoff note summarizing what changed and what remains for the next phase

## What to avoid in this pass

- no UI
- no scheduler activation
- no background daemon
- no auto-run behavior
- no consume RPC
- no auth login flow work
- no broad refactor unrelated to Phase 1

## Deliverable expectations

When done, provide:

1. summary of changed files
2. explanation of the chosen architecture
3. tests run and their result
4. remaining risks / unknowns
5. what should be done next in Phase 1.5 or Phase 2
