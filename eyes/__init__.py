"""
MIO EYES: Visual Perception & On-Screen Grounding
==================================================
Modular, zero-dependency, privacy-first eyes for MIO.
Seamlessly collaborates with MIO Hands (Mouse, Keyboard) and MIO People (Dr. Aegis).

Key Operations:
- see(query, target_window): Locates on-screen text/controls via UI tree or WinRT OCR.
- click_element(query, target_window): Locates target via Eyes and clicks it via Hands.
- type_into(query, text, target_window): Locates field via Eyes, focuses it, and types via Hands.
- read_dialog(): Detects active dialogs/alerts, extracting message and button options.
- get_status(): Returns mechanical shutter and privacy shield status.
"""

from typing import Dict, Any, Optional
import time

from eyes.guard import get_guard_status, SafeEyeShutter, is_window_safe, redact_sensitive_text
from eyes.ocr import recognize_image, capture_and_recognize_region
from eyes.ui_tree import inspect_ui_elements
from eyes.locator import locate_element, find_target_window, wait_for_element
from eyes.reader import read_active_dialog, read_screen_region
from eyes.watcher import get_screen_hash, wait_for_visual_change, wait_for_screen_stabilize

from hands.action.mouse import move_cursor, click as mouse_click, drag_to as mouse_drag_to, mouse_scroll
from hands.action.input import type_text


def see(query: str, target_window: str = "", control_type: str = "", timeout: float = 0.0) -> Dict[str, Any]:
    """
    Looks for an on-screen visual element or button matching query.
    If timeout > 0, performs adaptive polling until the element appears.
    Returns its bounding box, clickable coordinates, and matched window.
    """
    if timeout > 0:
        return wait_for_element(query=query, target_window=target_window, control_type=control_type, timeout=timeout)
    return locate_element(query=query, target_window=target_window, control_type=control_type)


def click_element(query: str, target_window: str = "", double_click: bool = False, timeout: float = 2.0) -> Dict[str, Any]:
    """
    Eyes find the element (with adaptive wait up to timeout seconds), and Action Hands click it.
    """
    if timeout > 0:
        loc_res = wait_for_element(query=query, target_window=target_window, timeout=timeout)
    else:
        loc_res = locate_element(query=query, target_window=target_window)

    if not loc_res.get("success"):
        return loc_res

    el = loc_res["element"]
    cx = el.get("clickable_x")
    cy = el.get("clickable_y")

    if cx is None or cy is None:
        return {"success": False, "error": f"Element '{query}' found but has no clickable coordinates."}

    # Move cursor to target and click via Action Hand
    move_cursor(cx, cy)
    click_res = mouse_click(button="left", double=double_click)

    return {
        "success": click_res.get("success", False),
        "action": "double_click" if double_click else "click",
        "target": query,
        "element": el,
        "method": loc_res.get("method"),
        "coordinates": {"x": cx, "y": cy},
        "mouse_result": click_res,
    }


def type_into(query: str, text: str, target_window: str = "", press_enter: bool = False) -> Dict[str, Any]:
    """
    Eyes locate the target input field, Action Hand clicks to focus, and types text.
    """
    loc_res = locate_element(query=query, target_window=target_window)
    if not loc_res.get("success"):
        return loc_res

    el = loc_res["element"]
    cx = el.get("clickable_x")
    cy = el.get("clickable_y")

    # 1. Click to focus
    move_cursor(cx, cy)
    mouse_click(button="left")
    time.sleep(0.1)

    # 2. Type text via Action Hand
    type_res = type_text(text=text)
    if press_enter:
        from hands.action.input import send_hotkey
        send_hotkey(["enter"])

    return {
        "success": type_res.get("success", False),
        "action": "type_into",
        "target_field": query,
        "typed_text": redact_sensitive_text(text),
        "element": el,
        "coordinates": {"x": cx, "y": cy},
        "input_result": type_res,
    }


def read_dialog() -> Dict[str, Any]:
    """Reads the active modal prompt or dialog on screen."""
    return read_active_dialog()


def read(x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> Dict[str, Any]:
    """Reads text from screen region. If 0 dimensions passed, inspects active dialog."""
    if width > 0 and height > 0:
        return read_screen_region(x=x, y=y, width=width, height=height)
    return read_active_dialog()


def drag_element(source_query: str, target_query: str = "", delta_x: int = 0, delta_y: int = 0, target_window: str = "") -> Dict[str, Any]:
    """
    Computer-Using Agent Drag: Locates source element via Eyes and smoothly drags it
    either to another visual target element or by (delta_x, delta_y) offset.
    """
    src_res = wait_for_element(query=source_query, target_window=target_window, timeout=2.0)
    if not src_res.get("success"):
        return src_res

    src_el = src_res["element"]
    start_x = src_el.get("clickable_x")
    start_y = src_el.get("clickable_y")

    if target_query:
        dest_res = wait_for_element(query=target_query, target_window=target_window, timeout=2.0)
        if not dest_res.get("success"):
            return dest_res
        dest_el = dest_res["element"]
        end_x = dest_el.get("clickable_x")
        end_y = dest_el.get("clickable_y")
    else:
        end_x = start_x + delta_x
        end_y = start_y + delta_y

    move_cursor(start_x, start_y)
    time.sleep(0.05)
    drag_res = mouse_drag_to(end_x, end_y, button="left", steps=20)

    return {
        "success": drag_res.get("success", False),
        "action": "drag_element",
        "source": source_query,
        "from": (start_x, start_y),
        "to": (end_x, end_y),
        "drag_result": drag_res,
    }


def scroll(direction: str = "down", clicks: int = 3) -> Dict[str, Any]:
    """
    Simulates mouse wheel scrolling.
    direction: 'up' or 'down'. clicks: number of scroll ticks.
    """
    amount = 120 * clicks if direction.lower() == "up" else -120 * clicks
    res = mouse_scroll(amount)
    return {
        "success": res.get("success", False),
        "action": "scroll",
        "direction": direction.lower(),
        "clicks": clicks,
        "message": f"Scrolled {direction.lower()} by {clicks} click(s)."
    }


def get_status() -> Dict[str, Any]:
    """Returns the mechanical shutter and security status of MIO Eyes."""
    return get_guard_status()


def wait_for_change(region: tuple[int, int, int, int] | None = None, timeout: float = 5.0) -> Dict[str, Any]:
    """Waits until screen or region visually mutates."""
    return wait_for_visual_change(region=region, timeout=timeout)


def wait_for_idle(region: tuple[int, int, int, int] | None = None, timeout: float = 6.0) -> Dict[str, Any]:
    """Waits until visual animations or rendering settle."""
    return wait_for_screen_stabilize(region=region, timeout=timeout)
