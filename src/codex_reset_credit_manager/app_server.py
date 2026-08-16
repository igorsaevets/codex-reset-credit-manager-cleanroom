from __future__ import annotations

import collections
import json
import queue
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import AppConfig
from .models import (
    AccountInfo,
    AppServerHandshakeInfo,
    CreditDetail,
    ObservationReport,
    RateLimitCreditsInfo,
    RateLimitInfo,
    RateLimitUsage,
    UsageWindowInfo,
)
from .sanitized_env import build_child_environment


class AppServerObservationError(Exception):
    """Raised when app-server observation fails or returns an error."""


def parse_codex_binary_command(codex_binary: str) -> list[str]:
    """Parse a codex binary or stub command string safely across Windows and POSIX."""
    if not codex_binary or not isinstance(codex_binary, str):
        return ["codex", "app-server", "--stdio"]
    is_windows = sys.platform == "win32"
    try:
        tokens = shlex.split(codex_binary, posix=not is_windows)
    except Exception:
        tokens = [codex_binary]
    clean_tokens = [t.strip('"\'') for t in tokens if t.strip()]
    if not clean_tokens:
        return ["codex", "app-server", "--stdio"]
    if len(clean_tokens) == 1:
        return [clean_tokens[0], "app-server", "--stdio"]
    return clean_tokens


def mask_email(email: str | None) -> str | None:
    if not email or not isinstance(email, str):
        return None
    if "@" in email:
        user, domain = email.split("@", 1)
        if user:
            masked_user = user[0] + "***"
        else:
            masked_user = "***"
        return f"{masked_user}@{domain}"
    return "***"


def parse_flexible_timestamp(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        # Handle milliseconds vs seconds
        if val > 1e11:
            val = val / 1000.0
        try:
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError):
            return str(val)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # Numeric string?
        try:
            num = float(val_str)
            return parse_flexible_timestamp(num)
        except ValueError:
            pass
        # ISO string?
        try:
            normalized = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            return val_str
    return str(val)


def compare_codex_home(reported_home: str | None, expected_home: Path) -> bool:
    if not reported_home:
        return False
    try:
        reported_path = Path(reported_home).expanduser().resolve()
        expected_path = expected_home.expanduser().resolve()
        return str(reported_path).lower() == str(expected_path).lower()
    except Exception:
        return False


class AppServerTransport:
    """Read-only JSONL transport for communicating with codex app-server --stdio."""

    def __init__(
        self,
        command: list[str],
        env: Mapping[str, str],
        timeout: float = 10.0,
    ) -> None:
        self._command = command
        self._env = dict(env)
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._next_id = 1
        self._stdout_queue: queue.Queue[str | Exception | None] | None = None
        self._stderr_lines: collections.deque[str] = collections.deque(maxlen=100)
        self._stderr_lock: threading.Lock = threading.Lock()
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

    def connect(self) -> None:
        try:
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._env,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except Exception as exc:
            raise AppServerObservationError(
                f"Failed to spawn app-server process '{' '.join(self._command)}': {exc}"
            ) from exc

        self._stdout_queue = queue.Queue()
        with self._stderr_lock:
            self._stderr_lines.clear()

        self._stdout_thread = threading.Thread(
            target=self._read_stdout_loop,
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr_loop,
            daemon=True,
        )

        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout_loop(self) -> None:
        if not self._process or not self._process.stdout or self._stdout_queue is None:
            return
        try:
            for line in iter(self._process.stdout.readline, ""):
                self._stdout_queue.put(line)
        except Exception as exc:
            self._stdout_queue.put(exc)
        finally:
            self._stdout_queue.put(None)

    def _read_stderr_loop(self) -> None:
        if not self._process or not self._process.stderr:
            return
        try:
            for line in iter(self._process.stderr.readline, ""):
                line_str = line if len(line) <= 2000 else line[:2000] + "... [truncated]\n"
                with self._stderr_lock:
                    self._stderr_lines.append(line_str)
        except Exception:
            pass

    def _get_stderr_snapshot(self) -> str:
        with self._stderr_lock:
            return "".join(self._stderr_lines).strip()

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._process or not self._process.stdin or self._stdout_queue is None:
            raise AppServerObservationError("Transport process is not running.")

        req_id = self._next_id
        self._next_id += 1
        request_msg = {
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        try:
            line_to_send = json.dumps(request_msg) + "\n"
            self._process.stdin.write(line_to_send)
            self._process.stdin.flush()
        except Exception as exc:
            stderr_output = self._get_stderr_snapshot()
            raise AppServerObservationError(
                f"Failed writing RPC request '{method}' (id={req_id}): {exc}. Stderr: {stderr_output}"
            ) from exc

        deadline = time.monotonic() + self._timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stderr_output = self._get_stderr_snapshot()
                raise AppServerObservationError(
                    f"Timeout ({self._timeout}s) waiting for app-server response to '{method}'. Stderr: {stderr_output}"
                )

            try:
                item = self._stdout_queue.get(timeout=remaining)
            except queue.Empty:
                stderr_output = self._get_stderr_snapshot()
                raise AppServerObservationError(
                    f"Timeout ({self._timeout}s) waiting for app-server response to '{method}'. Stderr: {stderr_output}"
                )

            if item is None:
                stderr_output = self._get_stderr_snapshot()
                raise AppServerObservationError(
                    f"App-server process exited unexpectedly while waiting for response to '{method}'. Stderr: {stderr_output}"
                )

            if isinstance(item, Exception):
                stderr_output = self._get_stderr_snapshot()
                raise AppServerObservationError(
                    f"Error reading stdout from app-server: {item}. Stderr: {stderr_output}"
                )

            line_str = item.strip()
            if not line_str:
                continue

            try:
                msg = json.loads(line_str)
            except json.JSONDecodeError:
                # Ignore non-JSON log noise if any
                continue

            if isinstance(msg, dict) and msg.get("id") == req_id:
                if "error" in msg:
                    err = msg["error"]
                    err_msg = err.get("message") if isinstance(err, dict) else str(err)
                    raise AppServerObservationError(
                        f"RPC request '{method}' returned error: {err_msg}"
                    )
                return msg.get("result", {})

    def send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        if not self._process or not self._process.stdin:
            raise AppServerObservationError("Transport process is not running.")

        notif_msg = {
            "method": method,
            "params": params or {},
        }

        try:
            line_to_send = json.dumps(notif_msg) + "\n"
            self._process.stdin.write(line_to_send)
            self._process.stdin.flush()
        except Exception as exc:
            stderr_output = self._get_stderr_snapshot()
            raise AppServerObservationError(
                f"Failed writing notification '{method}': {exc}. Stderr: {stderr_output}"
            ) from exc

    def close(self) -> None:
        proc = self._process
        if not proc:
            return
        self._process = None

        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
        except Exception:
            pass

        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass


def _parse_usage_window(data: Any) -> UsageWindowInfo | None:
    if not isinstance(data, dict) or not data:
        return None
    used_percent_raw = data.get("usedPercent")
    used_percent: float | None = None
    if isinstance(used_percent_raw, (int, float)):
        used_percent = float(used_percent_raw)
    elif isinstance(used_percent_raw, str):
        try:
            used_percent = float(used_percent_raw.strip())
        except ValueError:
            pass

    window_mins_raw = data.get("windowDurationMins")
    window_duration_mins: int | None = None
    if isinstance(window_mins_raw, int):
        window_duration_mins = window_mins_raw
    elif isinstance(window_mins_raw, (float, str)):
        try:
            window_duration_mins = int(window_mins_raw)
        except (ValueError, OverflowError):
            pass

    resets_at_raw = data.get("resetsAt") or data.get("resets_at")
    resets_at_utc: str | None = None
    resets_at_epoch: int | None = None
    if isinstance(resets_at_raw, (int, float)):
        epoch_val = float(resets_at_raw)
        if epoch_val > 1e11:
            epoch_val /= 1000.0
        try:
            resets_at_epoch = int(epoch_val)
            resets_at_utc = datetime.fromtimestamp(epoch_val, tz=timezone.utc).isoformat()
        except (ValueError, OverflowError):
            pass
    elif isinstance(resets_at_raw, str) and resets_at_raw.strip():
        try:
            epoch_val = float(resets_at_raw.strip())
            if epoch_val > 1e11:
                epoch_val /= 1000.0
            resets_at_epoch = int(epoch_val)
            resets_at_utc = datetime.fromtimestamp(epoch_val, tz=timezone.utc).isoformat()
        except ValueError:
            try:
                dt = datetime.fromisoformat(resets_at_raw.strip().replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                resets_at_epoch = int(dt.timestamp())
                resets_at_utc = dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                resets_at_utc = resets_at_raw.strip()

    if used_percent is None and window_duration_mins is None and resets_at_utc is None:
        return None

    return UsageWindowInfo(
        used_percent=used_percent,
        window_duration_mins=window_duration_mins,
        resets_at_utc=resets_at_utc,
        resets_at_epoch=resets_at_epoch,
    )


def parse_rate_limit_usage(raw_rate_limits: Any) -> RateLimitUsage | None:
    if not isinstance(raw_rate_limits, dict) or not raw_rate_limits:
        return None

    limit_id = raw_rate_limits.get("limitId")
    if limit_id is not None:
        limit_id = str(limit_id)

    plan_type = raw_rate_limits.get("planType")
    if plan_type is not None:
        plan_type = str(plan_type)

    primary = _parse_usage_window(raw_rate_limits.get("primary"))
    secondary = _parse_usage_window(raw_rate_limits.get("secondary"))

    credits_obj = raw_rate_limits.get("credits")
    credits_info: RateLimitCreditsInfo | None = None
    if isinstance(credits_obj, dict):
        has_credits = credits_obj.get("hasCredits")
        unlimited = credits_obj.get("unlimited")
        bal = credits_obj.get("balance")
        balance: float | None = None
        if isinstance(bal, (int, float)):
            balance = float(bal)
        credits_info = RateLimitCreditsInfo(
            has_credits=bool(has_credits) if has_credits is not None else None,
            unlimited=bool(unlimited) if unlimited is not None else None,
            balance=balance,
        )

    spend_control_reached = raw_rate_limits.get("spendControlReached")
    if spend_control_reached is not None:
        spend_control_reached = bool(spend_control_reached)

    rate_limit_reached_type = raw_rate_limits.get("rateLimitReachedType")
    if rate_limit_reached_type is not None:
        rate_limit_reached_type = str(rate_limit_reached_type)

    return RateLimitUsage(
        limit_id=limit_id,
        plan_type=plan_type,
        primary=primary,
        secondary=secondary,
        credits=credits_info,
        spend_control_reached=spend_control_reached,
        rate_limit_reached_type=rate_limit_reached_type,
    )


def observe_app_server_rate_limits(
    config: AppConfig,
    *,
    command_override: list[str] | None = None,
    codex_home_override: Path | None = None,
    timeout: float = 10.0,
) -> ObservationReport:
    if command_override:
        cmd = command_override
    elif config.codex_binary:
        cmd = [config.codex_binary, "app-server", "--stdio"]
    else:
        cmd = ["codex", "app-server", "--stdio"]

    if codex_home_override is not None:
        expected_codex_home = codex_home_override.expanduser().resolve()
        if not expected_codex_home.is_dir():
            raise AppServerObservationError(
                "The selected signed-in Codex home does not exist."
            )
    else:
        expected_codex_home = config.child_codex_home
        try:
            expected_codex_home.mkdir(parents=True, exist_ok=True)
            (expected_codex_home / "sqlite").mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AppServerObservationError(
                "The isolated Codex home could not be created."
            ) from exc

    child_env = build_child_environment(isolated_codex_home=expected_codex_home)
    transport = AppServerTransport(cmd, child_env, timeout=timeout)

    try:
        transport.connect()

        # 1. initialize
        init_res = transport.send_request(
            "initialize",
            {
                "clientInfo": {
                    "name": "codex_reset_credit_manager",
                    "title": "Codex Reset Credit Manager",
                    "version": "0.1.0",
                }
            },
        )

        # 2. initialized
        transport.send_notification("initialized", {})

        # 3. account/read
        acc_res = transport.send_request("account/read", {})

        # 4. account/rateLimits/read
        rl_res = transport.send_request("account/rateLimits/read", {})

    finally:
        transport.close()

    # Process initialize response
    reported_codex_home = init_res.get("codexHome")
    matches_home = compare_codex_home(reported_codex_home, expected_codex_home)
    handshake = AppServerHandshakeInfo(
        user_agent=init_res.get("userAgent"),
        codex_home=reported_codex_home,
        platform_family=init_res.get("platformFamily"),
        platform_os=init_res.get("platformOs"),
        codex_home_matches_expected=matches_home,
    )

    # Process account/read response
    acc_obj = acc_res.get("account")
    if isinstance(acc_obj, dict):
        account_type = acc_obj.get("type")
        raw_email = acc_obj.get("email")
        plan_type = acc_obj.get("planType")
    else:
        account_type = None
        raw_email = None
        plan_type = None

    account = AccountInfo(
        type=account_type,
        email_masked=mask_email(raw_email),
        plan_type=plan_type,
        requires_openai_auth=acc_res.get("requiresOpenaiAuth"),
    )

    # Process account/rateLimits/read response
    rl_credits_obj = rl_res.get("rateLimitResetCredits")
    if isinstance(rl_credits_obj, dict):
        available_count = rl_credits_obj.get("availableCount")
        raw_credits = rl_credits_obj.get("credits")
        if not isinstance(raw_credits, list):
            raw_credits = []
    else:
        available_count = None
        raw_credits = []

    parsed_credits: list[CreditDetail] = []
    for item in raw_credits:
        if not isinstance(item, dict):
            continue
        parsed_credits.append(
            CreditDetail(
                id=item.get("id"),
                expires_at=parse_flexible_timestamp(
                    item.get("expiresAt") or item.get("expires_at")
                ),
                granted_at=parse_flexible_timestamp(
                    item.get("grantedAt") or item.get("granted_at")
                ),
                reset_type=item.get("resetType") or item.get("reset_type"),
                status=item.get("status"),
                title=item.get("title"),
                description=item.get("description"),
            )
        )

    detail_count = len(parsed_credits)
    has_unlisted = (
        available_count is not None and isinstance(available_count, int) and available_count > detail_count
    )

    raw_rl = rl_res.get("rateLimits") if isinstance(rl_res.get("rateLimits"), dict) else {}
    parsed_usage = parse_rate_limit_usage(raw_rl)

    rate_limits = RateLimitInfo(
        available_count=available_count,
        detail_count=detail_count,
        has_unlisted_credits=has_unlisted,
        credits=tuple(parsed_credits),
        raw_rate_limits=raw_rl,
        usage=parsed_usage,
    )

    now_utc = datetime.now(timezone.utc).isoformat()
    return ObservationReport(
        mode="read-only",
        live_read_allowed=True,
        timestamp_utc=now_utc,
        handshake=handshake,
        account=account,
        rate_limits=rate_limits,
        environment_drift_detected=not matches_home,
        legacy_install_touched=False,
        live_consume_allowed=False,
    )

