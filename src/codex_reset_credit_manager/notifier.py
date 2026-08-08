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
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html import escape as xml_escape
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .models import CreditDetail, ObservationReport


STATE_SCHEMA_VERSION = 1
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
    }


def _validate_state(value: Mapping[str, Any]) -> None:
    if set(value) != set(_default_state()):
        raise NotifierError("Notifier state has an unexpected shape.")
    if value.get("schemaVersion") != STATE_SCHEMA_VERSION:
        raise NotifierError("Notifier state schema is unsupported.")
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
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    try:
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
