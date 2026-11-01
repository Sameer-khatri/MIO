"""
Unit tests for MIO Action History & Conversational Introspection (core.history).
"""

import os
import shutil
import tempfile
import unittest

from core.history import (
    record_action,
    get_recent_actions,
    get_last_action,
    get_history_summary,
    clear_history,
)
from core.agent import handle_command, get_last_action as agent_get_last_action
from core.registry import execute_action, TOOL_CATALOG
from hands.storage.filesystem import organize_folder, search_files
from hands.control.flow import set_work_mode, set_chill_mode


class TestActionHistory(unittest.TestCase):
    def setUp(self):
        clear_history()

    def tearDown(self):
        clear_history()

    def test_record_and_retrieve_last_action(self):
        record_action(
            tool_name="filesystem",
            action="organize_desktop",
            args={},
            result={"success": True, "message": "Moved 5 loose files."},
            duration_ms=12.4
        )

        last = get_last_action()
        self.assertIsNotNone(last)
        self.assertEqual(last["tool"], "filesystem")
        self.assertEqual(last["action"], "organize_desktop")
        self.assertTrue(last["success"])
        self.assertEqual(last["duration_ms"], 12.4)

    def test_get_recent_actions_limit(self):
        for i in range(15):
            record_action(
                tool_name="test_tool",
                action=f"action_{i}",
                args={"idx": i},
                result={"success": True, "message": f"Step {i}"},
                duration_ms=float(i)
            )

        recent = get_recent_actions(limit=5)
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0]["action"], "action_14")
        self.assertEqual(recent[4]["action"], "action_10")

    def test_history_summary(self):
        record_action("audio", "set_volume", {"level": 50}, {"success": True, "message": "Volume set to 50%."})
        summary = get_history_summary(limit=5)
        self.assertIn("Recent Actions", summary)
        self.assertIn("audio.set_volume", summary)

    def test_clear_history(self):
        record_action("screen", "take_screenshot", {}, {"success": True, "message": "Screenshot saved."})
        res = clear_history()
        self.assertTrue(res["success"])
        self.assertIsNone(get_last_action())
        self.assertEqual(len(get_recent_actions()), 0)


class TestOrganizeAndSearchTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mio_test_organize_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_organize_folder(self):
        # Create dummy files
        img = os.path.join(self.test_dir, "photo.png")
        doc = os.path.join(self.test_dir, "report.pdf")
        code = os.path.join(self.test_dir, "script.py")
        sc = os.path.join(self.test_dir, "app.lnk")

        for p in [img, doc, code, sc]:
            with open(p, "w") as f:
                f.write("test content")

        res = organize_folder(self.test_dir, keep_shortcuts=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["moved_count"], 3)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images", "photo.png")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents", "report.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Code", "script.py")))
        # Shortcut should remain at root
        self.assertTrue(os.path.exists(sc))

    def test_search_files(self):
        sample_file = os.path.join(self.test_dir, "quarterly_budget_2026.xlsx")
        with open(sample_file, "w") as f:
            f.write("budget")

        res = search_files("quarterly_budget", root_dir=self.test_dir)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["count"], 1)
        self.assertEqual(res["matches"][0]["name"], "quarterly_budget_2026.xlsx")


class TestAgentConversationalIntrospection(unittest.TestCase):
    def setUp(self):
        clear_history()

    def test_tell_me_what_u_just_did_now(self):
        # Run a command
        cont, msg = handle_command("set volume 50")
        self.assertTrue(cont)

        # Ask what was just done
        cont2, msg2 = handle_command("tell me what u just did now")
        self.assertTrue(cont2)
        self.assertIn("Just now, I executed", msg2)
        self.assertIn("set volume 50", msg2)

    def test_work_mode_and_chill_mode_commands(self):
        cont, msg = handle_command("work mode")
        self.assertTrue(cont)
        self.assertIn("Work Mode activated", msg)

        cont, msg = handle_command("chill mode")
        self.assertTrue(cont)
        self.assertIn("Chill Mode activated", msg)


if __name__ == "__main__":
    unittest.main()
