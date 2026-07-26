import unittest

from codex_reset_credit_manager.planner import build_planning_windows, parse_utc_timestamp


class PlannerTests(unittest.TestCase):
    def test_build_planning_windows_orders_checkpoints(self) -> None:
        expires = parse_utc_timestamp("2026-08-02T12:00:00Z")
        windows = build_planning_windows(
            expires,
            warmup_seconds=180,
            validation_seconds=60,
            dispatch_seconds=20,
        )

        self.assertLess(windows.warmup_at_utc, windows.validation_at_utc)
        self.assertLess(windows.validation_at_utc, windows.dispatch_at_utc)
        self.assertLess(windows.dispatch_at_utc, windows.expires_at_utc)

    def test_parse_utc_timestamp_requires_timezone(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            parse_utc_timestamp("2026-08-02T12:00:00")
