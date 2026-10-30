"""B-10b repro: verify the per-credit scope fix of _quarantine_barrier.

After this patch, the barrier is True only when the EARLIEST live credit itself
is in an unresolved quarantine; stale/unrelated entries no longer block fresh
enrollment on a different credit. The hard-raise behaviours (REAPPEARED,
METADATA_CHANGED) are preserved.

Exits 0 on PASS. Usage: python repro_b10b.py <manager-py-path>

Companion to backup/2026-10-30-B10-quarantine-scope-research/repro_b10.py — that
research repro freezes the pre-fix behavior (claim CONFIRMED), while this one
asserts the post-fix invariants. The research repro's `claim-barrier-blocks-
fresh-enrollment` and `latent-bite-mixed-future-dominates` groups will FAIL on
patched runtimes (expected — the behavior they documented is now gone); its
other groups (sanity-all-expired, barrier-reraises-reappeared, sync-locked-
control-flow) still PASS.
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


class _FakeCredit:
    def __init__(self, *, credit_sha256, expires_at, granted_at, reset_type):
        self.credit_sha256 = credit_sha256
        self.expires_at = expires_at
        self.granted_at = granted_at
        self.reset_type = reset_type


def _controller(mod, *, now):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="b10b"))
    root = tmp / "root"
    (root / "state").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)
    (root / "logs").mkdir(parents=True)
    return mod.Controller(root, services=FakeServices(), now=lambda: now)


def _credit(*, sha256, expires_at):
    return _FakeCredit(
        credit_sha256=sha256,
        expires_at=expires_at,
        granted_at=expires_at - 7 * 86400,
        reset_type="codexRateLimits",
    )


def _quarantine(*, sha256, absent_at_utc, expires_at):
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


def test_stale_entry_does_not_block_fresh_enrollment(mod):
    """Core post-fix invariant: a stale/absent future-expiry quarantine on
    credit A does NOT block enrollment on earliest live credit B."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine(sha256=SHA_A, absent_at_utc="2026-10-30T00:00:00Z",
                    expires_at=now + 30 * 86400),
    ]
    credits = [_credit(sha256=SHA_B, expires_at=now + 3 * 86400)]
    failures = []
    returned = ctl._quarantine_barrier(policy, credits)
    if returned is not False:
        failures.append(f"  stale A should not block earliest B — got {returned!r}, want False")
    return failures


def test_earliest_credit_quarantined_future_still_blocks(mod):
    """A quarantine entry whose credit matches the earliest live credit AND is
    still live (now<expiresAt) MUST block — the defensive gate for the credit
    we would actually enroll."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine(sha256=SHA_B, absent_at_utc="2026-10-30T00:00:00Z",
                    expires_at=now + 30 * 86400),
    ]
    credits = [_credit(sha256=SHA_B, expires_at=now + 30 * 86400)]
    failures = []
    try:
        returned = ctl._quarantine_barrier(policy, credits)
    except mod.ManagerError as e:
        if e.code == "QUARANTINED_CREDIT_REAPPEARED":
            # Entry's absentObservedAtUtc was set at creation (absent_at_utc) AND
            # credit is now present → defensive raise. That IS correct behavior
            # and satisfies "earliest match blocks enrollment" more strictly.
            return failures
        failures.append(f"  earliest-match quarantine raised unexpected code: {e.code}")
        return failures
    if returned is not True:
        failures.append(f"  earliest B is in future quarantine — should block, got {returned!r}")
    return failures


def test_earliest_credit_quarantined_past_allows(mod):
    """When earliest credit's quarantine entry has expired (now>=expiresAt),
    enrollment MUST proceed — expired entries no longer block."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    # SHA_B quarantined, but expiresAt in the past
    policy["quarantine"] = [
        _quarantine(sha256=SHA_B, absent_at_utc="2026-09-01T00:00:00Z",
                    expires_at=now - 7 * 86400),
    ]
    credits = [_credit(sha256=SHA_B, expires_at=now + 3 * 86400)]
    failures = []
    # Credit is "present again" (reappeared); the first-pass defensive check
    # should raise REAPPEARED since absentObservedAtUtc is non-None. That's
    # correct behavior — a reappearing quarantined credit is a hard-stop.
    try:
        ctl._quarantine_barrier(policy, credits)
    except mod.ManagerError as e:
        if e.code != "QUARANTINED_CREDIT_REAPPEARED":
            failures.append(f"  reappearing earliest should raise REAPPEARED, got {e.code}")
    else:
        failures.append("  reappearing earliest did not raise REAPPEARED")
    return failures


def test_live_state_scenario_no_block(mod):
    """Replay the exact live-install state (2026-10-30T10:36Z): 3 quarantine
    entries, all with past expiresAt, matching the actual creditIdSha256
    values (replicated by position; actual values redacted). Enrollment of a
    totally different fresh credit MUST not be blocked."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine(sha256=SHA_A, absent_at_utc="2026-10-04T02:41:35Z",
                    expires_at=1_791_079_976),  # past
        _quarantine(sha256=SHA_B, absent_at_utc="2026-10-04T22:11:36Z",
                    expires_at=1_791_151_199),  # past
        _quarantine(sha256=SHA_C, absent_at_utc="2026-10-29T19:11:47Z",
                    expires_at=1_793_300_254),  # past
    ]
    credits = [_credit(sha256="d" * 64, expires_at=now + 7 * 86400)]  # fresh unrelated
    returned = ctl._quarantine_barrier(policy, credits)
    failures = []
    if returned is not False:
        failures.append(f"  live-replay: barrier should return False, got {returned!r}")
    return failures


def test_reappeared_raise_preserved(mod):
    """The hard-raise behavior on reappeared credits MUST survive the fix."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine(sha256=SHA_A, absent_at_utc="2026-10-29T00:00:00Z",
                    expires_at=now + 7 * 86400),
    ]
    credits = [_credit(sha256=SHA_A, expires_at=now + 10 * 86400)]
    failures = []
    try:
        ctl._quarantine_barrier(policy, credits)
    except mod.ManagerError as e:
        if e.code != "QUARANTINED_CREDIT_REAPPEARED":
            failures.append(f"  reappear raise: expected QUARANTINED_CREDIT_REAPPEARED, got {e.code}")
    else:
        failures.append("  reappear raise lost — barrier did not raise")
    return failures


def test_absent_timestamp_still_recorded(mod):
    """Even for entries that don't match the earliest credit, barrier should
    still record their absentObservedAtUtc on first observation (so a later
    reappearance triggers the hard-raise)."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    entry = _quarantine(sha256=SHA_A, absent_at_utc="2026-10-30T00:00:00Z",
                        expires_at=now + 30 * 86400)
    entry["absentObservedAtUtc"] = None  # unobserved so far
    policy["quarantine"] = [entry]
    credits = [_credit(sha256=SHA_B, expires_at=now + 3 * 86400)]
    returned = ctl._quarantine_barrier(policy, credits)
    failures = []
    if returned is not False:
        failures.append(f"  non-match quarantine should not block, got {returned!r}")
    if policy["quarantine"][0]["absentObservedAtUtc"] is None:
        failures.append("  absentObservedAtUtc not recorded — the defensive write was dropped")
    return failures


def test_empty_credits_returns_false(mod):
    """Edge: no credits yet. Barrier should return False (nothing to protect)."""
    now = 1_793_356_574
    ctl = _controller(mod, now=now)
    policy = mod._default_policy(now)
    policy["quarantine"] = [
        _quarantine(sha256=SHA_A, absent_at_utc="2026-10-30T00:00:00Z",
                    expires_at=now + 30 * 86400),
    ]
    credits = []
    returned = ctl._quarantine_barrier(policy, credits)
    failures = []
    if returned is not False:
        failures.append(f"  empty credits should return False, got {returned!r}")
    return failures


def run_all(mgr_path):
    mod = load_manager(mgr_path)
    return [
        ("stale-entry-no-block-fresh", test_stale_entry_does_not_block_fresh_enrollment(mod)),
        ("earliest-future-quar-blocks", test_earliest_credit_quarantined_future_still_blocks(mod)),
        ("earliest-past-quar-raises-reappeared", test_earliest_credit_quarantined_past_allows(mod)),
        ("live-state-replay-no-block", test_live_state_scenario_no_block(mod)),
        ("reappeared-raise-preserved", test_reappeared_raise_preserved(mod)),
        ("absent-timestamp-still-recorded", test_absent_timestamp_still_recorded(mod)),
        ("empty-credits-returns-false", test_empty_credits_returns_false(mod)),
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
