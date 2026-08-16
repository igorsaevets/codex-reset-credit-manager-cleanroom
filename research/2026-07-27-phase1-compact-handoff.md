# Phase 1 App-Server Read-Only Implementation — Handoff Note

**Date**: 2026-07-27
**Milestone**: Phase 1 Read-Only App-Server Observability & Transport Hardening

---

## 1. What was changed

1. **Read-Only App-Server Transport Hardening (`src/codex_reset_credit_manager/app_server.py`)**:
   - Added background daemon reader thread (`_read_stdout_loop`) + `queue.Queue` with deadline-based timeout enforcement in `send_request`. Unresponsive child app-server calls now time out and fail closed (`AppServerObservationError`).
   - Added background daemon reader thread (`_read_stderr_loop`) continuously draining stderr into a thread-safe `collections.deque(maxlen=100)` with per-line string truncation (2000 chars). Prevents OS pipe buffer exhaustion and child process deadlock under noisy stderr output.
   - Added safe Windows and POSIX binary command parsing helper (`parse_codex_binary_command`) using `shlex.split(..., posix=not is_windows)` to preserve Windows backslashes and quoted executable paths.
   - Ensured transport process teardown (`close()`) immediately terminates running sub-processes (`proc.kill()`) if un-exited, guaranteeing fast teardown without hanging.

2. **CLI Integration (`src/codex_reset_credit_manager/cli.py`)**:
   - Integrated `parse_codex_binary_command` for `--codex-binary` option parsing.
   - Enforced required opt-in flag `--allow-live-read`.

3. **Models & Protocol**:
   - Kept scope strictly limited to documented read-only RPCs (`initialize`, `account/read`, `account/rateLimits/read`).
   - No mutating RPCs or live consume paths added (`live_consume_allowed` remains `False`).

4. **Deterministic Test Suite (`tests/fake_app_server.py`, `tests/test_app_server.py`)**:
   - Updated `fake_app_server.py` to support `--mode hang` (simulated infinite process hang) and `--mode noisy_stderr` (simulated 50,000 line stderr flood).
   - Expanded unit tests to **22 tests** covering:
     - Normal observation & field parsing
     - Missing/null credits objects & lists
     - Unlisted credits count flags
     - Timestamp format variations
     - Child environment drift detection
     - RPC error fail-closed handling
     - Server crash fail-closed handling
     - **Transport timeout fail-closed enforcement** (`test_timeout_fails_closed`)
     - **Deadlock-free large stderr handling** (`test_large_stderr_does_not_deadlock`)
     - **Cross-platform command parsing** (`test_parse_codex_binary_command`)
     - CLI opt-in flag enforcement & JSON invocation.

---

## 2. Why it was changed

- To address hidden transport risks identified during transport code review:
  - Eliminate un-timeoutable `stdout.readline()` blocks.
  - Eliminate OS pipe deadlocks caused by un-drained `stderr` output.
  - Fix backslash mangling on Windows when `--codex-binary` contains Windows paths.

---

## 3. Tests run & results

- Command: `$env:PYTHONPATH="src"; python -m unittest discover -s tests -v`
- Result: **22 / 22 tests passed (0 failures, 0 errors)** in ~1.22s.

---

## 4. What remains next

- **Phase 1.5 / Phase 2 — Operator-in-the-loop Planning Ledger**:
  - Build persistent planning ledger artifacts linking observed expiry timestamps with warmup/validation checkpoints.
  - Render inspectable operator summary reports before any live redemption gate is evaluated.
- **Phase 3 Decision Gate**:
  - Re-evaluate policy and safety requirements before considering any mutating `consume` RPC or automated scheduler registration.

