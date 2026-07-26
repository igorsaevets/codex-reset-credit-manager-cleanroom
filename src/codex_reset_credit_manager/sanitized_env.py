from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


_ALLOWLIST = {
    "APPDATA",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
}


def build_child_environment(
    base_env: Mapping[str, str] | None = None,
    *,
    isolated_codex_home: Path,
) -> dict[str, str]:
    source = dict(base_env or os.environ)
    child: dict[str, str] = {}
    for key in sorted(_ALLOWLIST):
        value = source.get(key)
        if value:
            child[key] = value
    child["CODEX_HOME"] = str(isolated_codex_home)
    child["CODEX_SQLITE_HOME"] = str(isolated_codex_home / "sqlite")
    child["PYTHONUTF8"] = "1"
    return child


def diff_environment_names(
    base_env: Mapping[str, str] | None = None,
    *,
    isolated_codex_home: Path,
) -> tuple[list[str], list[str]]:
    source = dict(base_env or os.environ)
    child = build_child_environment(source, isolated_codex_home=isolated_codex_home)
    kept = sorted(child)
    stripped = sorted(name for name in source if name not in child)
    return kept, stripped

