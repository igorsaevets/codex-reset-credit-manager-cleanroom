import unittest

from codex_reset_credit_manager.planner import parse_utc_timestamp
from codex_reset_credit_manager.task_preview import render_task_xml


class TaskPreviewTests(unittest.TestCase):
    def test_render_task_xml_embeds_command_and_interactive_token(self) -> None:
        xml = render_task_xml(
            run_at_utc=parse_utc_timestamp("2026-08-02T11:59:40Z"),
            command="python",
            arguments="-m codex_reset_credit_manager dry-run",
        )

        self.assertIn("<LogonType>InteractiveToken</LogonType>", xml)
        self.assertIn("<RunLevel>LeastPrivilege</RunLevel>", xml)
        self.assertIn("<Command>python</Command>", xml)
        self.assertIn("<Arguments>-m codex_reset_credit_manager dry-run</Arguments>", xml)
