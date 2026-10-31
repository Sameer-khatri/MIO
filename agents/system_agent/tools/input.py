import ctypes
import time
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

# Key codes mapping
KEY_MAP = {
    "win": 0x5B,
    "windows": 0x5B,
    "super": 0x5B,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "enter": 0x0D,
    "return": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def _resolve_vk(key: str) -> int | None:
    """Maps a key name or single character to its Win32 virtual-key code."""
    clean = key.strip().lower()
    if clean in KEY_MAP:
        return KEY_MAP[clean]
    if len(clean) == 1:
        # A-Z, 0-9
        ch = clean.upper()
        return ord(ch)
    return None


def send_hotkey(keys: list[str]) -> dict:
    """
    Simulates pressing a combination of keys together (e.g. ['ctrl', 's'] or ['win', 'd']).
    Presses all keys in order, then releases them in reverse order.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    if not keys or not isinstance(keys, (list, tuple)):
        return {"success": False, "message": "Please specify a list of keys to press."}

    vk_codes = []
    for k in keys:
        vk = _resolve_vk(str(k))
        if vk is None:
            return {"success": False, "message": f"Unrecognized key: '{k}'."}
        vk_codes.append(vk)

    # Press down in order
    for vk in vk_codes:
        user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.02)

    # Release in reverse order
    for vk in reversed(vk_codes):
        user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.02)

    combo_str = " + ".join(str(k).upper() for k in keys)
    return {
        "success": True,
        "combination": combo_str,
        "message": f"Pressed hotkey: {combo_str}."
    }


def show_desktop() -> dict:
    """Minimizes all windows to show the desktop (Win + D)."""
    return send_hotkey(["win", "d"])


def open_task_manager() -> dict:
    """Launches or focuses Windows Task Manager (Ctrl + Shift + Esc)."""
    return send_hotkey(["ctrl", "shift", "esc"])


def switch_app_alt_tab() -> dict:
    """Switches to the previous active application (Alt + Tab)."""
    return send_hotkey(["alt", "tab"])


def type_text(text: str) -> dict:
    """
    Types text into the active foreground window character by character.
    Uses Win32 unicode input (KEYEVENTF_UNICODE = 0x0004).
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    if not text:
        return {"success": True, "message": "Typed 0 characters."}

    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    for ch in text:
        code = ord(ch)
        user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
        user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)

    return {
        "success": True,
        "length": len(text),
        "message": f"Typed {len(text)} characters into active window."
    }
