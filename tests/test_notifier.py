from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codex_reset_credit_manager.models import (
    AccountInfo,
    AppServerHandshakeInfo,
    CreditDetail,
    ObservationReport,
    RateLimitInfo,
)
from codex_reset_credit_manager.notifier import (
    NOTICE_START_GRACE_SECONDS,
    NotifierError,
    StateStore,
    display_scheduled_notice,
    notice_task_name,
    parse_expiry_utc,
    record_notifier_error,
    render_notice_task_xml,
    sanitized_notifier_status,
    select_nearest_available,
    synchronize_notifier,
)


NOW = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)


def credit(
    opaque_id: str,
    expires_at: datetime,
    *,
    status: str = "available",
    reset_type: str = "codex_rate_limits",
) -> CreditDetail:
    return CreditDetail(
        id=opaque_id,
        expires_at=expires_at.isoformat(),
        granted_at=None,
        reset_type=reset_type,
        status=status,
        title=None,
        description=None,
    )


def observation(
    credits: list[CreditDetail],
    *,
    available_count: int | None = None,
    has_unlisted: bool = False,
    drift: bool = False,
    live_consume_allowed: bool = False,
) -> ObservationReport:
    if available_count is None:
        available_count = sum(
            1 for item in credits if (item.status or "").lower() == "available"
        )
    return ObservationReport(
        mode="read-only",
        live_read_allowed=True,
        timestamp_utc=NOW.isoformat(),
        handshake=AppServerHandshakeInfo(
            user_agent="test",
            codex_home=r"C:\isolated",
            platform_family="windows",
            platform_os="windows",
            codex_home_matches_expected=not drift,
        ),
        account=AccountInfo(
            type="chatgpt",
            email_masked="u***@example.com",
            plan_type="plus",
            requires_openai_auth=True,
        ),
        rate_limits=RateLimitInfo(
            available_count=available_count,
            detail_count=len(credits),
            has_unlisted_credits=has_unlisted,
            credits=tuple(credits),
            raw_rate_limits={},
        ),
        environment_drift_detected=drift,
        legacy_install_touched=False,
        live_consume_allowed=live_consume_allowed,
    )


class FakeScheduler:
    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}
        self.registered: list[str] = []
        self.deleted: list[str] = []

    def task_exists(self, task_name: str) -> bool:
        return task_name in self.tasks

    def register_notice(self, **kwargs) -> None:
        task_name = kwargs["task_name"]
        self.tasks[task_name] = dict(kwargs)
        self.registered.append(task_name)

    def delete_notice(self, task_name: str) -> None:
        self.tasks.pop(task_name, None)
        self.deleted.append(task_name)


class NotifierSelectionTests(unittest.TestCase):
    def test_selects_nearest_available_and_subtracts_exactly_twelve_hours(self) -> None:
        earliest = datetime(2026, 7, 31, 19, 55, 17, tzinfo=timezone.utc)
        later = earliest + timedelta(days=10)
        candidate = select_nearest_available(
            observation(
                [
                    credit("opaque-later", later),
                    credit("opaque-earliest", earliest),
                ]
            ),
            now_utc=NOW,
            lead_hours=12,
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.expires_at_utc, earliest)
        self.assertEqual(candidate.notify_at_utc, earliest - timedelta(hours=12))
        self.assertEqual(
            candidate.expires_at_utc - candidate.notify_at_utc,
            timedelta(hours=12),
        )
        self.assertNotIn("opaque-earliest", candidate.fingerprint)

    def test_accepts_live_app_server_camel_case_reset_type(self) -> None:
        candidate = select_nearest_available(
            observation(
                [
                    credit(
                        "opaque-live-shape",
                        NOW + timedelta(days=2),
                        reset_type="codexRateLimits",
                    )
                ]
            ),
            now_utc=NOW,
        )
        self.assertIsNotNone(candidate)

    def test_no_available_credit_returns_none(self) -> None:
        self.assertIsNone(
            select_nearest_available(
                observation([], available_count=0),
                now_utc=NOW,
            )
        )

    def test_incomplete_inventory_fails_closed(self) -> None:
        with self.assertRaisesRegex(NotifierError, "complete detail"):
            select_nearest_available(
                observation([], available_count=1, has_unlisted=True),
                now_utc=NOW,
            )

    def test_count_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(NotifierError, "does not match"):
            select_nearest_available(
                observation(
                    [credit("opaque", NOW + timedelta(days=2), status="redeemed")],
                    available_count=1,
                ),
                now_utc=NOW,
            )

    def test_wrong_reset_type_fails_closed(self) -> None:
        with self.assertRaisesRegex(NotifierError, "unexpected reset type"):
            select_nearest_available(
                observation(
                    [
                        credit(
                            "opaque",
                            NOW + timedelta(days=2),
                            reset_type="some_other_product",
                        )
                    ]
                ),
                now_utc=NOW,
            )

    def test_expired_available_row_fails_closed(self) -> None:
        with self.assertRaisesRegex(NotifierError, "already-expired"):
            select_nearest_available(
                observation([credit("opaque", NOW - timedelta(seconds=1))]),
                now_utc=NOW,
            )

    def test_read_only_proof_and_environment_identity_are_required(self) -> None:
        future = [credit("opaque", NOW + timedelta(days=2))]
        with self.assertRaisesRegex(NotifierError, "read-only"):
            select_nearest_available(
                observation(future, live_consume_allowed=True),
                now_utc=NOW,
            )
        with self.assertRaisesRegex(NotifierError, "unexpected Codex home"):
            select_nearest_available(
                observation(future, drift=True),
                now_utc=NOW,
            )

    def test_naive_timestamps_are_rejected(self) -> None:
        with self.assertRaisesRegex(NotifierError, "timezone-naive"):
            parse_expiry_utc("2026-07-31T12:00:00")


class NotifierControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = StateStore(Path(self.temp.name))
        self.scheduler = FakeScheduler()
        self.expiry = NOW + timedelta(days=2, hours=3)

    def test_schedules_once_then_is_idempotent(self) -> None:
        report = observation([credit("opaque-a", self.expiry)])
        first = synchronize_notifier(
            report,
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
            language="ru",
        )
        second = synchronize_notifier(
            report,
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW + timedelta(days=1),
            language="ru",
        )

        self.assertEqual(first.action, "scheduled")
        self.assertEqual(second.action, "unchanged")
        self.assertEqual(len(self.scheduler.registered), 1)
        self.assertEqual(first.notify_at_utc, (self.expiry - timedelta(hours=12)).isoformat().replace("+00:00", "Z"))
        state = self.store.load()
        self.assertEqual(state["scheduled"]["language"], "ru")
        self.assertNotIn("opaque-a", self.store.state_path.read_text(encoding="utf-8"))

    def test_late_discovery_schedules_immediate_grace_not_after_expiry(self) -> None:
        expiry = NOW + timedelta(hours=3)
        plan = synchronize_notifier(
            observation([credit("opaque-a", expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        scheduled_for = parse_expiry_utc(plan.scheduled_for_utc)
        self.assertEqual(
            scheduled_for,
            NOW + timedelta(seconds=NOTICE_START_GRACE_SECONDS),
        )
        self.assertLess(scheduled_for, expiry)

    def test_too_late_refuses_to_schedule(self) -> None:
        expiry = NOW + timedelta(seconds=NOTICE_START_GRACE_SECONDS)
        plan = synchronize_notifier(
            observation([credit("opaque-a", expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        self.assertEqual(plan.action, "too_late")
        self.assertEqual(self.scheduler.registered, [])

    def test_new_nearest_credit_replaces_only_owned_old_task(self) -> None:
        later = observation([credit("opaque-later", NOW + timedelta(days=5))])
        first = synchronize_notifier(
            later,
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        earlier = observation([credit("opaque-earlier", NOW + timedelta(days=3))])
        second = synchronize_notifier(
            earlier,
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW + timedelta(hours=1),
        )

        self.assertEqual(second.action, "scheduled")
        self.assertIn(first.task_name, self.scheduler.deleted)
        self.assertNotEqual(first.task_name, second.task_name)

    def test_no_credit_removes_existing_notice(self) -> None:
        first = synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        result = synchronize_notifier(
            observation([], available_count=0),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW + timedelta(days=1),
        )
        self.assertEqual(result.action, "no_available_credit")
        self.assertIn(first.task_name, self.scheduler.deleted)
        self.assertIsNone(self.store.load()["scheduled"])

    def test_corrupt_state_cannot_delete_an_unrelated_task(self) -> None:
        synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        state = self.store.load()
        state["scheduled"]["taskName"] = "UnrelatedBackupTask"
        self.store.save(state)

        with self.assertRaisesRegex(NotifierError, "outside the notifier namespace"):
            synchronize_notifier(
                observation([], available_count=0),
                store=self.store,
                scheduler=self.scheduler,
                now_utc=NOW + timedelta(days=1),
            )
        self.assertNotIn("UnrelatedBackupTask", self.scheduler.deleted)

    def test_records_only_a_sanitized_error_code(self) -> None:
        record_notifier_error(
            self.store,
            error_code="AppServerObservationError",
            now_utc=NOW,
        )
        state = self.store.load()
        self.assertEqual(state["lastCheckResult"], "error")
        self.assertEqual(state["lastError"], "AppServerObservationError")

    def test_dry_run_never_registers_or_writes_state(self) -> None:
        plan = synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
            dry_run=True,
        )
        self.assertEqual(plan.action, "would_schedule")
        self.assertEqual(self.scheduler.registered, [])
        self.assertFalse(self.store.state_path.exists())

    def test_modal_is_claimed_once_and_requires_explicit_display_return(self) -> None:
        plan = synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
            language="ru",
        )
        calls: list[tuple[str, str]] = []

        result = display_scheduled_notice(
            store=self.store,
            fingerprint=plan.fingerprint,
            expires_at_utc=self.expiry,
            language="ru",
            task_prefix="CodexResetCreditNotifier",
            now_utc=NOW + timedelta(days=1, hours=3),
            display=lambda title, message: calls.append((title, message)),
        )
        second = display_scheduled_notice(
            store=self.store,
            fingerprint=plan.fingerprint,
            expires_at_utc=self.expiry,
            language="ru",
            task_prefix="CodexResetCreditNotifier",
            now_utc=NOW + timedelta(days=1, hours=4),
            display=lambda title, message: calls.append((title, message)),
        )

        self.assertEqual(result, "notified")
        self.assertIn(second, {"stale", "already_notified"})
        self.assertEqual(len(calls), 1)
        self.assertIn("Нажмите OK", calls[0][1])
        self.assertIn(self.expiry.strftime("%Y-%m-%d"), calls[0][1])
        self.assertNotIn("opaque", calls[0][1])
        self.assertEqual(self.store.load()["lastNotified"]["status"], "closed")

    def test_expired_notice_does_not_display(self) -> None:
        plan = synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        calls: list[str] = []
        result = display_scheduled_notice(
            store=self.store,
            fingerprint=plan.fingerprint,
            expires_at_utc=self.expiry,
            language="en",
            task_prefix="CodexResetCreditNotifier",
            now_utc=self.expiry,
            display=lambda title, message: calls.append(message),
        )
        self.assertEqual(result, "expired")
        self.assertEqual(calls, [])

    def test_sanitized_status_removes_full_fingerprint(self) -> None:
        plan = synchronize_notifier(
            observation([credit("opaque", self.expiry)]),
            store=self.store,
            scheduler=self.scheduler,
            now_utc=NOW,
        )
        status = sanitized_notifier_status(self.store)
        self.assertNotIn("fingerprint", status["scheduled"])
        self.assertNotIn(plan.fingerprint, str(status))


class NotifierTaskContractTests(unittest.TestCase):
    def test_one_shot_xml_is_modal_friendly_and_wake_capable(self) -> None:
        run_at = datetime(2026, 7, 31, 7, 55, 17, tzinfo=timezone.utc)
        expiry = run_at + timedelta(hours=12)
        xml = render_notice_task_xml(
            run_at_utc=run_at,
            expires_at_utc=expiry,
            command=Path(r"C:\Python\pythonw.exe"),
            arguments="-m codex_reset_credit_manager notifier-show",
            working_directory=Path(r"C:\Notifier\app"),
            user_id=r"HOST\user",
        )
        self.assertIn('<Task version="1.3"', xml)
        self.assertIn("<LogonType>InteractiveToken</LogonType>", xml)
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", xml)
        self.assertIn("<WakeToRun>true</WakeToRun>", xml)
        self.assertIn("<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>", xml)
        self.assertIn("<DeleteExpiredTaskAfter>PT1H</DeleteExpiredTaskAfter>", xml)
        self.assertIn("pythonw.exe", xml)
        self.assertNotIn("account/rateLimitResetCredit", xml)

    def test_task_name_uses_only_hash_prefix(self) -> None:
        fingerprint = "a" * 64
        name = notice_task_name("CodexResetCreditNotifier", fingerprint)
        self.assertEqual(name, "CodexResetCreditNotifier-Notice-" + "a" * 16)

    def test_python_sources_have_no_reset_redemption_rpc(self) -> None:
        source_root = Path(__file__).parents[1] / "src"
        forbidden = (
            "account/rateLimitResetCredit/" + "consume",
            "/backend-api/wham/rate-limit-reset-credits/" + "consume",
        )
        for path in source_root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            for needle in forbidden:
                self.assertNotIn(needle, content, path)


if __name__ == "__main__":
    unittest.main()
