from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import webbrowser
import contextlib
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html import escape as xml_escape
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from . import __version__
from .models import CreditDetail, ObservationReport, RateLimitUsage, UsageWindowInfo


APP_ICON_PNG_64_BASE64 = """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"""

STATE_SCHEMA_VERSION = 2
SUPPORTED_STATE_SCHEMA_VERSIONS = {1, 2}
DEFAULT_LEAD_HOURS = 12
DEFAULT_TASK_PREFIX = "CodexResetCreditNotifier"
NOTICE_START_GRACE_SECONDS = 15
_TASK_PREFIX_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class NotifierError(Exception):
    """Raised when the read-only notifier cannot make a safe decision."""


@dataclass(frozen=True)
class NotificationCandidate:
    fingerprint: str
    expires_at_utc: datetime
    notify_at_utc: datetime


@dataclass(frozen=True)
class NotificationPlan:
    action: str
    fingerprint: str | None
    expires_at_utc: str | None
    notify_at_utc: str | None
    scheduled_for_utc: str | None
    task_name: str | None


class NoticeScheduler(Protocol):
    def task_exists(self, task_name: str) -> bool: ...

    def register_notice(
        self,
        *,
        task_name: str,
        run_at_utc: datetime,
        expires_at_utc: datetime,
        fingerprint: str,
        state_root: Path,
        language: str,
        task_prefix: str,
    ) -> None: ...

    def delete_notice(self, task_name: str) -> None: ...


class PreviewScheduler:
    """Non-mutating scheduler used by previews and cross-platform tests."""

    def task_exists(self, task_name: str) -> bool:
        return False

    def register_notice(self, **kwargs: Any) -> None:
        raise AssertionError("Preview mode must not register a task.")

    def delete_notice(self, task_name: str) -> None:
        raise AssertionError("Preview mode must not delete a task.")


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise NotifierError("A timezone-aware datetime is required.")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_expiry_utc(value: str | None) -> datetime:
    if not value or not isinstance(value, str):
        raise NotifierError("An available reset is missing expiresAt.")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise NotifierError("An available reset has an invalid expiresAt.") from exc
    if parsed.tzinfo is None:
        raise NotifierError("An available reset has a timezone-naive expiresAt.")
    return parsed.astimezone(timezone.utc)


def _candidate_from_credit(
    credit: CreditDetail,
    *,
    lead_hours: int,
) -> NotificationCandidate:
    if not credit.id or not isinstance(credit.id, str):
        raise NotifierError("An available reset is missing its opaque ID.")
    normalized_type = re.sub(r"[^a-z0-9]", "", (credit.reset_type or "").lower())
    if normalized_type != "codexratelimits":
        raise NotifierError("An available reset has an unexpected reset type.")
    expires_at = parse_expiry_utc(credit.expires_at)
    digest_input = f"{credit.id}\0{_utc_iso(expires_at)}".encode("utf-8")
    fingerprint = hashlib.sha256(digest_input).hexdigest()
    return NotificationCandidate(
        fingerprint=fingerprint,
        expires_at_utc=expires_at,
        notify_at_utc=expires_at - timedelta(hours=lead_hours),
    )


def select_nearest_available(
    report: ObservationReport,
    *,
    now_utc: datetime,
    lead_hours: int = DEFAULT_LEAD_HOURS,
) -> NotificationCandidate | None:
    """Select the earliest complete Codex reset without exposing its raw ID."""
    if now_utc.tzinfo is None:
        raise NotifierError("now_utc must be timezone-aware.")
    if not isinstance(lead_hours, int) or not 1 <= lead_hours <= 168:
        raise NotifierError("lead_hours must be an integer from 1 through 168.")
    if report.mode != "read-only" or report.live_consume_allowed:
        raise NotifierError("Observation did not prove read-only mode.")
    if report.environment_drift_detected:
        raise NotifierError("Codex app-server reported an unexpected Codex home.")

    info = report.rate_limits
    if info.has_unlisted_credits:
        raise NotifierError("The server reports available resets without complete detail rows.")
    if type(info.available_count) is not int or info.available_count < 0:
        raise NotifierError("The server did not report a trustworthy available reset count.")

    available_rows = [
        credit
        for credit in info.credits
        if (credit.status or "").strip().lower() == "available"
    ]
    if len(available_rows) != info.available_count:
        raise NotifierError("The available reset count does not match the detailed inventory.")
    if not available_rows:
        return None

    candidates = [
        _candidate_from_credit(credit, lead_hours=lead_hours)
        for credit in available_rows
    ]
    future = [item for item in candidates if item.expires_at_utc > now_utc]
    if len(future) != len(candidates):
        raise NotifierError("The server marked an already-expired reset as available.")
    return min(future, key=lambda item: item.expires_at_utc)


def _default_state() -> dict[str, Any]:
    return {
        "schemaVersion": STATE_SCHEMA_VERSION,
        "lastCheckAtUtc": None,
        "lastCheckResult": None,
        "scheduled": None,
        "lastNotified": None,
        "lastError": None,
        "lastUsage": None,
        "lastUpdateCheckAtUtc": None,
        "lastKnownLatestVersion": None,
    }


def _validate_state(value: Mapping[str, Any]) -> None:
    schema_ver = value.get("schemaVersion")
    if schema_ver not in SUPPORTED_STATE_SCHEMA_VERSIONS:
        raise NotifierError(f"Notifier state schema version {schema_ver} is unsupported.")

    base_required = {
        "schemaVersion",
        "lastCheckAtUtc",
        "lastCheckResult",
        "scheduled",
        "lastNotified",
        "lastError",
    }
    allowed_keys = base_required | {"lastUsage", "lastUpdateCheckAtUtc", "lastKnownLatestVersion"}
    if not base_required.issubset(set(value)) or not set(value).issubset(allowed_keys):
        raise NotifierError("Notifier state has an unexpected shape.")

    scheduled = value.get("scheduled")
    if scheduled is not None:
        required = {
            "fingerprint",
            "expiresAtUtc",
            "notifyAtUtc",
            "scheduledForUtc",
            "taskName",
            "language",
        }
        if not isinstance(scheduled, dict) or set(scheduled) != required:
            raise NotifierError("Scheduled notification state is invalid.")
        fingerprint = scheduled.get("fingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise NotifierError("Scheduled notification fingerprint is invalid.")
        if not isinstance(scheduled.get("taskName"), str):
            raise NotifierError("Scheduled notification task name is invalid.")
        if scheduled.get("language") not in {"en", "ru"}:
            raise NotifierError("Scheduled notification language is invalid.")
        for field in ("expiresAtUtc", "notifyAtUtc", "scheduledForUtc"):
            timestamp = scheduled.get(field)
            if not isinstance(timestamp, str):
                raise NotifierError("Scheduled notification timestamp is invalid.")
            parse_expiry_utc(timestamp)

    notified = value.get("lastNotified")
    if notified is not None:
        required = {
            "fingerprint",
            "expiresAtUtc",
            "startedAtUtc",
            "closedAtUtc",
            "status",
        }
        if not isinstance(notified, dict) or set(notified) != required:
            raise NotifierError("Notification receipt state is invalid.")
        fingerprint = notified.get("fingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise NotifierError("Notification receipt fingerprint is invalid.")
        if notified.get("status") not in {"displaying", "closed"}:
            raise NotifierError("Notification receipt status is invalid.")
        for field in ("expiresAtUtc", "startedAtUtc"):
            timestamp = notified.get(field)
            if not isinstance(timestamp, str):
                raise NotifierError("Notification receipt timestamp is invalid.")
            parse_expiry_utc(timestamp)
        closed_at = notified.get("closedAtUtc")
        if closed_at is not None:
            if not isinstance(closed_at, str):
                raise NotifierError("Notification close timestamp is invalid.")
            parse_expiry_utc(closed_at)

    last_usage = value.get("lastUsage")
    if last_usage is not None and not isinstance(last_usage, dict):
        raise NotifierError("Notifier lastUsage state must be an object or null.")

    last_update_check = value.get("lastUpdateCheckAtUtc")
    if last_update_check is not None and not isinstance(last_update_check, str):
        raise NotifierError("Notifier lastUpdateCheckAtUtc must be an ISO string or null.")

    last_known_ver = value.get("lastKnownLatestVersion")
    if last_known_ver is not None and not isinstance(last_known_ver, str):
        raise NotifierError("Notifier lastKnownLatestVersion must be a string or null.")


def format_usage_bar(used_percent: float | None, width: int = 20) -> str:
    if used_percent is None:
        return f"[{'░' * width}] ?"
    clamped = max(0.0, min(100.0, float(used_percent)))
    filled_len = int(round((clamped / 100.0) * width))
    bar = "█" * filled_len + "░" * (width - filled_len)
    return f"[{bar}] {clamped:5.1f}%"


def format_window_duration(duration_mins: int | None, language: str = "en") -> str:
    if duration_mins is None:
        return "unknown" if language != "ru" else "неизвестно"
    if duration_mins == 10080:
        return "7 days (weekly)" if language != "ru" else "7 дней (недельное)"
    if duration_mins == 300:
        return "5 hours" if language != "ru" else "5 часов"
    if duration_mins == 60:
        return "1 hour" if language != "ru" else "1 час"

    days, rem = divmod(duration_mins, 1440)
    hours, mins = divmod(rem, 60)
    parts = []
    if language == "ru":
        if days:
            parts.append(_russian_unit(days, "день", "дня", "дней"))
        if hours:
            parts.append(_russian_unit(hours, "час", "часа", "часов"))
        if mins or not parts:
            parts.append(_russian_unit(mins, "минута", "минуты", "минут"))
    else:
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if mins or not parts:
            parts.append(f"{mins} min{'s' if mins != 1 else ''}")
    return " ".join(parts)


def format_usage_time_remaining(
    resets_at_raw: str | int | float | None,
    *,
    now_utc: datetime,
    language: str = "en",
) -> str:
    if resets_at_raw is None:
        return "n/a" if language != "ru" else "н/д"
    try:
        if isinstance(resets_at_raw, (int, float)):
            resets_dt = datetime.fromtimestamp(float(resets_at_raw), tz=timezone.utc)
        else:
            resets_dt = parse_expiry_utc(str(resets_at_raw))
    except Exception:
        return str(resets_at_raw)

    diff_seconds = int((resets_dt.astimezone(timezone.utc) - now_utc.astimezone(timezone.utc)).total_seconds())
    if diff_seconds <= 0:
        return "resets now" if language != "ru" else "сбрасывается сейчас"

    days, rem = divmod(diff_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    if language == "ru":
        parts = []
        if days:
            parts.append(_russian_unit(days, "день", "дня", "дней"))
        if days or hours:
            parts.append(_russian_unit(hours, "час", "часа", "часов"))
        parts.append(_russian_unit(minutes, "минута", "минуты", "минут"))
        return "через " + " ".join(parts)
    else:
        parts = []
        if days:
            parts.append(f"{days}d")
        if days or hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return f"in {' '.join(parts)}"


def _format_local_or_utc(timestamp_str: str | None) -> str:
    if not timestamp_str:
        return "n/a"
    try:
        dt = parse_expiry_utc(timestamp_str)
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return str(timestamp_str)


def sanitize_usage_record(usage: RateLimitUsage, *, now_utc: datetime) -> dict[str, Any]:
    def _win_dict(w: UsageWindowInfo | None) -> dict[str, Any] | None:
        if w is None:
            return None
        return {
            "usedPercent": w.used_percent,
            "windowDurationMins": w.window_duration_mins,
            "resetsAtUtc": w.resets_at_utc,
            "resetsAtEpoch": w.resets_at_epoch,
        }

    credits_dict = None
    if usage.credits is not None:
        credits_dict = {
            "hasCredits": usage.credits.has_credits,
            "unlimited": usage.credits.unlimited,
            "balance": usage.credits.balance,
        }

    return {
        "checkedAtUtc": _utc_iso(now_utc),
        "planType": usage.plan_type,
        "primary": _win_dict(usage.primary),
        "secondary": _win_dict(usage.secondary),
        "credits": credits_dict,
        "spendControlReached": usage.spend_control_reached,
        "rateLimitReachedType": usage.rate_limit_reached_type,
    }


def format_rate_limit_usage_report(
    usage: RateLimitUsage,
    *,
    language: str = "en",
    now_utc: datetime | None = None,
) -> list[str]:
    effective_now = now_utc or datetime.now(timezone.utc)
    lines: list[str] = []
    is_ru = language == "ru"
    plan_title = "Plan" if not is_ru else "Тариф"
    lines.append(f"{plan_title}: {usage.plan_type or 'unknown'}")

    if usage.primary is not None:
        p = usage.primary
        dur_text = format_window_duration(p.window_duration_mins, language=language)
        bar = format_usage_bar(p.used_percent, width=20)
        rem_pct = f"{max(0.0, 100.0 - (p.used_percent or 0.0)):.1f}%"
        rem_time = format_usage_time_remaining(p.resets_at_utc, now_utc=effective_now, language=language)

        if is_ru:
            lines.append(f"Основной лимит ({dur_text}):")
            lines.append(f"  Использовано:   {bar} (осталось {rem_pct})")
            lines.append(f"  Сброс лимита:   {rem_time} ({_format_local_or_utc(p.resets_at_utc)})")
        else:
            lines.append(f"Primary limit window ({dur_text}):")
            lines.append(f"  Usage:          {bar} ({rem_pct} remaining)")
            lines.append(f"  Resets:         {rem_time} ({_format_local_or_utc(p.resets_at_utc)})")

    if usage.secondary is not None:
        s = usage.secondary
        dur_text = format_window_duration(s.window_duration_mins, language=language)
        bar = format_usage_bar(s.used_percent, width=20)
        rem_pct = f"{max(0.0, 100.0 - (s.used_percent or 0.0)):.1f}%"
        rem_time = format_usage_time_remaining(s.resets_at_utc, now_utc=effective_now, language=language)

        if is_ru:
            lines.append(f"Вторичный лимит ({dur_text}):")
            lines.append(f"  Использовано:   {bar} (осталось {rem_pct})")
            lines.append(f"  Сброс лимита:   {rem_time} ({_format_local_or_utc(s.resets_at_utc)})")
        else:
            lines.append(f"Secondary limit window ({dur_text}):")
            lines.append(f"  Usage:          {bar} ({rem_pct} remaining)")
            lines.append(f"  Resets:         {rem_time} ({_format_local_or_utc(s.resets_at_utc)})")

    if usage.credits is not None:
        c = usage.credits
        if is_ru:
            lines.append(f"Кредиты аккаунта: {'активны' if c.has_credits else 'нет'} (безлимит: {c.unlimited})")
        else:
            lines.append(f"Account credits: {'active' if c.has_credits else 'none'} (unlimited: {c.unlimited})")

    if usage.spend_control_reached:
        lines.append("[!] Предел расходов достигнут (spend control reached)" if is_ru else "[!] Spend control reached")

    return lines


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.state_path = self.root / "notifier-state.json"
        self.lock_path = self.root / "notifier-state.lock"

    def load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return _default_state()
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise NotifierError("Notifier state could not be read safely.") from exc
        if not isinstance(value, dict):
            raise NotifierError("Notifier state is not a JSON object.")
        _validate_state(value)
        if "lastUsage" not in value:
            value["lastUsage"] = None
        return value

    def save(self, value: Mapping[str, Any]) -> None:
        _validate_state(value)
        self.root.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix="notifier-state-",
            suffix=".tmp",
            dir=self.root,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.state_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def lock(self, timeout_seconds: float = 10.0) -> "StateFileLock":
        return StateFileLock(self.lock_path, timeout_seconds=timeout_seconds)


class StateFileLock(AbstractContextManager["StateFileLock"]):
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self._handle: Any = None

    def __enter__(self) -> "StateFileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+b")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.write(b"\0")
            self._handle.flush()

        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self._lock_once()
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise NotifierError("Notifier state is busy.")
                time.sleep(0.05)

    def _lock_once(self) -> None:
        assert self._handle is not None
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def validate_task_prefix(value: str) -> str:
    if not _TASK_PREFIX_RE.fullmatch(value):
        raise NotifierError(
            "task_prefix must contain only ASCII letters, digits, underscore, or hyphen."
        )
    return value


def notice_task_name(task_prefix: str, fingerprint: str) -> str:
    validate_task_prefix(task_prefix)
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise NotifierError("Notification fingerprint is invalid.")
    return f"{task_prefix}-Notice-{fingerprint[:16]}"


def assert_owned_scheduled_task(
    scheduled: Mapping[str, Any],
    *,
    task_prefix: str,
) -> None:
    fingerprint = scheduled.get("fingerprint")
    expected = notice_task_name(task_prefix, fingerprint)
    if scheduled.get("taskName") != expected:
        raise NotifierError("Refusing to mutate a task outside the notifier namespace.")


def _current_interactive_user() -> str:
    domain = os.environ.get("USERDOMAIN", "").strip()
    username = os.environ.get("USERNAME", "").strip() or getpass.getuser()
    return f"{domain}\\{username}" if domain else username


def _windowless_python() -> Path:
    executable = Path(sys.executable).resolve()
    if os.name == "nt" and executable.name.lower() == "python.exe":
        sibling = executable.with_name("pythonw.exe")
        if sibling.is_file():
            return sibling
    return executable


def _module_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _windows_command_line(arguments: list[str]) -> str:
    return subprocess.list2cmdline(arguments)


def render_notice_task_xml(
    *,
    run_at_utc: datetime,
    expires_at_utc: datetime,
    command: Path,
    arguments: str,
    working_directory: Path,
    user_id: str,
) -> str:
    if run_at_utc.tzinfo is None or expires_at_utc.tzinfo is None:
        raise NotifierError("Task timestamps must be timezone-aware.")
    if run_at_utc >= expires_at_utc:
        raise NotifierError("A notification task must start before expiry.")
    run_local = run_at_utc.astimezone()
    expiry_local = expires_at_utc.astimezone()
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Read-only Codex reset expiry reminder. This task never redeems a reset.</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{xml_escape(run_local.isoformat(timespec="seconds"))}</StartBoundary>
      <EndBoundary>{xml_escape(expiry_local.isoformat(timespec="seconds"))}</EndBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{xml_escape(user_id)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <DeleteExpiredTaskAfter>PT1H</DeleteExpiredTaskAfter>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{xml_escape(str(command))}</Command>
      <Arguments>{xml_escape(arguments)}</Arguments>
      <WorkingDirectory>{xml_escape(str(working_directory))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


class WindowsTaskScheduler:
    """Minimal Task Scheduler adapter for controller-owned one-shot notices."""

    def __init__(
        self,
        *,
        python_executable: Path | None = None,
        working_directory: Path | None = None,
        user_id: str | None = None,
    ) -> None:
        if os.name != "nt":
            raise NotifierError("Windows Task Scheduler is required for live notifier mode.")
        self.python_executable = (python_executable or _windowless_python()).resolve()
        self.working_directory = (working_directory or _module_root()).resolve()
        self.user_id = user_id or _current_interactive_user()

    @staticmethod
    def _run(arguments: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            ["schtasks.exe", *arguments],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
        )

    def task_exists(self, task_name: str) -> bool:
        result = self._run(["/Query", "/TN", task_name], check=False)
        return result.returncode == 0

    def register_notice(
        self,
        *,
        task_name: str,
        run_at_utc: datetime,
        expires_at_utc: datetime,
        fingerprint: str,
        state_root: Path,
        language: str,
        task_prefix: str,
    ) -> None:
        expected_name = notice_task_name(task_prefix, fingerprint)
        if task_name != expected_name:
            raise NotifierError("Refusing to register a task outside the notifier namespace.")
        arguments = _windows_command_line(
            [
                "-m",
                "codex_reset_credit_manager",
                "--root",
                str(state_root),
                "notifier-show",
                "--fingerprint",
                fingerprint,
                "--expires-at",
                _utc_iso(expires_at_utc),
                "--language",
                language,
                "--task-prefix",
                task_prefix,
            ]
        )
        xml = render_notice_task_xml(
            run_at_utc=run_at_utc,
            expires_at_utc=expires_at_utc,
            command=self.python_executable,
            arguments=arguments,
            working_directory=self.working_directory,
            user_id=self.user_id,
        )
        state_root.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix="notice-task-",
            suffix=".xml",
            dir=state_root,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-16", newline="\r\n") as handle:
                handle.write(xml)
            result = self._run(
                ["/Create", "/TN", task_name, "/XML", str(temp_path), "/F"],
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise NotifierError(f"Task Scheduler rejected the reminder task: {detail}")
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def delete_notice(self, task_name: str) -> None:
        result = self._run(["/Delete", "/TN", task_name, "/F"], check=False)
        if result.returncode != 0 and self.task_exists(task_name):
            detail = (result.stderr or result.stdout).strip()
            raise NotifierError(f"Task Scheduler could not remove a stale reminder: {detail}")


def _scheduled_record(
    candidate: NotificationCandidate,
    *,
    run_at_utc: datetime,
    task_name: str,
    language: str,
) -> dict[str, str]:
    return {
        "fingerprint": candidate.fingerprint,
        "expiresAtUtc": _utc_iso(candidate.expires_at_utc),
        "notifyAtUtc": _utc_iso(candidate.notify_at_utc),
        "scheduledForUtc": _utc_iso(run_at_utc),
        "taskName": task_name,
        "language": language,
    }


def _plan_from_state(action: str, scheduled: Mapping[str, Any] | None) -> NotificationPlan:
    if not scheduled:
        return NotificationPlan(action, None, None, None, None, None)
    return NotificationPlan(
        action=action,
        fingerprint=scheduled["fingerprint"],
        expires_at_utc=scheduled["expiresAtUtc"],
        notify_at_utc=scheduled["notifyAtUtc"],
        scheduled_for_utc=scheduled["scheduledForUtc"],
        task_name=scheduled["taskName"],
    )


def synchronize_notifier(
    report: ObservationReport,
    *,
    store: StateStore,
    scheduler: NoticeScheduler,
    now_utc: datetime,
    lead_hours: int = DEFAULT_LEAD_HOURS,
    language: str = "en",
    task_prefix: str = DEFAULT_TASK_PREFIX,
    dry_run: bool = False,
) -> NotificationPlan:
    if language not in {"en", "ru"}:
        raise NotifierError("language must be 'en' or 'ru'.")
    validate_task_prefix(task_prefix)
    if now_utc.tzinfo is None:
        raise NotifierError("now_utc must be timezone-aware.")
    now_utc = now_utc.astimezone(timezone.utc)
    candidate = select_nearest_available(
        report,
        now_utc=now_utc,
        lead_hours=lead_hours,
    )

    with store.lock():
        state = store.load()
        state["lastCheckAtUtc"] = _utc_iso(now_utc)
        state["lastError"] = None
        if report.rate_limits.usage is not None:
            state["lastUsage"] = sanitize_usage_record(report.rate_limits.usage, now_utc=now_utc)
        old = state.get("scheduled")

        if isinstance(old, dict):
            assert_owned_scheduled_task(old, task_prefix=task_prefix)
        if candidate is None:
            if not dry_run:
                if old:
                    scheduler.delete_notice(old["taskName"])
                state["scheduled"] = None
                state["lastCheckResult"] = "no_available_credit"
                store.save(state)
            return _plan_from_state("no_available_credit", None)

        if (
            isinstance(state.get("lastNotified"), dict)
            and state["lastNotified"].get("fingerprint") == candidate.fingerprint
        ):
            state["lastCheckResult"] = "already_notified"
            if not dry_run:
                store.save(state)
            return NotificationPlan(
                action="already_notified",
                fingerprint=candidate.fingerprint,
                expires_at_utc=_utc_iso(candidate.expires_at_utc),
                notify_at_utc=_utc_iso(candidate.notify_at_utc),
                scheduled_for_utc=None,
                task_name=None,
            )

        task_name = notice_task_name(task_prefix, candidate.fingerprint)
        if (
            old
            and old.get("fingerprint") == candidate.fingerprint
            and old.get("expiresAtUtc") == _utc_iso(candidate.expires_at_utc)
            and scheduler.task_exists(task_name)
        ):
            state["lastCheckResult"] = "unchanged"
            if not dry_run:
                store.save(state)
            return _plan_from_state("unchanged", old)

        earliest_start = now_utc + timedelta(seconds=NOTICE_START_GRACE_SECONDS)
        run_at = max(candidate.notify_at_utc, earliest_start)
        if run_at >= candidate.expires_at_utc:
            state["lastCheckResult"] = "too_late"
            if not dry_run:
                if old:
                    scheduler.delete_notice(old["taskName"])
                state["scheduled"] = None
                store.save(state)
            return NotificationPlan(
                action="too_late",
                fingerprint=candidate.fingerprint,
                expires_at_utc=_utc_iso(candidate.expires_at_utc),
                notify_at_utc=_utc_iso(candidate.notify_at_utc),
                scheduled_for_utc=None,
                task_name=None,
            )

        scheduled = _scheduled_record(
            candidate,
            run_at_utc=run_at,
            task_name=task_name,
            language=language,
        )
        action = "would_schedule" if dry_run else "scheduled"
        if dry_run:
            return _plan_from_state(action, scheduled)

        scheduler.register_notice(
            task_name=task_name,
            run_at_utc=run_at,
            expires_at_utc=candidate.expires_at_utc,
            fingerprint=candidate.fingerprint,
            state_root=store.root,
            language=language,
            task_prefix=task_prefix,
        )
        state["scheduled"] = scheduled
        state["lastCheckResult"] = action
        store.save(state)

        if old and old.get("taskName") != task_name:
            scheduler.delete_notice(old["taskName"])
        return _plan_from_state(action, scheduled)


def _local_expiry_text(expires_at_utc: datetime) -> str:
    local = expires_at_utc.astimezone()
    offset = local.strftime("%z")
    formatted_offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
    zone = local.tzname() or "local"
    return f"{local:%Y-%m-%d %H:%M:%S} {zone} (UTC{formatted_offset})"


def _russian_unit(value: int, singular: str, paucal: str, plural: str) -> str:
    remainder_100 = value % 100
    if 11 <= remainder_100 <= 14:
        form = plural
    else:
        remainder_10 = value % 10
        if remainder_10 == 1:
            form = singular
        elif 2 <= remainder_10 <= 4:
            form = paucal
        else:
            form = plural
    return f"{value} {form}"


def _remaining_time_text(
    expires_at_utc: datetime,
    *,
    now_utc: datetime,
    language: str,
) -> str:
    if expires_at_utc.tzinfo is None or now_utc.tzinfo is None:
        raise NotifierError("Remaining-time timestamps must be timezone-aware.")
    remaining_seconds = max(
        0,
        int(
            (
                expires_at_utc.astimezone(timezone.utc)
                - now_utc.astimezone(timezone.utc)
            ).total_seconds()
        ),
    )
    days, remainder = divmod(remaining_seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, seconds = divmod(remainder, 60)
    if language == "ru":
        return ", ".join(
            (
                _russian_unit(days, "день", "дня", "дней"),
                _russian_unit(hours, "час", "часа", "часов"),
                _russian_unit(minutes, "минута", "минуты", "минут"),
                _russian_unit(seconds, "секунда", "секунды", "секунд"),
            )
        )
    if language != "en":
        raise NotifierError("language must be 'en' or 'ru'.")
    values = ((days, "day"), (hours, "hour"), (minutes, "minute"), (seconds, "second"))
    return ", ".join(
        f"{value} {unit if value == 1 else unit + 's'}" for value, unit in values
    )


def notice_copy(
    expires_at_utc: datetime,
    *,
    language: str,
    now_utc: datetime | None = None,
) -> tuple[str, str]:
    local_text = _local_expiry_text(expires_at_utc)
    utc_text = _utc_iso(expires_at_utc)
    effective_now = now_utc or datetime.now(timezone.utc)
    remaining_text = _remaining_time_text(
        expires_at_utc,
        now_utc=effective_now,
        language=language,
    )
    if language == "ru":
        return (
            "Codex: активация сброса скоро исчезнет",
            "Ближайшая сохранённая активация сброса лимитов Codex исчезнет:\n\n"
            f"{local_text}\n"
            f"{utc_text}\n\n"
            f"Осталось на момент открытия окна: {remaining_text}.\n\n"
            "Это напоминание только читает срок действия. Оно не активирует и не расходует сброс.\n\n"
            "Нажмите OK или закройте окно.",
        )
    if language != "en":
        raise NotifierError("language must be 'en' or 'ru'.")
    return (
        "Codex reset activation expires soon",
        "Your nearest saved Codex usage-limit reset activation expires at:\n\n"
        f"{local_text}\n"
        f"{utc_text}\n\n"
        f"Time remaining when this window opened: {remaining_text}.\n\n"
        "This reminder only reads the expiry. It does not activate or redeem a reset.\n\n"
        "Select OK or close this window.",
    )


def show_modal_notice(title: str, message: str) -> None:
    """Show a top-most modal dialog that remains until OK or the close button."""
    if sys.platform.startswith("win"):
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"OpenAI.Codex.ResetCreditNotifier.{__version__}"
            )
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    try:
        with contextlib.suppress(Exception):
            icon_img = tk.PhotoImage(data=APP_ICON_PNG_64_BASE64)
            root.iconphoto(True, icon_img)
        root.withdraw()
        root.attributes("-topmost", True)
        root.update_idletasks()
        messagebox.showinfo(title, message, parent=root)
    finally:
        root.destroy()


def display_scheduled_notice(
    *,
    store: StateStore,
    fingerprint: str,
    expires_at_utc: datetime,
    language: str,
    task_prefix: str,
    now_utc: datetime,
    display: Callable[[str, str], None] = show_modal_notice,
) -> str:
    expected_task_name = notice_task_name(task_prefix, fingerprint)
    if now_utc.tzinfo is None or expires_at_utc.tzinfo is None:
        raise NotifierError("Notification timestamps must be timezone-aware.")
    now_utc = now_utc.astimezone(timezone.utc)
    expires_at_utc = expires_at_utc.astimezone(timezone.utc)

    with store.lock():
        state = store.load()
        scheduled = state.get("scheduled")
        if (
            not isinstance(scheduled, dict)
            or scheduled.get("fingerprint") != fingerprint
            or scheduled.get("expiresAtUtc") != _utc_iso(expires_at_utc)
            or scheduled.get("taskName") != expected_task_name
        ):
            return "stale"
        notified = state.get("lastNotified")
        if isinstance(notified, dict) and notified.get("fingerprint") == fingerprint:
            return "already_notified"
        if now_utc >= expires_at_utc:
            state["scheduled"] = None
            state["lastCheckResult"] = "expired_before_display"
            store.save(state)
            return "expired"

        state["lastNotified"] = {
            "fingerprint": fingerprint,
            "expiresAtUtc": _utc_iso(expires_at_utc),
            "startedAtUtc": _utc_iso(now_utc),
            "closedAtUtc": None,
            "status": "displaying",
        }
        state["lastError"] = None
        store.save(state)

    title, message = notice_copy(
        expires_at_utc,
        language=language,
        now_utc=now_utc,
    )
    try:
        display(title, message)
    except Exception as exc:
        with store.lock():
            state = store.load()
            current = state.get("lastNotified")
            if isinstance(current, dict) and current.get("fingerprint") == fingerprint:
                state["lastNotified"] = None
                state["scheduled"] = None
                state["lastError"] = f"Display failed: {type(exc).__name__}"
                state["lastCheckResult"] = "display_failed"
                store.save(state)
        raise NotifierError("The modal reminder could not be displayed.") from exc

    closed_at = datetime.now(timezone.utc)
    with store.lock():
        state = store.load()
        current = state.get("lastNotified")
        if isinstance(current, dict) and current.get("fingerprint") == fingerprint:
            current["closedAtUtc"] = _utc_iso(closed_at)
            current["status"] = "closed"
            state["scheduled"] = None
            state["lastCheckResult"] = "notified"
            store.save(state)
    return "notified"


def record_notifier_error(
    store: StateStore,
    *,
    error_code: str,
    now_utc: datetime,
) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", error_code):
        raise NotifierError("Notifier error code is invalid.")
    if now_utc.tzinfo is None:
        raise NotifierError("now_utc must be timezone-aware.")
    with store.lock():
        state = store.load()
        state["lastCheckAtUtc"] = _utc_iso(now_utc)
        state["lastCheckResult"] = "error"
        state["lastError"] = error_code
        store.save(state)


def sanitized_notifier_status(store: StateStore) -> dict[str, Any]:
    with store.lock():
        state = store.load()
    payload = dict(state)
    scheduled = payload.get("scheduled")
    if isinstance(scheduled, dict):
        payload["scheduled"] = {
            key: value
            for key, value in scheduled.items()
            if key != "fingerprint"
        }
    notified = payload.get("lastNotified")
    if isinstance(notified, dict):
        payload["lastNotified"] = {
            key: value
            for key, value in notified.items()
            if key != "fingerprint"
        }
    return payload


def plan_as_dict(plan: NotificationPlan) -> dict[str, Any]:
    return asdict(plan)


def _is_system_russian() -> bool:
    try:
        import locale
        loc = locale.getdefaultlocale()[0] or ""
        if loc.lower().startswith("ru"):
            return True
    except Exception:
        pass
    lang_env = os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")
    return "ru" in lang_env.lower()


def show_status_gui(
    fetch_report: Callable[[], ObservationReport],
    *,
    language: str = "auto",
    store: StateStore | None = None,
) -> None:
    """Display a live, read-only desktop status monitor for Codex usage & reset credits."""
    if sys.platform.startswith("win"):
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"OpenAI.Codex.ResetCreditManager.{__version__}"
            )
    import tkinter as tk
    from tkinter import messagebox, ttk
    import queue
    import threading

    current_lang = "ru" if (language == "ru" or (language == "auto" and _is_system_russian())) else "en"

    root = tk.Tk()
    # Set App Icon
    with contextlib.suppress(Exception):
        icon_img = tk.PhotoImage(data=APP_ICON_PNG_64_BASE64)
        root.iconphoto(True, icon_img)
    root.geometry("640x580")
    root.minsize(580, 500)
    root.configure(background="#0F172A")

    # Set icon if available, configure font
    with contextlib.suppress(Exception):
        root.option_add("*Font", ("Segoe UI", 9))

    style = ttk.Style(root)
    with contextlib.suppress(Exception):
        style.theme_use("clam")

    # Color Palette (Dark slate / Clean aesthetic)
    bg_dark = "#0F172A"
    card_bg = "#1E293B"
    card_border = "#334155"
    text_white = "#F8FAFC"
    text_muted = "#94A3B8"
    accent_blue = "#38BDF8"
    green_ok = "#34D399"
    yellow_warn = "#FBBF24"
    red_alert = "#F87171"

    style.configure("Main.TFrame", background=bg_dark)
    style.configure("Card.TFrame", background=card_bg, relief="solid", borderwidth=1)
    style.configure("Inner.TFrame", background=card_bg)
    style.configure("Title.TLabel", background=bg_dark, foreground=text_white, font=("Segoe UI", 15, "bold"))
    style.configure("Subtitle.TLabel", background=bg_dark, foreground=text_muted, font=("Segoe UI", 9))
    style.configure("CardHeader.TLabel", background=card_bg, foreground=accent_blue, font=("Segoe UI", 10, "bold"))
    style.configure("CardTitle.TLabel", background=card_bg, foreground=text_white, font=("Segoe UI", 10, "bold"))
    style.configure("CardLabel.TLabel", background=card_bg, foreground=text_muted, font=("Segoe UI", 9))
    style.configure("CardValue.TLabel", background=card_bg, foreground=text_white, font=("Segoe UI", 9, "bold"))
    style.configure("CardValueGreen.TLabel", background=card_bg, foreground=green_ok, font=("Segoe UI", 9, "bold"))
    style.configure("CardValueYellow.TLabel", background=card_bg, foreground=yellow_warn, font=("Segoe UI", 9, "bold"))
    style.configure("CardValueRed.TLabel", background=card_bg, foreground=red_alert, font=("Segoe UI", 9, "bold"))
    style.configure("Footer.TLabel", background=bg_dark, foreground=text_muted, font=("Segoe UI", 8))
    style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 6))

    main_frame = ttk.Frame(root, style="Main.TFrame", padding=(20, 16, 20, 16))
    main_frame.pack(fill="both", expand=True)

    # Update Notification Banner (Hidden by default)
    banner_update = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
    lbl_update_text = ttk.Label(banner_update, text="", style="CardValueGreen.TLabel")
    lbl_update_text.pack(side="left", fill="x", expand=True)
    btn_open_release = ttk.Button(banner_update, text="Обновить", style="Action.TButton")
    btn_open_release.pack(side="right", padx=(10, 0))

    # Title Bar
    title_label = ttk.Label(main_frame, text="", style="Title.TLabel")
    title_label.pack(anchor="w")
    subtitle_label = ttk.Label(main_frame, text="", style="Subtitle.TLabel")
    subtitle_label.pack(anchor="w", pady=(2, 12))

    # Content Container
    content_frame = ttk.Frame(main_frame, style="Main.TFrame")
    content_frame.pack(fill="both", expand=True)

    # Card 1: Account & Plan
    card_account = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
    card_account.pack(fill="x", pady=4)
    lbl_acc_title = ttk.Label(card_account, text="", style="CardHeader.TLabel")
    lbl_acc_title.pack(anchor="w")
    lbl_acc_details = ttk.Label(card_account, text="", style="CardValue.TLabel")
    lbl_acc_details.pack(anchor="w", pady=(2, 0))

    # Card 2: Primary Limit Window Usage
    card_primary = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
    card_primary.pack(fill="x", pady=4)
    lbl_primary_title = ttk.Label(card_primary, text="", style="CardHeader.TLabel")
    lbl_primary_title.pack(anchor="w")
    lbl_primary_usage = ttk.Label(card_primary, text="", style="CardValue.TLabel")
    lbl_primary_usage.pack(anchor="w", pady=(3, 0))
    prog_primary = ttk.Progressbar(card_primary, orient="horizontal", mode="determinate", length=540)
    prog_primary.pack(fill="x", pady=4)
    lbl_primary_reset = ttk.Label(card_primary, text="", style="CardLabel.TLabel")
    lbl_primary_reset.pack(anchor="w")

    # Card 3: Secondary Limit Window (hidden if none)
    card_secondary = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
    lbl_secondary_title = ttk.Label(card_secondary, text="", style="CardHeader.TLabel")
    lbl_secondary_title.pack(anchor="w")
    lbl_secondary_usage = ttk.Label(card_secondary, text="", style="CardValue.TLabel")
    lbl_secondary_usage.pack(anchor="w", pady=(3, 0))
    prog_secondary = ttk.Progressbar(card_secondary, orient="horizontal", mode="determinate", length=540)
    prog_secondary.pack(fill="x", pady=4)
    lbl_secondary_reset = ttk.Label(card_secondary, text="", style="CardLabel.TLabel")
    lbl_secondary_reset.pack(anchor="w")

    # Card 4: Reset Credits & Expiry
    card_credits = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
    card_credits.pack(fill="x", pady=4)
    lbl_credits_title = ttk.Label(card_credits, text="", style="CardHeader.TLabel")
    lbl_credits_title.pack(anchor="w")
    lbl_credits_info = ttk.Label(card_credits, text="", style="CardValue.TLabel")
    lbl_credits_info.pack(anchor="w", pady=(2, 0))

    # Card 5: Notifier Scheduler Status
    card_notifier = ttk.Frame(content_frame, style="Card.TFrame", padding=12)
    card_notifier.pack(fill="x", pady=4)
    lbl_notifier_title = ttk.Label(card_notifier, text="", style="CardHeader.TLabel")
    lbl_notifier_title.pack(anchor="w")
    lbl_notifier_info = ttk.Label(card_notifier, text="", style="CardLabel.TLabel")
    lbl_notifier_info.pack(anchor="w", pady=(2, 0))

    # Status Message / Last Refreshed
    status_bar = ttk.Label(main_frame, text="", style="Footer.TLabel")
    status_bar.pack(anchor="w", pady=(8, 4))

    # Action Buttons
    btn_frame = ttk.Frame(main_frame, style="Main.TFrame")
    btn_frame.pack(fill="x", pady=(4, 0))

    btn_refresh = ttk.Button(btn_frame, text="", style="Action.TButton")
    btn_refresh.pack(side="left")

    btn_check_update = ttk.Button(btn_frame, text="", style="Action.TButton")
    btn_check_update.pack(side="left", padx=8)

    btn_lang = ttk.Button(btn_frame, text="", style="Action.TButton")
    btn_lang.pack(side="left")

    btn_close = ttk.Button(btn_frame, text="", style="Action.TButton", command=root.destroy)
    btn_close.pack(side="right")

    events: queue.Queue[tuple[str, Any]] = queue.Queue()
    is_busy = False

    def update_texts(lang: str) -> None:
        is_r = lang == "ru"
        root.title(f"Codex: Монитор использования и сбросов v{__version__}" if is_r else f"Codex Usage & Rate Limit Monitor v{__version__}")
        title_label.config(text=f"Codex: Монитор лимитов и сбросов  v{__version__}" if is_r else f"Codex Usage & Rate Limit Monitor  v{__version__}")
        subtitle_label.config(text=f"Версия {__version__} · Безопасный read-only мониторинг квоты и срока сбросов" if is_r else f"Version {__version__} · Safe, read-only rate-limit quota & reset expiry monitor")
        lbl_acc_title.config(text="УЧЕТНАЯ ЗАПИСЬ И ТАРИФ" if is_r else "ACCOUNT & PLAN")
        lbl_primary_title.config(text="ОСНОВНОЙ ЛИМИТ" if is_r else "PRIMARY USAGE LIMIT")
        lbl_secondary_title.config(text="ВТОРИЧНЫЙ ЛИМИТ" if is_r else "SECONDARY USAGE LIMIT")
        lbl_credits_title.config(text="ДОСТУПНЫЕ СБРОСЫ ЛИМИТОВ (RESET CREDITS)" if is_r else "RESET CREDITS INVENTORY")
        lbl_notifier_title.config(text="СЛУЖБА НАПОМИНАНИЙ (NOTIFIER)" if is_r else "DAILY NOTIFIER STATUS")
        btn_refresh.config(text="Обновить сейчас" if is_r else "Check Now")
        btn_check_update.config(text="Обновления" if is_r else "Check Updates")
        btn_lang.config(text="English" if is_r else "Русский")
        btn_close.config(text="Закрыть" if is_r else "Close")
        btn_open_release.config(text="Обновить / GitHub" if is_r else "Update / GitHub")

    def toggle_lang() -> None:
        nonlocal current_lang
        current_lang = "en" if current_lang == "ru" else "ru"
        update_texts(current_lang)
        if latest_report is not None:
            render_report(latest_report, current_lang)

    btn_lang.config(command=toggle_lang)

    latest_report: ObservationReport | None = None

    def render_report(report: ObservationReport, lang: str) -> None:
        nonlocal latest_report
        latest_report = report
        is_r = lang == "ru"
        now_utc = datetime.now(timezone.utc)

        # 1. Account
        email = report.account.email_masked or ("неизвестен" if is_r else "unknown")
        plan = report.account.plan_type or ("неизвестен" if is_r else "unknown")
        lbl_acc_details.config(text=f"Email: {email}   |   {'Тариф' if is_r else 'Plan'}: {plan.upper()}   |   Mode: Read-Only")

        # 2. Usage
        usage = report.rate_limits.usage
        if usage is not None and usage.primary is not None:
            p = usage.primary
            dur_text = format_window_duration(p.window_duration_mins, language=lang)
            lbl_primary_title.config(text=f"{'ОСНОВНОЙ ЛИМИТ' if is_r else 'PRIMARY LIMIT'} ({dur_text})")
            used = p.used_percent if p.used_percent is not None else 0.0
            rem_pct = max(0.0, 100.0 - used)
            lbl_primary_usage.config(text=f"{used:5.1f}% {'использовано' if is_r else 'used'}  ({rem_pct:5.1f}% {'осталось' if is_r else 'remaining'})")
            prog_primary["value"] = min(100.0, max(0.0, used))

            rem_time = format_usage_time_remaining(p.resets_at_utc, now_utc=now_utc, language=lang)
            resets_local = _format_local_or_utc(p.resets_at_utc)
            lbl_primary_reset.config(text=f"{'Сброс лимита' if is_r else 'Window resets'}: {rem_time} ({resets_local})")
        else:
            lbl_primary_usage.config(text="Данные о лимитах недоступны" if is_r else "No rate-limit usage reported")
            prog_primary["value"] = 0
            lbl_primary_reset.config(text="")

        # 3. Secondary window
        if usage is not None and usage.secondary is not None:
            card_secondary.pack(fill="x", pady=4, after=card_primary)
            s = usage.secondary
            dur_text = format_window_duration(s.window_duration_mins, language=lang)
            lbl_secondary_title.config(text=f"{'ВТОРИЧНЫЙ ЛИМИТ' if is_r else 'SECONDARY LIMIT'} ({dur_text})")
            used_s = s.used_percent if s.used_percent is not None else 0.0
            rem_pct_s = max(0.0, 100.0 - used_s)
            lbl_secondary_usage.config(text=f"{used_s:5.1f}% {'использовано' if is_r else 'used'}  ({rem_pct_s:5.1f}% {'осталось' if is_r else 'remaining'})")
            prog_secondary["value"] = min(100.0, max(0.0, used_s))
            rem_time_s = format_usage_time_remaining(s.resets_at_utc, now_utc=now_utc, language=lang)
            resets_local_s = _format_local_or_utc(s.resets_at_utc)
            lbl_secondary_reset.config(text=f"{'Сброс лимита' if is_r else 'Window resets'}: {rem_time_s} ({resets_local_s})")
        else:
            card_secondary.pack_forget()

        # 4. Credits
        avail = report.rate_limits.available_count
        credits_list = report.rate_limits.credits
        if avail and avail > 0 and credits_list:
            nearest = credits_list[0]
            exp_time = format_usage_time_remaining(nearest.expires_at, now_utc=now_utc, language=lang)
            exp_local = _format_local_or_utc(nearest.expires_at)
            lbl_credits_info.config(
                text=f"{avail} {'доступно' if is_r else 'available'}   |   {'Ближайшее истечение' if is_r else 'Nearest expiry'}: {exp_time} ({exp_local})"
            )
        else:
            lbl_credits_info.config(text="0 доступных сбросов лимитов" if is_r else "0 available reset credits")

        # 5. Notifier state
        if store is not None:
            try:
                st = sanitized_notifier_status(store)
                last_chk = _format_local_or_utc(st.get("lastCheckAtUtc"))
                scheduled = st.get("scheduled")
                if isinstance(scheduled, dict):
                    rem_target = _format_local_or_utc(scheduled.get("scheduledForUtc"))
                    lbl_notifier_info.config(
                        text=f"{'Последняя проверка' if is_r else 'Last check'}: {last_chk}   |   {'Напоминание запланировано на' if is_r else 'Reminder scheduled for'}: {rem_target}"
                    )
                else:
                    lbl_notifier_info.config(
                        text=f"{'Последняя проверка' if is_r else 'Last check'}: {last_chk}   |   {'Нет запланированных окон T-12' if is_r else 'No active T-12 notice scheduled'}"
                    )
            except Exception:
                lbl_notifier_info.config(text="Статус службы недоступен" if is_r else "Notifier state unavailable")
        else:
            lbl_notifier_info.config(text="Автономный режим (без StateStore)" if is_r else "Standalone mode (no StateStore)")

        local_now = now_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        status_bar.config(text=f"{'Обновлено' if is_r else 'Last updated'}: {local_now}")

    def fetch_worker() -> None:
        try:
            rep = fetch_observation()
            events.put(("success", rep))
        except Exception as exc:
            events.put(("error", str(exc)))

    def update_checker_worker(force: bool) -> None:
        try:
            from .updater import check_for_updates

            res = check_for_updates(
                store=store,
                current_version=__version__,
                force=force,
            )
            events.put(("update_check", (res, force)))
        except Exception:
            pass

    def trigger_refresh() -> None:
        nonlocal is_busy
        if is_busy:
            return
        is_busy = True
        btn_refresh.config(state="disabled")
        status_bar.config(text="Запрос данных от Codex app-server..." if current_lang == "ru" else "Querying Codex app-server...")
        threading.Thread(target=fetch_worker, daemon=True).start()

    def trigger_update_check() -> None:
        status_bar.config(text="Проверка обновлений на GitHub..." if current_lang == "ru" else "Checking for updates on GitHub...")
        threading.Thread(target=update_checker_worker, args=(True,), daemon=True).start()

    btn_refresh.config(command=trigger_refresh)
    btn_check_update.config(command=trigger_update_check)

    def process_queue() -> None:
        nonlocal is_busy
        try:
            while True:
                kind, data = events.get_nowait()
                if kind == "success":
                    is_busy = False
                    btn_refresh.config(state="normal")
                    render_report(data, current_lang)
                elif kind == "error":
                    is_busy = False
                    btn_refresh.config(state="normal")
                    status_bar.config(text=f"{'Ошибка обновления' if current_lang == 'ru' else 'Update error'}: {data}")
                elif kind == "update_check":
                    res, forced = data
                    if res.is_update_available:
                        banner_update.pack(fill="x", pady=(0, 10), before=title_label)
                        is_r = current_lang == "ru"
                        lbl_update_text.config(
                            text=f"🎉 Доступно обновление v{res.latest_version}! (Текущая: v{__version__})"
                            if is_r
                            else f"🎉 New update v{res.latest_version} is available! (Current: v{__version__})"
                        )
                        btn_open_release.config(command=lambda u=res.release_url: webbrowser.open(u))
                    elif forced:
                        is_r = current_lang == "ru"
                        status_bar.config(
                            text=f"У вас последняя версия (v{__version__})" if is_r else f"You have the latest version (v{__version__})"
                        )
        except queue.Empty:
            pass
        root.after(100, process_queue)

    update_texts(current_lang)
    trigger_refresh()
    # Run automatic monthly update check in background
    threading.Thread(target=update_checker_worker, args=(False,), daemon=True).start()
    root.after(100, process_queue)
    root.mainloop()

