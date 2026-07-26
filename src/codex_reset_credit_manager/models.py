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

