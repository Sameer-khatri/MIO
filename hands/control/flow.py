"""
MIO System Agent - Flow & Task Orchestration Engine (hands.control.flow)

Provides high-speed compound workflow execution, pipelined task chaining,
adaptive window state synchronization, and zero-latency macro dispatch.
Replaces brittle static time.sleep pauses with event-driven OS polling.
"""

import re
import time
from typing import Any

from hands.control.windows import (
    _get_all_windows,
    _match_windows_for_query,
    bring_to_foreground,
    minimize_window,
    maximize_window,
    restore_window,
    close_application,
    snap_window,
    user32,
)
from hands.control.applications import open_application
from hands.connectivity.browser import (
    open_website,
    search_web,
    POPULAR_SITES,
    parse_multi_tab_query,
    batch_search,
)
from hands.action.input import send_hotkey, type_text, show_desktop


def wait_for_window_state(
    app_query: str,
    expected_state: str = "visible",
    timeout: float = 3.0,
    poll_interval: float = 0.03,
) -> dict:
    """
    Adaptively waits for an application window to reach a target state.
    States: 'visible', 'foreground', 'minimized', 'maximized', 'normal'.
    Returns the window dict as soon as condition is met, or failure on timeout.
    """
    clean_app = app_query.strip().lower()
    start_time = time.perf_counter()
    target_state = expected_state.strip().lower()

    while (time.perf_counter() - start_time) < timeout:
        wins = _get_all_windows()
        matched = _match_windows_for_query(clean_app, wins)
        if matched:
            win = matched[0]
            hwnd = win["hwnd"]

            if target_state == "visible":
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                return {
                    "success": True,
                    "elapsed_ms": elapsed_ms,
                    "window": win,
                    "message": f"Window '{win['title']}' is visible ({elapsed_ms}ms)."
                }

            if target_state == "foreground":
                fg_hwnd = user32.GetForegroundWindow() if user32 else 0
                if hwnd == fg_hwnd:
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    return {
                        "success": True,
                        "elapsed_ms": elapsed_ms,
                        "window": win,
                        "message": f"Window '{win['title']}' is now in foreground ({elapsed_ms}ms)."
                    }

            if target_state == "minimized":
                if user32 and user32.IsIconic(hwnd):
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    return {
                        "success": True,
                        "elapsed_ms": elapsed_ms,
                        "window": win,
                        "message": f"Window '{win['title']}' is now minimized ({elapsed_ms}ms)."
                    }

            if target_state == "maximized":
                if user32 and user32.IsZoomed(hwnd):
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    return {
                        "success": True,
                        "elapsed_ms": elapsed_ms,
                        "window": win,
                        "message": f"Window '{win['title']}' is now maximized ({elapsed_ms}ms)."
                    }

            if target_state == "normal":
                if user32 and not user32.IsIconic(hwnd) and not user32.IsZoomed(hwnd):
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    return {
                        "success": True,
                        "elapsed_ms": elapsed_ms,
                        "window": win,
                        "message": f"Window '{win['title']}' is in normal state ({elapsed_ms}ms)."
                    }

        time.sleep(poll_interval)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
    return {
        "success": False,
        "elapsed_ms": elapsed_ms,
        "window": None,
        "message": f"Timed out waiting for '{app_query}' to reach state '{target_state}' after {elapsed_ms}ms."
    }


def _execute_single_step(step: dict | str) -> dict:
    """Executes a single workflow step with microsecond timing."""
    step_start = time.perf_counter()

    if isinstance(step, str):
        # Convert string step into structured action
        cmd = step.strip()
        lower = cmd.lower()

        # Check for wait / pause: "wait 2s" or "pause 500ms"
        wait_m = re.match(r"^(?:wait|pause|sleep)\s+([0-9.]+)\s*(s|sec|second|seconds|ms|milli|millis|milliseconds?)?$", lower)
        if wait_m:
            val = float(wait_m.group(1))
            unit = wait_m.group(2) or "s"
            duration = val / 1000.0 if "ms" in unit else val
            time.sleep(duration)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": True, "action": "wait", "target": f"{duration}s", "elapsed_ms": elapsed_ms, "message": f"Waited {duration}s."}

        # Check for window minimize
        if lower.startswith("minimize ") or lower.startswith("min "):
            target = re.sub(r"^(?:minimize|min)\s+", "", cmd, flags=re.I).strip()
            res = minimize_window(target)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": res.get("success", False), "action": "minimize", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for window maximize
        if lower.startswith("maximize ") or lower.startswith("max "):
            target = re.sub(r"^(?:maximize|max)\s+", "", cmd, flags=re.I).strip()
            res = maximize_window(target)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": res.get("success", False), "action": "maximize", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for window restore
        if lower.startswith("restore "):
            target = cmd[8:].strip()
            res = restore_window(target)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": res.get("success", False), "action": "restore", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for foreground / focus
        if lower.startswith("focus ") or lower.startswith("bring ") or lower.startswith("foreground "):
            target = re.sub(r"^(?:focus|bring|foreground)\s+(?:to\s+foreground\s+)?", "", cmd, flags=re.I).strip()
            target = re.sub(r"\s+to\s+(?:front|foreground)$", "", target, flags=re.I).strip()
            res = bring_to_foreground(target)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": res.get("success", False), "action": "focus", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for multi-tab browser request
        multi_tab = parse_multi_tab_query(cmd)
        if multi_tab:
            engine = multi_tab.get("engine", "youtube")
            queries = multi_tab.get("queries", [])
            res = batch_search(queries, engine=engine)
            wait_for_window_state(engine, expected_state="visible", timeout=2.0)
            bring_to_foreground(engine)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": True, "action": "batch_search", "target": f"{len(queries)} tabs", "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for open website / youtube / app
        if lower.startswith("open "):
            raw_target = cmd[5:].strip()
            # Embedded search: "open youtube and search bbs" or "open youtube search bbs"
            yt_search_m = re.search(r"^(?:youtube|yt)\s+(?:and\s+)?search(?:\s+for)?\s+(.+)$", raw_target, flags=re.I)
            if yt_search_m:
                sq = yt_search_m.group(1).strip()
                res = search_web(sq, engine="youtube")
                wait_for_window_state("youtube", expected_state="visible", timeout=2.0)
                bring_to_foreground("youtube")
                elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
                return {"success": True, "action": "search_youtube", "target": sq, "elapsed_ms": elapsed_ms, "message": res.get("message")}

            # General search: "open google and search ai news"
            search_m = re.search(r"^(.*?)(?:\s+in\s+browser)?\s+and\s+search(?:\s+for)?\s+(.+)$", raw_target, flags=re.I)
            if search_m:
                eng = search_m.group(1).strip().lower()
                sq = search_m.group(2).strip()
                res = search_web(sq, engine=eng if eng in ("google", "bing", "youtube") else "google")
                elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
                return {"success": True, "action": "search_web", "target": sq, "elapsed_ms": elapsed_ms, "message": res.get("message")}

            domain_exts = (".com", ".org", ".net", ".io", ".ai", ".co", ".in", ".edu", ".gov", ".app", ".dev", ".xyz", ".me")
            if (
                raw_target.lower().startswith("http://")
                or raw_target.lower().startswith("https://")
                or raw_target.lower().startswith("www.")
                or any(raw_target.lower().endswith(ext) or f"{ext}/" in raw_target.lower() for ext in domain_exts)
                or raw_target.lower() in POPULAR_SITES
            ):
                res = open_website(raw_target)
                elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
                return {"success": res.get("success", True), "action": "open_website", "target": raw_target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

            res = open_application(raw_target)
            wait_for_window_state(raw_target, expected_state="visible", timeout=2.0)
            bring_to_foreground(raw_target)
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": res.get("success", False), "action": "open_app", "target": raw_target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Check for show desktop
        if lower in ("show desktop", "desktop"):
            res = show_desktop()
            elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
            return {"success": True, "action": "show_desktop", "target": "desktop", "elapsed_ms": elapsed_ms, "message": res.get("message")}

        # Fallback to agent's handle_command
        from core.agent import handle_command
        _, msg = handle_command(cmd)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": True, "action": "command", "target": cmd, "elapsed_ms": elapsed_ms, "message": msg}

    # Structured step dict
    action = step.get("action", "").strip().lower()
    target = step.get("target", "")

    if action == "wait":
        secs = float(step.get("seconds", step.get("duration", 1.0)))
        time.sleep(secs)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": True, "action": "wait", "target": f"{secs}s", "elapsed_ms": elapsed_ms, "message": f"Waited {secs}s."}

    if action == "wait_window":
        state = step.get("state", "visible")
        timeout = float(step.get("timeout", 3.0))
        res = wait_for_window_state(target, expected_state=state, timeout=timeout)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "wait_window", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "minimize":
        res = minimize_window(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "minimize", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "maximize":
        res = maximize_window(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "maximize", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "restore":
        res = restore_window(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "restore", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action in ("focus", "foreground", "bring"):
        res = bring_to_foreground(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "focus", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "close":
        res = close_application(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "close", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "snap":
        pos = step.get("position", "left")
        res = snap_window(target, pos)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", False), "action": "snap", "target": f"{target}:{pos}", "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "open":
        if target.startswith("http://") or target.startswith("https://") or "." in target:
            res = open_website(target)
        else:
            res = open_application(target)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", True), "action": "open", "target": target, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "hotkey":
        keys = step.get("keys", [target] if isinstance(target, str) else target)
        res = send_hotkey(keys)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", True), "action": "hotkey", "target": "+".join(keys), "elapsed_ms": elapsed_ms, "message": res.get("message")}

    if action == "type":
        text = step.get("text", target)
        res = type_text(text)
        elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
        return {"success": res.get("success", True), "action": "type", "target": text, "elapsed_ms": elapsed_ms, "message": res.get("message")}

    elapsed_ms = round((time.perf_counter() - step_start) * 1000, 1)
    return {"success": False, "action": action, "target": str(target), "elapsed_ms": elapsed_ms, "message": f"Unsupported action: '{action}'."}


def execute_flow(steps: list[dict | str], stop_on_failure: bool = False) -> dict:
    """
    Executes a list of workflow steps sequentially with sub-millisecond dispatch.
    Returns overall flow execution statistics, elapsed time, and per-step output.
    """
    if not steps:
        return {"success": False, "total_steps": 0, "elapsed_ms": 0.0, "steps": [], "message": "No steps provided in flow."}

    flow_start = time.perf_counter()
    results = []
    success_count = 0

    for idx, step in enumerate(steps):
        res = _execute_single_step(step)
        results.append(res)
        if res.get("success"):
            success_count += 1
        elif stop_on_failure:
            break

    total_elapsed_ms = round((time.perf_counter() - flow_start) * 1000, 1)
    all_ok = (success_count == len(steps))

    summary_lines = [f"⚡ Executed {len(results)}/{len(steps)} steps in {total_elapsed_ms}ms ({success_count} succeeded):"]
    for i, r in enumerate(results, 1):
        status_icon = "✓" if r.get("success") else "✗"
        summary_lines.append(f"  {status_icon} [{r.get('elapsed_ms')}ms] {r.get('action')}: {r.get('message')}")

    return {
        "success": all_ok,
        "total_steps": len(steps),
        "executed_steps": len(results),
        "success_count": success_count,
        "elapsed_ms": total_elapsed_ms,
        "steps": results,
        "message": "\n".join(summary_lines)
    }


def parse_pipeline(query: str) -> list[str]:
    """
    Parses a natural language compound query into a list of atomic action strings.
    Delimiters supported: ' -> ', ' then ', ' and then ', ';', and ',' (when followed by action verbs).
    """
    q = query.strip()
    # Normalize 'and then' -> 'then'
    q = re.sub(r"\s+and\s+then\s+", " then ", q, flags=re.IGNORECASE)
    q = re.sub(r"\s*->\s*", " then ", q)
    q = re.sub(r"\s*;\s*", " then ", q)

    # Split on 'then'
    parts = re.split(r"\s+then\s+", q, flags=re.IGNORECASE)

    # For any part containing commas, split if following part begins with an action verb
    action_verbs = (
        "open", "launch", "start", "minimize", "min", "maximize", "max",
        "restore", "focus", "bring", "close", "kill", "wait", "pause", "sleep",
        "type", "click", "snap", "show desktop", "set volume", "press"
    )

    final_steps = []
    for p in parts:
        if parse_multi_tab_query(p):
            final_steps.append(p.strip())
            continue

        subparts = [s.strip() for s in p.split(",") if s.strip()]
        if len(subparts) <= 1:
            if p.strip():
                final_steps.append(p.strip())
        else:
            # Check if all or most subparts start with an action verb
            is_action_chain = any(subparts[0].lower().startswith(v) for v in action_verbs)
            if is_action_chain:
                for sp in subparts:
                    final_steps.append(sp)
            else:
                final_steps.append(p.strip())

    return final_steps


def run_pipeline(command_query: str, stop_on_failure: bool = False) -> dict:
    """
    Parses a compound multi-step instruction and executes it immediately via fast flow dispatch.
    Example: 'minimize antigravity, open youtube search bbs, wait 2s, minimize brave, maximize antigravity'
    """
    steps = parse_pipeline(command_query)
    if not steps:
        return {"success": False, "message": "Could not parse any steps from command."}
    return execute_flow(steps, stop_on_failure=stop_on_failure)


def set_work_mode() -> dict:
    """
    Enters focused work environment:
    - Sets volume to 20%
    - Switches Windows theme to Dark Mode
    - Trims background memory footprint
    """
    from hands.sensory.audio import set_volume
    from hands.connectivity.settings import set_windows_theme
    from hands.connectivity.healer import trim_all_memory

    vol_res = set_volume(20)
    theme_res = set_windows_theme("dark")
    mem_res = trim_all_memory()

    return {
        "success": True,
        "mode": "work",
        "volume": 20,
        "theme": "dark",
        "memory": mem_res.get("freed_mb", 0),
        "message": "💼 Work Mode activated: Volume at 20%, Dark Theme active, and memory trimmed for peak performance."
    }


def set_chill_mode(play_music: bool = False) -> dict:
    """
    Enters relaxed chill environment:
    - Sets volume to 40%
    - Optionally opens lofi/ambient stream
    """
    from hands.sensory.audio import set_volume
    set_volume(40)

    if play_music:
        from hands.connectivity.browser import open_youtube
        open_youtube("lofi chill beats live")
        return {
            "success": True,
            "mode": "chill",
            "volume": 40,
            "music": True,
            "message": "☕ Chill Mode activated: Volume at 40% and playing Lo-Fi chill beats."
        }

    return {
        "success": True,
        "mode": "chill",
        "volume": 40,
        "music": False,
        "message": "☕ Chill Mode activated: Master volume set to 40%."
    }
