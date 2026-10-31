## Linux twin of the B-03 child-install diagnostics

v2.7.5 made Windows child-install failures diagnosable: the installer's stderr is classified into a specific `CHILD_*` code and written to `logs/child-install-<UTC>.log`. On Linux, `LinuxServices.create_child` still discarded the stderr of `install_linux.py` and raised a generic `CHILD_INSTALL_FAILED` — the same diagnostic gap that made the Windows incident of 2026-10-22 hard to diagnose. This release closes it on Linux.

### What changed
- New `_LINUX_INSTALLER_SIGNATURES` table and `_classify_linux_installer_stderr()`, the Linux counterpart of the v2.7.5 Windows classifier. It maps `install_linux.py` error messages onto the existing codes:
  - `CHILD_ADMISSION_REFUSED` — policy, pin and identity refusals
  - `CHILD_TIME_UNVERIFIED` — `Linux system time is not synchronized.`
  - `CHILD_PWSH_FAILED` — runtime-environment prerequisites (WSL, sudo/root, systemd user session, Python probe, npm launcher, `CODEX_HOME`)
  - `CHILD_TASK_REG_FAILED` — systemd timer/service registration and one-shot state
- `LinuxServices.create_child`: a spawn error or the 600-second timeout becomes `CHILD_PWSH_FAILED`; a non-zero installer exit is classified by the table. Each of these writes `logs/child-install-<UTC>.log` with the code plus either the exception text or the exit status, full stderr and the last 2,048 characters of stdout — including failures the table does not recognise.
- `ERROR_MESSAGES["CHILD_PWSH_FAILED"]` now reads "The child installer could not start its native runtime.", so this code fits both platforms.
- `APP_VERSION` is 2.7.6. A version assertion in `tests/test_manager_console.py` that still expected 2.7.4 is fixed.

### Coverage
`install_linux.py` raises 133 distinct `InstallError` messages. The table gives 59 of them a specific code; the other 74 still map to `CHILD_INSTALL_FAILED` as before, but their full text now lands in the child-install log. Each of the 55 table entries occurs verbatim in a real installer message, and no message matches two codes. Full mapping: [coverage-v2.7.6.txt](https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom/blob/0a235425569c136832ed724fefa89d0ba66294bf/backup/2026-10-30-B03-linux-twin/coverage-v2.7.6.txt).

### Compatibility
- No policy-schema change: the four codes exist since v2.7.5 and the policy validator accepts them.
- Windows: control flow unchanged. Visible differences are the version string and the reworded `CHILD_PWSH_FAILED` message.
- The controller cleans up a failed child for any error code, so the new codes do not change cleanup.

### Known limitations
- One log file per failed attempt and no rotation yet: with the 30-minute Linux ManagerSync timer, a persistent failure writes up to about 48 small files a day.
- Two failures within the same UTC second share a file name; the later one overwrites the earlier.
- On Linux, `CHILD_TASK_REG_FAILED` still reads "could not register the Scheduled Task" — Windows wording for what is a systemd timer there.
- A spawn error, a timeout or a non-zero exit is logged; an exit 0 with unreadable output (`CHILD_INSTALL_OUTPUT_INVALID`) is not, on either platform.

### Verification
- Fresh clone of this tag on Windows (Python 3.14): `pytest tests/` — 318 passed, 3 skipped.
- Fresh clone in a Linux container (Python 3.12, non-root): v2.7.5 shows 22 test errors and failures there, v2.7.6 shows 21. The difference is the version test fixed here; the 21 are Windows-only tests that are not skipped on Linux plus the guard's WSL check, which fires inside Docker Desktop's WSL2 VM.
- [`repro_b03_linux.py`](https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom/blob/0a235425569c136832ed724fefa89d0ba66294bf/backup/2026-10-30-B03-linux-twin/repro_b03_linux.py) drives the real `LinuxServices.create_child` with a mocked `subprocess.run` (8 outcomes plus a pre-flight rejection). It passes on v2.7.6 on Windows and Linux; on v2.7.5 (control run on Windows) it fails exactly on the six post-spawn outcomes. [`verify_signatures_v276.py`](https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom/blob/0a235425569c136832ed724fefa89d0ba66294bf/backup/2026-10-30-B03-linux-twin/verify_signatures_v276.py) checks the table against the installer source.
- Not tested: a real install on a physical, non-WSL Linux host.

Audit trail and the write-up of the Windows incident: [codex-reset-credit-manager-cleanroom](https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom).
