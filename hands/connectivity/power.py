import ctypes
import re
import subprocess
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    user32 = None
    kernel32 = None

HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
MONITOR_OFF = 2


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def lock_workstation() -> dict:
    """Locks the current Windows user session immediately."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    ret = user32.LockWorkStation()
    if ret:
        return {"success": True, "message": "Workstation locked successfully."}
    return {"success": False, "message": "Failed to lock workstation."}


def turn_off_screen() -> dict:
    """Puts the display monitors to sleep power-saving mode."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
    return {"success": True, "message": "Display turned off (monitor sleeping)."}


def sleep_system() -> dict:
    """Puts the computer to Sleep (standby)."""
    try:
        powrprof = ctypes.windll.powrprof
        powrprof.SetSuspendState(0, 1, 0)
        return {"success": True, "message": "System put into sleep mode."}
    except Exception as err:
        return {"success": False, "message": f"Failed to sleep system: {err}"}


def hibernate_system() -> dict:
    """Puts the computer into Hibernation."""
    try:
        powrprof = ctypes.windll.powrprof
        powrprof.SetSuspendState(1, 1, 0)
        return {"success": True, "message": "System put into hibernation."}
    except Exception as err:
        return {"success": False, "message": f"Failed to hibernate: {err}"}


def schedule_shutdown(seconds: int = 60) -> dict:
    """Schedules a system shutdown after N seconds."""
    sec = max(0, int(seconds))
    try:
        subprocess.check_output(["shutdown.exe", "/s", "/t", str(sec)], stderr=subprocess.STDOUT)
        return {"success": True, "seconds": sec, "message": f"Shutdown scheduled in {sec} second(s)."}
    except Exception as err:
        return {"success": False, "message": f"Failed to schedule shutdown: {err}"}


def schedule_restart(seconds: int = 60) -> dict:
    """Schedules a system restart after N seconds."""
    sec = max(0, int(seconds))
    try:
        subprocess.check_output(["shutdown.exe", "/r", "/t", str(sec)], stderr=subprocess.STDOUT)
        return {"success": True, "seconds": sec, "message": f"Restart scheduled in {sec} second(s)."}
    except Exception as err:
        return {"success": False, "message": f"Failed to schedule restart: {err}"}


def cancel_shutdown() -> dict:
    """Cancels any pending scheduled shutdown or restart."""
    try:
        subprocess.check_output(["shutdown.exe", "/a"], stderr=subprocess.STDOUT)
        return {"success": True, "message": "Pending scheduled shutdown/restart has been cancelled."}
    except Exception as err:
        return {"success": False, "message": f"Failed to cancel shutdown: {err}"}


def get_active_power_plan() -> dict:
    """Retrieves the active Windows power plan scheme (Balanced, High Performance, Silent, etc.)."""
    try:
        output = subprocess.check_output(
            ["powercfg", "/getactivescheme"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        ).strip()

        match = re.search(r"\((.*?)\)", output)
        plan_name = match.group(1) if match else output
        return {
            "success": True,
            "plan": plan_name,
            "raw": output,
            "message": f"Active Power Plan: {plan_name}"
        }
    except Exception as err:
        return {"success": False, "message": f"Could not retrieve active power plan: {err}"}


def get_battery_status() -> dict:
    """Reads system battery percentage, charging state, and estimated remaining run time."""
    if not kernel32:
        return {"success": False, "message": "kernel32 is unavailable."}

    sps = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
        return {"success": False, "message": "Failed to read system power status."}

    percent = sps.BatteryLifePercent
    is_ac = (sps.ACLineStatus == 1)
    is_charging = bool(sps.BatteryFlag & 8)
    no_battery = (sps.BatteryFlag == 128)

    if no_battery or percent == 255:
        return {
            "success": True,
            "has_battery": False,
            "ac_connected": is_ac,
            "message": "Desktop system: Running on AC power (No battery detected)."
        }

    status_str = "Plugged in, charging" if (is_ac and is_charging) else ("Plugged in, not charging" if is_ac else "On battery power")

    time_remaining_min = None
    if sps.BatteryLifeTime != 0xFFFFFFFF and sps.BatteryLifeTime > 0:
        time_remaining_min = sps.BatteryLifeTime // 60

    time_str = f" (~{time_remaining_min} mins remaining)" if time_remaining_min else ""

    power_src_str = "AC Adapter" if is_ac else "Battery"
    return {
        "success": True,
        "has_battery": True,
        "percent": percent,
        "charging": is_charging,
        "ac_connected": is_ac,
        "time_remaining_minutes": time_remaining_min,
        "message": f"Power Source: {power_src_str}. Battery: {percent}% ({status_str}){time_str}."
    }
