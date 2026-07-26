import unittest
from pathlib import Path

from codex_reset_credit_manager.sanitized_env import build_child_environment


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
