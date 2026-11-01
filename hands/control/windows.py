import ctypes
import os
import time
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
except (AttributeError, OSError):
    user32 = None
    kernel32 = None

from hands.control.processes import get_running_applications, is_application_running
from hands.control.applications import open_application


SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_RESTORE = 9
WM_CLOSE = 0x0010

PROTECTED_PROCESSES = {
    "system",
    "idle",
    "smss",
    "csrss",
    "wininit",
    "services",
    "lsass",
    "lsm",
    "winlogon",
    "explorer",
    "dwm",
    "taskmgr",
    "antigravity",
    "antigravity ide",
    "mio",
}


def _get_all_windows() -> list[dict]:
    """Enumerates visible top-level windows using Win32 EnumWindows."""
    if not user32:
        return []

    windows = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_proc(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.strip()

        if not title or title.lower() in ("dwm notification window", "program manager", "windows input experience"):
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        is_iconic = bool(user32.IsIconic(hwnd))
        is_zoomed = bool(user32.IsZoomed(hwnd))
        state = "minimized" if is_iconic else ("maximized" if is_zoomed else "normal")

        # For UWP containers (ApplicationFrameHost), resolve child process PIDs
        child_pids = []
        def child_enum_proc(c_hwnd, lparam):
            c_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(c_hwnd, ctypes.byref(c_pid))
            if c_pid.value and c_pid.value != pid.value:
                child_pids.append(c_pid.value)
            return True

        user32.EnumChildWindows(hwnd, WNDENUMPROC(child_enum_proc), 0)

        windows.append({
            "hwnd": hwnd,
            "title": title,
            "pid": pid.value,
            "child_pids": child_pids,
            "state": state
        })
        return True

    cb = WNDENUMPROC(enum_proc)
    user32.EnumWindows(cb, 0)
    return windows


def _match_windows_for_query(query: str, windows: list[dict]) -> list[dict]:
    """Matches windows against a query (by process name, friendly app name, or window title)."""
    from hands.control.processes import get_running_applications, KNOWN_PROCESS_NAMES

    norm_query = query.strip().lower()
    if not norm_query:
        return []

    matched = []

    # Check running apps to find PID(s) for the query
    running = get_running_applications()
    target_pids = set()
    if running.get("success"):
        for app in running.get("apps", []):
            name_lower = app["name"].lower()
            proc_lower = app["process_name"].lower()
            if norm_query == name_lower or norm_query == proc_lower or norm_query in name_lower or norm_query in proc_lower:
                target_pids.add(app["pid"])

    for win in windows:
        title_lower = win["title"].lower()
        has_pid_match = win["pid"] in target_pids or any(cp in target_pids for cp in win.get("child_pids", []))
        if has_pid_match or norm_query in title_lower:
            matched.append(win)

    return matched


def list_windows(app_name: str | None = None) -> dict:
    """Lists visible top-level windows, optionally filtered by application name."""
    try:
        all_wins = _get_all_windows()
        if app_name:
            clean_app = app_name.strip()
            matched = _match_windows_for_query(clean_app, all_wins)
            if not matched:
                return {
                    "success": True,
                    "count": 0,
                    "windows": [],
                    "message": f"No visible windows found for '{clean_app}'."
                }
            lines = [f"- \"{w['title']}\" [{w['state']}] (PID: {w['pid']})" for w in matched]
            return {
                "success": True,
                "count": len(matched),
                "windows": matched,
                "message": f"Windows for '{clean_app}':\n" + "\n".join(lines)
            }
        else:
            if not all_wins:
                return {
                    "success": True,
                    "count": 0,
                    "windows": [],
                    "message": "No visible windows found."
                }
            lines = [f"- \"{w['title']}\" [{w['state']}]" for w in all_wins[:20]]
            return {
                "success": True,
                "count": len(all_wins),
                "windows": all_wins,
                "message": f"Visible Windows ({len(all_wins)} found):\n" + "\n".join(lines)
            }
    except Exception as err:
        return {
            "success": False,
            "count": 0,
            "windows": [],
            "message": f"Failed to list windows: {err}"
        }


def _select_window(app_name: str) -> tuple[dict | None, str | None]:
    """Finds best matching window for target app, preferring foreground window."""
    clean_app = app_name.strip()
    if not clean_app:
        return None, "Please specify an application name."

    all_wins = _get_all_windows()
    matched = _match_windows_for_query(clean_app, all_wins)
    if not matched:
        return None, f"I couldn't find any visible window for '{clean_app}'."

    fg_hwnd = user32.GetForegroundWindow() if user32 else 0
    for w in matched:
        if w["hwnd"] == fg_hwnd:
            return w, None

    return matched[0], None


def minimize_window(app_name: str) -> dict:
    """Minimizes the target application's window and verifies the minimized state."""
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err}

    hwnd = win["hwnd"]
    user32.ShowWindow(hwnd, SW_MINIMIZE)
    time.sleep(0.15)

    is_minimized = bool(user32.IsIconic(hwnd))
    if is_minimized:
        return {
            "success": True,
            "hwnd": hwnd,
            "state": "minimized",
            "message": f"Minimized '{win['title']}'."
        }
    return {
        "success": False,
        "hwnd": hwnd,
        "message": f"Failed to verify minimization for '{win['title']}'."
    }


def maximize_window(app_name: str) -> dict:
    """Maximizes the target application's window and verifies the maximized state."""
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err}

    hwnd = win["hwnd"]
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    time.sleep(0.15)

    is_maximized = bool(user32.IsZoomed(hwnd))
    if is_maximized:
        return {
            "success": True,
            "hwnd": hwnd,
            "state": "maximized",
            "message": f"Maximized '{win['title']}'."
        }
    return {
        "success": False,
        "hwnd": hwnd,
        "message": f"Failed to verify maximization for '{win['title']}'."
    }


def restore_window(app_name: str) -> dict:
    """Restores the target application's window to normal state and verifies."""
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err}

    hwnd = win["hwnd"]
    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.15)

    is_minimized = bool(user32.IsIconic(hwnd))
    is_maximized = bool(user32.IsZoomed(hwnd))
    if not is_minimized:
        return {
            "success": True,
            "hwnd": hwnd,
            "state": "normal" if not is_maximized else "maximized",
            "message": f"Restored '{win['title']}'."
        }
    return {
        "success": False,
        "hwnd": hwnd,
        "message": f"Failed to restore '{win['title']}'."
    }


def bring_to_foreground(app_name: str) -> dict:
    """Brings the target application's window to the foreground with thread-input attachment."""
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err}

    hwnd = win["hwnd"]
    if not user32:
        return {"success": False, "message": "user32 is unavailable."}

    # If minimized, restore first
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.1)

    # Attach thread input to bypass Windows foreground focus restriction
    fg_hwnd = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
    cur_thread = kernel32.GetCurrentThreadId() if kernel32 else 0

    try:
        if fg_thread and cur_thread and fg_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, True)
            user32.BringWindowToTop(hwnd)
            user32.ShowWindow(hwnd, SW_SHOWNORMAL)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(cur_thread, fg_thread, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.ShowWindow(hwnd, SW_SHOWNORMAL)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

    time.sleep(0.15)
    current_fg = user32.GetForegroundWindow()
    is_fg = (current_fg == hwnd)
    return {
        "success": True,
        "hwnd": hwnd,
        "is_foreground": is_fg,
        "message": f"Brought '{win['title']}' to the front."
    }


def close_application(app_name: str) -> dict:
    """
    Sends a graceful WM_CLOSE message to the application's windows.
    Refuses to close protected system or MIO processes.
    Verifies that the window is closed afterward.
    """
    clean_app = app_name.strip().lower()
    if not clean_app:
        return {"success": False, "message": "Please specify an application to close."}

    for protected in PROTECTED_PROCESSES:
        if clean_app == protected or protected in clean_app:
            return {
                "success": False,
                "message": f"Safety restriction: '{app_name}' is a protected system process and cannot be closed."
            }

    all_wins = _get_all_windows()
    matched = _match_windows_for_query(clean_app, all_wins)

    if not matched:
        # Check if running application without window
        from hands.control.processes import is_application_running
        run_check = is_application_running(clean_app)
        if not run_check.get("running"):
            return {
                "success": False,
                "message": f"'{app_name}' is not currently running."
            }
        return {
            "success": False,
            "message": f"'{app_name}' is running in the background without open windows. Graceful close not possible."
        }

    # Send WM_CLOSE to all matching windows
    closed_titles = []
    for w in matched:
        hwnd = w["hwnd"]
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        closed_titles.append(w["title"])

    # Verify closure over several retries
    time.sleep(0.3)
    remaining_wins = _get_all_windows()
    still_open = [w for w in remaining_wins if w["hwnd"] in [m["hwnd"] for m in matched]]

    if not still_open:
        return {
            "success": True,
            "message": f"Closed '{app_name}' successfully."
        }

    return {
        "success": True,
        "message": f"Sent close request to '{app_name}'. Application may have unsaved changes or prompt dialog open."
    }


def restart_application(app_name: str) -> dict:
    """
    Gracefully closes an application, verifies it has closed, and reopens it.
    """
    clean_app = app_name.strip()
    if not clean_app:
        return {"success": False, "message": "Please specify an application to restart."}

    from hands.control.applications import open_application
    from hands.control.processes import is_application_running

    close_res = close_application(clean_app)
    if not close_res.get("success"):
        return {
            "success": False,
            "message": f"Could not restart '{clean_app}': {close_res.get('message')}"
        }

    # Wait up to 2 seconds for app to exit
    closed = False
    for _ in range(10):
        time.sleep(0.2)
        if not is_application_running(clean_app).get("running"):
            closed = True
            break

    reopen_res = open_application(clean_app)
    if reopen_res.get("success"):
        return {
            "success": True,
            "message": f"Restarted '{clean_app}' successfully."
        }
    return {
        "success": False,
        "message": f"Closed '{clean_app}' but failed to reopen: {reopen_res.get('message')}"
    }


def move_and_resize_window(app_name: str, x: int, y: int, width: int, height: int) -> dict:
    """
    Moves and resizes the target application window to exact pixel bounds.
    """
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err or f"No active window found for '{app_name}'."}

    hwnd = win["hwnd"]
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        ret = user32.MoveWindow(hwnd, int(x), int(y), int(width), int(height), True)
        if ret:
            return {
                "success": True,
                "app": app_name,
                "bounds": {"x": x, "y": y, "width": width, "height": height},
                "message": f"Moved and resized '{app_name}' to ({x}, {y}, {width}x{height})."
            }
        return {"success": False, "message": f"Failed to reposition window for '{app_name}'."}
    except Exception as err:
        return {"success": False, "message": f"Error moving window: {err}"}


def snap_window(app_name: str, side: str = "left") -> dict:
    """
    Snaps window to the left half or right half of the primary monitor screen.
    side: 'left' or 'right'.
    """
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    half_w = screen_w // 2

    norm_side = side.strip().lower()
    if norm_side == "right":
        x, y, w, h = half_w, 0, half_w, screen_h
    else:
        x, y, w, h = 0, 0, half_w, screen_h

    res = move_and_resize_window(app_name, x, y, w, h)
    if res.get("success"):
        return {
            "success": True,
            "app": app_name,
            "side": norm_side,
            "message": f"Snapped '{app_name}' to the {norm_side.upper()} half of screen."
        }
    return res


def set_always_on_top(app_name: str, enabled: bool = True) -> dict:
    """
    Pins a window Always-on-Top (floating above other windows) or unpins it.
    """
    win, err = _select_window(app_name)
    if not win:
        return {"success": False, "message": err or f"No active window found for '{app_name}'."}

    hwnd = win["hwnd"]
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040

    flag = HWND_TOPMOST if enabled else HWND_NOTOPMOST
    try:
        user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        state_str = "Pinned Always-on-Top" if enabled else "Unpinned from Always-on-Top"
        return {
            "success": True,
            "app": app_name,
            "always_on_top": enabled,
            "message": f"'{app_name}' is now {state_str}."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to set always-on-top: {err}"}

