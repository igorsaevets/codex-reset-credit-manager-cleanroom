from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class PlanningWindows:
    expires_at_utc: datetime
    warmup_at_utc: datetime
    validation_at_utc: datetime
    dispatch_at_utc: datetime


@dataclass(frozen=True)
class DoctorFinding:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class DoctorReport:
    root: Path
    legacy_install_root: Path
    codex_binary: str | None
    findings: tuple[DoctorFinding, ...]


@dataclass(frozen=True)
class AppServerHandshakeInfo:
    user_agent: str | None
    codex_home: str | None
    platform_family: str | None
    platform_os: str | None
    codex_home_matches_expected: bool


@dataclass(frozen=True)
class AccountInfo:
    type: str | None
    email_masked: str | None
    plan_type: str | None
    requires_openai_auth: bool | None


@dataclass(frozen=True)
class CreditDetail:
    id: str | None
    expires_at: str | None
    granted_at: str | None
    reset_type: str | None
    status: str | None
    title: str | None
    description: str | None


@dataclass(frozen=True)
class RateLimitInfo:
    available_count: int | None
    detail_count: int
    has_unlisted_credits: bool
    credits: tuple[CreditDetail, ...]
    raw_rate_limits: dict


@dataclass(frozen=True)
class ObservationReport:
    mode: str
    live_read_allowed: bool
    timestamp_utc: str
    handshake: AppServerHandshakeInfo
    account: AccountInfo
    rate_limits: RateLimitInfo
    environment_drift_detected: bool
    legacy_install_touched: bool
    live_consume_allowed: bool


