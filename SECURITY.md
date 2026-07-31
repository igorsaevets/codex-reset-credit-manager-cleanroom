# Security Policy

## Scope

This repository is a public read-only observer and local expiry notifier for a
Windows-first Codex reset-credit workflow. It must not perform live reset-credit
consumption during design, test, CI, review, installation, or scheduled use.

## Secret and Environment Guarantees

1. **No secret transmission**: The manager does not send API keys, token values, or credentials anywhere.
2. **No private backend calls**: The repository does not contact private or undocumented backend endpoints (e.g., `/backend-api/wham/*`).
3. **No live consume path**: There is no live reset consumption or automatic credit redemption logic.
4. **Scrubbed child environment**: Ambient environment values are not forwarded by default. The environment builder only reads values for a minimal allowlist of system variables (such as `PATH`, `TEMP`, `SYSTEMROOT`).
5. **No secret materialization**: Ambient non-allowlisted environment variables are observed strictly by key name when diffing environment state; their values are never read into memory for forwarding, logged, or sent anywhere.
6. **No secrets in planning artifacts**: Phase 1.5 planning-ledger documents or future dry-run artifacts must not contain API keys, token values, raw cookies, auth-file contents, or unrelated credential material.

## Hard rules

1. Do not add any code path that calls a live consume/reset RPC in tests.
2. Do not log secrets, tokens, refresh credentials, or raw account identifiers.
3. Do not inherit ambient API keys or unrelated tokens into child processes.
4. Scheduled Task installation must require an explicit installer invocation and
   remain reversible.
5. Reminder tasks may only perform a read-only app-server observation or display
   an already-planned local modal inside the `CodexResetCreditNotifier-*` namespace.
6. Do not add scheduled or interactive reset consumption without a separate
   provenance, licensing, terms-risk, idempotency, and user-intent review.

## Reporting

If you find a security issue, avoid posting exploit details publicly at first.
Open a minimal issue without sensitive proof-of-concept material or contact the
maintainer privately first. Do not publish proof-of-concept code that can
trigger a live reset or expose credentials.
