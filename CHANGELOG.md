# Changelog

## 0.3.3 - 2026-08-17

- fix `NameError` crash in GUI monitor startup caused by unimported `contextlib` module

## 0.3.2 - 2026-08-16

- add monthly GitHub repository update checker with 30-day throttle and automatic prompt
- add `check-updates` CLI subcommand with `--force`, `--repo`, and `--json` flags
- add custom ChatGPT-inspired cyclic reset app icon across Window, Taskbar, and Start Menu shortcuts
- add non-blocking in-app update notification banner and direct GitHub release launcher
- update documentation with high-resolution logo and release badges

## 0.3.1 - 2026-08-16

- add real-time Usage % and window duration display in desktop GUI status cards
- add explicit version display across window title, header, and subtitle in both Russian and English
- improve resilient refresh and error presentation in GUI status monitor
- update packaging metadata and full test suite

## 0.3.0 - 2026-08-16

- add live rate-limit usage and quota inspection from `codex app-server` (`primary` and `secondary` windows, `usedPercent`, `resetsAt`, window duration, account credits, and spend control)
- add dedicated `usage` CLI command with visual progress bar, quota percentage, and localized reset countdowns (Russian / English / JSON)
- add interactive read-only desktop status monitor GUI (`gui`) with live gauges and asynchronous refresh
- enhance `observe-rate-limits` and `notifier-status` with structured usage reporting
- persist sanitized `lastUsage` snapshots in state store (`schemaVersion: 2` with seamless v1 backward compatibility)
- add comprehensive test coverage for usage parsing, progress bar rendering, duration formatting, and state migration

## 0.2.1 - 2026-07-31

- show days, hours, minutes, and seconds remaining when the modal opens
- add correct Russian singular and plural forms for remaining-time units
- default the Windows installer to automatic Russian/English UI-culture selection

## 0.2.0 - 2026-07-31

- add an optional Windows expiry notifier
- check Codex reset-credit inventory once per day through the read-only app-server adapter
- schedule one deterministic local reminder for 12 hours before the nearest expiry
- show a persistent English or Russian modal that requires OK or close
- add fail-closed inventory, timestamp, environment, stale-task, and duplicate-notice checks
- add a WhatIf-capable Windows installer
- add notifier unit tests, Task Scheduler contract tests, and source-level no-redemption checks
- refresh README and package metadata for accurate SEO and generative-search discovery

## 0.1.0

- publish the isolated, read-only planning and app-server observation MVP
