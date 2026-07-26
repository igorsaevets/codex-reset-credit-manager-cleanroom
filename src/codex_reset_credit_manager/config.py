from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


APP_HOME_ENV = "CODEX_RESET_CLEANROOM_HOME"


@dataclass(frozen=True)
class AppConfig:
    root: Path
    child_codex_home: Path
    legacy_install_root: Path
    codex_binary: str | None


def _windows_local_appdata() -> Path:
    candidate = os.environ.get("LOCALAPPDATA")
    if candidate:
        return Path(candidate)
    return Path.home() / "AppData" / "Local"


def default_root() -> Path:
    override = os.environ.get(APP_HOME_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return (_windows_local_appdata() / "CodexResetCreditDraft").resolve()


def legacy_install_root() -> Path:
    return (_windows_local_appdata() / "CodexResetCredit").resolve()


def load_config(explicit_root: Path | None = None) -> AppConfig:
    root = (explicit_root or default_root()).expanduser().resolve()
    return AppConfig(
        root=root,
        child_codex_home=root / "codex-home",
        legacy_install_root=legacy_install_root(),
        codex_binary=shutil.which("codex"),
    )

