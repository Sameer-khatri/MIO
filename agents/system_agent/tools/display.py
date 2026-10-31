import ctypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80


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

        return {
            "success": True,
            "primary_resolution": f"{primary_w}x{primary_h}",
            "primary_width": primary_w,
            "primary_height": primary_h,
            "virtual_resolution": f"{virtual_w}x{virtual_h}",
            "virtual_width": virtual_w,
            "virtual_height": virtual_h,
            "monitor_count": monitor_count,
            "dpi": dpi,
            "scaling_percent": scale_percent,
            "message": (
                f"Display: {primary_w}x{primary_h} ({scale_percent}% scaling) | "
                f"Monitors: {monitor_count} | Virtual Desktop: {virtual_w}x{virtual_h}"
            )
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to retrieve display metrics: {err}"
        }
