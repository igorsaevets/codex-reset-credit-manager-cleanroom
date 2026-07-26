# Security Policy

## Scope

This repository is a private draft for a Windows-first, read-only Codex reset
credit manager. It must not perform live reset-credit consumption during design,
test, CI, or review.

## Hard rules

1. Do not add any code path that calls a live consume/reset RPC in tests.
2. Do not log secrets, tokens, refresh credentials, or raw account identifiers.
3. Do not inherit ambient API keys or unrelated tokens into child processes.
4. Do not auto-install Scheduled Tasks as part of the default workflow.
5. Do not publish the repository until provenance, licensing, and terms-risk
   review are complete.

## Reporting

If you find a security issue, document it privately in the repository issue
tracker or in a private review note. Do not publish proof-of-concept code that
can trigger a live reset or expose credentials.

