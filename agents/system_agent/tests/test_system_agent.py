import unittest
from unittest.mock import patch, MagicMock
import json
import os
import shutil
import tempfile
import sys

# Ensure system_agent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import handle_command, extract_is_running_target, extract_where_target
from tools.applications import (
    open_application,
    discover_all_applications,
    load_memory,
    save_memory,
    remember_application,
    forget_application,
    find_in_memory,
    normalize_name,
    deduplicate_memory,
    launch_app,
    _get_start_menu_shortcuts,
    _get_registry_app_paths,
    _get_packaged_start_apps,
    _get_path_executable,
    BUILTIN_APPS,
    ALIASES,
)
from tools.processes import (
    get_running_applications,
    is_application_running,
    get_friendly_name,
    KNOWN_PROCESS_NAMES,
    IGNORED_PROCESS_NAMES,
)
from tools.filesystem import (
    resolve_location,
    list_files,
    find_file_or_folder,
    create_folder,
    locate_executable,
    locate_executable_in_path,
    FRIENDLY_LOCATIONS,
)


class TestSystemAgent(unittest.TestCase):
    def setUp(self):
        self.patcher_mem = patch("tools.applications.load_memory", return_value={})
        self.mock_load_mem = self.patcher_mem.start()

        self.patcher_save = patch("tools.applications.save_memory")
        self.mock_save_mem = self.patcher_save.start()

    def tearDown(self):
        self.patcher_mem.stop()
        self.patcher_save.stop()

    def use_fake_memory(self, fake_storage):
        self.mock_load_mem.side_effect = lambda: fake_storage

        def save_fake_memory(data):
            snapshot = json.loads(json.dumps(data))
            fake_storage.clear()
            fake_storage.update(snapshot)

        self.mock_save_mem.side_effect = save_fake_memory

    # -------------------------------------------------------------
    # 1. Normalization & Deduplication Tests
    # -------------------------------------------------------------
    def test_normalize_name(self):
        self.assertEqual(normalize_name("  Google   Chrome  "), "google chrome")
        self.assertEqual(normalize_name("WhatsApp"), "whatsapp")
        self.assertEqual(normalize_name("VISUAL STUDIO CODE"), "visual studio code")
        self.assertEqual(normalize_name(""), "")
        self.assertEqual(normalize_name(None), "")

    def test_deduplicate_memory_merges_duplicates(self):
        raw_memory = {
            "chrome": {
                "name": "Google Chrome",
                "launch_method": "shortcut",
                "target": r"C:\Programs\Google Chrome.lnk"
            },
            "google chrome": {
                "name": "Google Chrome",
                "launch_method": "shortcut",
                "target": r"C:\Programs\Google Chrome.lnk"
            }
        }
        cleaned = deduplicate_memory(raw_memory)
        self.assertEqual(len(cleaned), 1)
        self.assertIn("chrome", cleaned)
        self.assertEqual(cleaned["chrome"]["name"], "Google Chrome")
        self.assertIn("google chrome", cleaned["chrome"]["aliases"])

    def test_remember_application_prevents_duplicate_records(self):
        fake_storage = {}
        self.mock_load_mem.side_effect = lambda: fake_storage
        self.mock_save_mem.side_effect = lambda data: fake_storage.update(data)

        remember_application("chrome", "Google Chrome", "shortcut", r"C:\Programs\Google Chrome.lnk")
        self.assertIn("chrome", fake_storage)
        self.assertEqual(len(fake_storage), 1)

        remember_application("google chrome", "Google Chrome", "shortcut", r"C:\Programs\Google Chrome.lnk")
        self.assertEqual(len(fake_storage), 1)
        self.assertIn("google chrome", fake_storage["chrome"]["aliases"])

    def test_find_in_memory_by_alias(self):
        mock_memory = {
            "chrome": {
                "name": "Google Chrome",
                "aliases": ["google chrome"],
                "launch_method": "shortcut",
                "target": r"C:\Programs\Google Chrome.lnk"
            }
        }
        k1, r1 = find_in_memory("chrome", mock_memory)
        self.assertEqual(k1, "chrome")
        self.assertEqual(r1["name"], "Google Chrome")

        k2, r2 = find_in_memory("google chrome", mock_memory)
        self.assertEqual(k2, "chrome")
        self.assertEqual(r2["name"], "Google Chrome")

    # -------------------------------------------------------------
    # 2. Running Processes Tool Tests (tools/processes.py)
    # -------------------------------------------------------------
    def test_get_friendly_name(self):
        self.assertEqual(get_friendly_name("chrome", "Count GitHub Branches - Google Chrome"), "Google Chrome")
        self.assertEqual(get_friendly_name("brave", "New Tab - Brave"), "Brave")
        self.assertEqual(get_friendly_name("whatsapp.root", "WhatsApp"), "WhatsApp")
        self.assertEqual(get_friendly_name("antigravity ide", "PRIMEX - Antigravity IDE"), "Antigravity IDE")

    @patch("tools.processes._get_apps_from_powershell")
    def test_get_running_applications_success(self, mock_ps):
        mock_ps.return_value = [
            {"pid": 101, "process_name": "chrome", "window_title": "Google Chrome"},
            {"pid": 102, "process_name": "chrome", "window_title": "Another Tab - Google Chrome"},
            {"pid": 201, "process_name": "WhatsApp.Root", "window_title": "WhatsApp"},
            {"pid": 301, "process_name": "svchost", "window_title": "Host Window"},
            {"pid": 401, "process_name": "Antigravity IDE", "window_title": "PRIMEX - Antigravity IDE"},
        ]

        result = get_running_applications()
        self.assertTrue(result["success"])
        names = [app["name"] for app in result["apps"]]

        self.assertIn("Google Chrome", names)
        self.assertIn("WhatsApp", names)
        self.assertIn("Antigravity IDE", names)
        self.assertNotIn("Host Window", names)
        self.assertEqual(names.count("Google Chrome"), 1)
        self.assertEqual(len(result["apps"]), 3)

    @patch("tools.processes._get_apps_from_tasklist", return_value=[])
    @patch("tools.processes._get_apps_from_powershell", return_value=[])
    def test_get_running_applications_empty(self, mock_ps, mock_tl):
        result = get_running_applications()
        self.assertTrue(result["success"])
        self.assertEqual(result["apps"], [])
        self.assertEqual(result["message"], "No running applications found.")

    @patch("tools.processes.get_running_applications")
    def test_is_application_running(self, mock_get_running):
        mock_get_running.return_value = {
            "success": True,
            "apps": [
                {"name": "Google Chrome", "process_name": "chrome", "pid": 100},
            ]
        }

        res_running = is_application_running("chrome")
        self.assertTrue(res_running["success"])
        self.assertTrue(res_running["running"])
        self.assertEqual(res_running["name"], "Google Chrome")

        res_not_running = is_application_running("spotify")
        self.assertTrue(res_not_running["success"])
        self.assertFalse(res_not_running["running"])
        self.assertEqual(res_not_running["name"], "Spotify")

    # -------------------------------------------------------------
    # 3. Filesystem Tool Tests (tools/filesystem.py)
    # -------------------------------------------------------------
    def test_resolve_location_friendly(self):
        home = os.path.expanduser("~")
        self.assertEqual(resolve_location("desktop"), os.path.join(home, "Desktop"))
        self.assertEqual(resolve_location("downloads"), os.path.join(home, "Downloads"))
        self.assertEqual(resolve_location("documents"), os.path.join(home, "Documents"))
        self.assertEqual(resolve_location("pictures"), os.path.join(home, "Pictures"))
        self.assertIsNone(resolve_location(""))
        self.assertIsNone(resolve_location(None))

    def test_list_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = os.path.join(tmpdir, "report.pdf")
            d1 = os.path.join(tmpdir, "images")
            open(f1, "w").close()
            os.mkdir(d1)

            res = list_files(tmpdir)
            self.assertTrue(res["success"])
            self.assertIn("report.pdf", res["items"])
            self.assertIn("images", res["items"])

    def test_list_files_invalid(self):
        res = list_files("non_existent_folder_xyz_123")
        self.assertFalse(res["success"])
        self.assertIn("not found", res["message"])

    def test_create_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = create_folder("new_project", tmpdir)
            self.assertTrue(res["success"])
            self.assertIn("created successfully", res["message"])
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "new_project")))

            # Already exists case
            res_exists = create_folder("new_project", tmpdir)
            self.assertTrue(res_exists["success"])
            self.assertTrue(res_exists.get("already_exists"))
            self.assertIn("already exists", res_exists["message"])

    def test_find_file_or_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "mio_subfolder")
            os.mkdir(sub)
            target_file = os.path.join(sub, "report.pdf")
            open(target_file, "w").close()

            with patch("tools.filesystem.resolve_location", side_effect=lambda l: tmpdir if l in ["desktop", "documents", "downloads"] else None):
                # Search for file
                res_file = find_file_or_folder("report.pdf")
                self.assertTrue(res_file["success"])
                self.assertTrue(any("report.pdf" in m.lower() for m in res_file["matches"]))

                # Search for folder with suffix
                res_folder = find_file_or_folder("mio_subfolder folder")
                self.assertTrue(res_folder["success"])
                self.assertTrue(any("mio_subfolder" in m.lower() for m in res_folder["matches"]))

    def test_valid_remembered_path_reused(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            remembered = os.path.join(tmpdir, "stable_project")
            os.mkdir(remembered)
            fake_storage = {
                "stable_project": {
                    "name": "stable_project",
                    "aliases": [],
                    "record_type": "path",
                    "launch_method": "folder",
                    "target": remembered,
                }
            }
            self.use_fake_memory(fake_storage)

            with patch("tools.filesystem.resolve_location", return_value=tmpdir):
                res = find_file_or_folder("stable_project")

            self.assertTrue(res["success"])
            self.assertEqual(res["matches"][0], remembered)
            self.assertEqual(fake_storage["stable_project"]["target"], remembered)
            self.assertIn("last_verified", fake_storage["stable_project"])

    def test_deleted_remembered_folder_triggers_rediscovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop = os.path.join(tmpdir, "Desktop")
            documents = os.path.join(tmpdir, "Documents")
            os.mkdir(desktop)
            os.mkdir(documents)
            old_path = os.path.join(desktop, "missing_project")
            new_path = os.path.join(documents, "missing_project")
            os.mkdir(new_path)
            fake_storage = {
                "missing_project": {
                    "name": "missing_project",
                    "aliases": [],
                    "record_type": "path",
                    "launch_method": "folder",
                    "target": old_path,
                }
            }
            self.use_fake_memory(fake_storage)

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else documents):
                res = find_file_or_folder("missing_project")

            self.assertTrue(res["success"])
            self.assertEqual(res["matches"][0], new_path)
            self.assertEqual(len(fake_storage), 1)
            self.assertEqual(next(iter(fake_storage.values()))["target"], new_path)

    def test_moved_folder_updates_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop = os.path.join(tmpdir, "Desktop")
            documents = os.path.join(tmpdir, "Documents")
            os.mkdir(desktop)
            os.mkdir(documents)
            old_path = os.path.join(desktop, "AIRA")
            new_path = os.path.join(documents, "AIRA")
            os.mkdir(new_path)
            fake_storage = {
                "aira": {
                    "name": "AIRA",
                    "aliases": ["project aira"],
                    "record_type": "path",
                    "launch_method": "folder",
                    "target": old_path,
                }
            }
            self.use_fake_memory(fake_storage)

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else documents):
                res = find_file_or_folder("AIRA")

            self.assertTrue(res["success"])
            self.assertEqual(res["matches"][0], new_path)
            self.assertEqual(fake_storage["aira"]["target"], new_path)
            self.assertIn("project aira", fake_storage["aira"]["aliases"])

    # -------------------------------------------------------------
    # 4. Executable / Application Lookup Tests (tools/filesystem.py)
    # -------------------------------------------------------------
    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={
        "WhatsApp": {"name": "WhatsApp", "launch_method": "appid", "target": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"}
    })
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={
        "Google Chrome": {"name": "Google Chrome", "launch_method": "shortcut", "target": r"C:\ProgramData\...\Google Chrome.lnk"}
    })
    @patch("tools.applications.load_memory")
    def test_locate_executable_from_memory(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        mock_mem.return_value = {
            "whatsapp": {
                "name": "WhatsApp",
                "aliases": [],
                "launch_method": "appid",
                "target": "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App"
            }
        }
        from tools.filesystem import locate_executable
        res = locate_executable("whatsapp")
        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "WhatsApp")
        self.assertEqual(res["type"], "appid")
        self.assertIn("5319275A", res["target"])

    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_builtin(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        from tools.filesystem import locate_executable
        res = locate_executable("notepad")
        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "notepad")
        self.assertEqual(res["type"], "exe")
        self.assertEqual(res["target"], "notepad.exe")

    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_path_single(self, mock_mem, mock_sm, mock_reg, mock_pkg):
        from tools.filesystem import locate_executable
        with patch("tools.filesystem._path_lookup", return_value=[r"C:\Program Files\nodejs\node.exe"]):
            res = locate_executable("node")
            self.assertTrue(res["success"])
            self.assertEqual(res["type"], "exe")
            self.assertEqual(res["matches"], [r"C:\Program Files\nodejs\node.exe"])
            self.assertEqual(res["message"], "Found node.")

    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_path_multiple(self, mock_mem, mock_sm, mock_reg, mock_pkg):
        from tools.filesystem import locate_executable
        with patch("tools.filesystem._path_lookup", return_value=[
            r"C:\Python311\python.exe",
            r"C:\Users\User\AppData\Local\Microsoft\WindowsApps\python.exe"
        ]):
            res = locate_executable("python")
            self.assertTrue(res["success"])
            self.assertEqual(len(res["matches"]), 2)

    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={
        "Google Chrome": {"name": "Google Chrome", "launch_method": "shortcut", "target": r"C:\ProgramData\...\Google Chrome.lnk"}
    })
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_start_menu_shortcut(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        from tools.filesystem import locate_executable
        res = locate_executable("google chrome")
        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "Google Chrome")
        self.assertEqual(res["type"], "shortcut")
        self.assertIn(".lnk", res["target"])

    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={
        "WhatsApp": {"name": "WhatsApp", "launch_method": "appid", "target": "5319275A.WhatsAppDesktop!App"}
    })
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_packaged_app(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        from tools.filesystem import locate_executable
        res = locate_executable("whatsapp")
        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "WhatsApp")
        self.assertEqual(res["type"], "appid")
        self.assertIn("5319275A", res["target"])

    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory", return_value={})
    def test_locate_executable_not_found(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        from tools.filesystem import locate_executable
        res = locate_executable("nonexistent_xyz_tool_12345")
        self.assertTrue(res["success"])
        self.assertIsNone(res["name"])
        self.assertEqual(res["matches"], [])
        self.assertIn("couldn't locate", res["message"])

    def test_broken_executable_path_triggers_rediscovery(self):
        fake_storage = {
            "node": {
                "name": "node",
                "aliases": [],
                "record_type": "application",
                "launch_method": "exe",
                "target": r"C:\Old\node.exe",
            }
        }
        self.use_fake_memory(fake_storage)

        with patch("tools.applications.os.path.isfile", return_value=False), \
             patch("tools.applications._get_packaged_start_apps", return_value={}), \
             patch("tools.applications._get_registry_app_paths", return_value={}), \
             patch("tools.applications._get_start_menu_shortcuts", return_value={}), \
             patch("tools.filesystem._path_lookup", return_value=[r"C:\New\node.exe"]):
            res = locate_executable("node")

        self.assertTrue(res["success"])
        self.assertEqual(res["target"], r"C:\New\node.exe")
        self.assertEqual(len(fake_storage), 1)
        self.assertEqual(fake_storage["node"]["target"], r"C:\New\node.exe")

    def test_broken_shortcut_triggers_rediscovery(self):
        fake_storage = {
            "chrome": {
                "name": "Google Chrome",
                "aliases": ["google chrome"],
                "record_type": "application",
                "launch_method": "shortcut",
                "target": r"C:\Old\Chrome.lnk",
            }
        }
        self.use_fake_memory(fake_storage)

        with patch("tools.applications.os.path.isfile", return_value=False), \
             patch("tools.filesystem._path_lookup", return_value=[]), \
             patch("tools.applications._get_packaged_start_apps", return_value={}), \
             patch("tools.applications._get_registry_app_paths", return_value={}), \
             patch("tools.applications._get_start_menu_shortcuts", return_value={
                 "Google Chrome": {"name": "Google Chrome", "launch_method": "shortcut", "target": r"C:\New\Chrome.lnk"}
             }):
            res = locate_executable("chrome")

        self.assertTrue(res["success"])
        self.assertEqual(res["target"], r"C:\New\Chrome.lnk")
        self.assertEqual(len(fake_storage), 1)
        self.assertEqual(fake_storage["chrome"]["target"], r"C:\New\Chrome.lnk")

    def test_stale_appid_triggers_rediscovery_where_practical(self):
        fake_storage = {
            "whatsapp": {
                "name": "WhatsApp",
                "aliases": [],
                "record_type": "application",
                "launch_method": "appid",
                "target": "Old.WhatsApp!App",
            }
        }
        self.use_fake_memory(fake_storage)

        with patch("tools.filesystem._path_lookup", return_value=[]), \
             patch("tools.applications._get_registry_app_paths", return_value={}), \
             patch("tools.applications._get_start_menu_shortcuts", return_value={}), \
             patch("tools.applications._get_packaged_start_apps", return_value={
                 "WhatsApp": {"name": "WhatsApp", "launch_method": "appid", "target": "New.WhatsApp!App"}
             }):
            res = locate_executable("whatsapp")

        self.assertTrue(res["success"])
        self.assertEqual(res["target"], "New.WhatsApp!App")
        self.assertEqual(fake_storage["whatsapp"]["target"], "New.WhatsApp!App")

    def test_aliases_still_work_after_target_changes(self):
        fake_storage = {
            "chrome": {
                "name": "Google Chrome",
                "aliases": ["google chrome"],
                "record_type": "application",
                "launch_method": "shortcut",
                "target": r"C:\Old\Chrome.lnk",
            }
        }
        self.use_fake_memory(fake_storage)

        with patch("tools.applications.os.path.isfile", return_value=False), \
             patch("tools.filesystem._path_lookup", return_value=[]), \
             patch("tools.applications._get_packaged_start_apps", return_value={}), \
             patch("tools.applications._get_registry_app_paths", return_value={}), \
             patch("tools.applications._get_start_menu_shortcuts", return_value={
                 "Google Chrome": {"name": "Google Chrome", "launch_method": "shortcut", "target": r"C:\New\Chrome.lnk"}
             }):
            res = locate_executable("google chrome")

        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "Google Chrome")
        self.assertEqual(res["target"], r"C:\New\Chrome.lnk")
        self.assertEqual(len(fake_storage), 1)

    def test_duplicate_memory_is_not_created_after_target_update(self):
        fake_storage = {
            "chrome": {
                "name": "Google Chrome",
                "aliases": ["browser"],
                "record_type": "application",
                "launch_method": "shortcut",
                "target": r"C:\Old\Chrome.lnk",
            }
        }
        self.use_fake_memory(fake_storage)

        remember_application("google chrome", "Google Chrome", "shortcut", r"C:\New\Chrome.lnk")
        remember_application("chrome", "Google Chrome", "shortcut", r"C:\New\Chrome.lnk")

        self.assertEqual(len(fake_storage), 1)
        self.assertEqual(fake_storage["chrome"]["target"], r"C:\New\Chrome.lnk")
        self.assertIn("google chrome", fake_storage["chrome"]["aliases"])

    @patch("tools.filesystem._path_lookup", return_value=[])
    @patch("tools.applications._get_packaged_start_apps", return_value={})
    @patch("tools.applications._get_registry_app_paths", return_value={})
    @patch("tools.applications._get_start_menu_shortcuts", return_value={})
    @patch("tools.applications.load_memory")
    def test_locate_executable_case_insensitive(self, mock_mem, mock_sm, mock_reg, mock_pkg, mock_path):
        mock_mem.return_value = {
            "chrome": {
                "name": "Google Chrome",
                "aliases": ["google chrome"],
                "launch_method": "shortcut",
                "target": r"C:\ProgramData\...\Google Chrome.lnk"
            }
        }
        from tools.filesystem import locate_executable
        with patch("tools.applications.os.path.isfile", return_value=True):
            for query in ("Chrome", "CHROME", "chrome"):
                with self.subTest(query=query):
                    res = locate_executable(query)
                    self.assertTrue(res["success"])
                    self.assertEqual(res["name"], "Google Chrome")

    # -------------------------------------------------------------
    # 5. Where Target Extraction Tests (agent.py)
    # -------------------------------------------------------------
    def test_extract_where_target(self):
        self.assertEqual(extract_where_target("where is node?"), "node")
        self.assertEqual(extract_where_target("where is node"), "node")
        self.assertEqual(extract_where_target("where node"), "node")
        self.assertEqual(extract_where_target("where node?"), "node")
        self.assertEqual(extract_where_target("WHERE IS PYTHON?"), "PYTHON")
        self.assertIsNone(extract_where_target("where"))
        self.assertIsNone(extract_where_target("is node running?"))

    # -------------------------------------------------------------
    # 6. Command Handler Tests (agent.py)
    # -------------------------------------------------------------
    def test_handle_command_where_exe(self):
        with patch("agent.locate_executable", return_value={
            "success": True, "query": "node", "type": "exe",
            "name": "node", "target": r"C:\Program Files\nodejs\node.exe",
            "matches": [r"C:\Program Files\nodejs\node.exe"],
            "message": "Found node."
        }):
            should_continue, msg = handle_command("where is node?")
            self.assertTrue(should_continue)
            self.assertIn("Application: node", msg)
            self.assertIn("Type: Executable", msg)
            self.assertIn(r"C:\Program Files\nodejs\node.exe", msg)

    def test_handle_command_where_appid(self):
        with patch("agent.locate_executable", return_value={
            "success": True, "query": "whatsapp", "type": "appid",
            "name": "WhatsApp", "target": "5319275A.WhatsAppDesktop!App",
            "matches": ["5319275A.WhatsAppDesktop!App"],
            "message": "Found WhatsApp."
        }):
            should_continue, msg = handle_command("where is whatsapp?")
            self.assertTrue(should_continue)
            self.assertIn("Application: WhatsApp", msg)
            self.assertIn("Type: Windows packaged app", msg)
            self.assertIn("AppID: 5319275A", msg)

    def test_handle_command_where_shortcut(self):
        with patch("agent.locate_executable", return_value={
            "success": True, "query": "chrome", "type": "shortcut",
            "name": "Google Chrome", "target": r"C:\ProgramData\...\Google Chrome.lnk",
            "matches": [r"C:\ProgramData\...\Google Chrome.lnk"],
            "message": "Found Google Chrome."
        }):
            should_continue, msg = handle_command("where chrome")
            self.assertTrue(should_continue)
            self.assertIn("Application: Google Chrome", msg)
            self.assertIn("Type: Shortcut", msg)
            self.assertIn("Location:", msg)

    def test_handle_command_where_not_found(self):
        with patch("agent.locate_executable", return_value={
            "success": True, "query": "nope", "type": None,
            "name": None, "target": None, "matches": [],
            "message": "I couldn't locate 'nope' on this system."
        }):
            should_continue, msg = handle_command("where is nope?")
            self.assertTrue(should_continue)
            self.assertEqual(msg, "I couldn't locate 'nope' on this system.")

    def test_handle_command_filesystem(self):
        with patch("agent.list_files", return_value={"success": True, "location": "Downloads", "items": ["file1.txt", "file2.pdf"]}):
            should_continue, msg = handle_command("show files in downloads")
            self.assertTrue(should_continue)
            self.assertIn("Downloads:", msg)
            self.assertIn("- file1.txt", msg)

        with patch("agent.create_folder", return_value={"success": True, "message": "Folder 'test' created successfully."}):
            should_continue, msg = handle_command("create folder test in desktop")
            self.assertTrue(should_continue)
            self.assertIn("✅ Folder 'test' created successfully.", msg)

        with patch("agent.find_file_or_folder", return_value={"success": True, "matches": [r"C:\Users\Desktop\test"]}):
            should_continue, msg = handle_command("find test folder")
            self.assertTrue(should_continue)
            self.assertIn("Found:", msg)
            self.assertIn(r"C:\Users\Desktop\test", msg)

    def test_handle_command_exit_quit(self):
        for cmd in ["exit", "quit", "EXIT", "QUIT"]:
            with self.subTest(cmd=cmd):
                should_continue, msg = handle_command(cmd)
                self.assertFalse(should_continue)
                self.assertEqual(msg, "Goodbye.")

    def test_handle_command_empty(self):
        should_continue, msg = handle_command("")
        self.assertTrue(should_continue)
        self.assertIsNone(msg)


if __name__ == "__main__":
    unittest.main()
