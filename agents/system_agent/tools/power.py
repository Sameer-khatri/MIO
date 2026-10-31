import ctypes
import os
import subprocess
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    user32 = None
    kernel32 = None


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
    """Immediately locks the Windows user session."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    ret = user32.LockWorkStation()
    if ret:
        return {
            "success": True,
            "message": "Windows workstation locked successfully."
        }
    return {
        "success": False,
        "message": "Failed to lock workstation."
    }


def turn_off_screen() -> dict:
    """Puts the display/monitors into low-power sleep mode."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    HWND_BROADCAST = 0xFFFF
    WM_SYSCOMMAND = 0x0112
    SC_MONITORPOWER = 0xF170
    MONITOR_OFF = 2

    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF)
    return {
        "success": True,
        "message": "Turned off display (moving mouse or typing will wake it)."
    }


def get_battery_status() -> dict:
    """Reads live hardware power status (AC power, battery percentage, charging state)."""
    if not kernel32:
        return {"success": False, "message": "kernel32 is unavailable."}

    sps = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
        return {"success": False, "message": "Failed to query system power status."}

    # AC Line Status: 0 = Offline (Battery), 1 = Online (Plugged in), 255 = Unknown
    ac_connected = sps.ACLineStatus == 1
    ac_label = "Plugged In" if ac_connected else ("On Battery" if sps.ACLineStatus == 0 else "Unknown")

    # BatteryFlag: 8 = Charging, 128 = No system battery (Desktop PC)
    has_battery = not bool(sps.BatteryFlag & 128)
    is_charging = bool(sps.BatteryFlag & 8)

    pct = int(sps.BatteryLifePercent)
    if pct == 255 or not has_battery:
        battery_pct = None
        batt_str = "No battery detected (Desktop)"
    else:
        battery_pct = pct
        batt_str = f"{pct}% {'(Charging)' if is_charging else ''}".strip()

    remaining_sec = sps.BatteryLifeTime if sps.BatteryLifeTime != 0xFFFFFFFF else None
    remaining_min = round(remaining_sec / 60) if remaining_sec else None

    lines = [f"Power Source: {ac_label}", f"Battery: {batt_str}"]
    if remaining_min:
        lines.append(f"Estimated Time Remaining: {remaining_min} minutes")

    return {
        "success": True,
        "ac_connected": ac_connected,
        "power_source": ac_label,
        "has_battery": has_battery,
        "battery_percent": battery_pct,
        "is_charging": is_charging,
        "remaining_minutes": remaining_min,
        "message": "\n".join(lines)
    }
