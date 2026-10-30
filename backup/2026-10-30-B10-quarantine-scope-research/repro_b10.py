"""B-10 research repro: confirm agy38flash's claim that `_quarantine_barrier`
blocks ALL enrollments on any unresolved quarantine, regardless of whether the
quarantined credit matches the earliest live credit.

READ-ONLY research. Does not patch the live install. Verdict is advisory; the
code fix (narrow barrier to per-credit scope) is a follow-up task.

Exits 0 on PASS (claim confirmed). Non-zero on FAIL (claim rebutted).
Usage: python repro_b10.py <manager-py-path>
"""
import importlib.util
import pathlib
import sys
import tempfile


def load_manager(path):
    spec = importlib.util.spec_from_file_location("mgr_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mgr_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeServices:
    def time_status(self): return "synchronized"
    def consume_tasks(self): return []
    def notify(self, title, message, level="info"): return True
    def validate_task(self, job): return None
    def disarm(self, job): return None
    def validate_cli(self, *a, **k): raise AssertionError
    def binary_pin_available(self, job): return True


def _make_controller(mod, *, now):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b10"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    return mod.Controller(root, services=FakeServices(), now=lambda: now)


class _FakeCredit:
    """Only the attributes `_quarantine_barrier` touches: credit_sha256,
    expires_at, granted_at, reset_type. The real `Credit` dataclass has
    additional fields (incl. `status`) that are irrelevant for the barrier."""

    def __init__(self, *, credit_sha256, expires_at, granted_at, reset_type):
        self.credit_sha256 = credit_sha256
        self.expires_at = expires_at
        self.granted_at = granted_at
        self.reset_type = reset_type


def _make_credit(mod, *, sha256, expires_at):
    del mod  # not needed with fake
    return _FakeCredit(
        credit_sha256=sha256,
        expires_at=expires_at,
        granted_at=expires_at - 7 * 86400,
        reset_type="codexRateLimits",
    )


def _quarantine_entry(*, sha256, absent_at_utc, expires_at):
    return {
        "creditIdSha256": sha256,
        "expiresAt": expires_at,
        "grantedAt": expires_at - 7 * 86400,
        "resetType": "codexRateLimits",
        "reason": "POST_DISPATCH_NOTHING_TO_RESET",
        "firstSeenAtUtc": absent_at_utc,
        "absentObservedAtUtc": absent_at_utc,
    }


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def test_claim_barrier_blocks_fresh_enrollment_on_stale_different_credit(mod):
    """CORE CLAIM: a quarantine entry on credit A (absent, future expiresAt)
    blocks enrollment of a DIFFERENT, healthy credit B. The barrier is global,
    not scoped per-credit."""
    now = 1_793_356_574  # 2026-10-30T10:36Z
    ctl = _make_controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine_entry(
            sha256=SHA_A,
            absent_at_utc="2026-10-30T00:00:00Z",
            expires_at=now + 7 * 86400,  # 7 days in the future
        ),
    ]
    # Credits list: only credit B, which is NOT quarantined — should be enrollable
    credits = [_make_credit(mod, sha256=SHA_B, expires_at=now + 3 * 86400)]

    returned = ctl._quarantine_barrier(policy, credits)

    failures = []
    if returned is not True:
        failures.append(
            f"  CLAIM REBUTTED: barrier returned {returned!r}, expected True "
            f"(claim is that unresolved quarantine blocks even unrelated healthy credits)"
        )
    return failures


def test_barrier_returns_false_when_all_quarantines_expired(mod):
    """SANITY: barrier correctly does NOT block when every quarantine entry
    has already reached expiresAt — this is the current live state."""
    now = 1_793_356_574
    ctl = _make_controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine_entry(
            sha256=SHA_A,
            absent_at_utc="2026-10-04T02:41:35Z",
            expires_at=1_791_079_976,  # past
        ),
        _quarantine_entry(
            sha256=SHA_B,
            absent_at_utc="2026-10-04T22:11:36Z",
            expires_at=1_791_151_199,  # past
        ),
        _quarantine_entry(
            sha256=SHA_C,
            absent_at_utc="2026-10-29T19:11:47Z",
            expires_at=1_793_300_254,  # past
        ),
    ]
    credits = [_make_credit(mod, sha256="d" * 64, expires_at=now + 7 * 86400)]

    returned = ctl._quarantine_barrier(policy, credits)
    failures = []
    if returned is not False:
        failures.append(
            f"  SANITY FAIL: with all quarantines expired, barrier should be False, got {returned!r}"
        )
    return failures


def test_barrier_future_entry_dominates_mixed(mod):
    """One future-expiry quarantine entry is enough to lock out enrollment,
    even when all other entries are past. This is the latent-bite scenario:
    a single POST_DISPATCH_NOTHING_TO_RESET event after 11-06 would push one
    entry's expiresAt ~30 days out, locking all enrollments until then."""
    now = 1_793_356_574
    ctl = _make_controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine_entry(
            sha256=SHA_A,
            absent_at_utc="2026-10-04T02:41:35Z",
            expires_at=1_791_079_976,  # past
        ),
        _quarantine_entry(
            sha256=SHA_B,
            absent_at_utc="2026-10-30T00:00:00Z",
            expires_at=now + 30 * 86400,  # future (simulating a new quarantine)
        ),
    ]
    credits = [_make_credit(mod, sha256="d" * 64, expires_at=now + 7 * 86400)]

    returned = ctl._quarantine_barrier(policy, credits)
    failures = []
    if returned is not True:
        failures.append(
            f"  LATENT-BITE REBUTTED: mixed quarantine (past+future) should return True, got {returned!r}"
        )
    return failures


def test_barrier_reraises_reappeared(mod):
    """Secondary: if a quarantined credit REAPPEARS in the live credits list
    (absentObservedAtUtc already set), the barrier raises
    QUARANTINED_CREDIT_REAPPEARED — this is a defensive hard-stop, not just
    blocking. Confirms the barrier has three behaviors (unresolved=True,
    unresolved=False, hard raise)."""
    now = 1_793_356_574
    ctl = _make_controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine_entry(
            sha256=SHA_A,
            absent_at_utc="2026-10-29T00:00:00Z",
            expires_at=now + 7 * 86400,
        ),
    ]
    # Credit A reappears in the live list
    credits = [_make_credit(mod, sha256=SHA_A, expires_at=now + 10 * 86400)]

    failures = []
    try:
        ctl._quarantine_barrier(policy, credits)
    except mod.ManagerError as e:
        if e.code != "QUARANTINED_CREDIT_REAPPEARED":
            failures.append(f"  wrong error code: expected QUARANTINED_CREDIT_REAPPEARED, got {e.code}")
    else:
        failures.append("  barrier did not raise on reappeared credit (behavior changed?)")
    return failures


def test_sync_locked_early_returns_waiting_when_barrier_true(mod):
    """INTEGRATION-ADJACENT: without running the full _sync_locked (which has
    heavy dependencies), we observe the control flow: line 2627 of _sync_locked
    uses the barrier return value to decide reservation. We trace that path
    textually in the manager module source."""
    import inspect
    src = inspect.getsource(mod.Controller._sync_locked)
    failures = []
    # Confirm the barrier is called and its True result short-circuits enrollment
    if "self._quarantine_barrier(policy, credits)" not in src:
        failures.append("  _sync_locked does not call _quarantine_barrier directly")
    # Count how many times barrier is called
    count = src.count("self._quarantine_barrier(policy, credits)")
    if count < 1:
        failures.append(f"  expected >=1 barrier call, found {count}")
    # Confirm early-return pattern after a True barrier
    if 'reservation="waiting"' not in src:
        failures.append("  no reservation='waiting' early-return seen in _sync_locked")
    # Confirm _create_child is positioned AFTER the barrier check
    create_idx = src.find("self._create_child(policy, credits)")
    barrier_idx = src.find("self._quarantine_barrier(policy, credits)")
    if create_idx < 0 or barrier_idx < 0 or create_idx < barrier_idx:
        failures.append(
            f"  control-flow invariant violated: _create_child idx={create_idx} should be AFTER "
            f"first _quarantine_barrier idx={barrier_idx}"
        )
    return failures


def run_all(mgr_path):
    mod = load_manager(mgr_path)
    return [
        ("claim-barrier-blocks-fresh-enrollment", test_claim_barrier_blocks_fresh_enrollment_on_stale_different_credit(mod)),
        ("sanity-all-expired-no-block", test_barrier_returns_false_when_all_quarantines_expired(mod)),
        ("latent-bite-mixed-future-dominates", test_barrier_future_entry_dominates_mixed(mod)),
        ("barrier-reraises-reappeared", test_barrier_reraises_reappeared(mod)),
        ("sync-locked-control-flow", test_sync_locked_early_returns_waiting_when_barrier_true(mod)),
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
        print("RESULT: FAIL (claim rebutted or control flow changed)")
        sys.exit(1)
    print("RESULT: PASS (B-10 claim CONFIRMED — barrier globally blocks on any unresolved quarantine; fix needed to scope per-credit)")
    sys.exit(0)
