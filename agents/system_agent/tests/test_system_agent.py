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


if __name__ == "__main__":
    unittest.main()

