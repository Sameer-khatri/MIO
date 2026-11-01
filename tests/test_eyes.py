"""
MIO Eyes Test Suite
-------------------
Verifies privacy guarantees, mechanical shutter mechanics, native OCR parsing,
UI Automation tree inspection, Hands collaboration, and Doctor integration.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure repo root is on sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [_ROOT, os.path.join(_ROOT, "core"), os.path.join(_ROOT, "hands"), os.path.join(_ROOT, "eyes"), os.path.join(_ROOT, "people")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import eyes
from eyes.guard import (
    is_window_safe,
    redact_sensitive_text,
    SafeEyeShutter,
    get_guard_status,
    SHUTTER_LOCKED,
)
from eyes.ocr import recognize_image
from eyes.ui_tree import inspect_ui_elements
from eyes.locator import locate_element
from eyes.reader import read_active_dialog
from core.agent import handle_command
from core.registry import execute_action
from people.aegis.aegis import AegisDoctor


class TestEyeGuard(unittest.TestCase):
    def test_shutter_default_state(self):
        status = get_guard_status()
        self.assertTrue(status["shutter_locked"])
        self.assertEqual(status["active_inspection_sessions"], 0)
        self.assertTrue(status["privacy_shield_active"])

    def test_privacy_shield_blacklisted_processes(self):
        for proc in ["bitwarden.exe", "1password", "KeePass.exe", "credentialuibroker.exe", "taskmgr"]:
            safe, reason = is_window_safe(title="My Notes", process_name=proc)
            self.assertFalse(safe, f"Process {proc} should be blocked by Privacy Shield")
            self.assertIn("Privacy Shield blocked", reason)

    def test_privacy_shield_sensitive_titles(self):
        for title in [
            "Google Chrome (Incognito)",
            "Bank Account Login - Chase",
            "Enter Master Password",
            "Sign In to Your Account",
            "Two-Factor Authenticator Setup",
        ]:
            safe, reason = is_window_safe(title=title, process_name="chrome.exe")
            self.assertFalse(safe, f"Title '{title}' should be blocked by Privacy Shield")
            self.assertIn("Privacy Shield blocked", reason)

    def test_privacy_shield_allowed_windows(self):
        safe, reason = is_window_safe(title="Visual Studio Code - mio", process_name="code.exe")
        self.assertTrue(safe)
        self.assertIn("Window cleared", reason)

    def test_shutter_context_manager(self):
        with SafeEyeShutter(target_title="Visual Studio Code", target_proc="code.exe") as shutter:
            self.assertTrue(shutter.is_open)
            self.assertFalse(eyes.guard.SHUTTER_LOCKED)
            self.assertEqual(eyes.guard._ACTIVE_SHUTTERS, 1)

        # After exiting context, shutter must immediately lock
        self.assertTrue(eyes.guard.SHUTTER_LOCKED)
        self.assertEqual(eyes.guard._ACTIVE_SHUTTERS, 0)

    def test_shutter_blocked_raises_permission_error(self):
        with self.assertRaises(PermissionError):
            with SafeEyeShutter(target_title="Chase Bank Login", target_proc="chrome.exe"):
                pass
        self.assertTrue(eyes.guard.SHUTTER_LOCKED)

    def test_redact_sensitive_text(self):
        raw = "My test visa 4111-2222-3333-4444 and key sk-1234567890abcdef1234567890abcdef with Bearer secret_token_abc_123_456_789"
        scrubbed = redact_sensitive_text(raw)
        self.assertNotIn("4111-2222-3333-4444", scrubbed)
        self.assertIn("[REDACTED_CARD]", scrubbed)
        self.assertNotIn("sk-1234567890abcdef1234567890abcdef", scrubbed)
        self.assertIn("[REDACTED_API_KEY]", scrubbed)
        self.assertIn("[REDACTED_TOKEN]", scrubbed)


class TestEyeOcr(unittest.TestCase):
    def test_ocr_nonexistent_image(self):
        res = recognize_image("C:\\nonexistent_image_12345.png")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

    @patch("subprocess.run")
    def test_ocr_parsing_with_mock(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"success": true, "text": "Skip Ad Now", "words": [{"text": "Skip", "x": 10, "y": 20, "width": 40, "height": 15, "clickable_x": 30, "clickable_y": 27}]}'
        mock_run.return_value = mock_proc

        with patch("os.path.exists", return_value=True):
            res = recognize_image("dummy.png")
            self.assertTrue(res["success"])
            self.assertEqual(res["text"], "Skip Ad Now")
            self.assertEqual(len(res["words"]), 1)
            self.assertEqual(res["words"][0]["clickable_x"], 30)


class TestUiTree(unittest.TestCase):
    def test_invalid_hwnd(self):
        res = inspect_ui_elements(hwnd=0)
        self.assertFalse(res["success"])
        self.assertIn("Invalid window handle", res["error"])

    @patch("subprocess.run")
    def test_ui_tree_parsing_with_mock(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"success": true, "hwnd": 1234, "total_found": 1, "elements": [{"name": "Save As", "type": "Button", "x": 100, "y": 200, "width": 80, "height": 30, "clickable_x": 140, "clickable_y": 215}]}'
        mock_run.return_value = mock_proc

        res = inspect_ui_elements(hwnd=1234, query="Save", window_title="Notepad", process_name="notepad")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_found"], 1)
        self.assertEqual(res["elements"][0]["name"], "Save As")
        self.assertEqual(res["elements"][0]["clickable_x"], 140)


class TestEyesHighLevel(unittest.TestCase):
    @patch("eyes.locator.inspect_ui_elements")
    @patch("eyes.locator.find_target_window")
    def test_see_finds_element(self, mock_win, mock_ui):
        mock_win.return_value = {"hwnd": 555, "title": "Calculator", "state": "normal"}
        mock_ui.return_value = {
            "success": True,
            "elements": [{
                "name": "Equals",
                "type": "Button",
                "x": 200,
                "y": 300,
                "width": 50,
                "height": 40,
                "clickable_x": 225,
                "clickable_y": 320,
            }]
        }

        res = eyes.see("Equals")
        self.assertTrue(res["success"])
        self.assertEqual(res["method"], "ui_tree")
        self.assertEqual(res["element"]["clickable_x"], 225)
        self.assertEqual(res["element"]["clickable_y"], 320)

    @patch("eyes.locate_element")
    @patch("eyes.move_cursor")
    @patch("eyes.mouse_click")
    def test_click_element_collaborates_with_hands(self, mock_click, mock_move, mock_loc):
        mock_loc.return_value = {
            "success": True,
            "element": {"clickable_x": 150, "clickable_y": 250},
            "method": "ui_tree",
        }
        mock_click.return_value = {"success": True, "message": "Clicked at (150, 250)"}

        res = eyes.click_element("Skip Ad")
        self.assertTrue(res["success"])
        mock_move.assert_called_once_with(150, 250)
        mock_click.assert_called_once_with(button="left", double=False)

    @patch("eyes.locate_element")
    @patch("eyes.move_cursor")
    @patch("eyes.mouse_click")
    @patch("eyes.type_text")
    def test_type_into_collaborates_with_hands(self, mock_type, mock_click, mock_move, mock_loc):
        mock_loc.return_value = {
            "success": True,
            "element": {"clickable_x": 120, "clickable_y": 180},
        }
        mock_type.return_value = {"success": True, "message": "Typed text"}

        res = eyes.type_into("Search", "believer song")
        self.assertTrue(res["success"])
        mock_move.assert_called_once_with(120, 180)
        mock_click.assert_called_once_with(button="left")
        mock_type.assert_called_once_with(text="believer song")


class TestDoctorAndAgentIntegration(unittest.TestCase):
    def test_registry_executes_eyes_get_status(self):
        res = execute_action("eyes", "get_status")
        self.assertTrue(res["shutter_locked"])
        self.assertTrue(res["privacy_shield_active"])

    def test_agent_eye_status_command(self):
        should_cont, msg = handle_command("eye status")
        self.assertTrue(should_cont)
        self.assertIn("MIO Eyes", msg)
        self.assertIn("Shutter [LOCKED (Secure)]", msg)

    @patch("eyes.click_element")
    def test_agent_click_command_dispatch(self, mock_click_el):
        mock_click_el.return_value = {
            "success": True,
            "method": "ui_tree",
            "coordinates": {"x": 300, "y": 400},
        }
        should_cont, msg = handle_command("click Skip Ad")
        self.assertTrue(should_cont)
        self.assertIn("Located 'Skip Ad'", msg)
        self.assertIn("(300, 400)", msg)

    @patch("eyes.read_dialog")
    def test_doctor_consult_uses_eyes(self, mock_read_dialog):
        mock_read_dialog.return_value = {
            "success": True,
            "window_title": "Windows Update Alert",
            "message": "Restart needed to complete driver installation",
            "buttons": [{"name": "Restart Now"}],
        }
        doc = AegisDoctor()
        consult = doc.doctor_consult("Doctor, I see an error alert popup on my screen")
        self.assertTrue(consult["success"])
        self.assertIn("Visual Screen Prompt (via MIO Eyes)", consult["doctor_diagnosis"])
        self.assertIn("Windows Update Alert", consult["doctor_diagnosis"])


if __name__ == "__main__":
    unittest.main()
