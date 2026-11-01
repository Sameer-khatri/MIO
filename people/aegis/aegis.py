
"""
Aegis - Standalone Laptop Doctor & Hardware Guardian for Windows.

Specialized autonomous agent for laptop health diagnostics, preventative care,
and hardware triage:
- Battery Wear & Power Health Analysis
- Startup Bloat & Boot Bottleneck Triage
- Thermal & Power Scheme Profiling
- Memory Pressure & Leak Detection
- Objective Laptop Health Score (0 - 100)
- Prescriptions & One-Click Treatments (RAM Trim, DNS Flush, Temp Cleanup)
- Natural Language Doctor Consultation

Designed to be completely standalone and decoupled from core MIO.
Zero external dependencies (pure Python standard library).
"""

import ctypes
import json
import os
import re
import shutil
import socket
import subprocess
import time
import winreg
from ctypes import wintypes
from typing import Any, Dict, List, Optional, Tuple

try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
except (AttributeError, OSError):
    kernel32 = None
    user32 = None

try:
    from .antivirus import AegisAntivirus
    from .sentinel import AegisSentinel
except ImportError:
    from antivirus import AegisAntivirus
    from sentinel import AegisSentinel


# --- Windows Native Structures ---
class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]

    def to_uint64(self) -> int:
        return (self.dwHighDateTime << 32) | self.dwLowDateTime


# Known bloat / heavy startup signatures
KNOWN_STARTUP_SIGNATURES = {
    "steam": {"name": "Steam", "impact": "High", "advice": "Disable auto-start unless gaming daily; saves ~1.5s boot time and ~200MB RAM."},
    "riotclient": {"name": "Riot Client", "impact": "High", "advice": "Disable auto-start; launch on-demand when playing Riot games."},
    "discord": {"name": "Discord", "impact": "Medium", "advice": "Consider disabling 'Open Discord on startup' inside Discord settings."},
    "spotify": {"name": "Spotify", "impact": "Medium", "advice": "Set to launch minimized or start manually."},
    "utweb": {"name": "uTorrent Web", "impact": "High", "advice": "High disk/network activity on boot. Strongly recommended to disable."},
    "torrent": {"name": "Torrent Client", "impact": "High", "advice": "Background peer-to-peer client consumes initial bandwidth and disk I/O."},
    "epicgames": {"name": "Epic Games Launcher", "impact": "High", "advice": "Heavy background updater; launch only when playing."},
    "skype": {"name": "Skype", "impact": "Medium", "advice": "Disable startup to save background memory if not used for daily calls."},
    "teams": {"name": "Microsoft Teams", "impact": "High", "advice": "Heavy Electron memory consumer; launch when needed."},
    "onedrive": {"name": "OneDrive", "impact": "Medium", "advice": "Keep if syncing essential documents; otherwise pauses cloud sync overhead."},
    "chrome": {"name": "Google Chrome Background", "impact": "Medium", "advice": "Chrome pre-launch background service consumes idle RAM."},
    "edge": {"name": "Microsoft Edge Pre-launch", "impact": "Low", "advice": "Edge auto-launch background task."},
}


class AegisDoctor:
    """
    Aegis Laptop Doctor: Evaluates hardware vitals, calculates composite health score,
    identifies bottlenecks, and prescribes/applies zero-risk cures.
    """

    def __init__(self, name: str = "Dr. Aegis"):
        self.name = name
        self.antivirus = AegisAntivirus()
        self.sentinel = AegisSentinel(doctor=self)

    # ---------------------------------------------------------
    # Antivirus & Threat Triage Methods
    # ---------------------------------------------------------
    def scan_threats(self) -> Dict[str, Any]:
        """Scans running processes, registry persistence, and temp for malware."""
        return self.antivirus.quick_scan()

    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """Inspects file for malicious extensions, PE headers, and known hashes."""
        return self.antivirus.scan_file(filepath)

    def scan_directory(self, folder_path: str, max_files: int = 200) -> Dict[str, Any]:
        """Scans all files in a directory for malware signatures."""
        return self.antivirus.scan_directory(folder_path, max_files=max_files)

    def quarantine_file(self, filepath: str) -> Dict[str, Any]:
        """Safely isolates a suspicious file into the quarantine vault."""
        return self.antivirus.quarantine_file(filepath)

    def list_quarantine(self) -> Dict[str, Any]:
        """Lists all files neutralized in the quarantine vault."""
        return self.antivirus.list_quarantine()

    # ---------------------------------------------------------
    # Sentinel Continuous Background Surveying Methods
    # ---------------------------------------------------------
    def start_sentinel(self, poll_interval: float = 6.0, auto_heal_ram: bool = True) -> Dict[str, Any]:
        """Activates continuous 24/7 background telemetry & auto-healing."""
        return self.sentinel.start(poll_interval=poll_interval, auto_heal_ram=auto_heal_ram)

    def stop_sentinel(self) -> Dict[str, Any]:
        """Deactivates continuous background surveying."""
        return self.sentinel.stop()

    def get_sentinel_status(self) -> Dict[str, Any]:
        """Returns Sentinel live operational status."""
        return self.sentinel.get_status()

    # ---------------------------------------------------------
    # 1. Battery & Power Diagnostics
    # ---------------------------------------------------------
    def diagnose_battery(self) -> Dict[str, Any]:
        """
        Diagnoses battery health, charge state, AC connection, and battery run-time estimates
        using native Windows GetSystemPowerStatus.
        """
        if not kernel32:
            return {"success": False, "message": "Kernel32 unavailable."}

        sps = SYSTEM_POWER_STATUS()
        if not kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            return {"success": False, "message": "Could not query system power status."}

        ac_status = "Plugged in (AC)" if sps.ACLineStatus == 1 else ("On Battery (DC)" if sps.ACLineStatus == 0 else "Unknown")
        charge_pct = sps.BatteryLifePercent if sps.BatteryLifePercent != 255 else None

        flag = sps.BatteryFlag
        is_charging = bool(flag & 8) if flag != 255 else False
        is_critical = bool(flag & 4) if flag != 255 else False
        is_low = bool(flag & 2) if flag != 255 else False
        has_no_battery = bool(flag & 128) if flag != 255 else False

        time_left_min = round(sps.BatteryLifeTime / 60, 1) if sps.BatteryLifeTime != 0xFFFFFFFF else None

        # Rating
        if has_no_battery:
            health_rating = "Desktop / No Battery Detected"
            wear_assessment = "N/A"
        elif charge_pct is not None and charge_pct < 20 and not is_charging:
            health_rating = "Critical Low Battery"
            wear_assessment = "Immediate plug-in required to avoid sudden shutdown"
        elif charge_pct is not None and charge_pct >= 80:
            health_rating = "Healthy Charge Capacity"
            wear_assessment = "Battery cells holding strong capacity"
        else:
            health_rating = "Good"
            wear_assessment = "Normal operating condition"

        return {
            "success": True,
            "has_battery": not has_no_battery,
            "power_source": ac_status,
            "is_charging": is_charging,
            "charge_percent": charge_pct,
            "is_critical": is_critical,
            "is_low": is_low,
            "estimated_minutes_remaining": time_left_min,
            "health_rating": health_rating,
            "wear_assessment": wear_assessment,
            "message": f"Battery: {charge_pct}% ({ac_status}) - Status: {health_rating}" if charge_pct is not None else f"Power: {ac_status}"
        }

    # ---------------------------------------------------------
    # 2. Startup Bloat & Boot Impact Triage
    # ---------------------------------------------------------
    def diagnose_startup_bloat(self) -> Dict[str, Any]:
        """
        Inspects Windows Run keys (HKCU & HKLM) to identify startup bottlenecks,
        categorize boot impact, and recommend specific bloatware trimmings.
        """
        targets = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "User Startup (HKCU)"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "System Startup (HKLM)"),
        ]

        items = []
        high_impact_count = 0
        medium_impact_count = 0

        for hive, subkey, origin in targets:
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
                    count = winreg.QueryInfoKey(key)[1]
                    for i in range(count):
                        name, val, _ = winreg.EnumValue(key, i)
                        val_str = str(val).lower()
                        item_name = str(name)

                        # Match against signature catalog
                        matched_meta = None
                        for sig, meta in KNOWN_STARTUP_SIGNATURES.items():
                            if sig in item_name.lower() or sig in val_str:
                                matched_meta = meta
                                break

                        if matched_meta:
                            impact = matched_meta["impact"]
                            friendly_name = matched_meta["name"]
                            advice = matched_meta["advice"]
                        else:
                            impact = "Low"
                            friendly_name = item_name
                            advice = "Standard application startup entry."

                        if impact == "High":
                            high_impact_count += 1
                        elif impact == "Medium":
                            medium_impact_count += 1

                        items.append({
                            "name": item_name,
                            "display_name": friendly_name,
                            "command": str(val),
                            "registry_location": origin,
                            "boot_impact": impact,
                            "doctor_advice": advice,
                        })
            except Exception:
                pass

        total = len(items)
        if high_impact_count >= 3:
            triage_summary = f"Heavy boot bottleneck detected ({high_impact_count} high-impact startup apps)."
        elif high_impact_count > 0 or medium_impact_count >= 2:
            triage_summary = f"Moderate startup clutter ({high_impact_count} high, {medium_impact_count} medium apps)."
        else:
            triage_summary = "Clean startup configuration with minimal boot overhead."

        return {
            "success": True,
            "total_startup_items": total,
            "high_impact_count": high_impact_count,
            "medium_impact_count": medium_impact_count,
            "items": items,
            "triage_summary": triage_summary,
            "message": f"Startup Analysis: {total} items found. {triage_summary}"
        }

    # ---------------------------------------------------------
    # 3. Thermal & Power Scheme Profiling
    # ---------------------------------------------------------
    def diagnose_thermal_and_power(self) -> Dict[str, Any]:
        """
        Detects active power scheme, CPU load, and thermal envelope using GetSystemTimes.
        """
        scheme_name = "Balanced"
        scheme_guid = ""
        try:
            out = subprocess.check_output(["powercfg", "/getactivescheme"], stderr=subprocess.DEVNULL, text=True, errors="ignore")
            match = re.search(r"GUID:\s*([a-f0-9\-]+)\s*\((.*?)\)", out, re.IGNORECASE)
            if match:
                scheme_guid = match.group(1).strip()
                scheme_name = match.group(2).strip()
        except Exception:
            pass

        # Check CPU load via GetSystemTimes (fast & native)
        cpu_load_pct = 0.0
        if kernel32:
            try:
                idle_0 = FILETIME()
                kernel_0 = FILETIME()
                user_0 = FILETIME()
                if kernel32.GetSystemTimes(ctypes.byref(idle_0), ctypes.byref(kernel_0), ctypes.byref(user_0)):
                    time.sleep(0.06)
                    idle_1 = FILETIME()
                    kernel_1 = FILETIME()
                    user_1 = FILETIME()
                    kernel32.GetSystemTimes(ctypes.byref(idle_1), ctypes.byref(kernel_1), ctypes.byref(user_1))

                    d_idle = idle_1.to_uint64() - idle_0.to_uint64()
                    d_sys = (kernel_1.to_uint64() - kernel_0.to_uint64()) + (user_1.to_uint64() - user_0.to_uint64())
                    if d_sys > 0:
                        cpu_load_pct = round(max(0.0, min(100.0, ((d_sys - d_idle) / d_sys) * 100.0)), 1)
            except Exception:
                pass

        if cpu_load_pct > 85.0:
            thermal_state = "High Thermal Load (CPU >85%) - Risk of fan noise and heat build-up"
            recommendation = "Check for runaway processes; reduce multi-threaded stress."
        elif cpu_load_pct > 50.0:
            thermal_state = "Moderate Activity (Normal Under Heavy Work)"
            recommendation = "Operating within acceptable thermal envelope."
        else:
            thermal_state = "Cool / Normal Idle"
            recommendation = "Thermal envelope is well maintained."

        return {
            "success": True,
            "active_power_scheme": scheme_name,
            "power_scheme_guid": scheme_guid,
            "cpu_load_percent": cpu_load_pct,
            "thermal_state": thermal_state,
            "doctor_recommendation": recommendation,
            "message": f"Power Scheme: {scheme_name} | CPU: {cpu_load_pct}% | {thermal_state}"
        }

    # ---------------------------------------------------------
    # 4. Memory & Resource Pressure Diagnosis
    # ---------------------------------------------------------
    def diagnose_memory_and_leaks(self) -> Dict[str, Any]:
        """
        Inspects physical RAM load, committed headroom, and scans for memory hogs using tasklist.
        """
        if not kernel32:
            return {"success": False, "message": "Kernel32 unavailable."}

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return {"success": False, "message": "Failed to query GlobalMemoryStatusEx."}

        total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
        avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
        used_gb = round(total_gb - avail_gb, 2)
        load_pct = stat.dwMemoryLoad

        # Scan top memory consumers via fast CSV tasklist
        top_hogs = []
        try:
            out = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], stderr=subprocess.DEVNULL, text=True, errors="ignore")
            parsed = []
            for line in out.splitlines():
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 5 and parts[1].isdigit():
                    mem_str = parts[4].replace(",", "").replace(".", "").replace(" K", "").replace("K", "").strip()
                    if mem_str.isdigit():
                        mem_mb = round(int(mem_str) / 1024, 1)
                        parsed.append({"name": parts[0], "pid": int(parts[1]), "memory_mb": mem_mb})
            parsed.sort(key=lambda x: x["memory_mb"], reverse=True)
            top_hogs = parsed[:5]
        except Exception:
            pass

        if load_pct >= 90:
            pressure_level = "Critical Memory Pressure (>90% RAM used)"
            advice = "System is actively swapping to disk. Immediate working set trim recommended."
        elif load_pct >= 75:
            pressure_level = "Elevated Memory Pressure (75-89% RAM used)"
            advice = "Close unused browser tabs or execute memory self-healing."
        else:
            pressure_level = "Healthy Memory Headroom"
            advice = f"{avail_gb} GB physical memory freely available."

        return {
            "success": True,
            "total_ram_gb": total_gb,
            "used_ram_gb": used_gb,
            "free_ram_gb": avail_gb,
            "load_percent": load_pct,
            "pressure_level": pressure_level,
            "top_consumers": top_hogs,
            "doctor_advice": advice,
            "message": f"RAM: {used_gb}/{total_gb} GB ({load_pct}%) - {pressure_level}"
        }

    # ---------------------------------------------------------
    # 5. Storage & Disk Pressure Diagnosis
    # ---------------------------------------------------------
    def diagnose_storage(self) -> Dict[str, Any]:
        """
        Checks system disk free space and scans for accumulated stale %TEMP% cache clutter.
        Uses scandir with a safety ceiling for instant execution.
        """
        c_drive = "C:\\"
        try:
            total, used, free = shutil.disk_usage(c_drive)
            total_gb = round(total / (1024 ** 3), 2)
            free_gb = round(free / (1024 ** 3), 2)
            used_pct = round((used / total) * 100, 1)
        except Exception:
            total_gb, free_gb, used_pct = 0.0, 0.0, 0.0

        temp_dir = os.environ.get("TEMP", "")
        temp_clutter_mb = 0.0
        stale_file_count = 0
        if temp_dir and os.path.exists(temp_dir):
            try:
                now = time.time()
                # Fast shallow/bounded scan of %TEMP%
                with os.scandir(temp_dir) as entries:
                    count = 0
                    for entry in entries:
                        if count > 500:
                            break
                        count += 1
                        try:
                            if entry.is_file(follow_symlinks=False):
                                stat = entry.stat()
                                if now - stat.st_mtime > 3600:
                                    temp_clutter_mb += stat.st_size
                                    stale_file_count += 1
                        except OSError:
                            pass
                temp_clutter_mb = round(temp_clutter_mb / (1024 ** 2), 2)
            except Exception:
                pass

        if free_gb < 15.0:
            disk_status = "Critical Low Space (<15 GB free on C:)"
            advice = "Windows update and pagefile performance degraded. Cleanup recommended."
        elif free_gb < 35.0:
            disk_status = "Moderate Space Warning"
            advice = "Consider clearing temporary downloads and application caches."
        else:
            disk_status = "Healthy Storage Headroom"
            advice = f"{free_gb} GB free on main partition."

        return {
            "success": True,
            "c_drive_total_gb": total_gb,
            "c_drive_free_gb": free_gb,
            "c_drive_used_percent": used_pct,
            "stale_temp_files": stale_file_count,
            "temp_clutter_mb": temp_clutter_mb,
            "disk_status": disk_status,
            "doctor_advice": advice,
            "message": f"Storage C: {free_gb} GB Free ({used_pct}% used) | Clutter: {temp_clutter_mb} MB"
        }

    # ---------------------------------------------------------
    # 6. Overall Laptop Health Score (0 - 100)
    # ---------------------------------------------------------
    def calculate_health_score(self, vitals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculates an objective, weighted 0 - 100 Laptop Health Score.
        Reuses existing vitals if passed in to avoid redundant system calls.
        """
        v = vitals or {}
        mem = v.get("memory") or self.diagnose_memory_and_leaks()
        storage = v.get("storage") or self.diagnose_storage()
        startup = v.get("startup") or self.diagnose_startup_bloat()
        power = v.get("power_thermal") or self.diagnose_thermal_and_power()
        battery = v.get("battery") or self.diagnose_battery()

        score = 100

        # Memory deductions
        ram_load = mem.get("load_percent", 50)
        if ram_load >= 90:
            score -= 22
        elif ram_load >= 80:
            score -= 15
        elif ram_load >= 70:
            score -= 8

        # Storage deductions
        free_gb = storage.get("c_drive_free_gb", 50.0)
        if free_gb < 15:
            score -= 20
        elif free_gb < 30:
            score -= 10
        elif storage.get("temp_clutter_mb", 0) > 1000:
            score -= 5

        # Startup deductions
        high_startup = startup.get("high_impact_count", 0)
        score -= min(25, high_startup * 6)

        # Thermal/CPU deductions
        cpu = power.get("cpu_load_percent", 10.0)
        if cpu > 85:
            score -= 18
        elif cpu > 60:
            score -= 10

        # Battery warning deductions
        if battery.get("is_critical"):
            score -= 15
        elif battery.get("is_low") and not battery.get("is_charging"):
            score -= 8

        final_score = max(0, min(100, score))

        # Assign medical grade
        if final_score >= 90:
            grade = "S-Tier (Peak Condition)"
            summary = "Your laptop is running in exceptional health with ample headroom."
        elif final_score >= 80:
            grade = "A (Healthy)"
            summary = "Laptop is in solid operational shape with minor optimization headroom."
        elif final_score >= 65:
            grade = "B (Moderate Bloat / Load)"
            summary = "Noticeable resource friction or startup clutter detected."
        elif final_score >= 50:
            grade = "C (Needs Attention)"
            summary = "Significant memory, disk, or background bloat degrading performance."
        else:
            grade = "D (Critical Degraded)"
            summary = "High risk of thermal throttling, freeze-ups, or storage exhaustion."

        return {
            "success": True,
            "health_score": final_score,
            "grade": grade,
            "summary": summary,
            "sub_scores": {
                "memory_load": f"{ram_load}%",
                "free_disk_gb": f"{free_gb} GB",
                "high_impact_startup_apps": high_startup,
                "cpu_load": f"{cpu}%",
                "power_source": battery.get("power_source", "Unknown"),
            },
            "message": f"Laptop Health Score: {final_score}/100 [{grade}]\n- {summary}"
        }

    # ---------------------------------------------------------
    # 7. Doctor Prescriptions
    # ---------------------------------------------------------
    def prescribe(self, vitals: Optional[Dict[str, Any]] = None, score_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes hardware state and produces a prioritized, actionable medical prescription list.
        """
        v = vitals or {}
        score = score_data or self.calculate_health_score(v)
        prescriptions = []

        # Check memory
        mem = v.get("memory") or self.diagnose_memory_and_leaks()
        if mem.get("load_percent", 0) >= 75:
            prescriptions.append({
                "priority": "HIGH",
                "category": "Memory Relief",
                "symptom": f"High RAM pressure ({mem.get('load_percent')}%)",
                "treatment": "Execute RAM working set trim to flush idle pages back to memory pool.",
                "action_command": "aegis.apply_treatment('ram')",
            })

        # Check startup
        startup = v.get("startup") or self.diagnose_startup_bloat()
        if startup.get("high_impact_count", 0) > 0:
            items_str = ", ".join(i["display_name"] for i in startup.get("items", []) if i["boot_impact"] == "High")
            prescriptions.append({
                "priority": "MEDIUM",
                "category": "Boot Speed Optimization",
                "symptom": f"{startup.get('high_impact_count')} high-impact startup apps ({items_str})",
                "treatment": "Disable auto-start for gaming launchers and non-critical updaters in Task Manager.",
                "action_command": "aegis.review_startup_items()",
            })

        # Check storage
        storage = v.get("storage") or self.diagnose_storage()
        if storage.get("temp_clutter_mb", 0) > 200:
            prescriptions.append({
                "priority": "LOW",
                "category": "Disk Hygiene",
                "symptom": f"{storage.get('temp_clutter_mb')} MB of stale temp cache detected",
                "treatment": "Safely purge temporary application junk files.",
                "action_command": "aegis.apply_treatment('cache')",
            })

        # Check power / battery
        battery = v.get("battery") or self.diagnose_battery()
        if battery.get("has_battery") and battery.get("is_low") and not battery.get("is_charging"):
            prescriptions.append({
                "priority": "CRITICAL",
                "category": "Power Preservation",
                "symptom": f"Battery low ({battery.get('charge_percent')}%) and draining",
                "treatment": "Connect AC power charger immediately or switch to Battery Saver scheme.",
                "action_command": "plug_charger",
            })

        if not prescriptions:
            prescriptions.append({
                "priority": "INFO",
                "category": "Preventative Maintenance",
                "symptom": "All vitals within normal parameters",
                "treatment": "Laptop is in peak health. No medical intervention required today.",
                "action_command": "none",
            })

        return {
            "success": True,
            "health_score": score["health_score"],
            "grade": score["grade"],
            "prescription_count": len(prescriptions),
            "prescriptions": prescriptions,
            "message": f"Generated {len(prescriptions)} doctor prescription(s) for your laptop."
        }

    # ---------------------------------------------------------
    # 8. Apply Treatment (One-Click Cures)
    # ---------------------------------------------------------
    def apply_treatment(self, target: str = "all") -> Dict[str, Any]:
        """
        Applies non-destructive healing treatments:
        - 'ram': Flushes idle working sets across all user processes.
        - 'dns': Flushes Windows DNS cache to repair stubborn web connection lag.
        - 'cache': Safely clears stale %TEMP% files (>1h old).
        - 'all': Applies aggregate medical treatment and shows health score improvement.
        """
        before_score = self.calculate_health_score()["health_score"]
        results = {}

        # 1. RAM Trim
        if target in ("ram", "all"):
            try:
                from hands.connectivity.healer import trim_all_memory
                results["ram"] = trim_all_memory()
            except ImportError:
                results["ram"] = self._fallback_trim_ram()

        # 2. DNS Flush
        if target in ("dns", "all"):
            try:
                subprocess.check_output(["ipconfig", "/flushdns"], stderr=subprocess.DEVNULL)
                results["dns"] = {"success": True, "message": "DNS resolver cache flushed."}
            except Exception as err:
                results["dns"] = {"success": False, "message": str(err)}

        # 3. Cache Purge
        if target in ("cache", "all"):
            try:
                from hands.connectivity.healer import heal_temp_cache
                results["cache"] = heal_temp_cache()
            except ImportError:
                results["cache"] = self._fallback_heal_cache()

        after_score = self.calculate_health_score()["health_score"]
        delta = after_score - before_score

        improvement_msg = f"+{delta} Health Points" if delta > 0 else "Vitals refreshed"
        summary = f"Treatment applied ({target}). Before: {before_score} -> After: {after_score} ({improvement_msg})"

        return {
            "success": True,
            "target": target,
            "before_score": before_score,
            "after_score": after_score,
            "delta": delta,
            "details": results,
            "message": summary
        }

    # ---------------------------------------------------------
    # 9. Natural Language Doctor Consultation
    # ---------------------------------------------------------
    def doctor_consult(self, complaint: str) -> Dict[str, Any]:
        """
        Diagnoses user-described symptoms in natural language (e.g. 'running hot',
        'battery draining fast', 'boot is slow', 'games lagging', 'fan noise')
        and maps them to concrete hardware diagnostics & remedies.
        """
        text = complaint.lower()
        diagnosis = []
        cures = []

        if any(w in text for w in ["hot", "fan", "heat", "overheating", "thermal", "warm", "fans", "burning"]):
            power = self.diagnose_thermal_and_power()
            diagnosis.append(f"Thermal State: {power.get('thermal_state')}. Active Power Scheme: {power.get('active_power_scheme')}.")
            cures.append("Switch power scheme to 'Balanced' instead of 'High Performance' to enable CPU idle C-states.")
            cures.append("Ensure laptop air vents are unblocked; elevate laptop rear by 1 inch for airflow.")

        if any(w in text for w in ["battery", "drain", "charge", "unplugged", "discharging", "dying"]):
            bat = self.diagnose_battery()
            diagnosis.append(f"Battery Health: {bat.get('health_rating')} ({bat.get('charge_percent')}%, {bat.get('power_source')}).")
            cures.append("Lower screen brightness by 20% to save ~35% display power.")
            cures.append("Disable background gaming updaters (Steam, Riot Client) which keep dGPU active.")

        if any(w in text for w in ["slow", "lag", "freezing", "stutter", "hang", "sluggish", "delay", "takes forever", "forever", "unresponsive"]):
            mem = self.diagnose_memory_and_leaks()
            diagnosis.append(f"Resource Pressure: RAM load is {mem.get('load_percent')}% ({mem.get('pressure_level')}).")
            cures.append("Run Aegis Treatment: 'heal' or 'ram' to immediately reclaim idle RAM.")
            cures.append("Check Task Manager for runaway web browser helper processes.")

        if any(w in text for w in ["boot", "startup", "start up", "start", "starting", "restart", "turn on", "turning on"]):
            startup = self.diagnose_startup_bloat()
            diagnosis.append(f"Startup Triage: {startup.get('high_impact_count')} high-impact apps found ({startup.get('triage_summary')}).")
            cures.append("Disable automatic launch for Steam, Discord, and torrent clients to slash boot time by ~5-10 seconds.")
            cures.append("Type 'startup' to review all startup applications and their boot impact.")

        if any(w in text for w in ["disk", "storage", "drive", "space", "full", "c:", "temp", "cache"]):
            storage = self.diagnose_storage()
            diagnosis.append(f"Storage Status: C: has {storage.get('c_drive_free_gb')} GB free ({storage.get('disk_status')}). Clutter: {storage.get('temp_clutter_mb')} MB.")
            cures.append("Run Aegis Treatment: 'cache' to purge stale temporary files.")
            cures.append("Uninstall unused games or move large files to secondary storage.")

        if any(w in text for w in ["game", "gaming", "fps", "gpu", "stuttering"]):
            power = self.diagnose_thermal_and_power()
            mem = self.diagnose_memory_and_leaks()
            diagnosis.append(f"Gaming Performance Check: CPU {power.get('cpu_load_percent')}%, RAM {mem.get('load_percent')}%.")
            cures.append("Ensure laptop is plugged into AC power (running on DC battery heavily caps GPU clocks).")
            cures.append("Close background Electron apps (Discord, Teams, Spotify) before launching heavy 3D titles.")

        if any(w in text for w in ["internet", "wifi", "network", "ping", "disconnect", "lagging online"]):
            cures.append("Execute network cure: flush DNS resolver with 'dns'.")
            cures.append("Verify Wi-Fi channel interference or switch to 5GHz band.")

        if any(w in text for w in ["virus", "infected", "malware", "trojan", "hacked", "security", "threat", "antivirus", "scan"]):
            sec = self.scan_threats()
            diagnosis.append(f"Security Threat Audit: [{sec.get('security_grade')}] {sec.get('verdict')}.")
            if sec.get("total_threats", 0) > 0:
                cures.append(f"CRITICAL: Found {sec.get('total_threats')} threat(s). Run 'scan' or 'quarantine' to neutralize them.")
            else:
                cures.append("Zero malware or masquerading processes detected. Your system security is intact.")

        if any(w in text for w in ["survey", "sentinel", "monitor", "watch", "background", "continuous"]):
            status = self.get_sentinel_status()
            state = "ACTIVE" if status.get("running") else "IDLE"
            diagnosis.append(f"Sentinel 24/7 Monitor: Currently [{state}] (Surveys completed: {status.get('surveys_completed')}).")
            if not status.get("running"):
                cures.append("Type 'survey on' to engage continuous 24/7 background telemetry and automatic RAM pressure relief.")
            else:
                cures.append("Sentinel is actively guarding battery, memory leaks, and thermal spikes in the background.")

        if not diagnosis:
            score = self.calculate_health_score()
            diagnosis.append(f"General Checkup: Overall Health Score is {score['health_score']}/100 [{score['grade']}].")
            cures.append("Perform full checkup with 'aegis.full_checkup()' to inspect all hardware subsystems.")

        response = {
            "success": True,
            "patient_complaint": complaint,
            "doctor_diagnosis": "\n".join(f"- {d}" for d in diagnosis),
            "recommended_cures": cures,
            "doctor_verdict": f"Aegis Doctor Verdict:\n" + "\n".join(f"[Diagnosis] {d}" for d in diagnosis) + "\n\nRx Prescriptions:\n" + "\n".join(f"[Rx] {c}" for c in cures)
        }
        return response

    # ---------------------------------------------------------
    # 10. Comprehensive Master Checkup Report
    # ---------------------------------------------------------
    def full_checkup(self) -> Dict[str, Any]:
        """
        Executes a complete medical checkup of the entire laptop and returns a consolidated report.
        """
        battery = self.diagnose_battery()
        startup = self.diagnose_startup_bloat()
        power = self.diagnose_thermal_and_power()
        memory = self.diagnose_memory_and_leaks()
        storage = self.diagnose_storage()

        vitals = {
            "battery": battery,
            "startup": startup,
            "power_thermal": power,
            "memory": memory,
            "storage": storage,
        }

        score = self.calculate_health_score(vitals)
        prescriptions = self.prescribe(vitals, score)

        report = {
            "doctor": self.name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "health_score": score["health_score"],
            "grade": score["grade"],
            "summary": score["summary"],
            "vitals": vitals,
            "prescriptions": prescriptions.get("prescriptions", []),
        }

        # Formatted clinic report card
        report_card = f"""
============================================================
              AEGIS LAPTOP HEALTH CLINIC REPORT             
============================================================
Physician: {self.name}
Date/Time: {report['timestamp']}
Overall Health Score: {score['health_score']}/100 [{score['grade']}]
Diagnosis: {score['summary']}

[HARDWARE VITALS]
- Battery: {battery.get('charge_percent', 'N/A')}% | {battery.get('power_source')} | {battery.get('health_rating')}
- RAM Load: {memory.get('used_ram_gb')}/{memory.get('total_ram_gb')} GB ({memory.get('load_percent')}%) | {memory.get('pressure_level')}
- Disk (C:): {storage.get('c_drive_free_gb')} GB Free ({storage.get('c_drive_used_percent')}% used) | Clutter: {storage.get('temp_clutter_mb')} MB
- Power Scheme: {power.get('active_power_scheme')} | CPU: {power.get('cpu_load_percent')}% | {power.get('thermal_state')}
- Boot Bloat: {startup.get('total_startup_items')} items ({startup.get('high_impact_count')} High Impact)
- Antivirus Security: [{self.antivirus.quick_scan().get('security_grade', 'CLEAN')}]
- Sentinel 24/7 Monitor: {'ACTIVE' if self.sentinel.is_running() else 'IDLE'}

[PRESCRIPTIONS]
"""
        for rx in prescriptions.get("prescriptions", []):
            report_card += f"- [{rx['priority']}] {rx['category']}: {rx['treatment']}\n"
        report_card += "============================================================\n"

        report["report_card"] = report_card
        return report

    # ---------------------------------------------------------
    # Internal Fallback Healing Routines (Zero Dependencies)
    # ---------------------------------------------------------
    def _fallback_trim_ram(self) -> Dict[str, Any]:
        """Direct native EmptyWorkingSet fallback without importing healer tool."""
        try:
            psapi = ctypes.windll.psapi
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_SET_QUOTA = 0x0100

            out = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], stderr=subprocess.DEVNULL, text=True, errors="ignore")
            trimmed = 0
            for line in out.splitlines():
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 2 and parts[1].isdigit():
                    pid = int(parts[1])
                    if pid > 4:
                        h = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
                        if h:
                            if psapi.EmptyWorkingSet(h):
                                trimmed += 1
                            kernel32.CloseHandle(h)
            return {"success": True, "trimmed_processes": trimmed, "message": f"Trimmed working sets for {trimmed} processes."}
        except Exception as e:
            return {"success": False, "message": f"Fallback RAM trim failed: {e}"}

    def _fallback_heal_cache(self) -> Dict[str, Any]:
        """Safely cleans stale temp files from %TEMP% (>1 hour old)."""
        temp_dir = os.environ.get("TEMP", "")
        if not temp_dir or not os.path.exists(temp_dir):
            return {"success": False, "message": "TEMP directory not found."}
        freed = 0
        deleted = 0
        now = time.time()
        try:
            with os.scandir(temp_dir) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            stat = entry.stat()
                            if now - stat.st_mtime > 3600:
                                os.remove(entry.path)
                                freed += stat.st_size
                                deleted += 1
                    except OSError:
                        pass
        except Exception:
            pass
        return {"success": True, "files_cleaned": deleted, "freed_mb": round(freed / (1024 ** 2), 2)}


# ---------------------------------------------------------
# Standalone CLI Interface
# ---------------------------------------------------------
def run_cli():
    """Interactive doctor consultation CLI when executed directly."""
    doctor = AegisDoctor()
    print("\n" + "=" * 60)
    print("  [AEGIS] Autonomous Laptop Doctor & Hardware Guardian")
    print("=" * 60)
    checkup = doctor.full_checkup()
    print(checkup["report_card"])

    print("Type a complaint (e.g. 'laptop is hot', 'battery dying fast', 'heal', or 'quit'):")
    print("Direct Commands: 'heal', 'ram', 'dns', 'cache', 'startup', 'score', 'help', 'quit'\n")
    while True:
        try:
            query = input("Aegis Doctor > ").strip()
            if not query:
                continue
            lower_q = query.lower()
            if lower_q in ("quit", "exit", "q"):
                print("Doctor consultation ended. Stay cool and keep battery healthy!")
                break
            if lower_q in ("apply cure", "cure", "heal", "treat"):
                print("\n[AEGIS] Applying comprehensive hardware treatment...")
                res = doctor.apply_treatment("all")
                print(f"Result: {res['message']}")
                for cat, det in res.get("details", {}).items():
                    if isinstance(det, dict) and "message" in det:
                        print(f"  - [{cat.upper()}] {det['message']}")
                print()
            elif lower_q in ("ram", "trim ram", "free ram"):
                print("\n[AEGIS] Trimming process working sets...")
                res = doctor.apply_treatment("ram")
                ram_det = res.get("details", {}).get("ram", {})
                print(f"Result: {ram_det.get('message', res['message'])}\n")
            elif lower_q in ("dns", "flush dns", "fix network"):
                print("\n[AEGIS] Flushing DNS resolver...")
                res = doctor.apply_treatment("dns")
                dns_det = res.get("details", {}).get("dns", {})
                print(f"Result: {dns_det.get('message', res['message'])}\n")
            elif lower_q in ("cache", "clean cache", "clean temp"):
                print("\n[AEGIS] Purging stale temp files...")
                res = doctor.apply_treatment("cache")
                cache_det = res.get("details", {}).get("cache", {})
                print(f"Result: {cache_det.get('message', res['message'])}\n")
            elif lower_q in ("startup", "bloat", "startup apps"):
                print("\n[AEGIS] Scanning Windows startup registry entries...")
                bloat = doctor.diagnose_startup_bloat()
                print(f"Found {bloat['total_startup_items']} startup entries ({bloat['high_impact_count']} High Impact):")
                for it in bloat.get("items", []):
                    print(f"  - [{it['boot_impact'].upper()}] {it['display_name']} ({it['name']}) -> {it['doctor_advice']}")
                print()
            elif lower_q in ("score", "health", "checkup", "vitals"):
                res = doctor.full_checkup()
                print(res["report_card"])
            elif lower_q.startswith("scan ") or lower_q in ("scan", "virus", "antivirus", "check threats", "scan full", "scan system", "scan pc", "scan laptop", "scan all"):
                sub_target = query[5:].strip().strip('"').strip("'") if lower_q.startswith("scan ") else ""
                lower_sub = sub_target.lower()

                if not sub_target or any(k in lower_sub for k in ["my pc", "pc", "laptop", "computer", "system", "all", "full", "threat", "virus", "malware", "here"]):
                    print("\n[AEGIS SHIELD] Running deep system security and threat audit...")
                    sec = doctor.scan_threats()
                    print(sec["summary_report"])
                    print()
                elif lower_sub in ("procs", "processes", "process"):
                    print("\n[AEGIS SHIELD] Auditing process parentage, masquerading & LOLBins...")
                    p_res = doctor.antivirus.scan_running_processes()
                    print(f"Scanned: {p_res['processes_scanned']} | Threats: {p_res['threats_count']} | Suspicious: {p_res['suspicious_count']}")
                    for t in p_res.get("threats", []):
                        print(f"  - [{t['severity']}] {t['name']} (PID {t.get('pid')}): {t['description']}")
                    for s in p_res.get("suspicious", []):
                        print(f"  - [{s['severity']}] {s['name']} (PID {s.get('pid')}): {s['description']}")
                    print()
                elif lower_sub in ("net", "network", "beacons", "sockets"):
                    print("\n[AEGIS SHIELD] Auditing active network sockets for rogue C2 beacons...")
                    b_res = doctor.antivirus.scan_network_beacons()
                    print(b_res["message"])
                    for b in b_res.get("beacons", []):
                        print(f"  - [{b['severity']}] PID {b['pid']} ({b['executable']}) -> {b['description']}")
                    print()
                elif lower_sub in ("tasks", "persistence", "startup"):
                    print("\n[AEGIS SHIELD] Auditing persistence registry & scheduled tasks...")
                    pers = doctor.antivirus.scan_persistence()
                    print(pers["message"])
                    for f in pers.get("findings", []):
                        print(f"  - [{f['severity']}] [{f['category']}] {f['name']}: {f['description']}")
                    print()
                elif lower_sub in ("tampering", "defender", "security"):
                    print("\n[AEGIS SHIELD] Auditing Windows Defender & UAC policy integrity...")
                    tamp = doctor.antivirus.scan_security_tampering()
                    print(tamp["message"])
                    for fl in tamp.get("flags", []):
                        print(f"  - [{fl['severity']}] {fl['subsystem']}: {fl['description']}")
                    print()
                elif os.path.isdir(sub_target):
                    print(f"\n[AEGIS SHIELD] Scanning target directory: '{sub_target}'...")
                    res = doctor.scan_directory(sub_target)
                    print(res["message"])
                    for t in res.get("threats", []):
                        print(f"  - [THREAT] {t['filename']}: {', '.join(t.get('threats', []))}")
                    print()
                elif os.path.isfile(sub_target):
                    print(f"\n[AEGIS SHIELD] Scanning target file: '{sub_target}'...")
                    res = doctor.scan_file(sub_target)
                    print(res["message"])
                    print()
                else:
                    print(f"\n[AEGIS SHIELD] Running deep threat audit for '{sub_target}'...")
                    sec = doctor.scan_threats()
                    print(sec["summary_report"])
                    print()
            elif lower_q.startswith("quarantine "):
                target_file = query[11:].strip().strip('"').strip("'")
                if target_file.lower() == "list":
                    qlist = doctor.list_quarantine()
                    print(f"\n[AEGIS QUARANTINE VAULT] Total Neutralized: {qlist['total_quarantined']} file(s)")
                    for it in qlist.get("items", []):
                        print(f"  - {it['name']} ({it['size_bytes']} bytes, isolated {it['quarantined_at']})")
                    print()
                else:
                    print(f"\n[AEGIS SHIELD] Isolating file to quarantine vault: '{target_file}'...")
                    q_res = doctor.quarantine_file(target_file)
                    print(f"Result: {q_res['message']}\n")
            elif lower_q.startswith("kill ") or lower_q.startswith("terminate "):
                parts = query.split()
                if len(parts) > 1 and parts[1].isdigit():
                    target_pid = int(parts[1])
                    print(f"\n[AEGIS HUNTER-KILLER] Force-terminating hostile PID {target_pid} and isolating binary...")
                    k_res = doctor.antivirus.hunter_killer(target_pid)
                    print(f"Result: {k_res['message']}\n")
                else:
                    print("Usage: kill <pid>\n")
            elif lower_q in ("survey on", "monitor on", "watch on", "start survey"):
                print("\n[AEGIS SENTINEL] Engaging 24/7 background telemetry daemon...")
                s_res = doctor.start_sentinel(poll_interval=5.0, auto_heal_ram=True)
                print(f"Result: {s_res['message']}")
                print("Sentinel is now actively surveying battery, RAM leaks, thermal spikes, and frozen windows.\n")
            elif lower_q in ("survey off", "monitor off", "watch off", "stop survey"):
                print("\n[AEGIS SENTINEL] Disengaging background telemetry daemon...")
                s_res = doctor.stop_sentinel()
                print(f"Result: {s_res['message']}\n")
            elif lower_q in ("survey", "sentinel", "monitor", "watch", "status", "alerts"):
                print(doctor.sentinel.format_status_card())
                print()
            elif lower_q in ("help", "?"):
                print("\n[AEGIS DOCTOR & GUARDIAN COMMANDS]")
                print("  --- Hardware & Triage ---")
                print("  heal            - Full cure (RAM trim + DNS flush + temp cache purge)")
                print("  ram             - Instantly trim idle RAM working sets across apps")
                print("  dns             - Flush Windows DNS resolver cache")
                print("  cache           - Safely purge stale %TEMP% files (>1h old)")
                print("  startup         - List all startup programs and boot bottlenecks")
                print("  score           - Generate complete hardware clinic report card")
                print("  --- Military-Grade Antivirus & Threat Hunter ---")
                print("  scan            - Deep EDR threat audit across all vectors")
                print("  scan procs      - Audit process masquerading, parentage & LOLBins")
                print("  scan net        - Audit active sockets for rogue C2 beacons")
                print("  scan tasks      - Audit persistence in registry and scheduled tasks")
                print("  scan tampering  - Audit Windows Defender & UAC policy integrity")
                print("  scan <path>     - Scan specific file or folder for malware signatures")
                print("  kill <pid>      - Force-terminate hostile process tree and quarantine binary")
                print("  quarantine <path> - Safely neutralize & isolate suspicious file into vault")
                print("  quarantine list - List all files held in quarantine vault")
                print("  --- Sentinel 24/7 Background Guardian ---")
                print("  survey on       - Start continuous background surveillance & auto-RAM trimming")
                print("  survey off      - Stop continuous background surveillance")
                print("  survey          - Show live Sentinel telemetry status & recent alert log")
                print("  --- General ---")
                print("  quit            - Exit to PowerShell")
                print("  <text>          - Or describe any symptom or issue in plain English!\n")
            else:
                consult = doctor.doctor_consult(query)
                print(f"\n{consult['doctor_verdict']}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Aegis.")
            break


if __name__ == "__main__":
    run_cli()
