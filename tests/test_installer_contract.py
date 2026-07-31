from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
INSTALLER = ROOT / "install-notifier.ps1"


class WindowsInstallerContractTests(unittest.TestCase):
    def test_installer_registers_one_daily_read_only_controller(self) -> None:
        content = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("$DailyTaskName = \"$TaskPrefix-DailyCheck\"", content)
        self.assertIn("New-ScheduledTaskTrigger", content)
        self.assertIn("-Daily", content)
        self.assertIn("ScheduleByDay.DaysInterval", content)
        self.assertIn("'1'", content)
        self.assertIn("'notifier-sync'", content)
        self.assertIn("'--allow-live-read'", content)
        self.assertIn("-StartWhenAvailable", content)
        self.assertIn("-WakeToRun", content)
        self.assertIn("-MultipleInstances IgnoreNew", content)
        self.assertIn("$registeredTask.Principal.RunLevel", content)
        self.assertIn("-ne 'Limited'", content)
        self.assertIn("-ExecutionTimeLimit (New-TimeSpan -Minutes 5)", content)
        self.assertIn("-Filter '*.py'", content)
        self.assertIn("'--dry-run'", content)
        self.assertIn("readiness probe", content.lower())
        self.assertIn("'--account-codex-home'", content)

    def test_installer_action_has_no_redemption_endpoint(self) -> None:
        content = INSTALLER.read_text(encoding="utf-8")
        self.assertNotIn(
            "account/rateLimitResetCredit/" + "consume",
            content,
        )
        self.assertNotIn(
            "/backend-api/wham/rate-limit-reset-credits/" + "consume",
            content,
        )

    @unittest.skipUnless(os.name == "nt", "Windows installer preview")
    def test_whatif_preview_makes_no_install_root(self) -> None:
        pwsh = shutil.which("pwsh")
        if not pwsh:
            self.skipTest("PowerShell 7 is unavailable")
        preview_root = Path(os.environ.get("TEMP", str(ROOT))) / (
            "codex-notifier-whatif-contract"
        )
        if preview_root.exists():
            self.skipTest("Preview sentinel path already exists")

        result = subprocess.run(
            [
                pwsh,
                "-NoProfile",
                "-File",
                str(INSTALLER),
                "-PythonPath",
                sys.executable,
                "-InstallRoot",
                str(preview_root),
                "-SkipInitialCheck",
                "-WhatIf",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WhatIf", result.stdout)
        self.assertFalse(preview_root.exists())


if __name__ == "__main__":
    unittest.main()
