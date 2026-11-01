"""
Unit Tests for MIO Ears Subsystem
=================================
Tests microphone discovery, speech recognition engine inspection,
targeted grammar recognition, background listening lifecycle, and error boundaries.
"""

import unittest
import time
import ears
from core.registry import get_tool_module


class TestMioEars(unittest.TestCase):

    def test_microphone_enumeration(self):
        """Microphone enumeration should return a list of devices with id and name."""
        mics = ears.list_microphones()
        self.assertIsInstance(mics, list)
        if mics:
            first = mics[0]
            self.assertIn("id", first)
            self.assertIn("name", first)
            self.assertIn("channels", first)

    def test_is_microphone_available(self):
        """Should return a boolean indicating mic presence."""
        avail = ears.is_microphone_available()
        self.assertIsInstance(avail, bool)

    def test_get_default_microphone(self):
        """Default microphone should either be None or a valid dict."""
        default_mic = ears.get_default_microphone()
        if ears.is_microphone_available():
            self.assertIsNotNone(default_mic)
            self.assertIn("name", default_mic)
        else:
            self.assertIsNone(default_mic)

    def test_recognizer_info(self):
        """Windows Speech Recognition engine info should be discoverable."""
        info = ears.get_recognizer_info()
        self.assertIsInstance(info, dict)
        self.assertIn("available", info)
        self.assertIn("engines", info)
        if info["available"]:
            self.assertGreater(info["count"], 0)
            self.assertIn("Id", info["primary"])

    def test_listen_silence_timeout(self):
        """Calling listen with short timeout should cleanly return silence or heard."""
        result = ears.listen(timeout=0.8, phrase_limit=1.0)
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn(result["status"], ["silence", "heard", "error"])
        self.assertIn("text", result)
        self.assertIn("confidence", result)
        self.assertIn("duration", result)

    def test_listen_for_empty_phrases(self):
        """Empty target phrases list should fail safely with error status."""
        result = ears.listen_for([], timeout=1.0)
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_listen_for_silence_timeout(self):
        """Calling listen_for with short timeout should handle silence cleanly."""
        result = ears.listen_for(["yes", "no", "stop"], timeout=0.8)
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn(result["status"], ["silence", "heard", "error"])
        self.assertIn("text", result)

    def test_background_listening_lifecycle(self):
        """Should cleanly start, verify active state, and stop background listening."""
        heard_items = []
        def on_heard(data):
            heard_items.append(data)

        # Initially not listening
        self.assertFalse(ears.is_listening())

        # Start background listener
        started = ears.listen_background(on_heard, timeout_per_phrase=1.0)
        self.assertTrue(started)
        self.assertTrue(ears.is_listening())

        # Duplicate start should return False
        dup_start = ears.listen_background(on_heard)
        self.assertFalse(dup_start)

        # Stop listening
        stopped = ears.stop_listening()
        self.assertTrue(stopped)
        self.assertFalse(ears.is_listening())

    def test_registry_integration(self):
        """Core registry should dynamically resolve 'ears' module."""
        mod = get_tool_module("ears")
        self.assertTrue(hasattr(mod, "listen"))
        self.assertTrue(hasattr(mod, "listen_for"))
        self.assertTrue(hasattr(mod, "list_microphones"))

    def test_module_exports(self):
        """All expected APIs should be present in ears.__all__."""
        for item in [
            "listen",
            "listen_for",
            "listen_background",
            "stop_listening",
            "is_listening",
            "list_microphones",
            "get_default_microphone",
            "is_microphone_available",
            "get_recognizer_info",
        ]:
            self.assertTrue(hasattr(ears, item), f"Missing export '{item}' in ears")


if __name__ == "__main__":
    unittest.main()
