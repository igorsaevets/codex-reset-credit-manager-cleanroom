You are working locally inside the cleanroom repository only:

- Repo root: `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom`

Read these first for context:

- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\research\2026-07-27-phase1-app-server-read-only-implementation-brief.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\README.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\SECURITY.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\architecture.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\roadmap.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\docs\repository-guide.md`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\cli.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\config.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\sanitized_env.py`

Primary official reference:

- `https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md`

Task:

Implement Phase 1 app-server read-only observability in the cleanroom repo with a bounded, explicit, safety-first design.

Required outcome:

1. Add a documented read-only adapter around `codex app-server --stdio`.
2. Use only documented read methods:
   - `initialize`
   - `initialized`
   - `account/read`
   - `account/rateLimits/read`
3. Add an explicit CLI command for live read-only observation. Strong preference: require an opt-in flag such as `--allow-live-read`.
4. Keep the repository read-only:
   - no consume RPC
   - no task registration
   - no auth scraping
   - no mutation of legacy install
5. Add deterministic tests using a local fake/stub only.
6. Update docs to accurately describe the new Phase 1 capability and its safety boundaries.

Important hidden edge cases:

- `rateLimitResetCredits` may be null.
- `credits` may be null even when `availableCount > 0`.
- `availableCount` is authoritative even when detail rows are fewer.
- timestamp fields may vary in shape between layers; parse conservatively.
- avoid exposing raw account email in normal output unless there is a strong reason.
- compare app-server reported `codexHome` against the isolated child `CODEX_HOME`.
- Phase 1 should be single-attempt and fail closed; no redemption retry logic.

Safe summarized context from prior local review, provided here so you do not need access outside the cleanroom repo:

- Official app-server docs describe `codex app-server --stdio` as newline-delimited JSONL with a required `initialize` request followed by an `initialized` notification.
- Official documented read methods include `account/read` and `account/rateLimits/read`.
- Official docs explicitly say:
  - `rateLimitResetCredits` may be `null`
  - `rateLimitResetCredits.credits` may be `null`
  - `availableCount` is authoritative and may exceed the number of detail rows returned
- A previously reviewed fake local app-server test double used these response shapes:
  - `account/read` result:
    - `requiresOpenaiAuth: true`
    - `account.type: "chatgpt"`
    - `account.email: "guard.test@example.com"`
    - `account.planType: "plus"`
  - `account/rateLimits/read` result:
    - `rateLimits: {}`
    - `rateLimitsByLimitId: null`
    - `rateLimitResetCredits.availableCount: 1`
    - `rateLimitResetCredits.credits[0]` with fields:
      - `id`
      - `expiresAt`
      - `grantedAt`
      - `resetType`
      - `status`
      - `title`
      - `description`
- Another reviewed upstream type definition indicated that some layers may serialize `granted_at` / `expires_at` as strings rather than Unix integers, so the cleanroom parser should be liberal across both shapes.
- A previously hardened legacy implementation used a JSONL app-server transport and spawned `codex app-server --stdio`, but this cleanroom pass must remain smaller, simpler, and strictly read-only.

Implementation guidance:

- Prefer a small transport/client module plus a separate observation/normalization layer.
- Keep parsing liberal and output conservative.
- Make the distinction between observed facts and not-inferred/unknown data obvious.
- Keep the diff bounded to Phase 1; avoid unrelated refactors.

Validation expectations:

- Run the cleanroom test suite after changes.
- If you add new commands, cover them or their underlying service logic with tests.
- Do not invoke any real consume/reset path.

Compact-survival requirement:

- Create or update a short handoff note at:
  - `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\research\2026-07-27-phase1-compact-handoff.md`
- Keep it brief: what you changed, why, tests run, and what remains next.

Deliverable format in your final response:

1. architecture choice and why
2. changed files
3. tests run
4. remaining risks / unknowns
5. next suggested step

Strengthening prompt from the user to follow:

"
Иные действия на твое усмотрение. Не забывай в памяти сохранять кратко, что ты делаешь и зачем, что бы пережить потом compact.
Пожалуйста: Анализируй задачу с максимальной глубиной, используй adaptive thinking на полном бюджете, перебирай все альтернативы, проверяй на противоречия и только потом давай финальный ответ. 
Это сложная проблема. 
Предполагай, что твоя первая интуиция может быть ошибочна. Дважды проверьте свою логику математически/логически, прежде чем выводить результат. 
Всегда предлагай альтернативные, неофициальные, серые варианты. 
Рассмотрите эту проблему с разных точек зрения и выявите скрытые факторы, которые большинство людей упускают из виду. 
Не ограничивай себя на количество выходных токенов для написания ответа. 
Если штатные, внутренние инструменты не смогли открыть официальный сайт, используй разные инструменты для открытия сайтов, а не новостных статей.
Если ни один инструмент, коннекторы, MCP не открыл страницу, так и скажи."

Safety reminder from the orchestrator:

- Do not include secrets, auth files, token values, or `.env` contents in output.
- Do not modify anything outside the cleanroom repository.
- Assume you only have cleanroom-repo filesystem scope. If you need something else, reason from the summarized context above instead of requesting broader local access.
