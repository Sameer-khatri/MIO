"""
Unit tests for MIO Flow & Workflow Orchestration Engine (hands.control.flow).
"""

import unittest
from unittest.mock import patch, MagicMock

from hands.control.flow import (
    parse_pipeline,
    execute_flow,
    run_pipeline,
    wait_for_window_state,
)
from core.agent import handle_command


class TestFlowEngine(unittest.TestCase):
    def test_parse_pipeline_delimiters(self):
        # Test 'then' delimiter
        steps = parse_pipeline("minimize antigravity then open youtube then maximize brave")
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "minimize antigravity")
        self.assertEqual(steps[1], "open youtube")
        self.assertEqual(steps[2], "maximize brave")

        # Test 'and then' delimiter
        steps = parse_pipeline("show desktop and then wait 1s and then open notepad")
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "show desktop")
        self.assertEqual(steps[1], "wait 1s")
        self.assertEqual(steps[2], "open notepad")

        # Test '->' delimiter
        steps = parse_pipeline("min vscode -> max terminal -> wait 500ms")
        self.assertEqual(len(steps), 3)

        # Test semicolon delimiter
        steps = parse_pipeline("minimize chrome; restore slack; focus brave")
        self.assertEqual(len(steps), 3)

        # Test action comma delimiter
        steps = parse_pipeline("minimize antigravity, open youtube search bbs, wait 2s, maximize antigravity")
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[0], "minimize antigravity")
        self.assertEqual(steps[1], "open youtube search bbs")
        self.assertEqual(steps[2], "wait 2s")
        self.assertEqual(steps[3], "maximize antigravity")

    def test_execute_flow_empty(self):
        res = execute_flow([])
        self.assertFalse(res["success"])
        self.assertEqual(res["total_steps"], 0)

    @patch("hands.control.flow.minimize_window")
    @patch("hands.control.flow.maximize_window")
    def test_execute_flow_structured(self, mock_max, mock_min):
        mock_min.return_value = {"success": True, "message": "Minimized"}
        mock_max.return_value = {"success": True, "message": "Maximized"}

        steps = [
            {"action": "minimize", "target": "antigravity"},
            {"action": "wait", "seconds": 0.01},
            {"action": "maximize", "target": "antigravity"},
        ]
        res = execute_flow(steps)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_steps"], 3)
        self.assertEqual(res["success_count"], 3)
        mock_min.assert_called_once_with("antigravity")
        mock_max.assert_called_once_with("antigravity")

    @patch("hands.control.flow.minimize_window")
    @patch("hands.control.flow.bring_to_foreground")
    def test_run_pipeline_string(self, mock_fg, mock_min):
        mock_min.return_value = {"success": True, "message": "Minimized"}
        mock_fg.return_value = {"success": True, "message": "Focused"}

        res = run_pipeline("minimize brave then focus antigravity")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_steps"], 2)
        mock_min.assert_called_once_with("brave")
        mock_fg.assert_called_once_with("antigravity")

    @patch("hands.control.flow.minimize_window")
    @patch("hands.control.flow.maximize_window")
    def test_agent_handle_command_flow_dispatch(self, mock_max, mock_min):
        mock_min.return_value = {"success": True, "message": "Minimized"}
        mock_max.return_value = {"success": True, "message": "Maximized"}

        # Test command with 'then'
        cont, msg = handle_command("minimize antigravity then wait 10ms then maximize antigravity")
        self.assertTrue(cont)
        self.assertIn("Executed 3/3 steps", msg)
        mock_min.assert_called_once_with("antigravity")
        mock_max.assert_called_once_with("antigravity")

    @patch("hands.control.flow._get_all_windows")
    def test_wait_for_window_state_timeout(self, mock_get):
        mock_get.return_value = []
        res = wait_for_window_state("nonexistent_app_xyz", timeout=0.05, poll_interval=0.01)
        self.assertFalse(res["success"])
        self.assertIn("Timed out", res["message"])


if __name__ == "__main__":
    unittest.main()
