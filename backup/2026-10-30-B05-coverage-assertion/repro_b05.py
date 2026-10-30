"""B-05 repro: streak lifecycle + atUtc preservation + validator + status fields + ERROR_MESSAGES.

Exits 0 on PASS, non-zero on FAIL. Usage: python repro_b05.py <manager-py-path>

What is proved:
1. streak starts at 1 on a fresh block; increments on same-code re-block; resets to 1 on
   code change; is dropped on _clear_block; new _block after clear is streak=1 again.
2. atUtc is PRESERVED across same-code re-blocks (blockedAgeSeconds measures the age of
   the problem, not the age of the last tick) and advances only on code transition.
3. The real 538-row 10-22 cycle: initial TIME_NOT_SYNCHRONIZED then 538 same-code
   CHILD_INSTALL_FAILED reblocks lands on streak=538, firstCode=TIME_NOT_SYNCHRONIZED.
4. _validate_policy accepts {streak:int>=1}, rejects streak as str/0/-1/bool and
   rejects unknown fields on blocked.
5. _status_from exposes blockedStreak, blockedAgeSeconds, firstCode and coverageGap;
   coverageGap=True iff blocked AND (no job OR terminal job OR not armed), bypassing
   the reservation-string masking that would hide the 10-22 scenario.
6. ERROR_MESSAGES carries human strings for all five child-install codes.
7. _log whitelist admits `streak` (otherwise the field would be silently stripped).
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


class FakeJob:
    """Minimal Job stand-in for _status_from (only reads these four fields)."""

    def __init__(self, *, armed=True, terminal=False, process_at=0, expires_at=0):
        self.armed = armed
        self.terminal = terminal
        self.process_at = process_at
        self.expires_at = expires_at


class FakeServices:
    def time_status(self):
        return "synchronized"

    def consume_tasks(self):
        return []

    def notify(self, title, message, level="info"):
        return True

    def validate_task(self, job):
        return None

    def disarm(self, job):
        return None

    def validate_cli(self, *a, **k):
        raise AssertionError

    def binary_pin_available(self, job):
        return True


def _fresh_root(mod, now):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b05"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    policy = mod._default_policy(now)
    policy["enabled"] = True
    policy["accountEmailSha256"] = "a" * 64
    (root / "state" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    return root, policy


def test_streak_lifecycle(mod):
    now_ref = [1_790_000_000.0]
    root, policy = _fresh_root(mod, now_ref[0])
    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now_ref[0])

    failures = []
    ctl._block(policy, "A_CODE_X")
    if policy["blocked"].get("streak") != 1:
        failures.append(f"  1st block: streak expected 1, got {policy['blocked'].get('streak')!r}")
    original_at = policy["blocked"]["atUtc"]

    now_ref[0] += 60.0
    ctl._block(policy, "A_CODE_X")
    if policy["blocked"].get("streak") != 2:
        failures.append(f"  2nd same-code: streak expected 2, got {policy['blocked'].get('streak')!r}")
    if policy["blocked"].get("atUtc") != original_at:
        failures.append(f"  same-code reblock changed atUtc from {original_at!r} to {policy['blocked'].get('atUtc')!r}")

    now_ref[0] += 60.0
    ctl._block(policy, "A_CODE_X")
    if policy["blocked"].get("streak") != 3:
        failures.append(f"  3rd same-code: streak expected 3, got {policy['blocked'].get('streak')!r}")

    now_ref[0] += 60.0
    ctl._block(policy, "B_CODE_Y")
    blocked = policy["blocked"]
    if blocked.get("streak") != 1:
        failures.append(f"  transition: streak expected 1, got {blocked.get('streak')!r}")
    if blocked.get("atUtc") == original_at:
        failures.append("  transition: atUtc did not advance after code change")

    ctl._clear_block(policy)
    if policy["blocked"] is not None:
        failures.append(f"  _clear_block left non-None: {policy['blocked']!r}")

    ctl._block(policy, "A_CODE_X")
    if policy["blocked"].get("streak") != 1:
        failures.append(f"  post-clear fresh block: streak expected 1, got {policy['blocked'].get('streak')!r}")

    return failures


def test_538_row_cycle(mod):
    now_ref = [1_790_000_000.0]
    root, policy = _fresh_root(mod, now_ref[0])
    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now_ref[0])

    ctl._block(policy, "TIME_NOT_SYNCHRONIZED")
    ctl._block(policy, "CHILD_INSTALL_FAILED")
    for _ in range(537):
        now_ref[0] += 1800.0
        ctl._block(policy, "CHILD_INSTALL_FAILED")

    failures = []
    blocked = policy["blocked"]
    if blocked.get("code") != "CHILD_INSTALL_FAILED":
        failures.append(f"  code: expected CHILD_INSTALL_FAILED, got {blocked.get('code')!r}")
    if blocked.get("streak") != 538:
        failures.append(f"  streak: expected 538, got {blocked.get('streak')!r}")
    if blocked.get("firstCode") != "TIME_NOT_SYNCHRONIZED":
        failures.append(f"  firstCode: expected TIME_NOT_SYNCHRONIZED, got {blocked.get('firstCode')!r}")

    try:
        mod._validate_policy(policy)
    except mod.ManagerError as e:
        failures.append(f"  validator rejected the 538-row policy: {e.code}")
    return failures


def test_validator(mod):
    now = 1_790_000_000.0
    base = mod._default_policy(now)
    base["enabled"] = True
    base["accountEmailSha256"] = "a" * 64

    def _validate(blocked_obj):
        pol = dict(base)
        pol["blocked"] = blocked_obj
        return mod._validate_policy(pol)

    cases_ok = [
        {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": 1},
        {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": 538},
        {
            "code": "CHILD_INSTALL_FAILED",
            "atUtc": "2026-10-09T20:27:27Z",
            "firstCode": "TIME_NOT_SYNCHRONIZED",
            "streak": 538,
        },
    ]
    cases_reject = [
        ("streak as str", {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": "1"}),
        ("streak=0", {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": 0}),
        ("streak=-1", {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": -1}),
        ("streak=True (bool subclass of int)", {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": True}),
        ("unknown field", {"code": "X_CODE", "atUtc": "2026-10-30T00:00:00Z", "streak": 1, "extra": "x"}),
    ]
    failures = []
    for ok in cases_ok:
        try:
            _validate(ok)
        except mod.ManagerError as e:
            failures.append(f"  {ok!r} should pass, got {e.code}")
    for label, bad in cases_reject:
        try:
            _validate(bad)
        except mod.ManagerError as e:
            if e.code != "POLICY_INVALID":
                failures.append(f"  {label}: expected POLICY_INVALID, got {e.code}")
        else:
            failures.append(f"  {label}: validator did not reject")
    return failures


def test_status_fields(mod):
    now_ref = [1_790_000_000.0]
    root, policy = _fresh_root(mod, now_ref[0])
    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now_ref[0])

    failures = []

    s = ctl._status_from(policy, None, time_state="synchronized")
    for key, expected in (
        ("coverageGap", False),
        ("blockedStreak", None),
        ("blockedAgeSeconds", None),
        ("firstCode", None),
    ):
        if s.get(key) is not expected:
            failures.append(f"  no-block case: {key} expected {expected!r}, got {s.get(key)!r}")

    ctl._block(policy, "A_CODE_X")
    s = ctl._status_from(policy, None, time_state="synchronized")
    if s.get("coverageGap") is not True:
        failures.append(f"  block+no-job: coverageGap expected True, got {s.get('coverageGap')!r}")
    if s.get("blockedStreak") != 1:
        failures.append(f"  block+no-job: blockedStreak expected 1, got {s.get('blockedStreak')!r}")
    if not isinstance(s.get("blockedAgeSeconds"), int):
        failures.append(f"  block+no-job: blockedAgeSeconds expected int, got {s.get('blockedAgeSeconds')!r}")

    now_ref[0] += 3600.0
    ctl._block(policy, "A_CODE_X")
    disarmed = FakeJob(armed=False, terminal=False)
    s = ctl._status_from(policy, disarmed, time_state="synchronized")
    if s.get("coverageGap") is not True:
        failures.append(f"  block+disarmed-job: coverageGap expected True, got {s.get('coverageGap')!r}")
    if s.get("blockedStreak") != 2:
        failures.append(f"  after same-code reblock: blockedStreak expected 2, got {s.get('blockedStreak')!r}")
    age = s.get("blockedAgeSeconds")
    if not isinstance(age, int) or age < 3600:
        failures.append(f"  blockedAgeSeconds expected >=3600 after 1h, got {age!r}")

    armed = FakeJob(armed=True, terminal=False)
    s = ctl._status_from(policy, armed, time_state="synchronized")
    if s.get("coverageGap") is not False:
        failures.append(f"  block+armed-job: coverageGap expected False (job covers us), got {s.get('coverageGap')!r}")

    terminal = FakeJob(armed=True, terminal=True)
    s = ctl._status_from(policy, terminal, time_state="synchronized")
    if s.get("coverageGap") is not True:
        failures.append(f"  block+terminal-job: coverageGap expected True, got {s.get('coverageGap')!r}")

    ctl._clear_block(policy)
    ctl._block(policy, "TIME_NOT_SYNCHRONIZED")
    ctl._block(policy, "CHILD_INSTALL_FAILED")
    s = ctl._status_from(policy, None, time_state="synchronized")
    if s.get("firstCode") != "TIME_NOT_SYNCHRONIZED":
        failures.append(f"  status firstCode expected TIME_NOT_SYNCHRONIZED, got {s.get('firstCode')!r}")
    if s.get("blockedCode") != "CHILD_INSTALL_FAILED":
        failures.append(f"  status blockedCode expected CHILD_INSTALL_FAILED, got {s.get('blockedCode')!r}")

    return failures


def test_error_messages(mod):
    required = (
        "CHILD_INSTALL_FAILED",
        "CHILD_ADMISSION_REFUSED",
        "CHILD_TIME_UNVERIFIED",
        "CHILD_PWSH_FAILED",
        "CHILD_TASK_REG_FAILED",
    )
    failures = []
    for code in required:
        if code not in mod.ERROR_MESSAGES:
            failures.append(f"  ERROR_MESSAGES missing {code}")
            continue
        value = mod.ERROR_MESSAGES[code]
        if not isinstance(value, str) or len(value) < 10:
            failures.append(f"  ERROR_MESSAGES[{code}] too short / wrong type: {value!r}")
    return failures


def test_log_whitelist_streak(mod):
    now_ref = [1_790_000_000.0]
    root, policy = _fresh_root(mod, now_ref[0])
    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now_ref[0])

    ctl._block(policy, "CODE_A")
    ctl._block(policy, "CODE_A")

    log_files = sorted((root / "logs").glob("*.jsonl"))
    failures = []
    if not log_files:
        failures.append(f"  no *.jsonl log file produced under {root / 'logs'}")
        return failures
    log_text = log_files[-1].read_text(encoding="utf-8")
    lines = [line for line in log_text.strip().splitlines() if line]
    if len(lines) < 2:
        failures.append(f"  expected >= 2 log lines, got {len(lines)}: {lines!r}")
        return failures
    last = json.loads(lines[-1])
    if last.get("event") != "blocked":
        failures.append(f"  last log event not 'blocked': {last!r}")
    if last.get("streak") != 2:
        failures.append(f"  last log streak expected 2, got {last.get('streak')!r} (whitelist missing 'streak'?)")
    if last.get("code") != "CODE_A":
        failures.append(f"  last log code expected CODE_A, got {last.get('code')!r}")
    return failures


def run_all(mgr_path):
    mod = load_manager(mgr_path)
    return [
        ("streak-lifecycle", test_streak_lifecycle(mod)),
        ("538-row-cycle", test_538_row_cycle(mod)),
        ("validator-streak", test_validator(mod)),
        ("status-fields", test_status_fields(mod)),
        ("error-messages", test_error_messages(mod)),
        ("log-whitelist-streak", test_log_whitelist_streak(mod)),
    ]


if __name__ == "__main__":
    path = sys.argv[1]
    print("testing: " + path)
    overall_fail = False
    for name, failures in run_all(path):
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
