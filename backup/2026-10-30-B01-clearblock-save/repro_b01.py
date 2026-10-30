"""B-01 repro: transient TIME poison -> next sync must present blocked:null on disk at create_child time.
Emulates installer Assert-ManagerChildAdmission disk read by reading policy.json from disk inside stubbed _create_child.
Exit 0 = fixed (disk null at enroll), exit 1 = bug present (disk still blocked).
Usage: python repro_b01.py <manager-py-path>
"""
import importlib.util, json, sys, tempfile, pathlib

def load_manager(path):
    spec = importlib.util.spec_from_file_location("mgr_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mgr_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod

def run_once(mgr_path):
    mod = load_manager(mgr_path)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b01repro"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    now = 1790000000.0
    policy = mod._default_policy(now)
    policy["enabled"] = True
    policy["accountEmailSha256"] = "a" * 64
    # poisoned disk state: previous run blocked on transient TIME
    policy["blocked"] = {"code": "TIME_NOT_SYNCHRONIZED", "atUtc": "2026-10-09T20:27:27Z"}
    (root / "state" / "policy.json").write_text(json.dumps(policy), encoding="utf-8")

    class FakeServices:
        def time_status(self):
            return "synchronized"  # transient passed on this run
        def consume_tasks(self):
            return []
        def notify(self, title, message, level="info"):
            return True
        def validate_task(self, job):
            return None
        def disarm(self, job):
            return None
        def validate_cli(self, *a, **k):
            raise AssertionError("must be stubbed at controller level")

    ctl = mod.Controller(root, services=FakeServices(), now=lambda: now)
    captured = {}
    credit = mod.Credit(credit_sha256="b"*64, expires_at=int(now)+86400*5, granted_at=int(now)-86400, reset_type="codexRateLimits", status="active")
    def fake_validate_runtime(policy):
        return ({"primaryUsedPercent": 10}, [credit])  # one schedulable credit
    def fake_quarantine_barrier(policy, credits):
        return False
    def fake_has_margin(credit):
        return True
    def fake_create_child(policy, credits):
        # THIS is the installer's disk read:
        on_disk = json.loads((root / "state" / "policy.json").read_text(encoding="utf-8"))
        captured["disk_blocked_at_enroll"] = on_disk.get("blocked")
        return None  # enroll would succeed; status reservation=none
    ctl._validate_runtime = fake_validate_runtime
    ctl._quarantine_barrier = fake_quarantine_barrier
    ctl._has_margin = fake_has_margin
    ctl._create_child = fake_create_child
    try:
        ctl.sync(scheduled=True)
    except Exception as e:
        print("sync raised: " + repr(e))
        return 2, captured
    return 0, captured

if __name__ == "__main__":
    path = sys.argv[1]
    print("testing: " + path)
    rc, captured = run_once(path)
    if rc == 2:
        print("RESULT: ERROR (sync raised)")
        sys.exit(2)
    disk = captured.get("disk_blocked_at_enroll", "<not captured>")
    print("disk blocked at create_child: " + json.dumps(disk))
    if disk is None:
        print("RESULT: PASS - cleared block persisted before enroll (bug fixed)")
        sys.exit(0)
    else:
        print("RESULT: FAIL - stale blocked still on disk at enroll (bug present, installer would refuse)")
        sys.exit(1)
