"""
MIO Eyes: Visual Element Locator
---------------------------------
Combines structural UI tree discovery with visual WinRT OCR to reliably
locate buttons, links, inputs, and text across any Windows application.
"""

from typing import Optional, Dict, Any, List
from eyes.guard import SafeEyeShutter
from eyes.ui_tree import inspect_ui_elements
from eyes.ocr import capture_and_recognize_region
from hands.control.windows import _get_all_windows, _match_windows_for_query
from hands.sensory.display import get_display_info


def find_target_window(query: str = "") -> Optional[Dict[str, Any]]:
    """Resolves a window dictionary given a title or process query. Defaults to active visible window."""
    windows = _get_all_windows()
    if not windows:
        return None

    if query and query.strip():
        matches = _match_windows_for_query(query, windows)
        if matches:
            return matches[0]

    # Return the first normal (non-minimized) window
    for w in windows:
        if w.get("state") != "minimized":
            return w
    return windows[0] if windows else None


def locate_element(query: str, target_window: str = "", control_type: str = "") -> Dict[str, Any]:
    """
    Locates an element on-screen by searching the accessibility tree first,
    then falling back to native OCR visual scanning.
    Returns:
        {
            "success": True,
            "query": query,
            "element": {
                "name": str,
                "type": str,
                "x": int,
                "y": int,
                "width": int,
                "height": int,
                "clickable_x": int,
                "clickable_y": int,
            },
            "method": "ui_tree" | "ocr",
            "window": window_info
        }
    """
    clean_query = query.strip()
    if not clean_query:
        return {"success": False, "error": "Search query cannot be empty"}

    win = find_target_window(target_window)
    hwnd = win["hwnd"] if win else 0
    win_title = win["title"] if win else ""
    proc_name = ""

    # Phase 1: Try UI Automation Tree
    if hwnd:
        ui_res = inspect_ui_elements(
            hwnd=hwnd,
            query=clean_query,
            control_type=control_type,
            max_elements=10,
            window_title=win_title,
            process_name=proc_name,
        )
        if ui_res.get("success") and ui_res.get("elements"):
            best_el = ui_res["elements"][0]
            return {
                "success": True,
                "query": clean_query,
                "element": best_el,
                "method": "ui_tree",
                "window": win,
            }

    # Phase 2: Visual OCR Fallback
    # Determine region: if window known, scan window rectangle; else scan primary monitor
    metrics = get_display_info()
    scan_x = 0
    scan_y = 0
    scan_w = metrics.get("primary_width", 1920) or 1920
    scan_h = metrics.get("primary_height", 1080) or 1080

    ocr_res = capture_and_recognize_region(
        x=scan_x,
        y=scan_y,
        width=scan_w,
        height=scan_h,
        window_title=win_title,
        process_name=proc_name,
    )

    if ocr_res.get("success"):
        norm_q = clean_query.lower()
        words = ocr_res.get("words", [])

        # Check exact or partial word match
        for w in words:
            word_txt = w.get("text", "").lower()
            if norm_q in word_txt or word_txt in norm_q:
                return {
                    "success": True,
                    "query": clean_query,
                    "element": {
                        "name": w.get("text"),
                        "type": "OcrText",
                        "x": w.get("x"),
                        "y": w.get("y"),
                        "width": w.get("width"),
                        "height": w.get("height"),
                        "clickable_x": w.get("clickable_x"),
                        "clickable_y": w.get("clickable_y"),
                    },
                    "method": "ocr",
                    "window": win,
                }

    return {
        "success": False,
        "error": f"Element matching '{clean_query}' could not be located via UI tree or OCR.",
        "window": win,
    }
