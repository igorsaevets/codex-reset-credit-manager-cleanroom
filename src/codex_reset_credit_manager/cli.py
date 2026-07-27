from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .app_server import (
    AppServerObservationError,
    observe_app_server_rate_limits,
    parse_codex_binary_command,
)
from .config import AppConfig, load_config
from .models import DoctorFinding, DoctorReport
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
    observe.add_argument("--allow-live-read", action="store_true", help="explicit opt-in flag required for live read-only observation")
    observe.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    observe.add_argument("--codex-binary", help="override path to codex binary or app-server stub")
    return parser


def main(argv: list[str] | None = None) -> int:
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
            cmd_override = None
            if args.codex_binary:
                cmd_override = parse_codex_binary_command(args.codex_binary)
            report = observe_app_server_rate_limits(config, command_override=cmd_override)
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
        print(f"  Available Credits:   {report.rate_limits.available_count if report.rate_limits.available_count is not None else 'unknown'}")
        print(f"  Detail Rows Count:   {report.rate_limits.detail_count}")
        print(f"  Unlisted Credits:    {report.rate_limits.has_unlisted_credits}")

        if report.rate_limits.credits:
            print("  Credit Details:")
            for c in report.rate_limits.credits:
                print(f"    - ID: {c.id or 'unknown'} | Expires: {c.expires_at or 'unknown'} | Reset: {c.reset_type or 'unknown'} | Status: {c.status or 'unknown'}")
        else:
            print("  Credit Details:      none listed")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
