# Security Policy

## Scope

This repository is a public read-only MVP for a Windows-first Codex reset
credit manager. It must not perform live reset-credit consumption during
design, test, CI, or review.

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
