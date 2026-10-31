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
5. APP_VERSION is 2.7.6.
6. The real LinuxServices.create_child (subprocess.run mocked) maps each
   outcome to its code and writes exactly one logs/child-install-*.log for
   every failure after spawn (classified, unclassified, timeout, OSError),
   while the success path, the bad-output path and pre-flight rejections
   are unchanged and write no log.

Signature provenance against the real install_linux.py lives in
verify_signatures_v276.py next to this file.
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
    if not hasattr(mod, "_classify_linux_installer_stderr"):
        return ["  _classify_linux_installer_stderr missing - cannot classify"]
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


def test_linux_create_child_end_to_end(mod) -> list[str]:
    """Drive the real LinuxServices.create_child with a mocked subprocess.run.

    The groups above only call the classifier; this one proves the patched
    method itself routes each outcome to the right code and log file.
    """
    import json
    import pathlib
    import shutil
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest import mock

    failures: list[str] = []
    job = {
        "manifestPath": "/x/manifests/job.json",
        "taskName": "codex-reset-consume-aaaaaaaaaaaa-bbbbbbbb.timer",
        "jobId": "12345678-1234-4234-9234-123456789abc",
    }

    def done(returncode: int, stderr: str = "", stdout: str = ""):
        return {"return_value": SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)}

    cases = [
        ("time", done(1, "error: Linux system time is not synchronized.\n"),
         "CHILD_TIME_UNVERIFIED", ["code=CHILD_TIME_UNVERIFIED", "returncode=1", "Linux system time is not synchronized"], None),
        ("admission", done(1, "error: Child enrollment requires enabled, unblocked automatic operation.\n"),
         "CHILD_ADMISSION_REFUSED", ["code=CHILD_ADMISSION_REFUSED", "Child enrollment requires"], None),
        ("task-reg", done(1, "error: The one-shot timer was not enabled and active.\n"),
         "CHILD_TASK_REG_FAILED", ["code=CHILD_TASK_REG_FAILED", "one-shot timer was not enabled"], None),
        ("unclassified-still-logged", done(1, "error: Something nobody anticipated.\n"),
         "CHILD_INSTALL_FAILED", ["code=CHILD_INSTALL_FAILED", "Something nobody anticipated"], None),
        ("timeout", {"side_effect": subprocess.TimeoutExpired(cmd=["python3"], timeout=600)},
         "CHILD_PWSH_FAILED", ["code=CHILD_PWSH_FAILED", "extra=TimeoutExpired"], subprocess.TimeoutExpired),
        ("oserror", {"side_effect": OSError("exec format error")},
         "CHILD_PWSH_FAILED", ["code=CHILD_PWSH_FAILED", "extra=OSError"], OSError),
        ("success-unchanged", done(0, "", json.dumps(job) + "\n"),
         "OK", None, None),
        ("bad-output-unchanged", done(0, "", "not json\n"),
         "CHILD_INSTALL_OUTPUT_INVALID", None, None),
    ]
    with tempfile.TemporaryDirectory(prefix="b03linux-e2e") as directory:
        root = pathlib.Path(directory)
        python = root / "python3.13"
        installer = root / "install_linux.py"
        guard = root / "codex_reset_guard.py"
        for path in (python, installer, guard):
            path.write_text("# test\n", encoding="utf-8")
        services = mod.LinuxServices(root)
        logs = pathlib.Path(services.root) / "logs"
        for name, run_kwargs, want_code, want_log, want_cause in cases:
            shutil.rmtree(logs, ignore_errors=True)
            got_code, got_cause, result = "OK", None, None
            with (
                mock.patch.object(mod.sys, "platform", "linux"),
                mock.patch.dict(mod.os.environ, {"PATH": "/usr/bin:/bin", "HOME": "/home/t"}, clear=True),
                mock.patch.object(mod, "_manager_console_python", return_value=python),
                mock.patch.object(mod.subprocess, "run", **run_kwargs),
            ):
                try:
                    result = services.create_child(installer, "/opt/npm/codex", str(guard))
                except mod.ManagerError as error:
                    got_code, got_cause = error.code, error.__cause__
            if got_code != want_code:
                failures.append(f"  {name}: code expected {want_code}, got {got_code}")
            if want_code == "OK" and result != job:
                failures.append(f"  {name}: success result changed: {result!r}")
            if want_cause is not None and not isinstance(got_cause, want_cause):
                failures.append(f"  {name}: __cause__ expected {want_cause.__name__}, got {type(got_cause).__name__}")
            files = sorted(logs.glob("child-install-*.log")) if logs.exists() else []
            if want_log is None:
                if files:
                    failures.append(f"  {name}: unexpected child-install log written: {[f.name for f in files]}")
                continue
            if len(files) != 1:
                failures.append(f"  {name}: expected exactly 1 child-install log, found {len(files)}")
                continue
            text = files[0].read_text(encoding="utf-8")
            for needle in want_log:
                if needle not in text:
                    failures.append(f"  {name}: log lacks {needle!r}")

        shutil.rmtree(logs, ignore_errors=True)
        with (
            mock.patch.object(mod.sys, "platform", "linux"),
            mock.patch.dict(mod.os.environ, {"PATH": "/usr/bin:/bin", "HOME": "/home/t"}, clear=True),
            mock.patch.object(mod, "_manager_console_python", return_value=python),
            mock.patch.object(mod.subprocess, "run") as run,
        ):
            try:
                services.create_child(installer, "/opt/npm/codex", str(root / "absent_guard.py"))
                code = "OK"
            except mod.ManagerError as error:
                code = error.code
        if code != "CHILD_INSTALL_FAILED":
            failures.append(f"  preflight-missing-guard: expected CHILD_INSTALL_FAILED, got {code}")
        if run.called:
            failures.append("  preflight-missing-guard: subprocess.run was called")
        if logs.exists() and any(logs.glob("child-install-*.log")):
            failures.append("  preflight-missing-guard: unexpected child-install log")
    return failures


def run_all(mgr_path: str) -> list[tuple[str, list[str]]]:
    mod = load_manager(mgr_path)
    return [
        ("linux-classifier-exists", test_linux_classifier_exists(mod)),
        ("linux-classifier-distinct-codes", test_linux_classifier_distinct_codes(mod)),
        ("windows-classifier-no-regression", test_windows_classifier_still_works(mod)),
        ("pwsh-message-platform-neutral", test_pwsh_message_platform_neutral(mod)),
        ("app-version-bumped-2.7.6", test_app_version_bumped(mod)),
        ("linux-create-child-end-to-end", test_linux_create_child_end_to_end(mod)),
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
