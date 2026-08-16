from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from . import __version__
from .notifier import StateStore


DEFAULT_REPOSITORY = "igorsaevets/codex-reset-credit-manager-cleanroom"
UPDATE_CHECK_INTERVAL = timedelta(days=30)
DEFAULT_TIMEOUT_SECONDS = 5.0


def parse_version_tuple(version_str: str) -> tuple[int, ...]:
    """Parse semantic version string like '0.3.2' or 'v1.0.0' into an integer tuple."""
    clean = re.sub(r"^[vV]", "", str(version_str).strip())
    parts: list[int] = []
    for chunk in clean.split("."):
        match = re.match(r"^\d+", chunk)
        if match:
            parts.append(int(match.group(0)))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(candidate: str, current: str) -> bool:
    """Return True if candidate version is strictly newer than current version."""
    return parse_version_tuple(candidate) > parse_version_tuple(current)


@dataclass(frozen=True)
class UpdateCheckResult:
    is_update_available: bool
    current_version: str
    latest_version: str
    release_url: str
    release_name: str
    release_notes: str
    checked_at_utc: str
    skipped_due_to_throttle: bool = False
    error: str | None = None


def fetch_latest_release(
    repo: str = DEFAULT_REPOSITORY,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Fetch latest release or tags metadata from GitHub API, with raw pyproject fallback."""
    # 1. Try Releases API
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"CodexResetCreditManager/{__version__} (Windows; read-only update-check)",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, dict):
                    return data
    except Exception:
        pass

    # 2. Try Tags API
    try:
        tags_url = f"https://api.github.com/repos/{repo}/tags"
        tags_req = urllib.request.Request(
            tags_url,
            headers={
                "User-Agent": f"CodexResetCreditManager/{__version__}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(tags_req, timeout=timeout) as tags_resp:
            if tags_resp.status == 200:
                tags_data = json.loads(tags_resp.read().decode("utf-8"))
                if isinstance(tags_data, list) and len(tags_data) > 0:
                    tag_name = tags_data[0].get("name", "")
                    return {
                        "tag_name": tag_name,
                        "html_url": f"https://github.com/{repo}/releases/tag/{tag_name}",
                        "name": f"Release {tag_name}",
                        "body": "Latest release tag",
                    }
    except Exception:
        pass

    # 3. Direct pyproject.toml read from main branch
    raw_url = f"https://raw.githubusercontent.com/{repo}/main/pyproject.toml"
    raw_req = urllib.request.Request(
        raw_url,
        headers={
            "User-Agent": f"CodexResetCreditManager/{__version__}",
        },
    )
    with urllib.request.urlopen(raw_req, timeout=timeout) as raw_resp:
        if raw_resp.status == 200:
            text = raw_resp.read().decode("utf-8")
            for line in text.splitlines():
                if "version =" in line:
                    parts = line.split("=")
                    if len(parts) >= 2:
                        remote_ver = parts[1].strip().strip('"\'')
                        return {
                            "tag_name": f"v{remote_ver}",
                            "html_url": f"https://github.com/{repo}",
                            "name": f"v{remote_ver}",
                            "body": f"Latest version in repository: v{remote_ver}",
                        }
    return {}


def check_for_updates(
    *,
    store: StateStore | None = None,
    current_version: str = __version__,
    repo: str = DEFAULT_REPOSITORY,
    force: bool = False,
    now_utc: datetime | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> UpdateCheckResult:
    """Check if a newer version exists in the repository, throttling to once per month."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    now_iso = now_utc.isoformat()

    # Throttling check
    if store is not None and not force:
        with store.lock():
            state = store.load()
            last_check_str = state.get("lastUpdateCheckAtUtc")
            if last_check_str:
                try:
                    last_check = datetime.fromisoformat(last_check_str)
                    if last_check.tzinfo is None:
                        last_check = last_check.replace(tzinfo=timezone.utc)
                    if (now_utc - last_check) < UPDATE_CHECK_INTERVAL:
                        latest_known = state.get("lastKnownLatestVersion", current_version)
                        return UpdateCheckResult(
                            is_update_available=is_newer_version(latest_known, current_version),
                            current_version=current_version,
                            latest_version=latest_known,
                            release_url=f"https://github.com/{repo}/releases",
                            release_name=f"Version {latest_known}",
                            release_notes="",
                            checked_at_utc=last_check_str,
                            skipped_due_to_throttle=True,
                        )
                except Exception:
                    pass

    try:
        release_info = fetch_latest_release(repo=repo, timeout=timeout)
        tag_name = release_info.get("tag_name") or release_info.get("name") or ""
        clean_tag = re.sub(r"^[vV]", "", tag_name.strip())
        release_url = release_info.get("html_url") or f"https://github.com/{repo}/releases"
        release_name = release_info.get("name") or f"Release {clean_tag}"
        release_notes = release_info.get("body") or ""

        if not clean_tag:
            clean_tag = current_version

        update_available = is_newer_version(clean_tag, current_version)

        # Update state with check timestamp
        if store is not None:
            with store.lock():
                state = store.load()
                state["lastUpdateCheckAtUtc"] = now_iso
                state["lastKnownLatestVersion"] = clean_tag
                store.save(state)

        return UpdateCheckResult(
            is_update_available=update_available,
            current_version=current_version,
            latest_version=clean_tag,
            release_url=release_url,
            release_name=release_name,
            release_notes=release_notes,
            checked_at_utc=now_iso,
            skipped_due_to_throttle=False,
        )

    except Exception as exc:
        return UpdateCheckResult(
            is_update_available=False,
            current_version=current_version,
            latest_version=current_version,
            release_url=f"https://github.com/{repo}/releases",
            release_name=f"Version {current_version}",
            release_notes="",
            checked_at_utc=now_iso,
            skipped_due_to_throttle=False,
            error=str(exc),
        )
