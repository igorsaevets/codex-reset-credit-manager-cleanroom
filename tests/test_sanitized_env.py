import unittest
from pathlib import Path
from typing import Iterator, Mapping

from codex_reset_credit_manager.sanitized_env import (
    build_child_environment,
    diff_environment_names,
)


class _SecretTrackingMapping(Mapping[str, str]):
    """Mapping wrapper that records which keys had their values accessed."""

    def __init__(self, data: dict[str, str]) -> None:
        self._data = data
        self.accessed_value_keys: set[str] = set()

    def get(self, key: str, default: str | None = None) -> str | None:
        if key in self._data:
            self.accessed_value_keys.add(key)
            return self._data[key]
        return default

    def __getitem__(self, key: str) -> str:
        self.accessed_value_keys.add(key)
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class SanitizedEnvTests(unittest.TestCase):
    def test_build_child_environment_keeps_small_allowlist_and_sets_codex_home(self) -> None:
        base = {
            "PATH": r"C:\Windows\System32",
            "SYSTEMROOT": r"C:\Windows",
            "TEMP": r"C:\Temp",
            "OPENAI_API_KEY": "secret",
            "HF_TOKEN": "secret",
            "RANDOM_VAR": "value",
        }
        child = build_child_environment(base, isolated_codex_home=Path(r"C:\Draft\codex-home"))

        self.assertEqual(child["PATH"], r"C:\Windows\System32")
        self.assertEqual(child["SYSTEMROOT"], r"C:\Windows")
        self.assertEqual(child["CODEX_HOME"], r"C:\Draft\codex-home")
        self.assertEqual(child["CODEX_SQLITE_HOME"], r"C:\Draft\codex-home\sqlite")
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("HF_TOKEN", child)
        self.assertNotIn("RANDOM_VAR", child)

    def test_non_allowlisted_secret_values_are_not_forwarded(self) -> None:
        base = {
            "PATH": r"C:\Windows\System32",
            "SECRET_TOKEN": "super-secret-value-12345",
            "OPENAI_API_KEY": "sk-proj-xyz987654321",
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        }
        child = build_child_environment(base, isolated_codex_home=Path(r"C:\Draft\codex-home"))
        self.assertNotIn("SECRET_TOKEN", child)
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", child)
        for key, val in child.items():
            self.assertNotIn("super-secret", val)
            self.assertNotIn("sk-proj", val)
            self.assertNotIn("wJalrXUt", val)

    def test_only_allowlisted_values_are_read(self) -> None:
        raw_env = {
            "PATH": r"C:\Windows\System32",
            "TEMP": r"C:\Temp",
            "OPENAI_API_KEY": "sk-secret-key-value",
            "UNRELATED_SECRET": "unrelated-secret-value",
        }
        tracking_env = _SecretTrackingMapping(raw_env)
        build_child_environment(tracking_env, isolated_codex_home=Path(r"C:\Draft\codex-home"))

        self.assertIn("PATH", tracking_env.accessed_value_keys)
        self.assertIn("TEMP", tracking_env.accessed_value_keys)
        self.assertNotIn("OPENAI_API_KEY", tracking_env.accessed_value_keys)
        self.assertNotIn("UNRELATED_SECRET", tracking_env.accessed_value_keys)

    def test_environment_preview_reports_names_not_values_and_only_reads_allowlisted_values(self) -> None:
        raw_env = {
            "PATH": r"C:\Windows\System32",
            "OPENAI_API_KEY": "sk-secret-key-value",
            "HF_TOKEN": "hf_secret_token",
        }
        tracking_env = _SecretTrackingMapping(raw_env)
        kept, stripped = diff_environment_names(
            tracking_env,
            isolated_codex_home=Path(r"C:\Draft\codex-home"),
        )

        self.assertIn("PATH", kept)
        self.assertIn("OPENAI_API_KEY", stripped)
        self.assertIn("HF_TOKEN", stripped)
        self.assertNotIn("OPENAI_API_KEY", tracking_env.accessed_value_keys)
        self.assertNotIn("HF_TOKEN", tracking_env.accessed_value_keys)
        for name in kept + stripped:
            self.assertNotIn("sk-secret", name)
            self.assertNotIn("hf_secret", name)

