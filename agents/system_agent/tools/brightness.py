import subprocess
import re


def get_brightness() -> dict:
    """
    Reads the current screen brightness level (0-100%) on Windows laptops/monitors
    supporting WMI monitor controls.
    """
    ps_cmd = (
        "Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness "
        "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentBrightness"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        if output and output.isdigit():
            val = int(output)
            return {
                "success": True,
                "brightness": val,
                "message": f"Current Display Brightness: {val}%"
            }
        return {
            "success": False,
            "brightness": None,
            "message": "Screen brightness control is not supported on this monitor (desktop/external display)."
        }
    except Exception as err:
        return {
            "success": False,
            "brightness": None,
            "message": f"Failed to retrieve brightness: {err}"
        }


def set_brightness(percent: int) -> dict:
    """
    Sets the display brightness to a specific percentage (0-100%).
    """
    try:
        val = int(percent)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid brightness value: '{percent}'."}

    val = max(0, min(100, val))

    ps_cmd = (
        f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods "
        f"-ErrorAction SilentlyContinue).WmiSetBrightness(1, {val})"
    )
    try:
        subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True
        )
        return {
            "success": True,
            "brightness": val,
            "message": f"Brightness set to {val}%."
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to set brightness to {val}%: {err}"
        }


def increase_brightness(delta: int = 10) -> dict:
    """Increases current screen brightness by delta (default 10%)."""
    curr = get_brightness()
    if not curr.get("success"):
        return curr
    current_val = curr.get("brightness", 50)
    return set_brightness(current_val + delta)


def decrease_brightness(delta: int = 10) -> dict:
    """Decreases current screen brightness by delta (default 10%)."""
    curr = get_brightness()
    if not curr.get("success"):
        return curr
    current_val = curr.get("brightness", 50)
    return set_brightness(current_val - delta)
