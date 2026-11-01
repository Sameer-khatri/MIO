"""
MIO Eyes: Visual Screen & Dialog Reader
---------------------------------------
Reads on-screen dialogs, alerts, prompts, and regional text safely with redaction.
Ideal for autonomous personas (like Dr. Aegis) to inspect system prompts.
"""

from typing import Dict, Any, Optional
from eyes.guard import SafeEyeShutter, redact_sensitive_text
from eyes.ocr import capture_and_recognize_region
from eyes.ui_tree import inspect_ui_elements
from hands.control.windows import _get_all_windows, _match_windows_for_query


def read_active_dialog() -> Dict[str, Any]:
    """
    Finds and reads the top-most active dialog, modal, or alert window.
    Extracts the dialog title, message prompt, and interactive buttons (e.g., OK, Cancel, Yes, No).
    """
    windows = _get_all_windows()
    if not windows:
        return {"success": False, "error": "No accessible windows found"}

    # Look for dialogs / small popup windows
    dialog_candidates = []
    for w in windows:
        title = w.get("title", "")
        # Common dialog titles
        lower_t = title.lower()
        if any(k in lower_t for k in ["prompt", "warning", "alert", "error", "confirm", "message", "setup", "update", "notice"]):
            dialog_candidates.append(w)

    target_win = dialog_candidates[0] if dialog_candidates else windows[0]
    hwnd = target_win["hwnd"]
    title = target_win["title"]

    # Use UI Automation to inspect buttons and text
    ui_info = inspect_ui_elements(hwnd=hwnd, max_elements=20, window_title=title)
    buttons = []
    text_elements = []

    if ui_info.get("success"):
        for el in ui_info.get("elements", []):
            el_type = el.get("type", "")
            el_name = el.get("name", "")
            if el_type == "Button" and el_name:
                buttons.append({
                    "name": el_name,
                    "clickable_x": el.get("clickable_x"),
                    "clickable_y": el.get("clickable_y"),
                })
            elif el_type in ("Text", "Label", "Edit") and el_name:
                text_elements.append(el_name)

    message = " ".join(text_elements) if text_elements else "(No distinct text element identified)"

    return {
        "success": True,
        "is_dialog": len(dialog_candidates) > 0,
        "window_title": redact_sensitive_text(title),
        "message": redact_sensitive_text(message),
        "buttons": buttons,
        "window": target_win,
    }


def read_screen_region(x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """Reads all visible text within an arbitrary screen bounding box."""
    if width <= 0 or height <= 0:
        return {"success": False, "error": "Width and height must be positive"}

    ocr_res = capture_and_recognize_region(x=x, y=y, width=width, height=height)
    if not ocr_res.get("success"):
        return ocr_res

    return {
        "success": True,
        "region": {"x": x, "y": y, "width": width, "height": height},
        "text": ocr_res.get("text", ""),
        "word_count": len(ocr_res.get("words", [])),
    }
