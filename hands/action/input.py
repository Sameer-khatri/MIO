import ctypes
import time

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

VK_CODES = {
    "win": 0x5B,
    "lwin": 0x5B,
    "rwin": 0x5C,
    "alt": 0x12,
    "ctrl": 0x11,
    "shift": 0x10,
    "tab": 0x09,
    "enter": 0x0D,
    "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "f4": 0x73,
    "e": 0x45,
    "i": 0x49,
    "r": 0x52,
    "d": 0x44,
    "v": 0x56,
    "c": 0x43,
    "a": 0x41,
    "z": 0x5A,
    "/": 0xBF,
    "?": 0xBF,
}


def _press(vk: int):
    if user32:
        user32.keybd_event(vk, 0, 0, 0)


def _release(vk: int):
    if user32:
        user32.keybd_event(vk, 0, 2, 0)


def send_hotkey(keys: list[str]) -> dict:
    """
    Sends a combination hotkey (e.g. ['ctrl', 'shift', 'esc'] or ['win', 'd']).
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    vk_list = []
    for k in keys:
        norm = k.strip().lower()
        if norm in VK_CODES:
            vk_list.append(VK_CODES[norm])
        elif len(norm) == 1 and norm.isalpha():
            vk_list.append(ord(norm.upper()))
        elif norm.startswith("f") and norm[1:].isdigit():
            fn_num = int(norm[1:])
            if 1 <= fn_num <= 12:
                vk_list.append(0x70 + (fn_num - 1))

    if not vk_list:
        return {"success": False, "message": f"Could not map keys: {keys}"}

    for vk in vk_list:
        _press(vk)
        time.sleep(0.01)

    for vk in reversed(vk_list):
        _release(vk)
        time.sleep(0.01)

    return {
        "success": True,
        "keys": keys,
        "message": f"Sent hotkey combination: {' + '.join(keys).upper()}."
    }


press_hotkey = send_hotkey


def press_key(key: str) -> dict:
    """Presses and releases a single key (e.g. 'enter', 'space', 'esc', 'tab', 'k', 'f', 'm')."""
    return send_hotkey([key])


def show_desktop() -> dict:
    """Simulates Win + D to minimize all windows and show desktop."""
    return send_hotkey(["win", "d"])


def open_task_manager() -> dict:
    """Simulates Ctrl + Shift + Esc to open Task Manager."""
    return send_hotkey(["ctrl", "shift", "esc"])


def switch_app_alt_tab() -> dict:
    """Simulates Alt + Tab to switch between active applications."""
    return send_hotkey(["alt", "tab"])


def open_file_explorer() -> dict:
    """Simulates Win + E to open Windows File Explorer."""
    return send_hotkey(["win", "e"])


def open_windows_settings() -> dict:
    """Simulates Win + I to open Windows Settings."""
    return send_hotkey(["win", "i"])


def open_run_dialog() -> dict:
    """Simulates Win + R to open the Windows Run dialog."""
    return send_hotkey(["win", "r"])


def close_active_window() -> dict:
    """Simulates Alt + F4 to cleanly close the active window."""
    return send_hotkey(["alt", "f4"])


def select_all() -> dict:
    """Simulates Ctrl + A to select all text or items."""
    return send_hotkey(["ctrl", "a"])


def copy_selection() -> dict:
    """Simulates Ctrl + C to copy selection."""
    return send_hotkey(["ctrl", "c"])


def paste_selection() -> dict:
    """Simulates Ctrl + V to paste selection."""
    return send_hotkey(["ctrl", "v"])


def type_text(text: str, delay_ms: int = 0) -> dict:
    """
    Simulates keyboard typing of arbitrary unicode text via SendInput.
    Supports optional per-character typing delay for human pacing.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("_input", _INPUT),
        ]

    INPUT_KEYBOARD = 1
    delay_sec = max(0, delay_ms) / 1000.0

    for char in text:
        scan_code = ord(char)

        inp_down = INPUT(type=INPUT_KEYBOARD)
        inp_down.ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)

        inp_up = INPUT(type=INPUT_KEYBOARD)
        inp_up.ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)

        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

        if delay_sec > 0:
            time.sleep(delay_sec)

    return {
        "success": True,
        "length": len(text),
        "characters_typed": len(text),
        "message": f"Successfully typed {len(text)} character(s)."
    }
