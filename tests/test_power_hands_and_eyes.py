"""
Unit tests for Advanced MIO Hands and Eyes Capabilities:
- Terminal Execution & Shell Isolation (hands.control.terminal)
- Media Session Metadata & Mic Mute (hands.sensory.audio)
- Headless Web Page Reading & Search Summary (hands.connectivity.browser)
- Visual Screen Change & Animation Stabilization (eyes.watcher)
- Unified Registry & Agent Command Dispatch
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from core.registry import execute_action, TOOL_CATALOG
from core.agent import handle_command
from hands.control.terminal import (
    run_command,
    run_powershell_script,
    get_environment_variable,
    set_environment_variable,
    _is_command_safe,
)
from hands.sensory.audio import get_current_media_info, toggle_microphone_mute
from hands.connectivity.browser import fetch_webpage_text, search_web_summary
from eyes.watcher import get_screen_hash, wait_for_visual_change, wait_for_screen_stabilize
import eyes


class TestTerminalHands(unittest.TestCase):
    def test_run_command_echo(self):
        res = run_command("Write-Output 'MIO_TERMINAL_ONLINE'")
        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("MIO_TERMINAL_ONLINE", res["stdout"])

    def test_command_safety_guardrail(self):
        safe, reason = _is_command_safe("format C: /y")
        self.assertFalse(safe)
        self.assertIn("blocked destructive pattern", reason)

        res = run_command("format C: /y")
        self.assertFalse(res["success"])
        self.assertIn("blocked", res["message"].lower())

    def test_environment_variables(self):
        # Set variable
        set_res = set_environment_variable("MIO_TEST_VAR_XYZ", "active_123")
        self.assertTrue(set_res["success"])
        self.assertEqual(os.environ.get("MIO_TEST_VAR_XYZ"), "active_123")

        # Get variable
        get_res = get_environment_variable("MIO_TEST_VAR_XYZ")
        self.assertTrue(get_res["success"])
        self.assertEqual(get_res["value"], "active_123")


class TestAudioAndMediaSensoryHands(unittest.TestCase):
    def test_get_current_media_info(self):
        res = get_current_media_info()
        self.assertTrue(res["success"])
        self.assertIn("has_media", res)

    def test_toggle_microphone_mute(self):
        res = toggle_microphone_mute()
        self.assertTrue(res["success"])


class TestBrowserHeadlessReading(unittest.TestCase):
    def test_fetch_webpage_text_invalid_url(self):
        res = fetch_webpage_text("")
        self.assertFalse(res["success"])

    def test_search_web_summary(self):
        res = search_web_summary("Python programming language")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(len(res["results"]), 1)


class TestEyesWatcher(unittest.TestCase):
    @patch("eyes.watcher.take_screenshot")
    def test_get_screen_hash(self, mock_take_screenshot):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"fake_image_pixels_123")
            tf_path = tf.name

        try:
            mock_take_screenshot.return_value = {"success": True, "file_path": tf_path}
            res = get_screen_hash()
            self.assertTrue(res["success"])
            self.assertGreater(len(res["hash"]), 10)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    @patch("eyes.watcher.get_screen_hash")
    def test_wait_for_visual_change(self, mock_get_hash):
        mock_get_hash.side_effect = [
            {"success": True, "hash": "hash_state_1"},
            {"success": True, "hash": "hash_state_1"},
            {"success": True, "hash": "hash_state_2_changed"},
        ]
        res = wait_for_visual_change(timeout=2.0, poll_interval=0.01)
        self.assertTrue(res["success"])
        self.assertTrue(res["changed"])

    @patch("eyes.watcher.get_screen_hash")
    def test_wait_for_screen_stabilize(self, mock_get_hash):
        mock_get_hash.return_value = {"success": True, "hash": "stable_hash_val"}
        res = wait_for_screen_stabilize(stable_duration=0.1, timeout=1.0, poll_interval=0.02)
        self.assertTrue(res["success"])
        self.assertTrue(res["stable"])


class TestRegistryAndAgentTerminalIntegration(unittest.TestCase):
    def test_registry_executes_terminal_action(self):
        self.assertIn("terminal", TOOL_CATALOG)
        res = execute_action("terminal", "run_command", command="Write-Output 'REGISTRY_EXEC_OK'")
        self.assertTrue(res["success"])
        self.assertIn("REGISTRY_EXEC_OK", res["stdout"])

    def test_agent_terminal_command_routing(self):
        cont, msg = handle_command("terminal Write-Output 'AGENT_CMD_ROUTED'")
        self.assertTrue(cont)
        self.assertIn("AGENT_CMD_ROUTED", msg)

    def test_agent_media_info_command_routing(self):
        cont, msg = handle_command("what song is playing")
        self.assertTrue(cont)
        self.assertIsNotNone(msg)

    def test_agent_mic_mute_routing(self):
        cont, msg = handle_command("mute mic")
        self.assertTrue(cont)
        self.assertIn("mute", msg.lower())


if __name__ == "__main__":
    unittest.main()
