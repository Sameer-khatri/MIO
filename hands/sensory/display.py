import ctypes
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
ENUM_CURRENT_SETTINGS = -1

MONITORINFOF_PRIMARY = 0x00000001


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", wintypes.SHORT),
        ("dmPaperSize", wintypes.SHORT),
        ("dmPaperLength", wintypes.SHORT),
        ("dmPaperWidth", wintypes.SHORT),
        ("dmScale", wintypes.SHORT),
        ("dmCopies", wintypes.SHORT),
        ("dmDefaultSource", wintypes.SHORT),
        ("dmPrintQuality", wintypes.SHORT),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
    ]


def get_display_info() -> dict:
    """
    Retrieves screen resolution, multi-monitor configuration, virtual desktop bounds,
    and display DPI scaling factor.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    try:
        primary_w = user32.GetSystemMetrics(SM_CXSCREEN)
        primary_h = user32.GetSystemMetrics(SM_CYSCREEN)
        virtual_w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        virtual_h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        monitor_count = user32.GetSystemMetrics(SM_CMONITORS) or 1

        dpi = 96
        if hasattr(user32, "GetDpiForSystem"):
            try:
                dpi = user32.GetDpiForSystem() or 96
            except Exception:
                dpi = 96

        scale_percent = int(round((dpi / 96.0) * 100))

        # Query refresh rate if possible
        refresh_rate = 60
        try:
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)
            if user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
                refresh_rate = dm.dmDisplayFrequency
        except Exception:
            pass

        return {
            "success": True,
            "primary_resolution": f"{primary_w}x{primary_h}",
            "primary_width": primary_w,
            "primary_height": primary_h,
            "virtual_resolution": f"{virtual_w}x{virtual_h}",
            "virtual_width": virtual_w,
            "virtual_height": virtual_h,
            "monitor_count": monitor_count,
            "refresh_rate_hz": refresh_rate,
            "dpi": dpi,
            "scaling_percent": scale_percent,
            "message": (
                f"Display: {primary_w}x{primary_h} @ {refresh_rate}Hz ({scale_percent}% scaling) | "
                f"Monitors: {monitor_count} | Virtual Desktop: {virtual_w}x{virtual_h}"
            )
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to retrieve display metrics: {err}"
        }


def get_monitors_detail() -> dict:
    """
    Enumerates all active physical monitors, their bounds, resolution, and primary status.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    monitors = []

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
            r = mi.rcMonitor
            w = r.right - r.left
            h = r.bottom - r.top
            is_primary = bool(mi.dwFlags & MONITORINFOF_PRIMARY)
            monitors.append({
                "device": mi.szDevice,
                "is_primary": is_primary,
                "left": r.left,
                "top": r.top,
                "right": r.right,
                "bottom": r.bottom,
                "width": w,
                "height": h,
                "resolution": f"{w}x{h}"
            })
        return 1

    try:
        MonitorEnumProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(RECT),
            wintypes.LPARAM
        )
        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(monitor_enum_proc), 0)

        return {
            "success": True,
            "count": len(monitors),
            "monitors": monitors,
            "message": f"Detected {len(monitors)} monitor(s): " + ", ".join(
                f"{m['device']} ({m['resolution']}{' [Primary]' if m['is_primary'] else ''})"
                for m in monitors
            )
        }
    except Exception as err:
        return {
            "success": False,
            "monitors": [],
            "message": f"Failed to enumerate monitors: {err}"
        }


def get_display_modes() -> dict:
    """
    Retrieves the active display hardware frequency (refresh rate in Hz), color depth,
    and orientation (Landscape vs Portrait).
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    try:
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
            orientations = {0: "Landscape", 1: "Portrait", 2: "Landscape (Flipped)", 3: "Portrait (Flipped)"}
            orient_str = orientations.get(dm.dmOrientation, "Landscape")
            return {
                "success": True,
                "width": dm.dmPelsWidth,
                "height": dm.dmPelsHeight,
                "refresh_rate_hz": dm.dmDisplayFrequency,
                "bits_per_pixel": dm.dmBitsPerPel,
                "orientation": orient_str,
                "message": f"Display Mode: {dm.dmPelsWidth}x{dm.dmPelsHeight} @ {dm.dmDisplayFrequency}Hz, {dm.dmBitsPerPel}-bit color ({orient_str})"
            }
        return {"success": False, "message": "Failed to query display settings."}
    except Exception as err:
        return {"success": False, "message": f"Could not retrieve display modes: {err}"}
