import ctypes
import time
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def get_cursor_position() -> dict:
    """Reads current mouse cursor screen coordinates (X, Y)."""
    if not user32:
        return {"success": False, "x": 0, "y": 0, "message": "user32 is unavailable."}

    pt = POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return {
            "success": True,
            "x": int(pt.x),
            "y": int(pt.y),
            "message": f"Cursor Position: X={pt.x}, Y={pt.y}"
        }
    return {"success": False, "x": 0, "y": 0, "message": "Failed to read cursor position."}


def move_cursor(x: int, y: int) -> dict:
    """Moves the mouse cursor to the specified screen coordinates (X, Y)."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    try:
        target_x = int(x)
        target_y = int(y)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid coordinates: ({x}, {y})."}

    ret = user32.SetCursorPos(target_x, target_y)
    if ret:
        return {
            "success": True,
            "x": target_x,
            "y": target_y,
            "message": f"Moved cursor to ({target_x}, {target_y})."
        }
    return {"success": False, "message": f"Failed to move cursor to ({target_x}, {target_y})."}


def click(button: str = "left", double: bool = False) -> dict:
    """
    Simulates a mouse click at current cursor position.
    button: 'left', 'right', or 'middle'.
    double: True for double click.
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    btn = button.strip().lower()
    if btn == "right":
        down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

    clicks = 2 if double else 1
    for i in range(clicks):
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        if double and i == 0:
            time.sleep(0.05)

    pos = get_cursor_position()
    action_type = f"Double {btn}-clicked" if double else f"{btn.title()}-clicked"
    return {
        "success": True,
        "button": btn,
        "double": double,
        "x": pos.get("x", 0),
        "y": pos.get("y", 0),
        "message": f"{action_type} at ({pos.get('x', 0)}, {pos.get('y', 0)})."
    }


def right_click() -> dict:
    """Convenience wrapper for right mouse click."""
    return click("right")


def double_click() -> dict:
    """Convenience wrapper for left double click."""
    return click("left", double=True)


def mouse_scroll(amount: int = 120) -> dict:
    """
    Scrolls the mouse wheel vertically.
    Positive values scroll up; negative values scroll down.
    Default standard wheel delta is 120 (1 notch up) or -120 (1 notch down).
    """
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    try:
        delta = int(amount)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid scroll amount: '{amount}'."}

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
    direction = "up" if delta > 0 else "down"
    return {
        "success": True,
        "amount": delta,
        "message": f"Scrolled mouse {direction} by {abs(delta)} units."
    }
