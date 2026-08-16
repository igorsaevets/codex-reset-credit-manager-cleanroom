You are doing a narrow follow-up hardening pass inside this repository only:

- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom`

Read first:

- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\src\codex_reset_credit_manager\app_server.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\tests\test_app_server.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\tests\fake_app_server.py`
- `C:\Users\igors\OneDrive\Документы\New project\codex-reset-credit-manager-cleanroom\research\2026-07-27-phase1-compact-handoff.md`

Goal:

Harden the new read-only app-server transport after manual review found hidden transport risks.

Specific issues to address:

1. `AppServerTransport._timeout` is currently stored but effectively unused.
   - `stdout.readline()` can block indefinitely.
   - The transport should fail closed on timeout.

2. `stderr=PIPE` is currently only read after EOF/error.
   - A noisy app-server could theoretically block if stderr fills up.
   - Add a bounded solution so stderr does not deadlock the transport.

3. Keep scope narrow.
   - Do not add new features.
   - Do not touch live consume paths.
   - Do not broaden filesystem scope.

Recommended direction:

- Use reader thread(s) + queue(s), or another Windows-safe approach, so timeout is real.
- Preserve the same documented read-only RPC set only.
- Add deterministic tests that prove:
  - timeout fails closed
  - large stderr output does not deadlock the observation flow

Nice-to-have if bounded:

- If you see a tiny low-risk improvement to Windows command parsing for `--codex-binary`, you may include it, but only if it stays small and well tested.

Update the compact handoff note with the hardening changes and tests run.

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
