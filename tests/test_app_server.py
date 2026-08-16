import json
import sys
import tempfile
import unittest
from pathlib import Path

from codex_reset_credit_manager.app_server import (
    AppServerObservationError,
    mask_email,
    observe_app_server_rate_limits,
    parse_codex_binary_command,
    parse_flexible_timestamp,
    parse_rate_limit_usage,
)
from codex_reset_credit_manager.cli import main
from codex_reset_credit_manager.config import AppConfig


class AppServerReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_script = str(Path(__file__).parent / "fake_app_server.py")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.draft_root = Path(self.temp.name) / "DraftRoot"
        self.child_codex_home = self.draft_root / "codex-home"
        self.config = AppConfig(
            root=self.draft_root,
            child_codex_home=self.child_codex_home,
            legacy_install_root=Path(r"C:\LegacyRoot"),
            codex_binary=None,
        )

    def test_mask_email(self) -> None:
        self.assertEqual(mask_email("guard.test@example.com"), "g***@example.com")
        self.assertEqual(mask_email("a@b.com"), "a***@b.com")
        self.assertIsNone(mask_email(None))
        self.assertEqual(mask_email("invalid_email"), "***")

    def test_parse_flexible_timestamp(self) -> None:
        # Seconds int
        parsed_sec = parse_flexible_timestamp(1754136000)
        self.assertIn("2025-08-02", parsed_sec)

        # Milliseconds int
        parsed_ms = parse_flexible_timestamp(1754136000000)
        self.assertIn("2025-08-02", parsed_ms)

        # String integer
        parsed_str_int = parse_flexible_timestamp("1754136000")
        self.assertIn("2025-08-02", parsed_str_int)

        # ISO string
        parsed_iso = parse_flexible_timestamp("2026-08-02T12:00:00Z")
        self.assertEqual(parsed_iso, "2026-08-02T12:00:00+00:00")

        # None
        self.assertIsNone(parse_flexible_timestamp(None))

    def test_normal_observation(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "normal",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertEqual(report.mode, "read-only")
        self.assertTrue(report.live_read_allowed)
        self.assertFalse(report.environment_drift_detected)
        self.assertTrue(report.handshake.codex_home_matches_expected)
        self.assertEqual(report.account.email_masked, "g***@example.com")
        self.assertEqual(report.account.plan_type, "plus")
        self.assertEqual(report.rate_limits.available_count, 1)
        self.assertEqual(report.rate_limits.detail_count, 1)
        self.assertFalse(report.rate_limits.has_unlisted_credits)
        self.assertEqual(report.rate_limits.credits[0].id, "credit_default")
        self.assertTrue(self.child_codex_home.is_dir())
        self.assertTrue((self.child_codex_home / "sqlite").is_dir())

    def test_existing_signed_in_home_override_is_used_without_copying_it(self) -> None:
        signed_in_home = self.draft_root / "signed-in-codex-home"
        signed_in_home.mkdir(parents=True)
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "normal",
            "--codex-home",
            str(signed_in_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
            codex_home_override=signed_in_home,
        )

        self.assertTrue(report.handshake.codex_home_matches_expected)
        self.assertEqual(
            Path(report.handshake.codex_home).resolve(),
            signed_in_home.resolve(),
        )
        self.assertFalse(self.child_codex_home.exists())

    def test_null_credits_object(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "null_credits",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertIsNone(report.rate_limits.available_count)
        self.assertEqual(report.rate_limits.detail_count, 0)
        self.assertFalse(report.rate_limits.has_unlisted_credits)
        self.assertEqual(len(report.rate_limits.credits), 0)

    def test_null_credits_list(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "null_credits_list",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertEqual(report.rate_limits.available_count, 2)
        self.assertEqual(report.rate_limits.detail_count, 0)
        self.assertTrue(report.rate_limits.has_unlisted_credits)
        self.assertEqual(len(report.rate_limits.credits), 0)

    def test_unlisted_credits_count(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "unlisted_credits",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertEqual(report.rate_limits.available_count, 3)
        self.assertEqual(report.rate_limits.detail_count, 1)
        self.assertTrue(report.rate_limits.has_unlisted_credits)

    def test_timestamp_variations(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "timestamp_string_and_iso",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertEqual(report.rate_limits.detail_count, 2)
        self.assertIn("2025-08-02", report.rate_limits.credits[0].expires_at)
        self.assertEqual(report.rate_limits.credits[1].expires_at, "2026-08-02T12:00:00+00:00")

    def test_environment_drift_detection(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "normal",
            "--codex-home",
            r"C:\OtherPath\codex-home",
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )

        self.assertTrue(report.environment_drift_detected)
        self.assertFalse(report.handshake.codex_home_matches_expected)

    def test_rpc_error_fails_closed(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "rpc_error",
        ]
        with self.assertRaises(AppServerObservationError):
            observe_app_server_rate_limits(
                self.config,
                command_override=cmd_override,
            )

    def test_server_crash_fails_closed(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "crash",
        ]
        with self.assertRaises(AppServerObservationError):
            observe_app_server_rate_limits(
                self.config,
                command_override=cmd_override,
            )

    def test_cli_requires_opt_in_flag(self) -> None:
        exit_code = main(["observe-rate-limits"])
        self.assertEqual(exit_code, 1)

    def test_cli_live_observation_with_fake_server(self) -> None:
        binary_arg = f'"{sys.executable}" "{self.fake_script}" --mode normal --codex-home "{self.child_codex_home}"'
        exit_code = main(
            [
                "--root",
                str(self.draft_root),
                "observe-rate-limits",
                "--allow-live-read",
                "--json",
                "--codex-binary",
                binary_arg,
            ]
        )
        self.assertEqual(exit_code, 0)

    def test_timeout_fails_closed(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "hang",
        ]
        with self.assertRaises(AppServerObservationError) as ctx:
            observe_app_server_rate_limits(
                self.config,
                command_override=cmd_override,
                timeout=0.2,
            )
        self.assertIn("Timeout", str(ctx.exception))

    def test_large_stderr_does_not_deadlock(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "noisy_stderr",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
            timeout=5.0,
        )
        self.assertEqual(report.mode, "read-only")
        self.assertEqual(report.rate_limits.available_count, 1)

    def test_parse_codex_binary_command(self) -> None:
        self.assertEqual(
            parse_codex_binary_command("codex"),
            ["codex", "app-server", "--stdio"],
        )
        self.assertEqual(
            parse_codex_binary_command(r'"C:\Program Files\Codex\codex.exe"'),
            [r"C:\Program Files\Codex\codex.exe", "app-server", "--stdio"],
        )
        self.assertEqual(
            parse_codex_binary_command(f'"{sys.executable}" "{self.fake_script}" --mode normal'),
            [sys.executable, self.fake_script, "--mode", "normal"],
        )

    def test_parse_rate_limit_usage(self) -> None:
        raw = {
            "limitId": "codex",
            "planType": "team",
            "primary": {
                "usedPercent": 42.5,
                "windowDurationMins": 10080,
                "resetsAt": 1754136000,
            },
            "secondary": {
                "usedPercent": 5,
                "windowDurationMins": 300,
                "resetsAt": "2026-08-02T12:00:00Z",
            },
            "credits": {
                "hasCredits": True,
                "unlimited": False,
                "balance": 100.0,
            },
            "spendControlReached": True,
            "rateLimitReachedType": "spend_limit",
        }
        usage = parse_rate_limit_usage(raw)
        self.assertIsNotNone(usage)
        self.assertEqual(usage.limit_id, "codex")
        self.assertEqual(usage.plan_type, "team")
        self.assertIsNotNone(usage.primary)
        self.assertEqual(usage.primary.used_percent, 42.5)
        self.assertEqual(usage.primary.window_duration_mins, 10080)
        self.assertEqual(usage.primary.resets_at_epoch, 1754136000)
        self.assertIsNotNone(usage.secondary)
        self.assertEqual(usage.secondary.used_percent, 5.0)
        self.assertEqual(usage.secondary.window_duration_mins, 300)
        self.assertTrue(usage.spend_control_reached)
        self.assertEqual(usage.rate_limit_reached_type, "spend_limit")
        self.assertIsNotNone(usage.credits)
        self.assertTrue(usage.credits.has_credits)
        self.assertFalse(usage.credits.unlimited)
        self.assertEqual(usage.credits.balance, 100.0)

    def test_normal_observation_parses_usage(self) -> None:
        cmd_override = [
            sys.executable,
            self.fake_script,
            "--mode",
            "normal",
            "--codex-home",
            str(self.child_codex_home),
        ]
        report = observe_app_server_rate_limits(
            self.config,
            command_override=cmd_override,
        )
        self.assertIsNotNone(report.rate_limits.usage)
        self.assertEqual(report.rate_limits.usage.plan_type, "plus")
        self.assertIsNotNone(report.rate_limits.usage.primary)
        self.assertEqual(report.rate_limits.usage.primary.used_percent, 25.0)
        self.assertEqual(report.rate_limits.usage.primary.window_duration_mins, 10080)
        self.assertIsNotNone(report.rate_limits.usage.secondary)
        self.assertEqual(report.rate_limits.usage.secondary.used_percent, 15.0)

    def test_cli_usage_command(self) -> None:
        binary_arg = f'"{sys.executable}" "{self.fake_script}" --mode normal --codex-home "{self.child_codex_home}"'
        exit_code = main(
            [
                "--root",
                str(self.draft_root),
                "usage",
                "--allow-live-read",
                "--json",
                "--codex-binary",
                binary_arg,
            ]
        )
        self.assertEqual(exit_code, 0)


