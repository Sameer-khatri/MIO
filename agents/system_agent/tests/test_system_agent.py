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
    resolve_destination,
    list_files,
    find_file_or_folder,
    create_folder,
    copy_file_or_folder,
    move_file_or_folder,
    rename_file_or_folder,
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

    def test_resolve_destination_absolute_and_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "Documents", "Reports")
            os.makedirs(nested)

            absolute = resolve_destination(nested)
            self.assertTrue(absolute["success"])
            self.assertEqual(absolute["path"], nested)

            with patch("tools.filesystem.resolve_location", side_effect=lambda name: os.path.join(tmpdir, name.title())):
                relative = resolve_destination("Documents\\Reports")
            self.assertTrue(relative["success"])
            self.assertEqual(relative["path"], nested)

    def test_resolve_destination_remembered_and_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            remembered = os.path.join(tmpdir, "remembered")
            os.mkdir(remembered)
            fake_storage = {
                "remembered": {
                    "name": "remembered",
                    "aliases": [],
                    "record_type": "path",
                    "launch_method": "folder",
                    "target": remembered,
                }
            }
            self.use_fake_memory(fake_storage)
            result = resolve_destination("remembered")
            self.assertTrue(result["success"])
            self.assertEqual(result["path"], remembered)

            shutil.rmtree(remembered)
            replacement = os.path.join(tmpdir, "Desktop", "remembered")
            os.makedirs(replacement)
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: os.path.dirname(replacement) if name == "desktop" else tmpdir):
                result = resolve_destination("remembered")
            self.assertTrue(result["success"])
            self.assertEqual(result["path"], replacement)
            self.assertEqual(fake_storage["remembered"]["target"], replacement)

    def test_resolve_destination_unique_ambiguous_and_missing_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop = os.path.join(tmpdir, "Desktop")
            documents = os.path.join(tmpdir, "Documents")
            os.makedirs(os.path.join(desktop, "unique"))
            os.makedirs(documents)
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop if name == "desktop" else documents):
                unique = resolve_destination("unique")
            self.assertTrue(unique["success"])
            self.assertEqual(unique["path"], os.path.join(desktop, "unique"))

            os.makedirs(os.path.join(documents, "ambiguous"))
            os.makedirs(os.path.join(desktop, "ambiguous"))
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop if name == "desktop" else documents):
                ambiguous = resolve_destination("ambiguous")
                missing = resolve_destination("no_such_destination")
            self.assertFalse(ambiguous["success"])
            self.assertEqual(len(ambiguous["matches"]), 2)
            self.assertIn("Please be more specific.", ambiguous["message"])
            self.assertFalse(missing["success"])
            self.assertIn("not found", missing["message"])

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

    def test_copy_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            desktop = os.path.join(tmpdir, "Desktop")
            os.mkdir(source_root)
            os.mkdir(desktop)
            source_file = os.path.join(source_root, "report.pdf")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write("copy me")

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else source_root):
                res = copy_file_or_folder("report.pdf", "desktop")

            destination = os.path.join(desktop, "report.pdf")
            self.assertTrue(res["success"])
            self.assertEqual(res["source"], source_file)
            self.assertEqual(res["destination"], destination)
            self.assertTrue(os.path.exists(source_file))
            self.assertTrue(os.path.exists(destination))

    def test_copy_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            documents = os.path.join(tmpdir, "Documents")
            os.mkdir(source_root)
            os.mkdir(documents)
            source_folder = os.path.join(source_root, "AIRA")
            os.mkdir(source_folder)
            nested_file = os.path.join(source_folder, "notes.txt")
            with open(nested_file, "w", encoding="utf-8") as f:
                f.write("folder copy")

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: documents if loc == "documents" else source_root):
                res = copy_file_or_folder("AIRA", "documents")

            destination = os.path.join(documents, "AIRA")
            self.assertTrue(res["success"])
            self.assertTrue(os.path.isdir(source_folder))
            self.assertTrue(os.path.isdir(destination))
            self.assertTrue(os.path.exists(os.path.join(destination, "notes.txt")))

    def test_copy_source_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.filesystem.resolve_location", return_value=tmpdir):
                res = copy_file_or_folder("missing.txt", "desktop")

            self.assertFalse(res["success"])
            self.assertEqual(res["message"], "I couldn't find 'missing.txt'.")

    def test_copy_multiple_source_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            desktop = os.path.join(tmpdir, "Desktop")
            os.mkdir(source_root)
            os.mkdir(desktop)
            one = os.path.join(source_root, "AIRA")
            two = os.path.join(source_root, "AIRA backup")
            os.mkdir(one)
            os.mkdir(two)

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else source_root):
                res = copy_file_or_folder("AIRA", "desktop")

            self.assertFalse(res["success"])
            self.assertEqual(res["matches"], [one, two])
            self.assertIn("Please be more specific.", res["message"])

    def test_copy_destination_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            desktop = os.path.join(tmpdir, "Desktop")
            os.mkdir(source_root)
            os.mkdir(desktop)
            source_file = os.path.join(source_root, "report.pdf")
            destination = os.path.join(desktop, "report.pdf")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write("source")
            with open(destination, "w", encoding="utf-8") as f:
                f.write("existing")

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else source_root):
                res = copy_file_or_folder("report.pdf", "desktop")

            self.assertFalse(res["success"])
            self.assertEqual(res["message"], "A file or folder named 'report.pdf' already exists in desktop.")
            with open(destination, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "existing")

    def test_copy_destination_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.filesystem.resolve_location", return_value=tmpdir) as mock_resolve, \
                 patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": []}):
                copy_file_or_folder("report.pdf", "pictures")

            mock_resolve.assert_called_with("pictures")

    def test_copy_verification_after_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            desktop = os.path.join(tmpdir, "Desktop")
            os.mkdir(source_root)
            os.mkdir(desktop)
            source_file = os.path.join(source_root, "report.pdf")
            with open(source_file, "w", encoding="utf-8") as f:
                f.write("copy me")

            real_exists = os.path.exists

            def exists_after_copy(path):
                if path == os.path.join(desktop, "report.pdf"):
                    return False
                return real_exists(path)

            with patch("tools.filesystem.resolve_location", side_effect=lambda loc: desktop if loc == "desktop" else source_root), \
                 patch("tools.filesystem.os.path.exists", side_effect=exists_after_copy):
                res = copy_file_or_folder("report.pdf", "desktop")

            self.assertFalse(res["success"])
            self.assertIn("Copy verification failed", res["message"])

    def test_copy_to_named_full_path_and_self_or_child_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            destination_root = os.path.join(tmpdir, "destination")
            os.makedirs(source_root)
            os.makedirs(destination_root)
            source_folder = os.path.join(source_root, "PRIMEX")
            os.mkdir(source_folder)

            self.assertTrue(copy_file_or_folder(source_folder, destination_root)["success"])
            self.assertTrue(os.path.isdir(os.path.join(destination_root, "PRIMEX")))
            child = os.path.join(source_folder, "child")
            os.mkdir(child)
            with patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": [source_folder]}):
                result = copy_file_or_folder(source_folder, child)
            self.assertFalse(result["success"])
            self.assertIn("itself or one of its child", result["message"])

    def test_move_file_to_friendly_destination_and_update_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_root = os.path.join(tmpdir, "source")
            desktop = os.path.join(tmpdir, "Desktop")
            os.makedirs(source_root)
            os.mkdir(desktop)
            source = os.path.join(source_root, "report.pdf")
            with open(source, "w", encoding="utf-8") as file:
                file.write("move me")
            fake_storage = {
                "report": {
                    "name": "report.pdf",
                    "aliases": ["weekly report"],
                    "record_type": "path",
                    "launch_method": "file",
                    "target": source,
                }
            }
            self.use_fake_memory(fake_storage)

            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop if name == "desktop" else source_root):
                result = move_file_or_folder("report.pdf", "desktop")

            destination = os.path.join(desktop, "report.pdf")
            self.assertTrue(result["success"])
            self.assertFalse(os.path.exists(source))
            self.assertTrue(os.path.exists(destination))
            self.assertEqual(fake_storage["report"]["target"], destination)
            self.assertIn("weekly report", fake_storage["report"]["aliases"])

    def test_move_folder_to_absolute_path_and_reject_collisions_and_child(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "AIRA")
            destination_root = os.path.join(tmpdir, "archive")
            os.mkdir(source)
            os.mkdir(destination_root)
            result = move_file_or_folder(source, destination_root)
            self.assertTrue(result["success"])
            moved = os.path.join(destination_root, "AIRA")
            self.assertTrue(os.path.isdir(moved))

            collision_source = os.path.join(tmpdir, "report.txt")
            collision_dest = os.path.join(destination_root, "report.txt")
            open(collision_source, "w").close()
            open(collision_dest, "w").close()
            with patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": [collision_source, collision_dest]}):
                collision = move_file_or_folder("report.txt", destination_root)
            self.assertFalse(collision["success"])
            self.assertIn("already exists", collision["message"])
            self.assertTrue(os.path.exists(collision_source))

            child_source = os.path.join(tmpdir, "folder")
            os.mkdir(child_source)
            child = os.path.join(child_source, "child")
            os.mkdir(child)
            with patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": [child_source]}):
                child_result = move_file_or_folder(child_source, child)
            self.assertFalse(child_result["success"])
            self.assertIn("itself or one of its child", child_result["message"])

    def test_move_rejects_ambiguous_source_and_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            one = os.path.join(tmpdir, "one.txt")
            two = os.path.join(tmpdir, "two.txt")
            open(one, "w").close()
            open(two, "w").close()
            destination = os.path.join(tmpdir, "archive")
            os.mkdir(destination)
            with patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": [one, two]}):
                source_result = move_file_or_folder("report.txt", destination)
            self.assertFalse(source_result["success"])
            self.assertEqual(source_result["matches"], [one, two])

            with patch("tools.filesystem.resolve_destination", return_value={"success": False, "path": "", "matches": [one, two], "message": "Please be more specific."}):
                destination_result = move_file_or_folder(one, "archive")
            self.assertFalse(destination_result["success"])
            self.assertIn("more specific", destination_result["message"])

    def test_move_verification_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "report.txt")
            open(source, "w").close()
            destination = os.path.join(tmpdir, "destination")
            os.mkdir(destination)
            with patch("tools.filesystem.shutil.move"):
                result = move_file_or_folder(source, destination)
            self.assertFalse(result["success"])
            self.assertIn("verification failed", result["message"])

    def test_rename_file_preserves_or_changes_extension_and_updates_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "report.pdf")
            open(source, "w").close()
            fake_storage = {
                "report": {
                    "name": "report.pdf",
                    "aliases": ["old report"],
                    "record_type": "path",
                    "launch_method": "file",
                    "target": source,
                }
            }
            self.use_fake_memory(fake_storage)
            result = rename_file_or_folder(source, "final_report")
            renamed = os.path.join(tmpdir, "final_report.pdf")
            self.assertTrue(result["success"])
            self.assertFalse(os.path.exists(source))
            self.assertTrue(os.path.exists(renamed))
            self.assertEqual(fake_storage["report"]["target"], renamed)
            self.assertIn("old report", fake_storage["report"]["aliases"])

            changed = rename_file_or_folder(renamed, "final_report.txt")
            self.assertTrue(changed["success"])
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "final_report.txt")))

    def test_rename_folder_collision_invalid_name_ambiguity_and_verification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "reports")
            os.mkdir(source)
            self.assertTrue(rename_file_or_folder(source, "archive")["success"])
            renamed = os.path.join(tmpdir, "archive")
            collision = os.path.join(tmpdir, "existing")
            os.mkdir(collision)
            result = rename_file_or_folder(renamed, "existing")
            self.assertFalse(result["success"])
            self.assertTrue(os.path.isdir(renamed))

            invalid = rename_file_or_folder(renamed, "bad/name")
            self.assertFalse(invalid["success"])

            one = os.path.join(tmpdir, "one")
            two = os.path.join(tmpdir, "two")
            os.mkdir(one)
            os.mkdir(two)
            with patch("tools.filesystem.find_file_or_folder", return_value={"success": True, "matches": [one, two]}):
                ambiguous = rename_file_or_folder("reports", "archive2")
            self.assertFalse(ambiguous["success"])
            self.assertEqual(ambiguous["matches"], [one, two])

            with patch("tools.filesystem.os.rename"):
                verification = rename_file_or_folder(renamed, "verified")
            self.assertFalse(verification["success"])
            self.assertIn("verification failed", verification["message"])

    def test_create_folder_uses_named_parent_and_rejects_ambiguous_parent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop = os.path.join(tmpdir, "Desktop")
            documents = os.path.join(tmpdir, "Documents")
            os.makedirs(os.path.join(desktop, "AIRA"))
            os.makedirs(documents)
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop if name == "desktop" else documents):
                result = create_folder("reports", "AIRA")
            self.assertTrue(result["success"])
            self.assertTrue(os.path.isdir(os.path.join(desktop, "AIRA", "reports")))

            os.makedirs(os.path.join(documents, "AIRA"))
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop if name == "desktop" else documents):
                ambiguous = create_folder("backup", "AIRA")
            self.assertFalse(ambiguous["success"])
            self.assertIn("multiple destination folders", ambiguous["message"])

    def test_find_ranks_exact_case_and_prefix_before_partial(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desktop = os.path.join(tmpdir, "Desktop")
            os.makedirs(os.path.join(desktop, "AIRA"))
            os.makedirs(os.path.join(desktop, "AIRA_some_asset"))
            os.makedirs(os.path.join(desktop, "project_AIRA"))
            with patch("tools.filesystem.resolve_location", side_effect=lambda name: desktop):
                result = find_file_or_folder("AIRA")
            self.assertEqual(os.path.basename(result["matches"][0]), "AIRA")
            self.assertEqual(os.path.basename(result["matches"][1]), "AIRA_some_asset")

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

        with patch("agent.copy_file_or_folder", return_value={"success": True, "source": r"C:\src\report.pdf", "destination": r"C:\dst\report.pdf", "message": "Copied 'report.pdf' to desktop."}) as mock_copy:
            should_continue, msg = handle_command("copy report.pdf to desktop")
            self.assertTrue(should_continue)
            self.assertEqual(msg, "Copied 'report.pdf' to desktop.")
            mock_copy.assert_called_once_with("report.pdf", "desktop")

        with patch("agent.move_file_or_folder", return_value={"success": True, "message": "Moved successfully."}) as mock_move:
            should_continue, msg = handle_command("MOVE report.pdf TO desktop")
            self.assertTrue(should_continue)
            self.assertEqual(msg, "Moved successfully.")
            mock_move.assert_called_once_with("report.pdf", "desktop")

        with patch("agent.rename_file_or_folder", return_value={"success": True, "message": "Renamed successfully."}) as mock_rename:
            should_continue, msg = handle_command("RENAME report.pdf TO final_report")
            self.assertTrue(should_continue)
            self.assertEqual(msg, "Renamed successfully.")
            mock_rename.assert_called_once_with("report.pdf", "final_report")

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

    # -------------------------------------------------------------------------
    # Tests for system_info
    # -------------------------------------------------------------------------

    def test_system_info_cpu_usage(self):
        from tools.system_info import get_cpu_usage
        with patch("tools.system_info.ctypes.windll.kernel32.GetSystemTimes", return_value=1):
            res = get_cpu_usage()
            self.assertTrue(res["success"])
            self.assertIn("CPU Usage", res["message"])

        with patch("tools.system_info.ctypes.windll.kernel32.GetSystemTimes", side_effect=RuntimeError("fail")):
            res = get_cpu_usage()
            self.assertFalse(res["success"])
            self.assertIn("Failed", res["message"])

    def test_system_info_ram_usage(self):
        from tools.system_info import get_ram_usage
        res = get_ram_usage()
        self.assertTrue(res["success"])
        self.assertGreater(res["total_gb"], 0)
        self.assertIn("RAM Usage", res["message"])

    def test_system_info_disk_space(self):
        from tools.system_info import get_disk_space
        res = get_disk_space("C:\\")
        self.assertTrue(res["success"])
        self.assertGreater(res["total_gb"], 0)

        with patch("tools.system_info.shutil.disk_usage", side_effect=Exception("Disk error")):
            err_res = get_disk_space("Z:\\")
            self.assertFalse(err_res["success"])

    def test_system_info_gpu(self):
        from tools.system_info import get_gpu_info, get_gpu_usage
        with patch("tools.system_info.shutil.which", return_value="C:\\nvidia-smi.exe"), \
             patch("tools.system_info.subprocess.check_output", return_value="GeForce RTX 3050, 4096"):
            info = get_gpu_info()
            self.assertTrue(info["success"])
            self.assertEqual(info["name"], "GeForce RTX 3050")

        with patch("tools.system_info.shutil.which", return_value="C:\\nvidia-smi.exe"), \
             patch("tools.system_info.subprocess.check_output", return_value="GeForce RTX 3050, 45, 1024, 4096"):
            usage = get_gpu_usage()
            self.assertTrue(usage["success"])
            self.assertEqual(usage["gpu_usage_percent"], 45)

    def test_system_info_aggregate(self):
        from tools.system_info import get_system_info
        res = get_system_info()
        self.assertTrue(res["success"])
        self.assertIn("OS:", res["message"])
        self.assertIn("Processor:", res["message"])

    # -------------------------------------------------------------------------
    # Tests for ports
    # -------------------------------------------------------------------------

    def test_ports_listening(self):
        from tools.ports import get_listening_ports
        fake_netstat = (
            "  Proto  Local Address          Foreign Address        State           PID\n"
            "  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       1234\n"
            "  TCP    127.0.0.1:3000         0.0.0.0:0              LISTENING       5678\n"
        )
        with patch("tools.ports.subprocess.check_output", return_value=fake_netstat), \
             patch("tools.ports._get_process_map", return_value={1234: "node.exe", 5678: "app.exe"}):
            res = get_listening_ports()
            self.assertTrue(res["success"])
            self.assertEqual(res["count"], 2)
            self.assertEqual(res["ports"][0]["port"], 3000)
            self.assertEqual(res["ports"][1]["port"], 8080)

    def test_ports_what_is_using_port(self):
        from tools.ports import what_is_using_port
        with patch("tools.ports.get_listening_ports", return_value={
            "success": True,
            "ports": [{"port": 8080, "process_name": "node.exe", "pid": 1234, "protocol": "TCP"}]
        }):
            in_use = what_is_using_port(8080)
            self.assertTrue(in_use["in_use"])
            self.assertEqual(in_use["process_name"], "node.exe")

            not_in_use = what_is_using_port(9999)
            self.assertFalse(not_in_use["in_use"])

        invalid = what_is_using_port("abc")
        self.assertFalse(invalid["success"])

    def test_ports_is_port_free(self):
        from tools.ports import is_port_free
        self.assertFalse(is_port_free(-1)["success"])
        self.assertFalse(is_port_free(999999)["success"])

    # -------------------------------------------------------------------------
    # Tests for network
    # -------------------------------------------------------------------------

    def test_network_internet_connectivity(self):
        from tools.network import is_connected_to_internet
        with patch("tools.network.socket.socket") as mock_sock:
            mock_inst = mock_sock.return_value
            mock_inst.connect.return_value = None
            res = is_connected_to_internet()
            self.assertTrue(res["connected"])

        with patch("tools.network.socket.socket") as mock_sock:
            mock_inst = mock_sock.return_value
            mock_inst.connect.side_effect = OSError("unreachable")
            res = is_connected_to_internet()
            self.assertFalse(res["connected"])

    def test_network_wifi_info(self):
        from tools.network import get_wifi_info
        fake_netsh = (
            "    State                  : connected\n"
            "    SSID                   : Office_5G\n"
            "    Signal                 : 85%\n"
            "    Radio type             : 802.11ax\n"
        )
        with patch("tools.network.subprocess.check_output", return_value=fake_netsh):
            res = get_wifi_info()
            self.assertTrue(res["connected"])
            self.assertEqual(res["ssid"], "Office_5G")
            self.assertEqual(res["signal"], "85%")

    def test_network_ping_safe_and_rejections(self):
        from tools.network import ping_host
        # Injection attempts must be rejected
        self.assertFalse(ping_host("google.com; rm -rf /")["success"])
        self.assertFalse(ping_host("127.0.0.1 && dir")["success"])
        self.assertFalse(ping_host("-evil")["success"])

        # Valid ping
        fake_ping = "Packets: Sent = 2, Received = 2, Lost = 0 (0% loss), Average = 12ms"
        with patch("tools.network.subprocess.check_output", return_value=fake_ping):
            res = ping_host("google.com", 2)
            self.assertTrue(res["success"])
            self.assertTrue(res["reachable"])
            self.assertEqual(res["average_ms"], 12)

    # -------------------------------------------------------------------------
    # Tests for windows
    # -------------------------------------------------------------------------

    def test_windows_list_and_match(self):
        from tools.windows import list_windows
        fake_wins = [
            {"hwnd": 100, "title": "Untitled - Notepad", "pid": 111, "state": "normal"},
            {"hwnd": 200, "title": "Google Chrome", "pid": 222, "state": "normal"},
        ]
        with patch("tools.windows._get_all_windows", return_value=fake_wins), \
             patch("tools.windows.get_running_applications", return_value={"success": True, "apps": []}):
            res = list_windows()
            self.assertTrue(res["success"])
            self.assertEqual(res["count"], 2)

            filtered = list_windows("notepad")
            self.assertTrue(filtered["success"])
            self.assertEqual(filtered["count"], 1)

    def test_windows_minimize_maximize_restore(self):
        from tools.windows import minimize_window, maximize_window, restore_window
        fake_win = {"hwnd": 100, "title": "Test App", "pid": 111, "state": "normal"}

        with patch("tools.windows._select_window", return_value=(fake_win, None)), \
             patch("tools.windows.user32.ShowWindow"), \
             patch("tools.windows.user32.IsIconic", return_value=1), \
             patch("tools.windows.user32.IsZoomed", return_value=0):
            res = minimize_window("Test App")
            self.assertTrue(res["success"])
            self.assertEqual(res["state"], "minimized")

        with patch("tools.windows._select_window", return_value=(fake_win, None)), \
             patch("tools.windows.user32.ShowWindow"), \
             patch("tools.windows.user32.IsIconic", return_value=0), \
             patch("tools.windows.user32.IsZoomed", return_value=1):
            res = maximize_window("Test App")
            self.assertTrue(res["success"])
            self.assertEqual(res["state"], "maximized")

        with patch("tools.windows._select_window", return_value=(fake_win, None)), \
             patch("tools.windows.user32.ShowWindow"), \
             patch("tools.windows.user32.IsIconic", return_value=0), \
             patch("tools.windows.user32.IsZoomed", return_value=0):
            res = restore_window("Test App")
            self.assertTrue(res["success"])
            self.assertEqual(res["state"], "normal")

    def test_windows_close_rejects_protected(self):
        from tools.windows import close_application
        for protected in ["explorer", "system", "dwm", "taskmgr", "antigravity"]:
            res = close_application(protected)
            self.assertFalse(res["success"])
            self.assertIn("Safety restriction", res["message"])

    def test_windows_close_and_restart(self):
        from tools.windows import close_application, restart_application
        fake_win = {"hwnd": 100, "title": "Notepad", "pid": 111, "state": "normal"}

        with patch("tools.windows._match_windows_for_query", return_value=[fake_win]), \
             patch("tools.windows.user32.PostMessageW"), \
             patch("tools.windows._get_all_windows", return_value=[]):
            res = close_application("notepad")
            self.assertTrue(res["success"])
            self.assertIn("Closed 'notepad' successfully", res["message"])

        with patch("tools.windows.close_application", return_value={"success": True}), \
             patch("tools.windows.is_application_running", return_value={"running": False}), \
             patch("tools.windows.open_application", return_value={"success": True}):
            res = restart_application("notepad")
            self.assertTrue(res["success"])
            self.assertIn("Restarted 'notepad' successfully", res["message"])

    # -------------------------------------------------------------------------
    # Tests for delete_file_or_folder
    # -------------------------------------------------------------------------

    def test_delete_rejects_protected_and_git(self):
        from tools.filesystem import delete_file_or_folder
        self.assertFalse(delete_file_or_folder("")["success"])
        self.assertFalse(delete_file_or_folder("C:\\")["success"])

        with patch("tools.filesystem._resolve_single_source", return_value=(r"C:\Windows\System32", None)):
            res = delete_file_or_folder("system32")
            self.assertFalse(res["success"])
            self.assertIn("Safety restriction", res["message"])

        with patch("tools.filesystem._resolve_single_source", return_value=(r"C:\repo\.git\HEAD", None)):
            res = delete_file_or_folder(".git")
            self.assertFalse(res["success"])
            self.assertIn("git repository", res["message"])

    def test_delete_success(self):
        from tools.filesystem import delete_file_or_folder
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"data")
            tmp_path = tmp.name

        try:
            self.assertTrue(os.path.exists(tmp_path))
            with patch("tools.filesystem._resolve_single_source", return_value=(tmp_path, None)), \
                 patch("tools.filesystem._recycle_path", return_value=True), \
                 patch("tools.filesystem.os.path.exists", return_value=False):
                res = delete_file_or_folder(tmp_path)
                self.assertTrue(res["success"])
                self.assertIn("Recycle Bin", res["message"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # -------------------------------------------------------------------------
    # Tests for agent handle_command routing
    # -------------------------------------------------------------------------

    def test_handle_command_new_features(self):
        from agent import handle_command

        with patch("agent.get_system_info", return_value={"message": "System: Windows"}):
            cont, msg = handle_command("show system info")
            self.assertTrue(cont)
            self.assertEqual(msg, "System: Windows")

        with patch("agent.get_cpu_usage", return_value={"message": "CPU: 10%"}):
            cont, msg = handle_command("show cpu usage")
            self.assertTrue(cont)
            self.assertEqual(msg, "CPU: 10%")

        with patch("agent.get_listening_ports", return_value={"message": "Ports: 80"}):
            cont, msg = handle_command("show listening ports")
            self.assertTrue(cont)
            self.assertEqual(msg, "Ports: 80")

        with patch("agent.what_is_using_port", return_value={"message": "Port 8080 is used by node"}):
            cont, msg = handle_command("what is using port 8080")
            self.assertTrue(cont)
            self.assertEqual(msg, "Port 8080 is used by node")

        with patch("agent.is_port_free", return_value={"message": "Port 3000 is free."}):
            cont, msg = handle_command("is port 3000 free")
            self.assertTrue(cont)
            self.assertEqual(msg, "Port 3000 is free.")

        with patch("agent.get_wifi_info", return_value={"message": "Wi-Fi: Connected"}):
            cont, msg = handle_command("show wifi info")
            self.assertTrue(cont)
            self.assertEqual(msg, "Wi-Fi: Connected")

        with patch("agent.is_connected_to_internet", return_value={"message": "Yes, connected"}):
            cont, msg = handle_command("am i connected to internet?")
            self.assertTrue(cont)
            self.assertEqual(msg, "Yes, connected")

        with patch("agent.ping_host", return_value={"message": "Ping OK"}):
            cont, msg = handle_command("ping 8.8.8.8")
            self.assertTrue(cont)
            self.assertEqual(msg, "Ping OK")

        with patch("agent.minimize_window", return_value={"message": "Minimized"}):
            cont, msg = handle_command("minimize notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Minimized")

        with patch("agent.maximize_window", return_value={"message": "Maximized"}):
            cont, msg = handle_command("maximize notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Maximized")

        with patch("agent.bring_to_foreground", return_value={"message": "Brought forward"}):
            cont, msg = handle_command("bring notepad to front")
            self.assertTrue(cont)
            self.assertEqual(msg, "Brought forward")

        with patch("agent.close_application", return_value={"message": "Closed"}):
            cont, msg = handle_command("close notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Closed")

        with patch("agent.restart_application", return_value={"message": "Restarted"}):
            cont, msg = handle_command("restart notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Restarted")

        with patch("agent.delete_file_or_folder", return_value={"message": "Deleted"}):
            cont, msg = handle_command("delete report.pdf")
            self.assertTrue(cont)
            self.assertEqual(msg, "Deleted")

    # -------------------------------------------------------------------------
    # Tests for Audio & Media Hands
    # -------------------------------------------------------------------------

    def test_audio_controls(self):
        from tools.audio import set_volume, volume_up, volume_down, toggle_mute, media_play_pause, media_next, media_prev, media_stop
        with patch("tools.audio.user32.keybd_event"):
            res = set_volume(50)
            self.assertTrue(res["success"])
            self.assertEqual(res["volume_percent"], 50)

            up_res = volume_up(2)
            self.assertTrue(up_res["success"])

            down_res = volume_down(2)
            self.assertTrue(down_res["success"])

            mute_res = toggle_mute()
            self.assertTrue(mute_res["success"])

            play_res = media_play_pause()
            self.assertTrue(play_res["success"])

            next_res = media_next()
            self.assertTrue(next_res["success"])

            prev_res = media_prev()
            self.assertTrue(prev_res["success"])

            stop_res = media_stop()
            self.assertTrue(stop_res["success"])

        invalid = set_volume("invalid")
        self.assertFalse(invalid["success"])

    # -------------------------------------------------------------------------
    # Tests for Clipboard Hands
    # -------------------------------------------------------------------------

    def test_clipboard_operations(self):
        from tools.clipboard import get_clipboard_text, set_clipboard_text, clear_clipboard
        with patch("tools.clipboard.user32.OpenClipboard", return_value=True), \
             patch("tools.clipboard.user32.CloseClipboard", return_value=True), \
             patch("tools.clipboard.user32.EmptyClipboard", return_value=True), \
             patch("tools.clipboard.kernel32.GlobalAlloc", return_value=12345), \
             patch("tools.clipboard.kernel32.GlobalLock", return_value=67890), \
             patch("tools.clipboard.kernel32.GlobalUnlock", return_value=True), \
             patch("tools.clipboard.user32.SetClipboardData", return_value=12345), \
             patch("tools.clipboard.ctypes.memmove"):
            set_res = set_clipboard_text("Hand Test Content")
            self.assertTrue(set_res["success"])
            self.assertEqual(set_res["text"], "Hand Test Content")

            clear_res = clear_clipboard()
            self.assertTrue(clear_res["success"])

        with patch("tools.clipboard.user32.OpenClipboard", return_value=False):
            err_set = set_clipboard_text("Fail")
            self.assertFalse(err_set["success"])

            err_get = get_clipboard_text()
            self.assertFalse(err_get["success"])

    # -------------------------------------------------------------------------
    # Tests for Input & Hotkeys Hands
    # -------------------------------------------------------------------------

    def test_input_hotkeys_and_typing(self):
        from tools.input import send_hotkey, show_desktop, open_task_manager, switch_app_alt_tab, type_text
        with patch("tools.input.user32.keybd_event"):
            desk = show_desktop()
            self.assertTrue(desk["success"])

            task = open_task_manager()
            self.assertTrue(task["success"])

            alt = switch_app_alt_tab()
            self.assertTrue(alt["success"])

            typed = type_text("Hello MIO")
            self.assertTrue(typed["success"])
            self.assertEqual(typed["length"], 9)

            custom_combo = send_hotkey(["ctrl", "c"])
            self.assertTrue(custom_combo["success"])

        invalid_combo = send_hotkey(["unknown_key_12345"])
        self.assertFalse(invalid_combo["success"])

    # -------------------------------------------------------------------------
    # Tests for Power & Battery Hands
    # -------------------------------------------------------------------------

    def test_power_and_battery(self):
        from tools.power import lock_workstation, turn_off_screen, get_battery_status
        with patch("tools.power.user32.LockWorkStation", return_value=1):
            lock_res = lock_workstation()
            self.assertTrue(lock_res["success"])

        with patch("tools.power.user32.SendMessageW", return_value=0):
            screen_res = turn_off_screen()
            self.assertTrue(screen_res["success"])

        with patch("tools.power.kernel32.GetSystemPowerStatus", return_value=1):
            batt_res = get_battery_status()
            self.assertTrue(batt_res["success"])
            self.assertIn("Power Source", batt_res["message"])

    # -------------------------------------------------------------------------
    # Tests for Screen Capture Hands
    # -------------------------------------------------------------------------

    def test_screen_capture(self):
        from tools.screen import take_screenshot
        with patch("tools.screen.subprocess.check_output", return_value=b""), \
             patch("tools.screen.os.path.exists", return_value=True), \
             patch("tools.screen.os.path.getsize", return_value=10240):
            shot = take_screenshot("shot.png")
            self.assertTrue(shot["success"])
            self.assertIn("shot.png", shot["path"])

    # -------------------------------------------------------------------------
    # Tests for Agent Hand Command Routing
    # -------------------------------------------------------------------------

    def test_agent_hand_commands(self):
        from agent import handle_command

        with patch("agent.set_volume", return_value={"message": "Volume 70%"}):
            cont, msg = handle_command("set volume 70%")
            self.assertTrue(cont)
            self.assertEqual(msg, "Volume 70%")

        with patch("agent.volume_up", return_value={"message": "Volume up"}):
            cont, msg = handle_command("volume up")
            self.assertTrue(cont)
            self.assertEqual(msg, "Volume up")

        with patch("agent.toggle_mute", return_value={"message": "Muted"}):
            cont, msg = handle_command("mute")
            self.assertTrue(cont)
            self.assertEqual(msg, "Muted")

        with patch("agent.media_play_pause", return_value={"message": "Play"}):
            cont, msg = handle_command("play")
            self.assertTrue(cont)
            self.assertEqual(msg, "Play")

        with patch("agent.media_next", return_value={"message": "Next"}):
            cont, msg = handle_command("next track")
            self.assertTrue(cont)
            self.assertEqual(msg, "Next")

        with patch("agent.get_clipboard_text", return_value={"message": "Clip: text"}):
            cont, msg = handle_command("show clipboard")
            self.assertTrue(cont)
            self.assertEqual(msg, "Clip: text")

        with patch("agent.set_clipboard_text", return_value={"message": "Copied"}):
            cont, msg = handle_command("copy text https://github.com")
            self.assertTrue(cont)
            self.assertEqual(msg, "Copied")

        with patch("agent.show_desktop", return_value={"message": "Desktop shown"}):
            cont, msg = handle_command("show desktop")
            self.assertTrue(cont)
            self.assertEqual(msg, "Desktop shown")

        with patch("agent.open_task_manager", return_value={"message": "Task Manager"}):
            cont, msg = handle_command("open task manager")
            self.assertTrue(cont)
            self.assertEqual(msg, "Task Manager")

        with patch("agent.lock_workstation", return_value={"message": "Locked"}):
            cont, msg = handle_command("lock screen")
            self.assertTrue(cont)
            self.assertEqual(msg, "Locked")

        with patch("agent.turn_off_screen", return_value={"message": "Screen off"}):
            cont, msg = handle_command("turn off monitor")
            self.assertTrue(cont)
            self.assertEqual(msg, "Screen off")

        with patch("agent.get_battery_status", return_value={"message": "Battery 85%"}):
            cont, msg = handle_command("show battery")
            self.assertTrue(cont)
            self.assertEqual(msg, "Battery 85%")

        with patch("agent.take_screenshot", return_value={"message": "Screenshot saved"}):
            cont, msg = handle_command("take screenshot")
            self.assertTrue(cont)
            self.assertEqual(msg, "Screenshot saved")

    # -------------------------------------------------------------------------
    # Tests for Notifications & Chimes
    # -------------------------------------------------------------------------

    def test_notifications_play_chime(self):
        from tools.notifications import play_chime
        with patch("tools.notifications.winsound.MessageBeep", return_value=None):
            res = play_chime("asterisk")
            self.assertTrue(res["success"])
            self.assertIn("asterisk", res["message"])

        with patch("tools.notifications.winsound.MessageBeep", side_effect=RuntimeError("Sound card error")):
            err_res = play_chime("asterisk")
            self.assertFalse(err_res["success"])
            self.assertIn("Failed", err_res["message"])

    def test_notifications_show_notification(self):
        from tools.notifications import show_notification
        with patch("tools.notifications.subprocess.Popen") as mock_popen, \
             patch("tools.notifications.play_chime") as mock_chime:
            res = show_notification("Meeting", "Starts in 5 minutes", with_chime=True)
            self.assertTrue(res["success"])
            self.assertEqual(res["title"], "Meeting")
            self.assertEqual(res["body"], "Starts in 5 minutes")
            mock_chime.assert_called_once_with("asterisk")
            mock_popen.assert_called_once()

    # -------------------------------------------------------------------------
    # Tests for Browser & Web Search
    # -------------------------------------------------------------------------

    def test_browser_open_url(self):
        from tools.browser import open_url
        with patch("tools.browser.webbrowser.open") as mock_open:
            res = open_url("github.com")
            self.assertTrue(res["success"])
            self.assertEqual(res["url"], "https://github.com")
            mock_open.assert_called_once_with("https://github.com", new=2)

        invalid_res = open_url("")
        self.assertFalse(invalid_res["success"])

    def test_browser_search_web(self):
        from tools.browser import search_web
        with patch("tools.browser.open_url", return_value={"success": True}) as mock_open:
            res = search_web("python tutorials", engine="google")
            self.assertTrue(res["success"])
            self.assertIn("google.com/search?q=python+tutorials", res["url"])

            yt_res = search_web("lofi hip hop", engine="youtube")
            self.assertTrue(yt_res["success"])
            self.assertIn("youtube.com/results?search_query=lofi+hip+hop", yt_res["url"])

            bing_res = search_web("weather", engine="bing")
            self.assertTrue(bing_res["success"])
            self.assertIn("bing.com/search?q=weather", bing_res["url"])

    def test_browser_open_incognito(self):
        from tools.browser import open_incognito
        with patch("tools.browser.shutil.which", side_effect=lambda x: "C:\\chrome.exe" if x == "chrome.exe" else None), \
             patch("tools.browser.subprocess.Popen") as mock_popen:
            res = open_incognito("https://example.com")
            self.assertTrue(res["success"])
            self.assertEqual(res["browser"], "chrome.exe")
            mock_popen.assert_called_once()

    # -------------------------------------------------------------------------
    # Tests for Mouse Hands
    # -------------------------------------------------------------------------

    def test_mouse_cursor_position(self):
        from tools.mouse import get_cursor_position
        with patch("tools.mouse.user32.GetCursorPos") as mock_pos:
            def fake_get_pos(pt_ref):
                pt_ref._obj.x = 450
                pt_ref._obj.y = 350
                return 1
            mock_pos.side_effect = fake_get_pos

            res = get_cursor_position()
            self.assertTrue(res["success"])
            self.assertEqual(res["x"], 450)
            self.assertEqual(res["y"], 350)

    def test_mouse_move_cursor(self):
        from tools.mouse import move_cursor
        with patch("tools.mouse.user32.SetCursorPos", return_value=1) as mock_set:
            res = move_cursor(100, 200)
            self.assertTrue(res["success"])
            self.assertEqual(res["x"], 100)
            self.assertEqual(res["y"], 200)
            mock_set.assert_called_once_with(100, 200)

        err_res = move_cursor("bad", 200)
        self.assertFalse(err_res["success"])

    def test_mouse_clicks_and_scroll(self):
        from tools.mouse import click, right_click, double_click, mouse_scroll
        with patch("tools.mouse.user32.mouse_event") as mock_event, \
             patch("tools.mouse.get_cursor_position", return_value={"x": 100, "y": 100}):
            left_res = click("left")
            self.assertTrue(left_res["success"])

            right_res = right_click()
            self.assertTrue(right_res["success"])
            self.assertEqual(right_res["button"], "right")

            dbl_res = double_click()
            self.assertTrue(dbl_res["success"])
            self.assertTrue(dbl_res["double"])

            scroll_res = mouse_scroll(240)
            self.assertTrue(scroll_res["success"])
            self.assertEqual(scroll_res["amount"], 240)

    # -------------------------------------------------------------------------
    # Tests for File Archives (Zip / Unzip)
    # -------------------------------------------------------------------------

    def test_archive_zip_and_unzip(self):
        from tools.archive import create_zip, extract_zip, list_zip_contents
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = os.path.join(tmpdir, "sample.txt")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("Hello MIO Archive Testing!")

            # Zip creation
            zip_target = os.path.join(tmpdir, "test.zip")
            res_zip = create_zip(sample_file, zip_target)
            self.assertTrue(res_zip["success"])
            self.assertTrue(os.path.exists(zip_target))
            self.assertEqual(res_zip["file_count"], 1)

            # Inspect contents
            res_list = list_zip_contents(zip_target)
            self.assertTrue(res_list["success"])
            self.assertEqual(res_list["total_items"], 1)
            self.assertEqual(res_list["files"][0]["filename"], "sample.txt")

            # Extract archive
            dest_dir = os.path.join(tmpdir, "extracted")
            res_extract = extract_zip(zip_target, dest_dir)
            self.assertTrue(res_extract["success"])
            self.assertEqual(res_extract["extracted_count"], 1)
            extracted_file = os.path.join(dest_dir, "sample.txt")
            self.assertTrue(os.path.exists(extracted_file))

    def test_archive_zip_slip_protection(self):
        import zipfile
        from tools.archive import extract_zip
        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_zip = os.path.join(tmpdir, "malicious.zip")
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                zf.writestr("../../evil.txt", "pwned")

            res = extract_zip(malicious_zip, os.path.join(tmpdir, "safe_dir"))
            self.assertFalse(res["success"])
            self.assertIn("Zip contains unsafe path", res["message"])


    # -------------------------------------------------------------------------
    # Tests for Settings (Theme & Accent)
    # -------------------------------------------------------------------------

    def test_settings_get_and_set_theme(self):
        from tools.settings import get_theme_mode, set_theme_mode, get_accent_color
        with patch("tools.settings.winreg.OpenKey"), \
             patch("tools.settings.winreg.QueryValueEx", side_effect=[(0, 4), (0, 4)]):
            theme_res = get_theme_mode()
            self.assertTrue(theme_res["success"])
            self.assertEqual(theme_res["theme"], "dark")

        with patch("tools.settings.winreg.OpenKey"), \
             patch("tools.settings.winreg.SetValueEx") as mock_set_val:
            set_res = set_theme_mode("light")
            self.assertTrue(set_res["success"])
            self.assertEqual(set_res["theme"], "light")
            self.assertEqual(mock_set_val.call_count, 2)

        with patch("tools.settings.winreg.OpenKey"), \
             patch("tools.settings.winreg.QueryValueEx", return_value=(0xC40078D7, 4)):
            accent_res = get_accent_color()
            self.assertTrue(accent_res["success"])
            self.assertEqual(accent_res["accent_hex"], "#0078D7")

    # -------------------------------------------------------------------------
    # Tests for Timer & Uptime
    # -------------------------------------------------------------------------

    def test_timer_uptime(self):
        from tools.timer import get_system_uptime
        with patch("tools.timer.kernel32.GetTickCount64", return_value=3661000):
            res = get_system_uptime()
            self.assertTrue(res["success"])
            self.assertEqual(res["hours"], 1)
            self.assertEqual(res["minutes"], 1)
            self.assertEqual(res["seconds"], 1)

    def test_timer_countdown(self):
        from tools.timer import start_timer, list_active_timers
        with patch("tools.timer.threading.Thread.start"):
            res = start_timer(60, "Tea")
            self.assertTrue(res["success"])
            self.assertEqual(res["label"], "Tea")
            self.assertEqual(res["duration_seconds"], 60)

        err_res = start_timer(-5)
        self.assertFalse(err_res["success"])

    # -------------------------------------------------------------------------
    # Tests for Agent Command Routing for 6 New Tools
    # -------------------------------------------------------------------------

    def test_agent_new_hand_commands_routing(self):
        from agent import handle_command

        with patch("agent.play_chime", return_value={"message": "Played asterisk"}):
            cont, msg = handle_command("play chime asterisk")
            self.assertTrue(cont)
            self.assertEqual(msg, "Played asterisk")

        with patch("agent.show_notification", return_value={"message": "Notification sent"}):
            cont, msg = handle_command("notify Meeting | Starts now")
            self.assertTrue(cont)
            self.assertEqual(msg, "Notification sent")

        with patch("agent.open_url", return_value={"message": "Opened url"}):
            cont, msg = handle_command("open url https://github.com")
            self.assertTrue(cont)
            self.assertEqual(msg, "Opened url")

        with patch("agent.search_web", return_value={"message": "Searching google"}):
            cont, msg = handle_command("search python tutorial")
            self.assertTrue(cont)
            self.assertEqual(msg, "Searching google")

        with patch("agent.search_web", return_value={"message": "Searching youtube"}):
            cont, msg = handle_command("search youtube for lo-fi")
            self.assertTrue(cont)
            self.assertEqual(msg, "Searching youtube")

        with patch("agent.open_incognito", return_value={"message": "Incognito opened"}):
            cont, msg = handle_command("open incognito https://google.com")
            self.assertTrue(cont)
            self.assertEqual(msg, "Incognito opened")

        with patch("agent.get_cursor_position", return_value={"message": "X=100, Y=200"}):
            cont, msg = handle_command("get cursor pos")
            self.assertTrue(cont)
            self.assertEqual(msg, "X=100, Y=200")

        with patch("agent.move_cursor", return_value={"message": "Moved to 300, 400"}):
            cont, msg = handle_command("move cursor 300 400")
            self.assertTrue(cont)
            self.assertEqual(msg, "Moved to 300, 400")

        with patch("agent.click", return_value={"message": "Clicked"}):
            cont, msg = handle_command("click")
            self.assertTrue(cont)
            self.assertEqual(msg, "Clicked")

        with patch("agent.right_click", return_value={"message": "Right-clicked"}):
            cont, msg = handle_command("right click")
            self.assertTrue(cont)
            self.assertEqual(msg, "Right-clicked")

        with patch("agent.double_click", return_value={"message": "Double-clicked"}):
            cont, msg = handle_command("double click")
            self.assertTrue(cont)
            self.assertEqual(msg, "Double-clicked")

        with patch("agent.mouse_scroll", return_value={"message": "Scrolled up"}):
            cont, msg = handle_command("scroll up 120")
            self.assertTrue(cont)
            self.assertEqual(msg, "Scrolled up")

        with patch("agent.create_zip", return_value={"message": "Created zip"}):
            cont, msg = handle_command("zip folder to backup.zip")
            self.assertTrue(cont)
            self.assertEqual(msg, "Created zip")

        with patch("agent.extract_zip", return_value={"message": "Extracted zip"}):
            cont, msg = handle_command("unzip backup.zip to folder")
            self.assertTrue(cont)
            self.assertEqual(msg, "Extracted zip")

        with patch("agent.get_theme_mode", return_value={"message": "Theme is dark"}):
            cont, msg = handle_command("show theme")
            self.assertTrue(cont)
            self.assertEqual(msg, "Theme is dark")

        with patch("agent.set_theme_mode", return_value={"message": "Switched to dark"}):
            cont, msg = handle_command("set theme dark")
            self.assertTrue(cont)
            self.assertEqual(msg, "Switched to dark")

        with patch("agent.get_system_uptime", return_value={"message": "Uptime: 2 hours"}):
            cont, msg = handle_command("system uptime")
            self.assertTrue(cont)
            self.assertEqual(msg, "Uptime: 2 hours")

        with patch("agent.start_timer", return_value={"message": "Timer started"}):
            cont, msg = handle_command("set timer 120 Coffee")
            self.assertTrue(cont)
            self.assertEqual(msg, "Timer started")

    # -------------------------------------------------------------------------
    # Tests for Brightness Hands
    # -------------------------------------------------------------------------

    def test_brightness_query_and_set(self):
        from tools.brightness import get_brightness, set_brightness, increase_brightness, decrease_brightness
        with patch("tools.brightness.subprocess.check_output", return_value="65"):
            res = get_brightness()
            self.assertTrue(res["success"])
            self.assertEqual(res["brightness"], 65)

        with patch("tools.brightness.subprocess.check_output", return_value=""):
            set_res = set_brightness(80)
            self.assertTrue(set_res["success"])
            self.assertEqual(set_res["brightness"], 80)

        with patch("tools.brightness.get_brightness", return_value={"success": True, "brightness": 50}), \
             patch("tools.brightness.set_brightness", return_value={"success": True, "brightness": 60}) as mock_set:
            inc_res = increase_brightness(10)
            self.assertTrue(inc_res["success"])
            mock_set.assert_called_once_with(60)

        with patch("tools.brightness.get_brightness", return_value={"success": True, "brightness": 50}), \
             patch("tools.brightness.set_brightness", return_value={"success": True, "brightness": 40}) as mock_set:
            dec_res = decrease_brightness(10)
            self.assertTrue(dec_res["success"])
            mock_set.assert_called_once_with(40)

    # -------------------------------------------------------------------------
    # Tests for Wi-Fi Tools & DNS
    # -------------------------------------------------------------------------

    def test_wifi_tools(self):
        from tools.wifi_tools import get_saved_wifi_profiles, get_wifi_password, scan_wifi_networks, flush_dns_cache

        fake_profiles = (
            "Profiles on interface Wi-Fi:\n"
            "    All User Profile     : HomeNetwork\n"
            "    All User Profile     : OfficeGuest\n"
        )
        with patch("tools.wifi_tools.subprocess.check_output", return_value=fake_profiles):
            res_profiles = get_saved_wifi_profiles()
            self.assertTrue(res_profiles["success"])
            self.assertEqual(res_profiles["count"], 2)
            self.assertIn("HomeNetwork", res_profiles["profiles"])

        fake_key = (
            "Security settings\n"
            "    Key Content            : SuperSecret123\n"
        )
        with patch("tools.wifi_tools.subprocess.check_output", return_value=fake_key):
            res_pwd = get_wifi_password("HomeNetwork")
            self.assertTrue(res_pwd["success"])
            self.assertEqual(res_pwd["password"], "SuperSecret123")

        fake_scan = (
            "SSID 1 : CafeWiFi\n"
            "    Network type            : Infrastructure\n"
            "    Signal                  : 85%\n"
        )
        with patch("tools.wifi_tools.subprocess.check_output", return_value=fake_scan):
            res_scan = scan_wifi_networks()
            self.assertTrue(res_scan["success"])
            self.assertEqual(res_scan["count"], 1)
            self.assertEqual(res_scan["networks"][0]["ssid"], "CafeWiFi")

        with patch("tools.wifi_tools.subprocess.check_output", return_value="Successfully flushed the DNS Resolver Cache."):
            res_flush = flush_dns_cache()
            self.assertTrue(res_flush["success"])

    # -------------------------------------------------------------------------
    # Tests for Windows Services
    # -------------------------------------------------------------------------

    def test_services_management(self):
        from tools.services import list_services, get_service_status, start_service, stop_service, restart_service

        fake_sc = (
            "SERVICE_NAME: Spooler\n"
            "DISPLAY_NAME: Print Spooler\n"
            "        STATE              : 4  RUNNING\n"
            "SERVICE_NAME: wuauserv\n"
            "DISPLAY_NAME: Windows Update\n"
            "        STATE              : 1  STOPPED\n"
        )
        with patch("tools.services.subprocess.check_output", return_value=fake_sc):
            res_list = list_services()
            self.assertTrue(res_list["success"])
            self.assertEqual(res_list["count"], 2)
            self.assertEqual(res_list["services"][0]["name"], "Spooler")
            self.assertEqual(res_list["services"][0]["state"], "RUNNING")

        fake_single = (
            "SERVICE_NAME: Spooler\n"
            "        STATE              : 4  RUNNING\n"
        )
        with patch("tools.services.subprocess.check_output", return_value=fake_single):
            status_res = get_service_status("Spooler")
            self.assertTrue(status_res["success"])
            self.assertTrue(status_res["running"])
            self.assertEqual(status_res["state"], "RUNNING")

        with patch("tools.services.subprocess.check_output", return_value="SERVICE_START_PENDING"):
            start_res = start_service("Spooler")
            self.assertTrue(start_res["success"])

        with patch("tools.services.subprocess.check_output", return_value="STOP_PENDING"):
            stop_res = stop_service("Spooler")
            self.assertTrue(stop_res["success"])

    # -------------------------------------------------------------------------
    # Tests for Installed Software
    # -------------------------------------------------------------------------

    def test_installed_software(self):
        from tools.installed_apps import list_installed_software, get_app_version
        with patch("tools.installed_apps.winreg.OpenKey"), \
             patch("tools.installed_apps.winreg.QueryInfoKey", return_value=(1, 0, 0)), \
             patch("tools.installed_apps.winreg.EnumKey", return_value="NodeJS"), \
             patch("tools.installed_apps.winreg.QueryValueEx", side_effect=lambda key, val: ("Node.js", 1) if val == "DisplayName" else ("20.10.0", 1) if val == "DisplayVersion" else ("OpenJS", 1)):
            res = list_installed_software()
            self.assertTrue(res["success"])
            self.assertGreaterEqual(res["count"], 1)

            ver_res = get_app_version("Node.js")
            self.assertTrue(ver_res["success"])
            self.assertEqual(ver_res["version"], "20.10.0")

    # -------------------------------------------------------------------------
    # Tests for Hasher Checksums
    # -------------------------------------------------------------------------

    def test_hasher_checksums(self):
        from tools.hasher import hash_file, verify_checksum
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.bin")
            with open(fpath, "wb") as f:
                f.write(b"MIO Super Agent Test")

            sha_res = hash_file(fpath, "sha256")
            self.assertTrue(sha_res["success"])
            self.assertEqual(len(sha_res["hash"]), 64)

            md5_res = hash_file(fpath, "md5")
            self.assertTrue(md5_res["success"])
            self.assertEqual(len(md5_res["hash"]), 32)

            verify_res = verify_checksum(fpath, sha_res["hash"])
            self.assertTrue(verify_res["success"])
            self.assertTrue(verify_res["matches"])

    # -------------------------------------------------------------------------
    # Tests for Display Metrics
    # -------------------------------------------------------------------------

    def test_display_metrics(self):
        from tools.display import get_display_info
        with patch("tools.display.user32.GetSystemMetrics", side_effect=lambda x: 1920 if x == 0 else 1080 if x == 1 else 1 if x == 80 else 1920 if x == 78 else 1080), \
             patch("tools.display.user32.GetDpiForSystem", return_value=96, create=True):
            res = get_display_info()
            self.assertTrue(res["success"])
            self.assertEqual(res["primary_resolution"], "1920x1080")
            self.assertEqual(res["scaling_percent"], 100)

    # -------------------------------------------------------------------------
    # Tests for Storage Drives
    # -------------------------------------------------------------------------

    def test_storage_drives(self):
        from tools.drives import list_drives, get_removable_drives
        with patch("tools.drives.kernel32.GetDriveTypeW", side_effect=lambda r: 3 if r == "C:\\" else 2 if r == "E:\\" else 1), \
             patch("tools.drives.kernel32.GetVolumeInformationW", return_value=1), \
             patch("tools.drives.shutil.disk_usage", return_value=type("obj", (), {"total": 500*1024**3, "free": 200*1024**3})()):
            res = list_drives()
            self.assertTrue(res["success"])
            self.assertEqual(res["count"], 2)

            rem_res = get_removable_drives()
            self.assertTrue(rem_res["success"])
            self.assertEqual(rem_res["count"], 1)
            self.assertEqual(rem_res["drives"][0]["letter"], "E")

    # -------------------------------------------------------------------------
    # Tests for Agent Command Routing for 7 New Tools
    # -------------------------------------------------------------------------

    def test_agent_extended_hands_command_routing(self):
        from agent import handle_command

        with patch("agent.get_brightness", return_value={"message": "Brightness: 70%"}):
            cont, msg = handle_command("show brightness")
            self.assertTrue(cont)
            self.assertEqual(msg, "Brightness: 70%")

        with patch("agent.set_brightness", return_value={"message": "Brightness set to 80%"}):
            cont, msg = handle_command("set brightness 80%")
            self.assertTrue(cont)
            self.assertEqual(msg, "Brightness set to 80%")

        with patch("agent.increase_brightness", return_value={"message": "Brightness increased"}):
            cont, msg = handle_command("brightness up")
            self.assertTrue(cont)
            self.assertEqual(msg, "Brightness increased")

        with patch("agent.decrease_brightness", return_value={"message": "Brightness decreased"}):
            cont, msg = handle_command("dim screen")
            self.assertTrue(cont)
            self.assertEqual(msg, "Brightness decreased")

        with patch("agent.get_saved_wifi_profiles", return_value={"message": "Saved Wi-Fi list"}):
            cont, msg = handle_command("show saved wifi")
            self.assertTrue(cont)
            self.assertEqual(msg, "Saved Wi-Fi list")

        with patch("agent.get_wifi_password", return_value={"message": "Password is secret"}):
            cont, msg = handle_command("wifi password for HomeNetwork")
            self.assertTrue(cont)
            self.assertEqual(msg, "Password is secret")

        with patch("agent.flush_dns_cache", return_value={"message": "DNS flushed"}):
            cont, msg = handle_command("flush dns")
            self.assertTrue(cont)
            self.assertEqual(msg, "DNS flushed")

        with patch("agent.list_services", return_value={"message": "Services list"}):
            cont, msg = handle_command("list services")
            self.assertTrue(cont)
            self.assertEqual(msg, "Services list")

        with patch("agent.start_service", return_value={"message": "Started Spooler"}):
            cont, msg = handle_command("start service Spooler")
            self.assertTrue(cont)
            self.assertEqual(msg, "Started Spooler")

        with patch("agent.stop_service", return_value={"message": "Stopped Spooler"}):
            cont, msg = handle_command("stop service Spooler")
            self.assertTrue(cont)
            self.assertEqual(msg, "Stopped Spooler")

        with patch("agent.restart_service", return_value={"message": "Restarted Spooler"}):
            cont, msg = handle_command("restart service Spooler")
            self.assertTrue(cont)
            self.assertEqual(msg, "Restarted Spooler")

        with patch("agent.get_app_version", return_value={"message": "Node.js v20"}):
            cont, msg = handle_command("app version Node.js")
            self.assertTrue(cont)
            self.assertEqual(msg, "Node.js v20")

        with patch("agent.hash_file", return_value={"message": "SHA256: 12345"}):
            cont, msg = handle_command("sha256 app.exe")
            self.assertTrue(cont)
            self.assertEqual(msg, "SHA256: 12345")

        with patch("agent.verify_checksum", return_value={"message": "Checksum MATCHES!"}):
            cont, msg = handle_command("verify checksum app.zip 12345")
            self.assertTrue(cont)
            self.assertEqual(msg, "Checksum MATCHES!")

        with patch("agent.get_display_info", return_value={"message": "Display 1920x1080"}):
            cont, msg = handle_command("screen resolution")
            self.assertTrue(cont)
            self.assertEqual(msg, "Display 1920x1080")

        with patch("agent.list_drives", return_value={"message": "Drives list"}):
            cont, msg = handle_command("show drives")
            self.assertTrue(cont)
            self.assertEqual(msg, "Drives list")

        with patch("agent.get_removable_drives", return_value={"message": "USB drives list"}):
            cont, msg = handle_command("show usb drives")
            self.assertTrue(cont)
            self.assertEqual(msg, "USB drives list")

    # =========================================================================
    # Tests for Master Capacity Expansions across All 25 Tools
    # =========================================================================

    def test_display_expanded(self):
        from tools.display import get_monitors_detail, get_display_modes
        res_monitors = get_monitors_detail()
        self.assertTrue(res_monitors["success"])
        self.assertIn("count", res_monitors)

        res_modes = get_display_modes()
        self.assertTrue(res_modes["success"])
        self.assertIn("refresh_rate_hz", res_modes)

    def test_browser_expanded(self):
        from tools.browser import open_with_browser, open_multiple_urls, get_default_browser
        with patch("tools.browser.webbrowser.get") as mock_get:
            mock_inst = MagicMock()
            mock_get.return_value = mock_inst
            res = open_with_browser("https://github.com", "chrome")
            self.assertTrue(res["success"])
            self.assertIn("chrome", res["browser"])

        with patch("tools.browser.webbrowser.open", return_value=True):
            res_multi = open_multiple_urls(["https://google.com", "https://bing.com"])
            self.assertTrue(res_multi["success"])
            self.assertEqual(res_multi["opened_count"], 2)

        def_browser = get_default_browser()
        self.assertTrue(def_browser["success"])
        self.assertIn("browser", def_browser)

    def test_audio_expanded(self):
        from tools.audio import speak_text, list_audio_devices
        with patch("tools.audio.subprocess.Popen") as mock_popen:
            res = speak_text("Hello from MIO")
            self.assertTrue(res["success"])
            self.assertEqual(res["text"], "Hello from MIO")

        with patch("tools.audio.subprocess.check_output", return_value='[{"Name":"Realtek Audio","Status":"OK"}]'):
            res_devs = list_audio_devices()
            self.assertTrue(res_devs["success"])
            self.assertEqual(res_devs["count"], 1)

    def test_mouse_expanded(self):
        from tools.mouse import drag_to, mouse_down, mouse_up, move_relative
        with patch("tools.mouse.user32.mouse_event"):
            res_down = mouse_down("left")
            self.assertTrue(res_down["success"])
            res_up = mouse_up("left")
            self.assertTrue(res_up["success"])

        with patch("tools.mouse.get_cursor_position", return_value={"success": True, "x": 100, "y": 100}), \
             patch("tools.mouse.move_cursor", return_value={"success": True, "x": 200, "y": 200}), \
             patch("tools.mouse.user32.SetCursorPos", return_value=1), \
             patch("tools.mouse.mouse_down", return_value={"success": True}), \
             patch("tools.mouse.mouse_up", return_value={"success": True}):
            res_drag = drag_to(200, 200, steps=2)
            self.assertTrue(res_drag["success"])

            res_rel = move_relative(50, 50)
            self.assertTrue(res_rel["success"])

    def test_input_expanded(self):
        from tools.input import (
            open_file_explorer,
            open_windows_settings,
            open_run_dialog,
            close_active_window,
            select_all,
            copy_selection,
            paste_selection,
        )
        with patch("tools.input.send_hotkey", return_value={"success": True, "message": "OK"}):
            self.assertTrue(open_file_explorer()["success"])
            self.assertTrue(open_windows_settings()["success"])
            self.assertTrue(open_run_dialog()["success"])
            self.assertTrue(close_active_window()["success"])
            self.assertTrue(select_all()["success"])
            self.assertTrue(copy_selection()["success"])
            self.assertTrue(paste_selection()["success"])

    def test_clipboard_expanded(self):
        from tools.clipboard import append_clipboard_text, get_clipboard_formats
        with patch("tools.clipboard.get_clipboard_text", return_value={"success": True, "text": "Part 1"}), \
             patch("tools.clipboard.set_clipboard_text", return_value={"success": True, "message": "OK"}):
            res_app = append_clipboard_text(" - Part 2")
            self.assertTrue(res_app["success"])

        with patch("tools.clipboard.user32.OpenClipboard", return_value=True), \
             patch("tools.clipboard.user32.CloseClipboard", return_value=True), \
             patch("tools.clipboard.user32.EnumClipboardFormats", side_effect=[13, 0]):
            res_fmts = get_clipboard_formats()
            self.assertTrue(res_fmts["success"])
            self.assertEqual(res_fmts["format_count"], 1)

    def test_screen_expanded(self):
        from tools.screen import take_region_screenshot, get_image_dimensions
        with patch("tools.screen.subprocess.check_output", return_value=b""), \
             patch("tools.screen.os.path.exists", return_value=True), \
             patch("tools.screen.os.path.getsize", return_value=5000):
            res_reg = take_region_screenshot(0, 0, 800, 600, "region.png")
            self.assertTrue(res_reg["success"])

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf_path = tf.name
            # Minimal PNG header and IHDR chunk (width=320, height=240)
            png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x40\x00\x00\x00\xf0\x08\x06\x00\x00\x00"
            tf.write(png_bytes)
        try:
            dims = get_image_dimensions(tf_path)
            self.assertTrue(dims["success"])
            self.assertEqual(dims["width"], 320)
            self.assertEqual(dims["height"], 240)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_notifications_expanded(self):
        from tools.notifications import beep, play_sound_pattern
        with patch("tools.notifications.winsound.Beep"):
            self.assertTrue(beep(1000, 100)["success"])
            self.assertTrue(play_sound_pattern("success")["success"])
            self.assertTrue(play_sound_pattern("error")["success"])
            self.assertTrue(play_sound_pattern("alert")["success"])
            self.assertFalse(play_sound_pattern("nonexistent")["success"])

    def test_settings_expanded(self):
        from tools.settings import get_wallpaper, set_wallpaper, set_transparency_effects
        with patch("tools.settings.user32.SystemParametersInfoW", return_value=1):
            res_get = get_wallpaper()
            self.assertTrue(res_get["success"])

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            wall_path = tf.name
        try:
            with patch("tools.settings.user32.SystemParametersInfoW", return_value=1):
                res_set = set_wallpaper(wall_path)
                self.assertTrue(res_set["success"])
        finally:
            if os.path.exists(wall_path):
                os.remove(wall_path)

        with patch("tools.settings.winreg.OpenKey"), \
             patch("tools.settings.winreg.SetValueEx"):
            res_trans = set_transparency_effects(True)
            self.assertTrue(res_trans["success"])

    def test_power_expanded(self):
        from tools.power import (
            sleep_system,
            hibernate_system,
            schedule_shutdown,
            schedule_restart,
            cancel_shutdown,
            get_active_power_plan,
        )
        with patch("tools.power.ctypes.windll.powrprof.SetSuspendState", return_value=1):
            self.assertTrue(sleep_system()["success"])
            self.assertTrue(hibernate_system()["success"])

        with patch("tools.power.subprocess.check_output", return_value=b""):
            self.assertTrue(schedule_shutdown(60)["success"])
            self.assertTrue(schedule_restart(60)["success"])
            self.assertTrue(cancel_shutdown()["success"])

        with patch("tools.power.subprocess.check_output", return_value="Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)"):
            plan_res = get_active_power_plan()
            self.assertTrue(plan_res["success"])
            self.assertEqual(plan_res["plan"], "Balanced")

    def test_brightness_expanded(self):
        from tools.brightness import fade_brightness
        with patch("tools.brightness.get_brightness", return_value={"success": True, "brightness": 20}), \
             patch("tools.brightness.set_brightness", return_value={"success": True, "brightness": 60}):
            res_fade = fade_brightness(60, steps=2)
            self.assertTrue(res_fade["success"])

    def test_services_expanded(self):
        from tools.services import set_service_startup, get_service_description
        with patch("tools.services.subprocess.check_output", return_value="[SC] ChangeServiceConfig SUCCESS"):
            res_start = set_service_startup("Spooler", "auto")
            self.assertTrue(res_start["success"])

        with patch("tools.services.subprocess.check_output", return_value="SERVICE_NAME: Spooler\nDESCRIPTION: Print Spooler Service"):
            res_desc = get_service_description("Spooler")
            self.assertTrue(res_desc["success"])
            self.assertIn("Print Spooler", res_desc["description"])

    def test_drives_expanded(self):
        from tools.drives import check_drive_space_warning, eject_usb_drive
        with patch("tools.drives.list_drives", return_value={
            "success": True,
            "drives": [{"device": "C:\\", "used_percent": 95, "free_gb": 5, "total_gb": 100}]
        }):
            res_warn = check_drive_space_warning(threshold_percent=90)
            self.assertTrue(res_warn["success"])
            self.assertTrue(res_warn["has_warnings"])

        with patch("tools.drives.subprocess.check_output", return_value="Ejected"):
            res_ej = eject_usb_drive("E")
            self.assertTrue(res_ej["success"])

    def test_wifi_expanded(self):
        from tools.wifi_tools import connect_to_wifi, disconnect_wifi, delete_wifi_profile
        with patch("tools.wifi_tools.subprocess.check_output", return_value="Connection request was completed successfully."):
            res_conn = connect_to_wifi("HomeWifi")
            self.assertTrue(res_conn["success"])

        with patch("tools.wifi_tools.subprocess.check_output", return_value="Disconnected"):
            res_disc = disconnect_wifi()
            self.assertTrue(res_disc["success"])

        with patch("tools.wifi_tools.subprocess.check_output", return_value="Profile 'OldWifi' is deleted from interface."):
            res_del = delete_wifi_profile("OldWifi")
            self.assertTrue(res_del["success"])

    def test_network_expanded(self):
        from tools.network import get_public_ip
        with patch("tools.network.urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"ip": "203.0.113.195"}'
            mock_resp.__enter__.return_value = mock_resp
            mock_open.return_value = mock_resp
            res_ip = get_public_ip()
            self.assertTrue(res_ip["success"])
            self.assertEqual(res_ip["public_ip"], "203.0.113.195")

    def test_ports_expanded(self):
        from tools.ports import kill_port_process, scan_remote_port
        with patch("tools.ports.what_is_using_port", return_value={
            "success": True, "in_use": True, "pid": 4321, "process_name": "server.exe"
        }), patch("tools.ports.subprocess.check_output", return_value="SUCCESS"):
            res_kill = kill_port_process(3000)
            self.assertTrue(res_kill["success"])

        with patch("tools.ports.socket.socket") as mock_sock:
            mock_inst = MagicMock()
            mock_inst.connect_ex.return_value = 0
            mock_sock.return_value = mock_inst
            res_scan = scan_remote_port("example.com", 443)
            self.assertTrue(res_scan["success"])
            self.assertTrue(res_scan["is_open"])

    def test_system_info_expanded(self):
        from tools.system_info import get_cpu_details, get_motherboard_info
        with patch("tools.system_info.subprocess.check_output", return_value='[{"Name":"Intel Core i9","NumberOfCores":16,"NumberOfLogicalProcessors":24,"MaxClockSpeed":5800}]'):
            res_cpu = get_cpu_details()
            self.assertTrue(res_cpu["success"])
            self.assertEqual(res_cpu["cores"], 16)

        with patch("tools.system_info.subprocess.check_output", return_value='[{"Manufacturer":"ASUS","Product":"ROG MAXIMUS","SerialNumber":"12345"}]'):
            res_mb = get_motherboard_info()
            self.assertTrue(res_mb["success"])
            self.assertEqual(res_mb["motherboard"]["Manufacturer"], "ASUS")

    def test_hasher_expanded(self):
        import hashlib
        from tools.hasher import hash_text, compare_files
        res_hash = hash_text("Hello World", "sha256")
        self.assertTrue(res_hash["success"])
        self.assertEqual(res_hash["hash"], hashlib.sha256(b"Hello World").hexdigest())

        with tempfile.NamedTemporaryFile(delete=False) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            f1.write(b"Same Content")
            f1.close()
            f2.write(b"Same Content")
            f2.close()
            try:
                comp = compare_files(f1.name, f2.name)
                self.assertTrue(comp["success"])
                self.assertTrue(comp["identical"])
            finally:
                if os.path.exists(f1.name):
                    os.remove(f1.name)
                if os.path.exists(f2.name):
                    os.remove(f2.name)

    def test_archive_expanded(self):
        from tools.archive import create_tar, test_archive
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "sample.txt")
            with open(src_file, "w") as f:
                f.write("Archive test data")

            tar_dst = os.path.join(tmpdir, "archive.tar.gz")
            res_tar = create_tar(src_file, tar_dst, gzip=True)
            self.assertTrue(res_tar["success"])
            self.assertTrue(os.path.exists(tar_dst))

            res_test = test_archive(tar_dst)
            self.assertTrue(res_test["success"])
            self.assertTrue(res_test["valid"])

    def test_installed_apps_expanded(self):
        from tools.installed_apps import get_app_uninstall_command
        with patch("tools.installed_apps.list_installed_software", return_value={
            "success": True,
            "apps": [{"name": "Sample App", "uninstall_string": "MsiExec.exe /X{12345}"}]
        }):
            res_cmd = get_app_uninstall_command("Sample App")
            self.assertTrue(res_cmd["success"])
            self.assertIn("MsiExec.exe", res_cmd["uninstall_string"])

    def test_processes_expanded(self):
        from tools.processes import kill_process, get_top_processes
        with patch("tools.processes.subprocess.check_output", return_value="SUCCESS: The process has been terminated."):
            res_kill = kill_process("notepad.exe")
            self.assertTrue(res_kill["success"])

        fake_tasklist = '"node.exe","1000","Console","1","50,000 K"\r\n"chrome.exe","2000","Console","1","100,000 K"\r\n'
        with patch("tools.processes.subprocess.check_output", return_value=fake_tasklist):
            res_top = get_top_processes(2)
            self.assertTrue(res_top["success"])
            self.assertEqual(len(res_top["top_processes"]), 2)

    def test_windows_expanded(self):
        from tools.windows import move_and_resize_window, snap_window, set_always_on_top
        fake_wins = [{"hwnd": 999, "title": "Test Window", "pid": 111, "state": "normal"}]
        with patch("tools.windows._get_all_windows", return_value=fake_wins), \
             patch("tools.windows.user32.MoveWindow", return_value=1), \
             patch("tools.windows.user32.SetWindowPos", return_value=1):
            res_mv = move_and_resize_window("Test Window", 10, 10, 800, 600)
            self.assertTrue(res_mv["success"])

            with patch("tools.windows.user32.GetSystemMetrics", side_effect=[1920, 1080]):
                res_snap = snap_window("Test Window", "left")
                self.assertTrue(res_snap["success"])

            res_top = set_always_on_top("Test Window", True)
            self.assertTrue(res_top["success"])

    def test_filesystem_expanded(self):
        from tools.filesystem import read_file_head, read_file_tail, get_folder_size
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write("line 1\nline 2\nline 3\nline 4\nline 5\n")
            tf_path = tf.name
        try:
            res_head = read_file_head(tf_path, 2)
            self.assertTrue(res_head["success"])
            self.assertEqual(res_head["line_count"], 2)

            res_tail = read_file_tail(tf_path, 2)
            self.assertTrue(res_tail["success"])
            self.assertEqual(res_tail["line_count"], 2)

            res_size = get_folder_size(os.path.dirname(tf_path))
            self.assertTrue(res_size["success"])
            self.assertIn("total_bytes", res_size)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_timer_expanded(self):
        from tools.timer import start_stopwatch, lap_stopwatch, stop_stopwatch
        res_start = start_stopwatch("task_timer")
        self.assertTrue(res_start["success"])

        res_lap = lap_stopwatch("task_timer")
        self.assertTrue(res_lap["success"])

        res_stop = stop_stopwatch("task_timer")
        self.assertTrue(res_stop["success"])
        self.assertIn("elapsed_seconds", res_stop)

    def test_applications_expanded(self):
        from tools.applications import open_application_as_admin, open_file_with_default_app
        with patch("tools.applications.ctypes.windll.shell32.ShellExecuteW", return_value=42), \
             patch("tools.filesystem.locate_executable", return_value={"success": True, "matches": ["C:\\Windows\\notepad.exe"]}):
            res_admin = open_application_as_admin("notepad")
            self.assertTrue(res_admin["success"])

        with patch("tools.applications.os.path.exists", return_value=True), \
             patch("tools.applications.os.startfile"):
            res_file = open_file_with_default_app("C:\\file.txt")
            self.assertTrue(res_file["success"])

    def test_agent_command_dispatch_expanded(self):
        from agent import handle_command
        with patch("agent.get_cpu_details", return_value={"message": "CPU details 16 cores"}):
            cont, msg = handle_command("cpu details")
            self.assertTrue(cont)
            self.assertEqual(msg, "CPU details 16 cores")

        with patch("agent.get_motherboard_info", return_value={"message": "ASUS Motherboard"}):
            cont, msg = handle_command("motherboard info")
            self.assertTrue(cont)
            self.assertEqual(msg, "ASUS Motherboard")

        with patch("agent.kill_port_process", return_value={"message": "Port 3000 freed"}):
            cont, msg = handle_command("kill port 3000")
            self.assertTrue(cont)
            self.assertEqual(msg, "Port 3000 freed")

        with patch("agent.get_public_ip", return_value={"message": "Public IP: 1.2.3.4"}):
            cont, msg = handle_command("public ip")
            self.assertTrue(cont)
            self.assertEqual(msg, "Public IP: 1.2.3.4")

        with patch("agent.snap_window", return_value={"message": "Snapped left"}):
            cont, msg = handle_command("snap left notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Snapped left")

        with patch("agent.set_always_on_top", return_value={"message": "Pinned on top"}):
            cont, msg = handle_command("pin on top notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Pinned on top")

        with patch("agent.get_top_processes", return_value={"message": "Top processes list"}):
            cont, msg = handle_command("top processes")
            self.assertTrue(cont)
            self.assertEqual(msg, "Top processes list")

        with patch("agent.kill_process", return_value={"message": "Process killed"}):
            cont, msg = handle_command("kill process notepad")
            self.assertTrue(cont)
            self.assertEqual(msg, "Process killed")

        with patch("agent.open_application_as_admin", return_value={"message": "Opened as admin"}):
            cont, msg = handle_command("run as admin powershell")
            self.assertTrue(cont)
            self.assertEqual(msg, "Opened as admin")

        with patch("agent.open_file_with_default_app", return_value={"message": "Opened file"}):
            cont, msg = handle_command("open file doc.pdf")
            self.assertTrue(cont)
            self.assertEqual(msg, "Opened file")

    def test_healer_tools(self):
        from tools.healer import (
            trim_process_memory,
            trim_all_memory,
            detect_hung_windows,
            heal_network,
            heal_stuck_ports,
            heal_temp_cache,
            auto_heal_system,
        )

        # 1. trim_process_memory
        with patch("tools.healer.kernel32.OpenProcess", return_value=9999), \
             patch("tools.healer.psapi.EmptyWorkingSet", return_value=1), \
             patch("tools.healer.kernel32.CloseHandle"):
            res = trim_process_memory(1234)
            self.assertTrue(res["success"])
            self.assertIn("Successfully trimmed", res["message"])

        # 2. trim_all_memory
        fake_tasklist = '"notepad.exe","1234","Console","1","10,000 K"\n"chrome.exe","5678","Console","1","50,000 K"\n'
        with patch("tools.system_info.get_ram_usage", side_effect=[{"used_gb": 12.0}, {"used_gb": 9.5}]), \
             patch("subprocess.check_output", return_value=fake_tasklist), \
             patch("tools.healer.trim_process_memory", return_value={"success": True}):
            res_all = trim_all_memory()
            self.assertTrue(res_all["success"])
            self.assertEqual(res_all["processes_trimmed"], 2)
            self.assertEqual(res_all["reclaimed_gb"], 2.5)

        # 3. detect_hung_windows
        with patch("tools.healer.user32.EnumWindows") as mock_enum:
            def fake_enum(cb, _):
                # Call callback to simulate no hung windows
                return True
            mock_enum.side_effect = fake_enum
            res_hung = detect_hung_windows()
            self.assertTrue(res_hung["success"])
            self.assertEqual(res_hung["count"], 0)

        # 4. heal_network
        with patch("subprocess.check_output", return_value=""), \
             patch("socket.socket") as mock_sock:
            mock_inst = mock_sock.return_value
            mock_inst.connect.return_value = None
            res_net = heal_network()
            self.assertTrue(res_net["success"])
            self.assertTrue(res_net["dns_flushed"])
            self.assertTrue(res_net["internet_reachable"])

        # 5. heal_stuck_ports
        with patch("tools.ports.what_is_using_port", return_value={"success": True, "in_use": True, "pid": 4321, "process_name": "node.exe"}), \
             patch("tools.ports.kill_port_process", return_value={"success": True}):
            res_ports = heal_stuck_ports([3000])
            self.assertTrue(res_ports["success"])
            self.assertEqual(res_ports["healed_count"], 1)

        # 6. heal_temp_cache
        with patch("os.environ.get", return_value="C:\\FakeTemp"), \
             patch("os.path.exists", return_value=True), \
             patch("os.walk", return_value=[("C:\\FakeTemp", [], ["old.tmp"])]), \
             patch("os.path.getmtime", return_value=0), \
             patch("os.path.getsize", return_value=1024 * 1024 * 5), \
             patch("os.remove"):
            res_temp = heal_temp_cache()
            self.assertTrue(res_temp["success"])
            self.assertEqual(res_temp["files_cleaned"], 1)
            self.assertEqual(res_temp["freed_mb"], 5.0)

        # 7. auto_heal_system
        with patch("tools.healer.trim_all_memory", return_value={"message": "Trimmed 5 GB"}), \
             patch("tools.healer.heal_network", return_value={"message": "DNS Flushed"}), \
             patch("tools.healer.detect_hung_windows", return_value={"message": "0 frozen"}), \
             patch("tools.healer.heal_temp_cache", return_value={"message": "Cleared 200 MB"}):
            res_auto = auto_heal_system()
            self.assertTrue(res_auto["success"])
            self.assertIn("System Self-Healing Complete", res_auto["message"])

    def test_healer_agent_dispatch(self):
        from agent import handle_command
        with patch("agent.auto_heal_system", return_value={"message": "System fully healed"}):
            cont, msg = handle_command("auto heal")
            self.assertTrue(cont)
            self.assertEqual(msg, "System fully healed")

        with patch("agent.trim_all_memory", return_value={"message": "Freed 3 GB RAM"}):
            cont, msg = handle_command("trim ram")
            self.assertTrue(cont)
            self.assertEqual(msg, "Freed 3 GB RAM")

        with patch("agent.heal_network", return_value={"message": "DNS Cache flushed"}):
            cont, msg = handle_command("heal network")
            self.assertTrue(cont)
            self.assertEqual(msg, "DNS Cache flushed")

        with patch("agent.detect_hung_windows", return_value={"message": "No hung windows"}):
            cont, msg = handle_command("check frozen apps")
            self.assertTrue(cont)
            self.assertEqual(msg, "No hung windows")

        with patch("agent.heal_temp_cache", return_value={"message": "Cleared 120 MB temp files"}):
            cont, msg = handle_command("heal cache")
            self.assertTrue(cont)
            self.assertEqual(msg, "Cleared 120 MB temp files")

    def test_youtube_tools(self):
        from tools.browser import (
            parse_timestamp,
            open_youtube,
            search_and_play_youtube,
            control_youtube,
            open_youtube_and_type,
        )
        from tools.input import press_key

        # Timestamp parsing tests
        self.assertEqual(parse_timestamp("2 minute"), 120)
        self.assertEqual(parse_timestamp("2 minutes"), 120)
        self.assertEqual(parse_timestamp("2m"), 120)
        self.assertEqual(parse_timestamp("2:00"), 120)
        self.assertEqual(parse_timestamp("01:30"), 90)
        self.assertEqual(parse_timestamp("1 hour 30 min"), 5400)
        self.assertEqual(parse_timestamp("45s"), 45)
        self.assertEqual(parse_timestamp(120), 120)

        # open_youtube
        with patch("tools.browser.webbrowser.open") as mock_open:
            res_hp = open_youtube()
            self.assertTrue(res_hp["success"])
            self.assertEqual(res_hp["mode"], "homepage")
            mock_open.assert_called_with("https://www.youtube.com", new=2)

            res_search = open_youtube(query="lofi", timestamp="2 minute")
            self.assertTrue(res_search["success"])
            self.assertEqual(res_search["mode"], "search")
            self.assertEqual(res_search["timestamp_seconds"], 120)
            self.assertIn("search_query=lofi", res_search["url"])

            res_vid = open_youtube(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", timestamp="2 minute")
            self.assertTrue(res_vid["success"])
            self.assertEqual(res_vid["mode"], "video_url")
            self.assertIn("&t=120s", res_vid["url"])

        # search_and_play_youtube
        with patch("tools.browser.webbrowser.open"):
            res_sp = search_and_play_youtube("interstellar theme", timestamp="1:45")
            self.assertTrue(res_sp["success"])
            self.assertEqual(res_sp["timestamp_seconds"], 105)

        # control_youtube
        with patch("tools.input.send_hotkey", return_value={"success": True}):
            res_ctrl = control_youtube("play")
            self.assertTrue(res_ctrl["success"])
            self.assertEqual(res_ctrl["key"], "k")

            res_fs = control_youtube("fullscreen")
            self.assertTrue(res_fs["success"])
            self.assertEqual(res_fs["key"], "f")

            res_mute = control_youtube("mute")
            self.assertTrue(res_mute["success"])
            self.assertEqual(res_mute["key"], "m")

        # press_key
        with patch("tools.input.send_hotkey", return_value={"success": True}) as mock_hk:
            res_pk = press_key("enter")
            self.assertTrue(res_pk["success"])
            mock_hk.assert_called_with(["enter"])

    def test_youtube_agent_command_dispatch(self):
        from agent import handle_command

        with patch("tools.browser.webbrowser.open"), \
             patch("tools.browser.get_top_youtube_video_id", return_value="W0DM5lcj6mw"):
            # The core user requirement: "open youtube type this and play video at 2 minute"
            cont, msg = handle_command("open youtube type this and play video at 2 minute")
            self.assertTrue(cont)
            self.assertIn("Playing 'this' on YouTube at 02:00", msg)
            self.assertIn("&t=120s", msg)

            # Variation: "open youtube type lofi and play video at 2 minute"
            cont, msg = handle_command("open youtube type lofi and play video at 2 minute")
            self.assertTrue(cont)
            self.assertIn("Playing 'lofi' on YouTube at 02:00", msg)

            # Variation: "play interstellar theme on youtube at 1:45"
            cont, msg = handle_command("play interstellar theme on youtube at 1:45")
            self.assertTrue(cont)
            self.assertIn("Playing 'interstellar theme' on YouTube at 01:45", msg)

            # Direct video link with cue
            cont, msg = handle_command("open youtube https://www.youtube.com/watch?v=dQw4w9WgXcQ at 2 minute")
            self.assertTrue(cont)
            self.assertIn("Playing YouTube video cued to 02:00", msg)

            # YouTube controls
            cont, msg = handle_command("youtube fullscreen")
            self.assertTrue(cont)
            self.assertIn("fullscreen", msg)

            # Press key
            with patch("agent.press_key", return_value={"message": "Pressed key 'enter'."}):
                cont, msg = handle_command("press key enter")
                self.assertTrue(cont)
                self.assertEqual(msg, "Pressed key 'enter'.")


if __name__ == "__main__":
    unittest.main()





