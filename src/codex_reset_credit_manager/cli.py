from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .app_server import (
    AppServerObservationError,
    observe_app_server_rate_limits,
    parse_codex_binary_command,
)
from .config import AppConfig, load_config
from .models import DoctorFinding, DoctorReport
from .notifier import (
    DEFAULT_LEAD_HOURS,
    DEFAULT_TASK_PREFIX,
    NotifierError,
    PreviewScheduler,
    StateStore,
    WindowsTaskScheduler,
    display_scheduled_notice,
    format_rate_limit_usage_report,
    format_usage_bar,
    format_window_duration,
    parse_expiry_utc,
    plan_as_dict,
    record_notifier_error,
    sanitized_notifier_status,
    show_status_gui,
    synchronize_notifier,
)
from .planner import build_planning_windows, parse_utc_timestamp
from .sanitized_env import diff_environment_names
from .task_preview import render_task_xml


def _doctor(config: AppConfig) -> DoctorReport:
    findings: list[DoctorFinding] = []
    if config.root == config.legacy_install_root:
        findings.append(
            DoctorFinding(
                level="error",
                code="ROOT_COLLISION",
                message="Draft root collides with the legacy install root.",
            )
        )
    else:
        findings.append(
            DoctorFinding(
                level="ok",
                code="ROOT_ISOLATED",
                message="Draft root is isolated from the legacy install root.",
            )
        )
    if config.codex_binary:
        findings.append(
            DoctorFinding(
                level="ok",
                code="CODEX_BINARY_FOUND",
                message=f"Found codex binary at {config.codex_binary}.",
            )
        )
    else:
        findings.append(
            DoctorFinding(
                level="warning",
                code="CODEX_BINARY_MISSING",
                message="No codex binary was found on PATH.",
            )
        )
    if config.legacy_install_root.exists():
        findings.append(
            DoctorFinding(
                level="warning",
                code="LEGACY_INSTALL_PRESENT",
                message=f"Legacy install exists at {config.legacy_install_root}.",
            )
        )
    else:
        findings.append(
            DoctorFinding(
                level="ok",
                code="LEGACY_INSTALL_ABSENT",
                message="No legacy install path was found.",
            )
        )
    return DoctorReport(
        root=config.root,
        legacy_install_root=config.legacy_install_root,
        codex_binary=config.codex_binary,
        findings=tuple(findings),
    )


def _json_default(value: object) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _print_json(payload: object) -> int:
    sys.stdout.write(json.dumps(payload, indent=2, default=_json_default))
    sys.stdout.write("\n")
    return 0


def _add_observation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-live-read",
        action="store_true",
        help="explicit opt-in flag required for the live read-only observation",
    )
    parser.add_argument(
        "--codex-binary",
        help="override path to codex binary or app-server stub",
    )
    parser.add_argument(
        "--account-codex-home",
        type=Path,
        help="existing signed-in Codex home; the manager does not parse its files",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-reset-credit-manager")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", type=Path, help="override the isolated draft root")

    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="check isolation and local prerequisites")
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    env_preview = commands.add_parser("env-preview", help="show kept vs stripped environment names")
    env_preview.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    plan = commands.add_parser("plan", help="compute read-only planning checkpoints")
    plan.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    plan.add_argument("--expires-at", required=True, help="UTC timestamp, for example 2026-08-02T12:00:00Z")
    plan.add_argument("--warmup-seconds", type=int, default=180)
    plan.add_argument("--validation-seconds", type=int, default=60)
    plan.add_argument("--dispatch-seconds", type=int, default=20)

    preview = commands.add_parser("preview-task", help="emit Scheduled Task XML without installing it")
    preview.add_argument("--run-at", required=True, help="UTC timestamp, for example 2026-08-02T11:59:40Z")
    preview.add_argument("--exec-command", required=True)
    preview.add_argument("--arguments", default="")

    dry_run = commands.add_parser("dry-run", help="print the intended read-only workflow")
    dry_run.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    dry_run.add_argument("--expires-at", required=True, help="UTC timestamp, for example 2026-08-02T12:00:00Z")

    observe = commands.add_parser("observe-rate-limits", help="query live codex app-server read-only rate limits")
    _add_observation_arguments(observe)
    observe.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    usage_cmd = commands.add_parser(
        "usage",
        help="display current Codex rate-limit usage, progress bar, and reset countdowns",
    )
    _add_observation_arguments(usage_cmd)
    usage_cmd.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    usage_cmd.add_argument(
        "--language",
        choices=("auto", "en", "ru"),
        default="auto",
        help="output language (default: auto)",
    )

    gui_cmd = commands.add_parser(
        "gui",
        help="open the interactive desktop status monitor for usage and reset credits",
    )
    _add_observation_arguments(gui_cmd)
    gui_cmd.add_argument(
        "--language",
        choices=("auto", "en", "ru"),
        default="auto",
        help="UI language (default: auto)",
    )

    notifier_sync = commands.add_parser(
        "notifier-sync",
        help="read reset expiries and reconcile one T-12-hour reminder",
    )
    _add_observation_arguments(notifier_sync)
    notifier_sync.add_argument(
        "--lead-hours",
        type=int,
        default=DEFAULT_LEAD_HOURS,
        help="hours before expiry to display the reminder (default: 12)",
    )
    notifier_sync.add_argument(
        "--language",
        choices=("en", "ru"),
        default="en",
        help="modal reminder language",
    )
    notifier_sync.add_argument(
        "--task-prefix",
        default=DEFAULT_TASK_PREFIX,
        help=argparse.SUPPRESS,
    )
    notifier_sync.add_argument(
        "--dry-run",
        action="store_true",
        help="perform the read but do not create, replace, or delete tasks",
    )
    notifier_sync.add_argument("--json", action="store_true")

    notifier_status = commands.add_parser(
        "notifier-status",
        help="show sanitized daily reminder state",
    )
    notifier_status.add_argument("--json", action="store_true")

    notifier_show = commands.add_parser(
        "notifier-show",
        help=argparse.SUPPRESS,
    )
    notifier_show.add_argument("--fingerprint", required=True)
    notifier_show.add_argument("--expires-at", required=True)
    notifier_show.add_argument("--language", choices=("en", "ru"), required=True)
    notifier_show.add_argument("--task-prefix", default=DEFAULT_TASK_PREFIX)
    return parser


def _observe(
    config: AppConfig,
    codex_binary: str | None,
    account_codex_home: Path | None,
):
    cmd_override = None
    if codex_binary:
        cmd_override = parse_codex_binary_command(codex_binary)
    return observe_app_server_rate_limits(
        config,
        command_override=cmd_override,
        codex_home_override=account_codex_home,
    )


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.root)

    if args.command == "doctor":
        report = _doctor(config)
        if args.json:
            return _print_json(asdict(report))
        for finding in report.findings:
            print(f"[{finding.level.upper()}] {finding.code}: {finding.message}")
        print(f"Draft root: {report.root}")
        print(f"Legacy root: {report.legacy_install_root}")
        return 0

    if args.command == "env-preview":
        kept, stripped = diff_environment_names(
            isolated_codex_home=config.child_codex_home,
        )
        payload = {
            "draftRoot": str(config.root),
            "childCodexHome": str(config.child_codex_home),
            "kept": kept,
            "stripped": stripped,
        }
        if args.json:
            return _print_json(payload)
        print("Kept variables:")
        for name in kept:
            print(f"  {name}")
        print("Stripped variables:")
        for name in stripped:
            print(f"  {name}")
        return 0

    if args.command == "plan":
        windows = build_planning_windows(
            parse_utc_timestamp(args.expires_at),
            warmup_seconds=args.warmup_seconds,
            validation_seconds=args.validation_seconds,
            dispatch_seconds=args.dispatch_seconds,
        )
        payload = asdict(windows)
        if args.json:
            return _print_json(payload)
        print(f"Expiry:      {windows.expires_at_utc.isoformat()}")
        print(f"Warmup:      {windows.warmup_at_utc.isoformat()}")
        print(f"Validation:  {windows.validation_at_utc.isoformat()}")
        print(f"Dispatch:    {windows.dispatch_at_utc.isoformat()}")
        return 0

    if args.command == "preview-task":
        sys.stdout.write(
            render_task_xml(
                run_at_utc=parse_utc_timestamp(args.run_at),
                command=args.exec_command,
                arguments=args.arguments,
            )
        )
        return 0

    if args.command == "dry-run":
        windows = build_planning_windows(parse_utc_timestamp(args.expires_at))
        payload = {
            "mode": "read-only",
            "legacyInstallTouched": False,
            "liveConsumeAllowed": False,
            "plannedCheckpoints": asdict(windows),
            "nextSteps": [
                "resolve isolated root",
                "build sanitized child environment",
                "query official read-only interfaces in a future milestone",
                "stop before any live mutation path",
            ],
        }
        if args.json:
            return _print_json(payload)
        print("Dry run mode: read-only")
        print(f"Legacy install touched: {payload['legacyInstallTouched']}")
        print(f"Live consume allowed:  {payload['liveConsumeAllowed']}")
        print("Planned checkpoints:")
        for name, value in payload["plannedCheckpoints"].items():
            print(f"  {name}: {value.isoformat()}")
        print("Next steps:")
        for step in payload["nextSteps"]:
            print(f"  - {step}")
        return 0

    if args.command == "observe-rate-limits":
        if not args.allow_live_read:
            sys.stderr.write("Error: Live observation requires explicit opt-in. Re-run with --allow-live-read.\n")
            return 1
        try:
            report = _observe(config, args.codex_binary, args.account_codex_home)
        except AppServerObservationError as exc:
            sys.stderr.write(f"Observation failed: {exc}\n")
            return 1

        if args.json:
            return _print_json(asdict(report))

        print("Phase 1 App-Server Read-Only Observation:")
        print(f"  Mode:                {report.mode}")
        print(f"  Live Read Allowed:   {report.live_read_allowed}")
        print(f"  User Agent:          {report.handshake.user_agent or 'unknown'}")
        print(f"  Codex Home:          {report.handshake.codex_home or 'unknown'}")
        print(f"  CODEX_HOME Match:    {report.handshake.codex_home_matches_expected}")
        print(f"  Account Auth Req:    {report.account.requires_openai_auth}")
        print(f"  Account Email:       {report.account.email_masked or 'none/hidden'}")
        print(f"  Account Plan:        {report.account.plan_type or 'unknown'}")

        if report.rate_limits.usage is not None:
            print("  Usage & Quota:")
            for line in format_rate_limit_usage_report(report.rate_limits.usage, language="en"):
                print(f"    {line}")

        print(f"  Available Credits:   {report.rate_limits.available_count if report.rate_limits.available_count is not None else 'unknown'}")
        print(f"  Detail Rows Count:   {report.rate_limits.detail_count}")
        print(f"  Unlisted Credits:    {report.rate_limits.has_unlisted_credits}")

        if report.rate_limits.credits:
            print("  Credit Details:")
            for credit in report.rate_limits.credits:
                print(
                    f"    - ID: {credit.id or 'unknown'} | "
                    f"Expires: {credit.expires_at or 'unknown'} | "
                    f"Reset: {credit.reset_type or 'unknown'} | "
                    f"Status: {credit.status or 'unknown'}"
                )
        else:
            print("  Credit Details:      none listed")
        return 0

    if args.command == "usage":
        if not args.allow_live_read:
            sys.stderr.write(
                "Error: Usage inspection requires explicit opt-in. Re-run with --allow-live-read.\n"
            )
            return 1
        try:
            report = _observe(config, args.codex_binary, args.account_codex_home)
        except AppServerObservationError as exc:
            sys.stderr.write(f"Usage observation failed: {exc}\n")
            return 1

        if args.json:
            usage_dict = asdict(report.rate_limits.usage) if report.rate_limits.usage else {}
            return _print_json(usage_dict)

        lang = "ru" if (args.language == "ru" or (args.language == "auto" and "ru" in (os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")).lower())) else "en"
        if args.language in {"en", "ru"}:
            lang = args.language

        if report.rate_limits.usage is not None:
            for line in format_rate_limit_usage_report(report.rate_limits.usage, language=lang):
                print(line)
        else:
            print("No rate limit usage data reported." if lang != "ru" else "Данные об использовании не получены.")

        avail = report.rate_limits.available_count
        if avail is not None:
            if lang == "ru":
                print(f"Доступно сбросов лимитов: {avail}")
            else:
                print(f"Available reset credits: {avail}")
        return 0

    if args.command == "gui":
        if not args.allow_live_read:
            sys.stderr.write(
                "Error: Desktop monitor requires explicit opt-in. Re-run with --allow-live-read.\n"
            )
            return 1

        def _fetch() -> Any:
            return _observe(config, args.codex_binary, args.account_codex_home)

        try:
            show_status_gui(
                _fetch,
                language=args.language,
                store=StateStore(config.root),
            )
        except Exception as exc:
            sys.stderr.write(f"GUI launch failed: {exc}\n")
            return 1
        return 0

    if args.command == "notifier-sync":
        if not args.allow_live_read:
            sys.stderr.write(
                "Error: Notifier sync requires explicit read-only opt-in. "
                "Re-run with --allow-live-read.\n"
            )
            return 1
        try:
            report = _observe(config, args.codex_binary, args.account_codex_home)
            scheduler = PreviewScheduler() if args.dry_run else WindowsTaskScheduler()
            notification_plan = synchronize_notifier(
                report,
                store=StateStore(config.root),
                scheduler=scheduler,
                now_utc=datetime.now(timezone.utc),
                lead_hours=args.lead_hours,
                language=args.language,
                task_prefix=args.task_prefix,
                dry_run=args.dry_run,
            )
        except (AppServerObservationError, NotifierError) as exc:
            try:
                record_notifier_error(
                    StateStore(config.root),
                    error_code=type(exc).__name__,
                    now_utc=datetime.now(timezone.utc),
                )
            except NotifierError:
                pass
            sys.stderr.write(f"Notifier sync failed: {exc}\n")
            return 1

        payload = plan_as_dict(notification_plan)
        if args.json:
            return _print_json(payload)
        print(f"Notifier action: {notification_plan.action}")
        if notification_plan.expires_at_utc:
            print(f"Expiry UTC:      {notification_plan.expires_at_utc}")
        if notification_plan.notify_at_utc:
            print(f"Reminder target: {notification_plan.notify_at_utc}")
        if notification_plan.scheduled_for_utc:
            print(f"Task run UTC:    {notification_plan.scheduled_for_utc}")
        if notification_plan.task_name:
            print(f"Task name:       {notification_plan.task_name}")
        return 0

    if args.command == "notifier-status":
        try:
            payload = sanitized_notifier_status(StateStore(config.root))
        except NotifierError as exc:
            sys.stderr.write(f"Notifier status failed: {exc}\n")
            return 1
        if args.json:
            return _print_json(payload)
        print(f"Last check:       {payload['lastCheckAtUtc'] or 'never'}")
        print(f"Last result:      {payload['lastCheckResult'] or 'none'}")
        last_usage = payload.get("lastUsage")
        if isinstance(last_usage, dict):
            primary = last_usage.get("primary")
            if isinstance(primary, dict):
                p_pct = primary.get("usedPercent")
                p_mins = primary.get("windowDurationMins")
                p_res = primary.get("resetsAtUtc")
                bar = format_usage_bar(p_pct)
                dur = format_window_duration(p_mins)
                print(f"Last usage ({dur}): {bar} (resets: {p_res or 'n/a'})")
        scheduled = payload.get("scheduled")
        if isinstance(scheduled, dict):
            print(f"Scheduled expiry: {scheduled['expiresAtUtc']}")
            print(f"Reminder time:    {scheduled['scheduledForUtc']}")
            print(f"Task name:        {scheduled['taskName']}")
        else:
            print("Scheduled notice: none")
        return 0

    if args.command == "notifier-show":
        try:
            result = display_scheduled_notice(
                store=StateStore(config.root),
                fingerprint=args.fingerprint,
                expires_at_utc=parse_expiry_utc(args.expires_at),
                language=args.language,
                task_prefix=args.task_prefix,
                now_utc=datetime.now(timezone.utc),
            )
        except NotifierError as exc:
            sys.stderr.write(f"Notifier display failed: {exc}\n")
            return 1
        return 0 if result in {"notified", "stale", "already_notified", "expired"} else 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
