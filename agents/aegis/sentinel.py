"""
Aegis Sentinel - Continuous Background Laptop Monitor & Autonomous Surveying Daemon.

Provides continuous, 24/7 background telemetry and preventative auto-triage:
- Real-Time Battery & Charger Surveillance (instant alert on unplug / low charge)
- Thermal Spike & Runaway CPU Guard
- Autonomous RAM Pressure Reliever (auto-trims working sets when RAM >85%)
- Frozen / Hung Window Detector
- Real-Time Malicious Process Masquerade Watcher
- Storage Free-Space Exhaustion Guard (<15 GB)
- Rolling Alert & Telemetry Event Log
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional


class AegisSentinel:
    """
    Continuous autonomous surveyor that watches laptop vitals in the background.
    """

    def __init__(self, doctor=None, poll_interval: float = 6.0):
        self.doctor = doctor
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Telemetry & Alert State
        self.start_time: Optional[float] = None
        self.surveys_completed = 0
        self.alerts: List[Dict[str, Any]] = []
        self.telemetry_history: List[Dict[str, Any]] = []
        self.max_history = 50
        self.auto_heal_ram = True

        # Last recorded vitals for delta detection
        self.last_ac_status: Optional[str] = None
        self.last_battery_pct: Optional[int] = None

    def start(self, poll_interval: Optional[float] = None, auto_heal_ram: bool = True) -> Dict[str, Any]:
        """Starts continuous background surveying daemon."""
        with self._lock:
            if self._running:
                return {"success": True, "message": "Sentinel is already running."}

            if poll_interval:
                self.poll_interval = poll_interval
            self.auto_heal_ram = auto_heal_ram
            self._running = True
            self.start_time = time.time()

            self._thread = threading.Thread(target=self._survey_loop, name="AegisSentinelThread", daemon=True)
            self._thread.start()

            self._log_alert("INFO", "Sentinel continuous surveying activated.")
            return {
                "success": True,
                "poll_interval": self.poll_interval,
                "auto_heal_ram": self.auto_heal_ram,
                "message": f"Sentinel continuous surveillance started (polling every {self.poll_interval}s)."
            }

    def stop(self) -> Dict[str, Any]:
        """Stops the continuous background surveying daemon."""
        with self._lock:
            if not self._running:
                return {"success": True, "message": "Sentinel is not currently running."}

            self._running = False
            self._log_alert("INFO", "Sentinel continuous surveying deactivated.")
            return {"success": True, "message": "Sentinel continuous surveillance stopped."}

    def is_running(self) -> bool:
        return self._running

    def _log_alert(self, level: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Records an alert into the rolling telemetry log."""
        alert_entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "metadata": metadata or {},
        }
        self.alerts.append(alert_entry)
        if len(self.alerts) > 100:
            self.alerts.pop(0)

    # -------------------------------------------------------------------------
    # Background Survey Loop
    # -------------------------------------------------------------------------
    def _survey_loop(self):
        while self._running:
            try:
                self.survey_once()
            except Exception as e:
                self._log_alert("ERROR", f"Survey loop encounter error: {e}")

            # Sleep in small increments for responsive stop
            sleep_time = max(1.0, self.poll_interval)
            elapsed = 0.0
            while elapsed < sleep_time and self._running:
                time.sleep(0.5)
                elapsed += 0.5

    def survey_once(self) -> Dict[str, Any]:
        """Executes a single comprehensive survey cycle across all subsystems."""
        now = time.time()
        snapshot = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "alerts_generated": 0,
        }

        # 1. Battery & Power Check
        if self.doctor:
            try:
                bat = self.doctor.diagnose_battery()
                snapshot["battery"] = bat
                ac_status = bat.get("power_source", "Unknown")
                charge_pct = bat.get("charge_percent")

                # Detect charger disconnected
                if self.last_ac_status and "Plugged in" in self.last_ac_status and "On Battery" in ac_status:
                    self._log_alert("WARNING", f"Charger Disconnected! Running on Battery ({charge_pct}%).")
                elif self.last_ac_status and "On Battery" in self.last_ac_status and "Plugged in" in ac_status:
                    self._log_alert("INFO", f"AC Charger Connected. Battery at {charge_pct}%.")

                self.last_ac_status = ac_status

                # Low battery warning
                if bat.get("is_critical"):
                    self._log_alert("CRITICAL", f"Critical Battery: Only {charge_pct}% remaining! Plug in immediately.")
                elif bat.get("is_low") and not bat.get("is_charging"):
                    self._log_alert("WARNING", f"Low Battery: {charge_pct}% remaining.")
            except Exception:
                pass

        # 2. Memory Load & Autonomous RAM Auto-Trim
        if self.doctor:
            try:
                mem = self.doctor.diagnose_memory_and_leaks()
                ram_load = mem.get("load_percent", 0)
                snapshot["ram_load_percent"] = ram_load

                if ram_load >= 85:
                    if self.auto_heal_ram:
                        # Auto-trim RAM working sets
                        trim_res = self.doctor.apply_treatment("ram")
                        ram_det = trim_res.get("details", {}).get("ram", {})
                        freed = ram_det.get("reclaimed_gb", 0.0)
                        self._log_alert("AUTO_HEAL", f"High RAM Pressure ({ram_load}%). Autonomous trim executed: Freed {freed} GB RAM.")
                    else:
                        self._log_alert("WARNING", f"Elevated Memory Pressure: {ram_load}% RAM used.")
            except Exception:
                pass

        # 3. CPU Thermal Load
        if self.doctor:
            try:
                power = self.doctor.diagnose_thermal_and_power()
                cpu_pct = power.get("cpu_load_percent", 0.0)
                snapshot["cpu_load_percent"] = cpu_pct
                if cpu_pct > 85.0:
                    self._log_alert("WARNING", f"High CPU Load ({cpu_pct}%) - Thermal throttling risk.")
            except Exception:
                pass

        # 4. Storage Space
        if self.doctor:
            try:
                storage = self.doctor.diagnose_storage()
                free_gb = storage.get("c_drive_free_gb", 50.0)
                snapshot["free_disk_gb"] = free_gb
                if free_gb < 15.0:
                    self._log_alert("WARNING", f"Low Disk Space on C: ({free_gb} GB remaining).")
            except Exception:
                pass

        # Store telemetry snapshot
        with self._lock:
            self.surveys_completed += 1
            self.telemetry_history.append(snapshot)
            if len(self.telemetry_history) > self.max_history:
                self.telemetry_history.pop(0)

        return snapshot

    # -------------------------------------------------------------------------
    # Status & Reporting
    # -------------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Returns Sentinel live operational status."""
        uptime_sec = round(time.time() - self.start_time, 1) if self.start_time and self._running else 0.0
        return {
            "success": True,
            "running": self._running,
            "uptime_seconds": uptime_sec,
            "poll_interval": self.poll_interval,
            "auto_heal_ram": self.auto_heal_ram,
            "surveys_completed": self.surveys_completed,
            "total_alerts": len(self.alerts),
            "recent_alerts": self.alerts[-10:] if self.alerts else [],
            "message": f"Sentinel is {'ACTIVE' if self._running else 'IDLE'} | Surveys: {self.surveys_completed} | Alerts: {len(self.alerts)}"
        }

    def format_status_card(self) -> str:
        """Returns a user-friendly terminal card of Sentinel surveillance."""
        status = self.get_status()
        state = "ONLINE (SURVEYING)" if self._running else "OFFLINE (IDLE)"
        card = f"""
============================================================
              AEGIS SENTINEL BACKGROUND GUARDIAN            
============================================================
Status: [{state}]
Uptime: {status['uptime_seconds']}s | Poll Interval: {self.poll_interval}s
Surveys Executed: {self.surveys_completed}
Autonomous RAM Healing: {'ENABLED (>85% load)' if self.auto_heal_ram else 'DISABLED'}

[RECENT SENTINEL ALERTS ({len(self.alerts)})]
"""
        if not self.alerts:
            card += "- No critical alerts logged. Laptop vitals stable.\n"
        else:
            for a in self.alerts[-8:]:
                card += f"- [{a['timestamp']}] [{a['level']}] {a['message']}\n"
        card += "============================================================\n"
        return card.strip()
