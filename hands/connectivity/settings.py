import ctypes
import os
import winreg

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
DWM_KEY = r"Software\Microsoft\Windows\DWM"

SPI_GETDESKWALLPAPER = 0x0073
SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


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


def get_wallpaper() -> dict:
    """
    Retrieves the full path to the currently active desktop wallpaper image.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    buf = ctypes.create_unicode_buffer(512)
    if user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 512, buf, 0):
        path = buf.value
        return {
            "success": True,
            "wallpaper_path": path,
            "message": f"Current Desktop Wallpaper: '{path}'"
        }
    return {"success": False, "message": "Failed to read wallpaper path."}


def set_wallpaper(image_path: str) -> dict:
    """
    Changes the Windows desktop background wallpaper to the specified image file.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    if not image_path or not isinstance(image_path, str):
        return {"success": False, "message": "Image path is required."}

    norm_path = os.path.abspath(os.path.expanduser(image_path.strip()))
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        return {"success": False, "message": f"Image file not found: '{norm_path}'"}

    ret = user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        norm_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if ret:
        return {
            "success": True,
            "wallpaper_path": norm_path,
            "message": f"Successfully updated desktop wallpaper to '{norm_path}'."
        }
    return {"success": False, "message": f"Failed to set wallpaper to '{norm_path}'."}


def set_transparency_effects(enabled: bool) -> dict:
    """
    Enables or disables Windows visual acrylic and transparency effects.
    """
    val = 1 if enabled else 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, val)

        state_str = "Enabled" if enabled else "Disabled"
        return {
            "success": True,
            "transparency_enabled": enabled,
            "message": f"{state_str} Windows visual transparency effects."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to update transparency: {err}"}


# Aliases for registry catalog and callers
get_windows_theme = get_theme_mode
set_windows_theme = set_theme_mode
