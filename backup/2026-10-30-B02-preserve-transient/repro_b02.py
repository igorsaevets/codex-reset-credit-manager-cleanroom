"""B-02 repro: a transient TIME_NOT_SYNCHRONIZED with ONE armed one-shot must
preserve the job; policy still becomes blocked (fail-closed), but no disarm.

Exit 0 = fixed (no disarm, policy blocked, preserved reference != None)
Exit 1 = bug present (disarm was called)
Exit 2 = unexpected error

Usage: python repro_b02.py <manager-py-path>
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


def run_once(mgr_path):
    mod = load_manager(mgr_path)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b02repro"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    now = 1790000000.0
    policy = mod._default_policy(now)
    policy["enabled"] = True
    policy["accountEmailSha256"] = "a" * 64
    (root / "state" / "policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )

    # Build an armed, pre-dispatch one-shot sitting 13 days before trigger -
    # exactly the 2026-10-09 incident shape.
    fake_job_path = root / "manifests" / "reset-credit-fake.json"
    fake_job = mod.Job(
        path=fake_job_path,
        schema_version=2,
        job_id="fakejobid-0000-0000-0000-000000000000",
        state="ARMED",
        armed=True,
        credit_sha256="b" * 64,
        expires_at=int(now) + 86400 * 13,
        granted_at=int(now) - 86400,
        reset_type="codexRateLimits",
        account_sha256="a" * 64,
        codex_exe="C:\\fake\\codex.exe",
        codex_version="codex-cli 0.0.0",
        codex_sha256="c" * 64,
        signer_subject="CN=fake",
        task_name="\\CodexResetCredit\\Consume-fakejob",
        trigger_at=int(now) + 86400 * 13 - 1020,
        process_at=int(now) + 86400 * 13 - 300,
        phase="preDispatch",
        result=None,
        failure_code=None,
        terminal_at=None,
    )

    disarm_calls = {"count": 0}

    class FakeServices:
        def time_status(self):
            raise mod.ManagerError("TIME_NOT_SYNCHRONIZED")

        def consume_tasks(self):
            return []

        def notify(self, title, message, level="info"):
            return True

        def validate_task(self, job):
            return None

        def disarm(self, job):
            disarm_calls["count"] += 1

        def validate_cli(self, *a, **k):
            raise AssertionError("validate_cli must not be called in this test")

        def binary_pin_available(self, job):
            return True

    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now)
    # Short-circuit disk and task-inventory I/O to isolate the exception
    # handler in _mutating_operation.
    ctl._jobs = lambda: [fake_job]

    def failing_sync_locked(policy, jobs):
        # Mirror _sync_locked:2439 - services.time_status() raises before
        # anything else touches the policy or the job.
        ctl.services.time_status()
        return None

    ctl._sync_locked = failing_sync_locked

    try:
        status = ctl.sync(scheduled=True)
    except Exception as e:  # noqa: BLE001
        return 2, {"error": repr(e), "disarm_calls": disarm_calls["count"]}

    # Read back the policy from disk to confirm fail-closed semantics are
    # preserved: the block MUST be persisted even though the job survives.
    saved = json.loads((root / "state" / "policy.json").read_text(encoding="utf-8"))
    return 0, {
        "disarm_calls": disarm_calls["count"],
        "policy_blocked": saved.get("blocked"),
        "status_automation": status.get("automation"),
        "status_reservation": status.get("reservation"),
    }


if __name__ == "__main__":
    path = sys.argv[1]
    print("testing: " + path)
    rc, info = run_once(path)
    print("disarm calls:", info.get("disarm_calls"))
    print("policy.blocked after sync:", json.dumps(info.get("policy_blocked")))
    print("status.automation:", info.get("status_automation"))
    print("status.reservation:", info.get("status_reservation"))
    if rc == 2:
        print("RESULT: ERROR -", info.get("error"))
        sys.exit(2)
    disarm = info["disarm_calls"]
    blocked = info["policy_blocked"]
    if disarm == 0 and isinstance(blocked, dict) and blocked.get("code") == "TIME_NOT_SYNCHRONIZED":
        print("RESULT: PASS - armed one-shot preserved; policy blocked (fail-closed OK)")
        sys.exit(0)
    if disarm == 0 and blocked is None:
        print("RESULT: FAIL-UNEXPECTED - no disarm but block was not persisted")
        sys.exit(3)
    print("RESULT: FAIL - active job was disarmed on a transient (bug present)")
    sys.exit(1)
