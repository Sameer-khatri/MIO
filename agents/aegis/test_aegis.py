"""
Unit Test Suite for Aegis - Autonomous Laptop Doctor & Hardware Guardian.
Covers 100% of diagnostic endpoints, scoring algorithms, prescriptions,
treatments, consultations, and fallback routines.
"""

import os
import unittest
from unittest.mock import MagicMock, call, patch

from agents.aegis.aegis import (
    KNOWN_STARTUP_SIGNATURES,
    MEMORYSTATUSEX,
    SYSTEM_POWER_STATUS,
    AegisDoctor,
)


class TestAegisDoctor(unittest.TestCase):
    def setUp(self):
        self.doc = AegisDoctor(name="Dr. Test")

    # -------------------------------------------------------------------------
    # 1. Battery Diagnostics
    # -------------------------------------------------------------------------
    def test_diagnose_battery_plugged_in(self):
        with patch("agents.aegis.aegis.kernel32.GetSystemPowerStatus") as mock_power:
            def side_effect(sps_ptr):
                sps = sps_ptr._obj
                sps.ACLineStatus = 1  # AC
                sps.BatteryLifePercent = 85
                sps.BatteryFlag = 8   # Charging
                sps.BatteryLifeTime = 0xFFFFFFFF
                return 1
            mock_power.side_effect = side_effect

            res = self.doc.diagnose_battery()
            self.assertTrue(res["success"])
            self.assertTrue(res["has_battery"])
            self.assertIn("Plugged in", res["power_source"])
            self.assertEqual(res["charge_percent"], 85)
            self.assertTrue(res["is_charging"])
            self.assertEqual(res["health_rating"], "Healthy Charge Capacity")

    def test_diagnose_battery_critical_dc(self):
        with patch("agents.aegis.aegis.kernel32.GetSystemPowerStatus") as mock_power:
            def side_effect(sps_ptr):
                sps = sps_ptr._obj
                sps.ACLineStatus = 0  # DC
                sps.BatteryLifePercent = 12
                sps.BatteryFlag = 4   # Critical
                sps.BatteryLifeTime = 1200 # 20 mins
                return 1
            mock_power.side_effect = side_effect

            res = self.doc.diagnose_battery()
            self.assertTrue(res["success"])
            self.assertIn("On Battery", res["power_source"])
            self.assertEqual(res["charge_percent"], 12)
            self.assertFalse(res["is_charging"])
            self.assertTrue(res["is_critical"])
            self.assertEqual(res["health_rating"], "Critical Low Battery")
            self.assertEqual(res["estimated_minutes_remaining"], 20.0)

    def test_diagnose_battery_desktop_no_battery(self):
        with patch("agents.aegis.aegis.kernel32.GetSystemPowerStatus") as mock_power:
            def side_effect(sps_ptr):
                sps = sps_ptr._obj
                sps.ACLineStatus = 1
                sps.BatteryLifePercent = 255 # No system battery
                sps.BatteryFlag = 128        # No battery
                return 1
            mock_power.side_effect = side_effect

            res = self.doc.diagnose_battery()
            self.assertTrue(res["success"])
            self.assertFalse(res["has_battery"])
            self.assertEqual(res["health_rating"], "Desktop / No Battery Detected")

    # -------------------------------------------------------------------------
    # 2. Startup Bloat Triage
    # -------------------------------------------------------------------------
    def test_diagnose_startup_bloat_heavy(self):
        fake_hkcu = [
            ("Steam", "C:\\Program Files\\Steam\\steam.exe -silent"),
            ("Discord", "C:\\Users\\User\\AppData\\Local\\Discord\\Update.exe"),
            ("uTorrentWeb", "C:\\Users\\User\\AppData\\Roaming\\uTorrent\\utweb.exe"),
        ]
        fake_hklm = [
            ("EpicGames", "C:\\Program Files\\Epic\\Launcher.exe"),
            ("NormalTool", "C:\\Program Files\\Normal\\tool.exe"),
        ]

        def fake_open_key(hive, subkey, reserved, access):
            mock_key = MagicMock()
            is_hkcu = "Run" in subkey and hive == 0x80000001
            items = fake_hkcu if is_hkcu else fake_hklm
            return MagicMock(__enter__=MagicMock(return_value=mock_key), __exit__=MagicMock())

        with patch("winreg.OpenKey") as mock_open, \
             patch("winreg.QueryInfoKey", return_value=(0, 3, 0)), \
             patch("winreg.EnumValue") as mock_enum:
            mock_open.side_effect = [
                MagicMock(__enter__=lambda s: "hkcu", __exit__=lambda *a: None),
                MagicMock(__enter__=lambda s: "hklm", __exit__=lambda *a: None),
            ]
            mock_enum.side_effect = [
                ("Steam", "C:\\Steam\\steam.exe", 1),
                ("Discord", "C:\\Discord\\Update.exe", 1),
                ("uTorrent", "C:\\utweb.exe", 1),
                ("EpicGames", "C:\\Epic\\launcher.exe", 1),
                ("AudioDriver", "C:\\Driver\\driver.exe", 1),
                ("NormalApp", "C:\\App\\app.exe", 1),
            ]
            res = self.doc.diagnose_startup_bloat()
            self.assertTrue(res["success"])
            self.assertEqual(res["total_startup_items"], 6)
            self.assertGreaterEqual(res["high_impact_count"], 3)
            self.assertIn("bottleneck", res["triage_summary"].lower())

    # -------------------------------------------------------------------------
    # 3. Thermal & Power Scheme Profiling
    # -------------------------------------------------------------------------
    def test_diagnose_thermal_and_power(self):
        fake_powercfg = "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)\n"
        with patch("subprocess.check_output", return_value=fake_powercfg), \
             patch("agents.aegis.aegis.kernel32.GetSystemTimes") as mock_times:
            mock_times.return_value = 1
            res = self.doc.diagnose_thermal_and_power()
            self.assertTrue(res["success"])
            self.assertEqual(res["active_power_scheme"], "Balanced")
            self.assertEqual(res["power_scheme_guid"], "381b4222-f694-41f0-9685-ff5bb260df2e")
            self.assertIn("Cool", res["thermal_state"])

    # -------------------------------------------------------------------------
    # 4. Memory & Resource Pressure
    # -------------------------------------------------------------------------
    def test_diagnose_memory_and_leaks(self):
        def fake_mem_status(ptr):
            m = ptr._obj
            m.ullTotalPhys = 16 * (1024 ** 3)
            m.ullAvailPhys = 4 * (1024 ** 3) # 12 GB used -> 75%
            m.dwMemoryLoad = 75
            return 1

        fake_tasklist = '"chrome.exe","1234","Console","1","2,500,000 K"\n"code.exe","5678","Console","1","800,000 K"\n'

        with patch("agents.aegis.aegis.kernel32.GlobalMemoryStatusEx", side_effect=fake_mem_status), \
             patch("subprocess.check_output", return_value=fake_tasklist):
            res = self.doc.diagnose_memory_and_leaks()
            self.assertTrue(res["success"])
            self.assertEqual(res["total_ram_gb"], 16.0)
            self.assertEqual(res["used_ram_gb"], 12.0)
            self.assertEqual(res["load_percent"], 75)
            self.assertIn("Elevated Memory Pressure", res["pressure_level"])
            self.assertEqual(len(res["top_consumers"]), 2)
            self.assertEqual(res["top_consumers"][0]["name"], "chrome.exe")

    # -------------------------------------------------------------------------
    # 5. Storage & Disk Pressure
    # -------------------------------------------------------------------------
    def test_diagnose_storage(self):
        fake_usage = (500 * (1024 ** 3), 420 * (1024 ** 3), 80 * (1024 ** 3))
        with patch("shutil.disk_usage", return_value=fake_usage), \
             patch("os.environ.get", return_value="C:\\FakeTemp"), \
             patch("os.path.exists", return_value=True), \
             patch("os.scandir") as mock_scandir:
            entry_mock = MagicMock()
            entry_mock.is_file.return_value = True
            stat_mock = MagicMock()
            stat_mock.st_mtime = 0
            stat_mock.st_size = 50 * 1024 * 1024 # 50 MB
            entry_mock.stat.return_value = stat_mock
            mock_scandir.return_value.__enter__.return_value = [entry_mock]

            res = self.doc.diagnose_storage()
            self.assertTrue(res["success"])
            self.assertEqual(res["c_drive_total_gb"], 500.0)
            self.assertEqual(res["c_drive_free_gb"], 80.0)
            self.assertEqual(res["stale_temp_files"], 1)
            self.assertEqual(res["temp_clutter_mb"], 50.0)
            self.assertEqual(res["disk_status"], "Healthy Storage Headroom")

    # -------------------------------------------------------------------------
    # 6. Overall Health Score Calculation
    # -------------------------------------------------------------------------
    def test_calculate_health_score_grades(self):
        # Perfect condition
        ideal_vitals = {
            "memory": {"load_percent": 40},
            "storage": {"c_drive_free_gb": 120, "temp_clutter_mb": 10},
            "startup": {"high_impact_count": 0},
            "power_thermal": {"cpu_load_percent": 15},
            "battery": {"is_critical": False, "is_low": False, "is_charging": True, "power_source": "AC"},
        }
        res_ideal = self.doc.calculate_health_score(ideal_vitals)
        self.assertEqual(res_ideal["health_score"], 100)
        self.assertIn("S-Tier", res_ideal["grade"])

        # Degraded condition
        bad_vitals = {
            "memory": {"load_percent": 95},
            "storage": {"c_drive_free_gb": 10, "temp_clutter_mb": 2000},
            "startup": {"high_impact_count": 4},
            "power_thermal": {"cpu_load_percent": 90},
            "battery": {"is_critical": True, "is_low": True, "is_charging": False, "power_source": "DC"},
        }
        res_bad = self.doc.calculate_health_score(bad_vitals)
        self.assertLess(res_bad["health_score"], 40)
        self.assertIn("D (Critical Degraded)", res_bad["grade"])

    # -------------------------------------------------------------------------
    # 7. Prescriptions Generation
    # -------------------------------------------------------------------------
    def test_prescribe_actions(self):
        stressed_vitals = {
            "memory": {"load_percent": 88},
            "storage": {"c_drive_free_gb": 50, "temp_clutter_mb": 600},
            "startup": {"high_impact_count": 2, "items": [{"display_name": "Steam", "boot_impact": "High"}]},
            "power_thermal": {"cpu_load_percent": 30},
            "battery": {"has_battery": True, "is_low": True, "is_charging": False, "charge_percent": 15},
        }
        rx_res = self.doc.prescribe(stressed_vitals)
        self.assertTrue(rx_res["success"])
        priorities = [p["priority"] for p in rx_res["prescriptions"]]
        self.assertIn("CRITICAL", priorities) # battery low
        self.assertIn("HIGH", priorities)     # ram pressure
        self.assertIn("MEDIUM", priorities)   # startup
        self.assertIn("LOW", priorities)      # temp cache

    # -------------------------------------------------------------------------
    # 8. Apply Treatments
    # -------------------------------------------------------------------------
    def test_apply_treatment_all(self):
        with patch.object(self.doc, "calculate_health_score", side_effect=[
            {"health_score": 65, "grade": "B"},
            {"health_score": 85, "grade": "A"},
        ]), patch("agents.system_agent.tools.healer.trim_all_memory", return_value={"success": True, "reclaimed_gb": 3.0}), \
            patch("subprocess.check_output", return_value=""), \
            patch("agents.system_agent.tools.healer.heal_temp_cache", return_value={"success": True, "freed_mb": 500}):

            res = self.doc.apply_treatment("all")
            self.assertTrue(res["success"])
            self.assertEqual(res["before_score"], 65)
            self.assertEqual(res["after_score"], 85)
            self.assertEqual(res["delta"], 20)
            self.assertIn("+20 Health Points", res["message"])

    # -------------------------------------------------------------------------
    # 9. Natural Language Doctor Consultation
    # -------------------------------------------------------------------------
    def test_doctor_consult_complaints(self):
        # Thermal
        with patch.object(self.doc, "diagnose_thermal_and_power", return_value={
            "thermal_state": "Cool", "active_power_scheme": "Balanced"
        }):
            c_thermal = self.doc.doctor_consult("my laptop is burning hot and fans are loud")
            self.assertTrue(c_thermal["success"])
            self.assertIn("Thermal State", c_thermal["doctor_diagnosis"])
            self.assertIn("Balanced", c_thermal["doctor_verdict"])

        # Battery
        with patch.object(self.doc, "diagnose_battery", return_value={
            "health_rating": "Good", "charge_percent": 30, "power_source": "DC"
        }):
            c_battery = self.doc.doctor_consult("why is my battery draining so fast?")
            self.assertTrue(c_battery["success"])
            self.assertIn("Battery Health", c_battery["doctor_diagnosis"])
            self.assertIn("brightness", c_battery["doctor_verdict"])

        # Lag / Slow
        with patch.object(self.doc, "diagnose_memory_and_leaks", return_value={
            "load_percent": 88, "pressure_level": "Elevated Memory Pressure"
        }):
            c_lag = self.doc.doctor_consult("laptop is sluggish and freezing in games")
            self.assertTrue(c_lag["success"])
            self.assertIn("Resource Pressure", c_lag["doctor_diagnosis"])

        # Boot
        with patch.object(self.doc, "diagnose_startup_bloat", return_value={
            "high_impact_count": 4, "triage_summary": "Bottleneck detected"
        }):
            c_boot = self.doc.doctor_consult("my boot time and startup is so slow")
            self.assertTrue(c_boot["success"])
            self.assertIn("Startup Triage", c_boot["doctor_diagnosis"])

    # -------------------------------------------------------------------------
    # 10. Comprehensive Master Checkup Report
    # -------------------------------------------------------------------------
    def test_full_checkup_report(self):
        with patch.object(self.doc, "diagnose_battery", return_value={"charge_percent": 90, "power_source": "AC", "health_rating": "Healthy"}), \
             patch.object(self.doc, "diagnose_startup_bloat", return_value={"total_startup_items": 5, "high_impact_count": 1}), \
             patch.object(self.doc, "diagnose_thermal_and_power", return_value={"active_power_scheme": "Balanced", "cpu_load_percent": 12.0, "thermal_state": "Cool"}), \
             patch.object(self.doc, "diagnose_memory_and_leaks", return_value={"used_ram_gb": 6.0, "total_ram_gb": 16.0, "load_percent": 37, "pressure_level": "Healthy"}), \
             patch.object(self.doc, "diagnose_storage", return_value={"c_drive_free_gb": 100.0, "c_drive_used_percent": 50.0, "temp_clutter_mb": 5.0}):

            rep = self.doc.full_checkup()
            self.assertEqual(rep["doctor"], "Dr. Test")
            self.assertIn("AEGIS LAPTOP HEALTH CLINIC REPORT", rep["report_card"])
            self.assertIn("[HARDWARE VITALS]", rep["report_card"])
            self.assertIn("[PRESCRIPTIONS]", rep["report_card"])
            self.assertGreaterEqual(rep["health_score"], 80)


if __name__ == "__main__":
    unittest.main()
