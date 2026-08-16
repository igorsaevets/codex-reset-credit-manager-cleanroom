from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from codex_reset_credit_manager.notifier import StateStore
from codex_reset_credit_manager.updater import (
    UpdateCheckResult,
    check_for_updates,
    is_newer_version,
    parse_version_tuple,
)


class TestUpdater(unittest.TestCase):
    def test_parse_version_tuple(self) -> None:
        self.assertEqual(parse_version_tuple("0.3.1"), (0, 3, 1))
        self.assertEqual(parse_version_tuple("v0.3.2"), (0, 3, 2))
        self.assertEqual(parse_version_tuple("V1.0"), (1, 0, 0))
        self.assertEqual(parse_version_tuple("2"), (2, 0, 0))
        self.assertEqual(parse_version_tuple("2.6.0-beta"), (2, 6, 0))

    def test_is_newer_version(self) -> None:
        self.assertTrue(is_newer_version("0.3.2", "0.3.1"))
        self.assertTrue(is_newer_version("v1.0.0", "0.9.9"))
        self.assertTrue(is_newer_version("0.4.0", "0.3.9"))
        self.assertFalse(is_newer_version("0.3.1", "0.3.1"))
        self.assertFalse(is_newer_version("0.3.0", "0.3.1"))
        self.assertFalse(is_newer_version("0.2.9", "0.3.0"))

    @patch("codex_reset_credit_manager.updater.fetch_latest_release")
    def test_check_for_updates_new_version_available(self, mock_fetch) -> None:
        mock_fetch.return_value = {
            "tag_name": "v0.4.0",
            "html_url": "https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom/releases/tag/v0.4.0",
            "name": "Release v0.4.0",
            "body": "New features and improvements",
        }
        res = check_for_updates(current_version="0.3.1", force=True)
        self.assertTrue(res.is_update_available)
        self.assertEqual(res.latest_version, "0.4.0")
        self.assertEqual(res.current_version, "0.3.1")
        self.assertIn("v0.4.0", res.release_url)
        self.assertFalse(res.skipped_due_to_throttle)
        self.assertIsNone(res.error)

    @patch("codex_reset_credit_manager.updater.fetch_latest_release")
    def test_check_for_updates_already_latest(self, mock_fetch) -> None:
        mock_fetch.return_value = {
            "tag_name": "v0.3.1",
            "html_url": "https://github.com/igorsaevets/codex-reset-credit-manager-cleanroom/releases/tag/v0.3.1",
            "name": "Release v0.3.1",
            "body": "Current release",
        }
        res = check_for_updates(current_version="0.3.1", force=True)
        self.assertFalse(res.is_update_available)
        self.assertEqual(res.latest_version, "0.3.1")

    @patch("codex_reset_credit_manager.updater.fetch_latest_release")
    def test_check_for_updates_throttling_30_days(self, mock_fetch) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(Path(tmpdir) / "state.json")
            now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)

            # First run: should call fetch_latest_release
            mock_fetch.return_value = {"tag_name": "v0.3.1"}
            res1 = check_for_updates(store=store, current_version="0.3.1", now_utc=now, force=False)
            self.assertFalse(res1.skipped_due_to_throttle)
            self.assertEqual(mock_fetch.call_count, 1)

            # Second run 5 days later: should be throttled
            five_days_later = now + timedelta(days=5)
            res2 = check_for_updates(store=store, current_version="0.3.1", now_utc=five_days_later, force=False)
            self.assertTrue(res2.skipped_due_to_throttle)
            self.assertEqual(mock_fetch.call_count, 1)  # not called again!

            # Third run 31 days later: should execute
            thirty_one_days_later = now + timedelta(days=31)
            mock_fetch.return_value = {"tag_name": "v0.4.0"}
            res3 = check_for_updates(store=store, current_version="0.3.1", now_utc=thirty_one_days_later, force=False)
            self.assertFalse(res3.skipped_due_to_throttle)
            self.assertTrue(res3.is_update_available)
            self.assertEqual(mock_fetch.call_count, 2)

    @patch("codex_reset_credit_manager.updater.fetch_latest_release")
    def test_check_for_updates_offline_fail_soft(self, mock_fetch) -> None:
        mock_fetch.side_effect = TimeoutError("Connection timed out")
        res = check_for_updates(current_version="0.3.1", force=True)
        self.assertFalse(res.is_update_available)
        self.assertIsNotNone(res.error)
        self.assertIn("Connection timed out", str(res.error))


if __name__ == "__main__":
    unittest.main()
