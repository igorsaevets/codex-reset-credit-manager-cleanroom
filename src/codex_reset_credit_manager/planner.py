from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import PlanningWindows


def parse_utc_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def build_planning_windows(
    expires_at_utc: datetime,
    *,
    warmup_seconds: int = 180,
    validation_seconds: int = 60,
    dispatch_seconds: int = 20,
) -> PlanningWindows:
    if expires_at_utc.tzinfo is None:
        raise ValueError("expires_at_utc must be timezone-aware")
    if not (warmup_seconds > validation_seconds > dispatch_seconds > 0):
        raise ValueError("timing offsets must be strictly descending and positive")
    return PlanningWindows(
        expires_at_utc=expires_at_utc,
        warmup_at_utc=expires_at_utc - timedelta(seconds=warmup_seconds),
        validation_at_utc=expires_at_utc - timedelta(seconds=validation_seconds),
        dispatch_at_utc=expires_at_utc - timedelta(seconds=dispatch_seconds),
    )

