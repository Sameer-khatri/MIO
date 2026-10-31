import os
import sys
import unittest

sys_agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys_agent_dir not in sys.path:
    sys.path.insert(0, sys_agent_dir)

from registry import (
    HAND_KITS,
    TOOL_CATALOG,
    list_kits,
    get_kit,
    list_all_tools,
    get_tool_module,
    execute_action,
    get_schemas,
)


class TestRegistry(unittest.TestCase):

    def test_kits_enumeration(self):
        kits_res = list_kits()
        self.assertTrue(kits_res["success"])
        self.assertEqual(len(kits_res["kits"]), 5)
        self.assertIn("sensory", kits_res["kits"])
        self.assertIn("action", kits_res["kits"])
        self.assertIn("control", kits_res["kits"])
        self.assertIn("storage", kits_res["kits"])
        self.assertIn("connectivity", kits_res["kits"])

    def test_get_kit_valid_and_invalid(self):
        sensory = get_kit("sensory")
        self.assertTrue(sensory["success"])
        self.assertIn("screen", sensory["tools"])
        self.assertIn("display", sensory["tools"])

        invalid = get_kit("unknown_kit_xyz")
        self.assertFalse(invalid["success"])

    def test_all_tools_catalog(self):
        tools_res = list_all_tools()
        self.assertTrue(tools_res["success"])
        self.assertEqual(tools_res["total_tools"], 25)
        self.assertEqual(len(TOOL_CATALOG), 25)

    def test_get_tool_module_dynamic_load(self):
        audio_mod = get_tool_module("audio")
        self.assertIsNotNone(audio_mod)
        self.assertTrue(hasattr(audio_mod, "set_volume"))

        with self.assertRaises(ValueError):
            get_tool_module("nonexistent_tool_123")

    def test_execute_action_dynamic_dispatch(self):
        # Test valid action execution via registry (e.g. hash_text on hasher tool)
        res = execute_action("hasher", "hash_text", text="Hello MIO", algorithm="sha256")
        self.assertTrue(res["success"])
        self.assertIn("hash", res)

        # Test invalid tool
        res_invalid_tool = execute_action("fake_tool", "do_something")
        self.assertFalse(res_invalid_tool["success"])

        # Test invalid action on valid tool
        res_invalid_act = execute_action("hasher", "nonexistent_action")
        self.assertFalse(res_invalid_act["success"])

    def test_get_schemas_generation(self):
        all_schemas = get_schemas()
        self.assertTrue(len(all_schemas) > 0)
        self.assertEqual(all_schemas[0]["type"], "function")
        self.assertIn("name", all_schemas[0]["function"])
        self.assertIn("parameters", all_schemas[0]["function"])

        sensory_schemas = get_schemas("sensory")
        self.assertTrue(len(sensory_schemas) > 0)
        self.assertTrue(len(sensory_schemas) < len(all_schemas))


if __name__ == "__main__":
    unittest.main()
