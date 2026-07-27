# Security Policy

## Scope

This repository is a public read-only MVP for a Windows-first Codex reset
credit manager. It must not perform live reset-credit consumption during
design, test, CI, or review.

## Secret and Environment Guarantees

1. **No secret transmission**: The current read-only MVP does not send your API keys, token values, or credentials anywhere.
2. **No private backend calls**: The repository does not contact private or undocumented backend endpoints (e.g., `/backend-api/wham/*`).
3. **No live consume path**: There is no live reset consumption or automatic credit redemption logic.
4. **Scrubbed child environment**: Ambient environment values are not forwarded by default. The environment builder only reads values for a minimal allowlist of system variables (such as `PATH`, `TEMP`, `SYSTEMROOT`).
5. **No secret materialization**: Ambient non-allowlisted environment variables are observed strictly by key name when diffing environment state; their values are never read into memory for forwarding, logged, or sent anywhere.
6. **No secrets in planning artifacts**: Phase 1.5 planning-ledger documents or future dry-run artifacts must not contain API keys, token values, raw cookies, auth-file contents, or unrelated credential material.

## Hard rules

1. Do not add any code path that calls a live consume/reset RPC in tests.
2. Do not log secrets, tokens, refresh credentials, or raw account identifiers.
3. Do not inherit ambient API keys or unrelated tokens into child processes.
4. Do not auto-install Scheduled Tasks as part of the default workflow.
5. Do not add live consume or task-registration behavior until provenance,
   licensing, and terms-risk review remain documented and intentional.

## Reporting

If you find a security issue, avoid posting exploit details publicly at first.
Open a minimal issue without sensitive proof-of-concept material or contact the
maintainer privately first. Do not publish proof-of-concept code that can
trigger a live reset or expose credentials.
