import os
import winreg


PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DWM_KEY = r"Software\Microsoft\Windows\DWM"


def get_theme_mode() -> dict:
    """
    Reads the current Windows system and application color theme (Dark or Light).
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY, 0, winreg.KEY_READ) as key:
            apps_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            system_light, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")

        app_theme = "light" if apps_light == 1 else "dark"
        sys_theme = "light" if system_light == 1 else "dark"

        return {
            "success": True,
            "apps_theme": app_theme,
            "system_theme": sys_theme,
            "theme": app_theme,
            "message": f"Windows Theme: Apps are in {app_theme} mode, System is in {sys_theme} mode."
        }
    except Exception as err:
        return {
            "success": False,
            "apps_theme": "unknown",
            "system_theme": "unknown",
            "message": f"Could not read Windows theme: {err}"
        }


def set_theme_mode(mode: str) -> dict:
    """
    Switches Windows theme between 'dark' and 'light' mode for both apps and system UI.
    """
    if not mode or not isinstance(mode, str):
        return {"success": False, "message": "Theme mode must be 'dark' or 'light'."}

    norm_mode = mode.strip().lower()
    if norm_mode not in ("dark", "light"):
        return {"success": False, "message": f"Invalid theme mode '{mode}'. Choose 'dark' or 'light'."}

    val = 1 if norm_mode == "light" else 0

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)

        return {
            "success": True,
            "theme": norm_mode,
            "message": f"Successfully switched Windows theme to {norm_mode.upper()} mode."
        }
    except Exception as err:
        return {
            "success": False,
            "theme": norm_mode,
            "message": f"Failed to set Windows theme: {err}"
        }


def get_accent_color() -> dict:
    """
    Reads the current Windows desktop accent color from the DWM registry key.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DWM_KEY, 0, winreg.KEY_READ) as key:
            color_val, _ = winreg.QueryValueEx(key, "ColorizationColor")

        # ColorizationColor is typically ARGB (e.g. 0xC40078D7)
        hex_str = f"#{color_val & 0xFFFFFF:06X}"
        return {
            "success": True,
            "accent_hex": hex_str,
            "raw_value": color_val,
            "message": f"Current Windows Accent Color: {hex_str}"
        }
    except Exception as err:
        return {
            "success": False,
            "accent_hex": "#000000",
            "message": f"Could not retrieve accent color: {err}"
        }
