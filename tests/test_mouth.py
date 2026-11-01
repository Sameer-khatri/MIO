"""
Unit tests for MIO Mouth (Vocal Speech Synthesis & Auditory Output Subsystem).
"""

import unittest
from unittest.mock import patch, MagicMock

import mouth
from mouth.voices import list_installed_voices, get_default_voice, find_voice
from mouth.speaker import (
    speak,
    say,
    stop,
    is_speaking,
    set_voice,
    set_rate,
    set_volume,
    get_voice_settings,
)
from core.registry import get_tool_module


class TestMouthVoices(unittest.TestCase):
    def test_list_installed_voices(self):
        voices = list_installed_voices()
        self.assertIsInstance(voices, list)
        self.assertGreaterEqual(len(voices), 1)

        first = voices[0]
        self.assertIn("name", first)
        self.assertIn("gender", first)
        self.assertIn("engine", first)

    def test_get_default_voice(self):
        v = get_default_voice()
        self.assertIsNotNone(v)
        self.assertIn("name", v)

    def test_find_voice_by_name_and_gender(self):
        # By gender
        female = find_voice("female")
        if female:
            self.assertEqual(female["gender"], "Female")

        male = find_voice("male")
        if male:
            self.assertEqual(male["gender"], "Male")

        # Nonexistent
        none_voice = find_voice("nonexistent_voice_9999_xyz")
        self.assertIsNone(none_voice)


class TestMouthSpeakerSettings(unittest.TestCase):
    def test_set_rate_and_clamping(self):
        res = set_rate(5)
        self.assertTrue(res["success"])
        self.assertEqual(res["rate"], 5)

        # Clamping above +10
        res_high = set_rate(99)
        self.assertTrue(res_high["success"])
        self.assertEqual(res_high["rate"], 10)

        # Clamping below -10
        res_low = set_rate(-50)
        self.assertTrue(res_low["success"])
        self.assertEqual(res_low["rate"], -10)

        # Invalid type
        res_inv = set_rate("not_a_number")
        self.assertFalse(res_inv["success"])

    def test_set_volume_and_clamping(self):
        res = set_volume(75)
        self.assertTrue(res["success"])
        self.assertEqual(res["volume"], 75)

        # Clamping
        res_high = set_volume(150)
        self.assertTrue(res_high["success"])
        self.assertEqual(res_high["volume"], 100)

        res_low = set_volume(-20)
        self.assertTrue(res_low["success"])
        self.assertEqual(res_low["volume"], 0)

        res_inv = set_volume("invalid")
        self.assertFalse(res_inv["success"])

    def test_set_voice(self):
        res = set_voice("zira")
        if res.get("success"):
            self.assertIn("zira", res["voice"].lower())
            settings = get_voice_settings()
            self.assertIn("zira", settings["voice"].lower())

        inv = set_voice("completely_fake_voice_xyz")
        self.assertFalse(inv["success"])


class TestMouthSpeechExecution(unittest.TestCase):
    def test_speak_empty_text(self):
        res1 = speak("")
        self.assertFalse(res1["success"])

        res2 = speak("   ")
        self.assertFalse(res2["success"])

        res3 = speak(None)
        self.assertFalse(res3["success"])

    @patch("subprocess.Popen")
    def test_speak_async_mocked(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        res = speak("Hello world from MIO Mouth", async_speech=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "async")
        self.assertTrue(is_speaking())

        # Test stop
        stop_res = stop()
        self.assertTrue(stop_res["success"])
        self.assertTrue(stop_res["stopped"])
        mock_proc.terminate.assert_called_once()
        self.assertFalse(is_speaking())

    @patch("subprocess.Popen")
    def test_speak_blocking_mocked(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        res = speak("Blocking test", async_speech=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "blocking")
        mock_proc.wait.assert_called_once()

    def test_registry_integration_loads_mouth(self):
        mouth_mod = get_tool_module("mouth")
        self.assertIsNotNone(mouth_mod)
        self.assertTrue(hasattr(mouth_mod, "speak"))
        self.assertTrue(hasattr(mouth_mod, "say"))
        self.assertTrue(hasattr(mouth_mod, "stop"))


if __name__ == "__main__":
    unittest.main()
