import ctypes
import time
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

MOUSEEVENTF_MOVE = 0x0001
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


get_mouse_position = get_cursor_position
set_mouse_position = move_cursor


def move_relative(dx: int, dy: int) -> dict:
    """Moves cursor relative to its current position."""
    pos = get_cursor_position()
    if not pos.get("success"):
        return pos
    new_x = pos["x"] + int(dx)
    new_y = pos["y"] + int(dy)
    return move_cursor(new_x, new_y)


def mouse_down(button: str = "left") -> dict:
    """Presses and holds down a mouse button ('left', 'right', 'middle')."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    btn = button.strip().lower()
    flag = MOUSEEVENTF_LEFTDOWN
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTDOWN
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEDOWN

    user32.mouse_event(flag, 0, 0, 0, 0)
    return {"success": True, "button": btn, "message": f"{btn.title()} mouse button pressed down."}


def mouse_up(button: str = "left") -> dict:
    """Releases a mouse button ('left', 'right', 'middle')."""
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    btn = button.strip().lower()
    flag = MOUSEEVENTF_LEFTUP
    if btn == "right":
        flag = MOUSEEVENTF_RIGHTUP
    elif btn == "middle":
        flag = MOUSEEVENTF_MIDDLEUP

    user32.mouse_event(flag, 0, 0, 0, 0)
    return {"success": True, "button": btn, "message": f"{btn.title()} mouse button released."}


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


def drag_to(target_x: int, target_y: int, button: str = "left", steps: int = 15) -> dict:
    """
    Smoothly drags the cursor from its current position to (target_x, target_y).
    """
    pos = get_cursor_position()
    if not pos.get("success"):
        return pos

    start_x, start_y = pos["x"], pos["y"]
    dest_x, dest_y = int(target_x), int(target_y)

    mouse_down(button)
    time.sleep(0.02)

    for i in range(1, steps + 1):
        curr_x = int(start_x + (dest_x - start_x) * (i / steps))
        curr_y = int(start_y + (dest_y - start_y) * (i / steps))
        user32.SetCursorPos(curr_x, curr_y)
        time.sleep(0.01)

    time.sleep(0.02)
    mouse_up(button)

    return {
        "success": True,
        "from": (start_x, start_y),
        "to": (dest_x, dest_y),
        "button": button,
        "message": f"Dragged cursor from ({start_x}, {start_y}) to ({dest_x}, {dest_y})."
    }


def mouse_scroll(amount: int = 120) -> dict:
    """
    Scrolls the mouse wheel vertically.
    Positive values scroll up; negative values scroll down.
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
