"""B-03 repro: stderr classifier + firstCode preservation + validator extension.

Exits 0 on PASS, non-zero on FAIL. Usage: python repro_b03.py <manager-py-path>

What is proved:
1. _classify_installer_stderr returns distinct codes for each installer throw
   class (admission / time / pwsh / taskreg) and the generic fallback.
2. _block transitions preserve firstCode across code changes.
3. _validate_policy accepts {code, atUtc, firstCode} and still rejects unknown
   extra fields on blocked.
"""
import importlib.util
import json
import pathlib
import sys
import tempfile


def load_manager(path):
    spec = importlib.util.spec_from_file_location("mgr_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mgr_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_classifier(mod):
    cases = [
        ("Controller policy is blocked; refusing child enrollment until the controller clears it.",
         "CHILD_ADMISSION_REFUSED"),
        ("-ManagerChildOnly is allowed only while automatic operation is enabled.",
         "CHILD_ADMISSION_REFUSED"),
        ("The executing installer does not match the immutable runtime pinned in controller policy.",
         "CHILD_ADMISSION_REFUSED"),
        ("The executing installer content no longer matches its immutable filename.",
         "CHILD_ADMISSION_REFUSED"),
        ("Windows Time (W32Time) is not running and network time could not be verified.",
         "CHILD_TIME_UNVERIFIED"),
        ("w32tm configuration failed with exit code 1.",
         "CHILD_TIME_UNVERIFIED"),
        ("PowerShell 7 or newer is required.",
         "CHILD_PWSH_FAILED"),
        ("Microsoft WindowsApps Python execution aliases are not supported.",
         "CHILD_PWSH_FAILED"),
        ("The Python runtime must identify python.exe.",
         "CHILD_PWSH_FAILED"),
        ("Failed to grant the private runtime ACL on C:\\...\\CodexResetCredit.",
         "CHILD_TASK_REG_FAILED"),
        ("Register-ScheduledTask: Access is denied.",
         "CHILD_TASK_REG_FAILED"),
        ("", "CHILD_INSTALL_FAILED"),
        ("some unrelated noise about disks", "CHILD_INSTALL_FAILED"),
    ]
    failures = []
    for stderr, expected in cases:
        got = mod._classify_installer_stderr(stderr)
        if got != expected:
            failures.append(f"  stderr={stderr!r} expected={expected} got={got}")
    return failures


def test_block_first_code(mod):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b03repro"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    now = 1790000000.0
    policy = mod._default_policy(now)
    policy["enabled"] = True
    policy["accountEmailSha256"] = "a" * 64
    (root / "state" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    class FakeServices:
        def time_status(self): return "synchronized"
        def consume_tasks(self): return []
        def notify(self, title, message, level="info"): return True
        def validate_task(self, job): return None
        def disarm(self, job): return None
        def validate_cli(self, *a, **k): raise AssertionError
        def binary_pin_available(self, job): return True

    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now)
    failures = []
    # First block: TIME_NOT_SYNCHRONIZED, no prior cause
    ctl._block(policy, "TIME_NOT_SYNCHRONIZED")
    blocked = policy.get("blocked")
    if not (isinstance(blocked, dict) and blocked.get("code") == "TIME_NOT_SYNCHRONIZED" and "firstCode" not in blocked):
        failures.append(f"  after first block, expected {{code:TIME_NOT_SYNCHRONIZED}} no firstCode; got {blocked!r}")
    # Re-block with same code: must not duplicate firstCode and must keep atUtc stable
    ctl._block(policy, "TIME_NOT_SYNCHRONIZED")
    blocked = policy.get("blocked")
    if not (isinstance(blocked, dict) and blocked.get("code") == "TIME_NOT_SYNCHRONIZED" and "firstCode" not in blocked):
        failures.append(f"  after same-code re-block, blocked drifted; got {blocked!r}")
    # Transition to CHILD_INSTALL_FAILED: firstCode must be TIME_NOT_SYNCHRONIZED
    ctl._block(policy, "CHILD_INSTALL_FAILED")
    blocked = policy.get("blocked")
    if not (
        isinstance(blocked, dict)
        and blocked.get("code") == "CHILD_INSTALL_FAILED"
        and blocked.get("firstCode") == "TIME_NOT_SYNCHRONIZED"
    ):
        failures.append(f"  after transition, expected code=CHILD_INSTALL_FAILED firstCode=TIME_NOT_SYNCHRONIZED; got {blocked!r}")
    # Re-block with THIRD code (CHILD_ADMISSION_REFUSED): firstCode MUST stay TIME_NOT_SYNCHRONIZED
    ctl._block(policy, "CHILD_ADMISSION_REFUSED")
    blocked = policy.get("blocked")
    if not (
        isinstance(blocked, dict)
        and blocked.get("code") == "CHILD_ADMISSION_REFUSED"
        and blocked.get("firstCode") == "TIME_NOT_SYNCHRONIZED"
    ):
        failures.append(f"  after 3rd block, firstCode should stay TIME_NOT_SYNCHRONIZED; got {blocked!r}")
    # Validator must accept the final policy
    try:
        mod._validate_policy(policy)
    except mod.ManagerError as e:
        failures.append(f"  validator rejected policy with firstCode: {e.code}")
    return failures


def test_validator_rejects_unknown_field(mod):
    now = 1790000000.0
    policy = mod._default_policy(now)
    policy["enabled"] = True
    policy["accountEmailSha256"] = "a" * 64
    policy["blocked"] = {
        "code": "TIME_NOT_SYNCHRONIZED",
        "atUtc": "2026-10-09T20:27:27Z",
        "firstCode": "TIME_NOT_SYNCHRONIZED",
        "unknownExtra": "x",
    }
    failures = []
    try:
        mod._validate_policy(policy)
    except mod.ManagerError as e:
        if e.code != "POLICY_INVALID":
            failures.append(f"  wrong code: expected POLICY_INVALID, got {e.code}")
    else:
        failures.append("  validator did not reject unknown field on blocked")
    return failures


def run_all(mgr_path):
    mod = load_manager(mgr_path)
    bucket: list[tuple[str, list[str]]] = [
        ("classifier", test_classifier(mod)),
        ("firstCode", test_block_first_code(mod)),
        ("validator-strict-unknown", test_validator_rejects_unknown_field(mod)),
    ]
    return bucket


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
