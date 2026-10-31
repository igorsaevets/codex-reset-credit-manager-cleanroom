"""B-03 Linux twin repro: stderr classifier for install_linux.py throw strings.

Exits 0 on PASS, non-zero on FAIL. Usage:
    python repro_b03_linux.py <manager-py-path>

What is proved:
1. _classify_linux_installer_stderr exists at module scope.
2. It returns distinct codes for each install_linux.py InstallError class:
   admission / time / python-runtime / systemd-task-reg, and the generic
   fallback for empty / unrelated text.
3. The Windows classifier _classify_installer_stderr still behaves the same
   as before (no regression from adding the Linux table).
4. ERROR_MESSAGES[CHILD_PWSH_FAILED] is platform-neutral (does not literally
   say 'PowerShell'), so the Linux twin can reuse the same code symbol
   without a misleading end-user message.
"""
from __future__ import annotations

import importlib.util
import sys


def load_manager(path: str):
    spec = importlib.util.spec_from_file_location("mgr_under_test_linux", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mgr_under_test_linux"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_linux_classifier_exists(mod) -> list[str]:
    failures: list[str] = []
    if not hasattr(mod, "_classify_linux_installer_stderr"):
        failures.append("  _classify_linux_installer_stderr is not defined at module scope")
    if not hasattr(mod, "_LINUX_INSTALLER_SIGNATURES"):
        failures.append("  _LINUX_INSTALLER_SIGNATURES tuple is not defined at module scope")
    return failures


def test_linux_classifier_distinct_codes(mod) -> list[str]:
    cases = [
        # CHILD_ADMISSION_REFUSED - policy / pin refusals
        ("Child enrollment requires enabled, unblocked automatic operation.",
         "CHILD_ADMISSION_REFUSED"),
        ("Executing installer does not match the policy runtime pin.",
         "CHILD_ADMISSION_REFUSED"),
        ("Guard runtime does not match the policy runtime pin.",
         "CHILD_ADMISSION_REFUSED"),
        ("Child Codex path differs from the approved CLI pin.",
         "CHILD_ADMISSION_REFUSED"),
        ("Child mode requires content-addressed installed runtimes.",
         "CHILD_ADMISSION_REFUSED"),
        ("A content-addressed runtime hash does not match its filename.",
         "CHILD_ADMISSION_REFUSED"),
        ("A new Linux installation must start paused.",
         "CHILD_ADMISSION_REFUSED"),
        # CHILD_TIME_UNVERIFIED
        ("Linux system time is not synchronized.",
         "CHILD_TIME_UNVERIFIED"),
        # CHILD_PWSH_FAILED - runtime environment on Linux
        ("The Linux installer requires native Linux.",
         "CHILD_PWSH_FAILED"),
        ("Do not run this installer with sudo or as root.",
         "CHILD_PWSH_FAILED"),
        ("WSL is not supported by the Linux installer.",
         "CHILD_PWSH_FAILED"),
        ("A systemd-based Linux installation is required.",
         "CHILD_PWSH_FAILED"),
        ("A logged-in systemd user session is required.",
         "CHILD_PWSH_FAILED"),
        ("Python capability probe did not return valid JSON.",
         "CHILD_PWSH_FAILED"),
        ("npm was not found on the interactive PATH.",
         "CHILD_PWSH_FAILED"),
        # CHILD_TASK_REG_FAILED - systemd timer/unit registration
        ("systemd returned duplicate metadata for codex-reset-consume-x.timer",
         "CHILD_TASK_REG_FAILED"),
        ("Loaded systemd unit contract differs from the installed file: foo.service",
         "CHILD_TASK_REG_FAILED"),
        ("More than one nonterminal manifest exists.",
         "CHILD_TASK_REG_FAILED"),
        ("A nonterminal one-shot already exists.",
         "CHILD_TASK_REG_FAILED"),
        ("The one-shot timer was not enabled and active.",
         "CHILD_TASK_REG_FAILED"),
        ("Guard enrollment failed.",
         "CHILD_TASK_REG_FAILED"),
        ("The armed manifest did not pin the exact timer unit.",
         "CHILD_TASK_REG_FAILED"),
        # Fallback
        ("", "CHILD_INSTALL_FAILED"),
        ("something unrelated about disks", "CHILD_INSTALL_FAILED"),
        ("Permission denied", "CHILD_INSTALL_FAILED"),
    ]
    failures: list[str] = []
    for stderr, expected in cases:
        got = mod._classify_linux_installer_stderr(stderr)
        if got != expected:
            failures.append(f"  stderr={stderr!r} expected={expected} got={got}")
    return failures


def test_windows_classifier_still_works(mod) -> list[str]:
    """Guard against a regression that would blur Windows classification."""
    cases = [
        ("refusing child enrollment because the installed controller policy is blocked",
         "CHILD_ADMISSION_REFUSED"),
        ("Windows Time (W32Time) is not running",
         "CHILD_TIME_UNVERIFIED"),
        ("PowerShell 7 or newer is required",
         "CHILD_PWSH_FAILED"),
        ("Register-ScheduledTask: Access is denied.",
         "CHILD_TASK_REG_FAILED"),
        ("", "CHILD_INSTALL_FAILED"),
    ]
    failures: list[str] = []
    for stderr, expected in cases:
        got = mod._classify_installer_stderr(stderr)
        if got != expected:
            failures.append(f"  windows stderr={stderr!r} expected={expected} got={got}")
    return failures


def test_pwsh_message_platform_neutral(mod) -> list[str]:
    msg = mod.ERROR_MESSAGES.get("CHILD_PWSH_FAILED", "")
    failures: list[str] = []
    if not isinstance(msg, str) or not msg:
        failures.append("  ERROR_MESSAGES[CHILD_PWSH_FAILED] is empty or missing")
        return failures
    if "PowerShell" in msg or "pwsh" in msg:
        failures.append(f"  ERROR_MESSAGES[CHILD_PWSH_FAILED] still names PowerShell: {msg!r}")
    return failures


def test_app_version_bumped(mod) -> list[str]:
    failures: list[str] = []
    want = "2.7.6"
    got = getattr(mod, "APP_VERSION", None)
    if got != want:
        failures.append(f"  APP_VERSION expected {want!r}, got {got!r}")
    return failures


def run_all(mgr_path: str) -> list[tuple[str, list[str]]]:
    mod = load_manager(mgr_path)
    return [
        ("linux-classifier-exists", test_linux_classifier_exists(mod)),
        ("linux-classifier-distinct-codes", test_linux_classifier_distinct_codes(mod)),
        ("windows-classifier-no-regression", test_windows_classifier_still_works(mod)),
        ("pwsh-message-platform-neutral", test_pwsh_message_platform_neutral(mod)),
        ("app-version-bumped-2.7.6", test_app_version_bumped(mod)),
    ]


if __name__ == "__main__":
    path = sys.argv[1]
    print("testing: " + path)
    results = run_all(path)
    overall_fail = False
    for name, failures in results:
        if failures:
            overall_fail = True
            print(f"  {name}: FAIL")
            for line in failures:
                print(line)
        else:
            print(f"  {name}: pass")
    if overall_fail:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: PASS")
    sys.exit(0)
