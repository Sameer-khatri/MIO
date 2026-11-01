import os
import re
import sys
import time

# Ensure UTF-8 console output for emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure root and tools directories are on sys.path
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CORE_DIR)
for _p in [_ROOT_DIR, _CORE_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hands.control.applications import (
    open_application,
    open_application_as_admin,
    open_file_with_default_app,
)
from hands.control.processes import (
    get_running_applications,
    is_application_running,
    kill_process,
    get_top_processes,
)
from hands.storage.filesystem import (
    list_files,
    find_file_or_folder,
    create_folder,
    copy_file_or_folder,
    move_file_or_folder,
    rename_file_or_folder,
    delete_file_or_folder,
    locate_executable,
    read_file_head,
    read_file_tail,
    get_folder_size,
    organize_desktop,
    organize_folder,
    search_files,
)
from hands.control.windows import (
    list_windows,
    minimize_window,
    maximize_window,
    restore_window,
    bring_to_foreground,
    close_application,
    restart_application,
    snap_window,
    set_always_on_top,
)
from hands.control.flow import (
    run_pipeline,
    execute_flow,
    wait_for_window_state,
    set_work_mode,
    set_chill_mode,
)
from hands.connectivity.system_info import (
    get_system_info,
    get_cpu_usage,
    get_cpu_details,
    get_ram_usage,
    get_disk_space,
    get_gpu_info,
    get_gpu_usage,
    get_motherboard_info,
)
from hands.connectivity.ports import (
    get_listening_ports,
    what_is_using_port,
    is_port_free,
    kill_port_process,
)
from hands.connectivity.network import (
    get_network_info,
    get_ip_address,
    get_public_ip,
    get_wifi_info,
    is_connected_to_internet,
    ping_host,
)
from hands.sensory.audio import (
    set_volume,
    volume_up,
    volume_down,
    toggle_mute,
    media_play_pause,
    media_next,
    media_prev,
    media_stop,
    speak_text,
    list_audio_devices,
    get_current_media_info,
    toggle_microphone_mute,
)
from hands.control.terminal import run_command as run_terminal_command
from hands.connectivity.browser import fetch_webpage_text, search_web_summary
from hands.action.clipboard import (
    get_clipboard_text,
    set_clipboard_text,
    append_clipboard_text,
    clear_clipboard,
    get_clipboard_formats,
)
from hands.action.input import (
    show_desktop,
    open_task_manager,
    switch_app_alt_tab,
    open_file_explorer,
    open_windows_settings,
    open_run_dialog,
    close_active_window,
    send_hotkey,
    type_text,
    press_key,
)
from hands.connectivity.power import (
    lock_workstation,
    turn_off_screen,
    sleep_system,
    hibernate_system,
    schedule_shutdown,
    cancel_shutdown,
    get_active_power_plan,
    get_battery_status,
)
from hands.sensory.screen import (
    take_screenshot,
    take_region_screenshot,
)
from hands.sensory.notifications import (
    play_chime,
    beep,
    play_sound_pattern,
    show_notification,
)
from hands.connectivity.browser import (
    open_url,
    search_web,
    open_incognito,
    open_with_browser,
    get_default_browser,
    open_youtube,
    search_and_play_youtube,
    control_youtube,
    open_youtube_and_type,
    parse_timestamp,
    open_website,
    POPULAR_SITES,
    open_multiple_tabs,
    batch_search,
    parse_multi_tab_query,
)

try:
    import eyes
except ImportError:
    eyes = None
from hands.action.mouse import (
    get_cursor_position,
    move_cursor,
    move_relative,
    drag_to,
    click,
    right_click,
    double_click,
    mouse_scroll,
)
from hands.storage.archive import (
    create_zip,
    extract_zip,
    list_zip_contents,
    create_tar,
    test_archive,
)
from hands.connectivity.settings import (
    get_theme_mode,
    set_theme_mode,
    get_accent_color,
    get_wallpaper,
    set_wallpaper,
    set_transparency_effects,
)
from hands.connectivity.timer import (
    get_system_uptime,
    start_timer,
    list_active_timers,
    start_stopwatch,
    lap_stopwatch,
    stop_stopwatch,
)
from hands.sensory.brightness import (
    get_brightness,
    set_brightness,
    increase_brightness,
    decrease_brightness,
    fade_brightness,
)
from hands.connectivity.wifi_tools import (
    get_saved_wifi_profiles,
    get_wifi_password,
    scan_wifi_networks,
    connect_to_wifi,
    disconnect_wifi,
    delete_wifi_profile,
    flush_dns_cache,
)
from hands.connectivity.services import (
    list_services,
    get_service_status,
    start_service,
    stop_service,
    restart_service,
    set_service_startup,
    get_service_description,
)
from hands.control.installed_apps import (
    list_installed_software,
    get_app_version,
    get_app_uninstall_command,
)
from hands.storage.hasher import (
    hash_file,
    hash_text,
    verify_checksum,
    compare_files,
)
from hands.sensory.display import (
    get_display_info,
    get_monitors_detail,
    get_display_modes,
)
from hands.storage.drives import (
    list_drives,
    get_removable_drives,
    check_drive_space_warning,
    eject_usb_drive,
)
from hands.connectivity.healer import (
    auto_heal_system,
    trim_all_memory,
    detect_hung_windows,
    heal_network,
    heal_stuck_ports,
    heal_temp_cache,
)





def extract_where_target(user_input: str) -> str | None:
    """Extracts target tool name from 'where is <tool>?' or 'where <tool>'."""
    cleaned = user_input.strip()
    lower = cleaned.lower().rstrip("?").strip()

    if lower.startswith("where is "):
        target = cleaned[9:].rstrip("?").strip()
        if target:
            return target

    if lower.startswith("where "):
        target = cleaned[6:].rstrip("?").strip()
        if target:
            return target

    return None


def extract_is_running_target(user_input: str) -> str | None:
    """Extracts target application name from 'is <app> running?' or 'check if <app> is running'."""
    cleaned = user_input.strip()
    lower = cleaned.lower().rstrip("?").strip()

    if lower.startswith("is ") and lower.endswith(" running"):
        target = cleaned[3:].rstrip("?").strip()
        if target.lower().endswith("running"):
            target = target[:-7].strip()
            if target:
                return target

    if lower.startswith("check if ") and lower.endswith(" is running"):
        target = cleaned[9:].rstrip("?").strip()
        if target.lower().endswith("is running"):
            target = target[:-10].strip()
            if target:
                return target

    if lower.startswith("check if ") and lower.endswith(" running"):
        target = cleaned[9:].rstrip("?").strip()
        if target.lower().endswith("running"):
            target = target[:-7].strip()
            if target:
                return target

    return None


_ACTION_HISTORY: list[dict] = []


def record_action(command: str, result_msg: str | None):
    """Records executed action for conversational recall and brain introspection."""
    if not command or not result_msg:
        return
    clean_msg = result_msg.strip()
    if clean_msg.startswith("Unknown command:") or clean_msg.startswith("I don't know how to do"):
        return
    lower_c = command.lower().strip()
    if any(k in lower_c for k in ("what did you", "what did u", "tell me what", "history", "recent actions", "last action")):
        return

    entry = {
        "command": command.strip(),
        "time": time.strftime("%H:%M:%S"),
        "result": clean_msg
    }
    _ACTION_HISTORY.append(entry)
    if len(_ACTION_HISTORY) > 50:
        _ACTION_HISTORY.pop(0)

    try:
        from core.history import record_action as _hist_record
        _hist_record("agent", "command", {"command": command.strip()}, {"message": clean_msg}, 0.0)
    except Exception:
        pass


def get_last_action() -> dict:
    """Returns details of the most recent action executed."""
    if _ACTION_HISTORY:
        last = _ACTION_HISTORY[-1]
        return {
            "success": True,
            "action": last,
            "message": f"Just now, I executed: '{last['command']}'. Result:\n{last['result']}"
        }

    try:
        from core.history import get_last_action as _hist_get_last
        hist = _hist_get_last()
        if hist:
            msg = hist.get("message") or f"{hist.get('tool')}.{hist.get('action')}"
            return {
                "success": True,
                "action": hist,
                "message": f"Just now, I executed: '{hist.get('action')}' on {hist.get('tool')}. Result:\n{msg}"
            }
    except Exception:
        pass

    return {"success": True, "action": None, "message": "I haven't performed any actions yet in this session."}


def get_action_history(limit: int = 5) -> dict:
    """Returns recent action history."""
    if _ACTION_HISTORY:
        recent = _ACTION_HISTORY[-limit:]
        lines = [f"- [{h['time']}] '{h['command']}' -> {h['result']}" for h in reversed(recent)]
        return {
            "success": True,
            "count": len(recent),
            "history": recent,
            "message": f"Recent Actions ({len(recent)}):\n" + "\n".join(lines)
        }

    try:
        from core.history import get_recent_actions
        recent_acts = get_recent_actions(limit)
        if recent_acts:
            lines = [f"- [{h.get('time')}] '{h.get('action')}' ({h.get('tool')}) -> {h.get('message')}" for h in recent_acts]
            return {
                "success": True,
                "count": len(recent_acts),
                "history": recent_acts,
                "message": f"Recent Actions ({len(recent_acts)}):\n" + "\n".join(lines)
            }
    except Exception:
        pass

    return {"success": True, "count": 0, "history": [], "message": "I haven't performed any actions yet in this session."}


def _execute_command(user_input: str) -> tuple[bool, str | None]:
    """
    Core command dispatcher for user input strings.

    Returns:
        tuple[bool, str | None]: (should_continue, message)
    """
    if user_input is None:
        return True, None

    cleaned = user_input.strip()
    if not cleaned:
        return True, None

    lower_input = cleaned.lower().rstrip("?").strip()

    # 1. Exit / Quit handling
    if lower_input in ("exit", "quit"):
        return False, "Goodbye."

    # 1.2 Action History & Conversational Introspection
    if any(k in lower_input for k in (
        "what did you just do", "what did u just do", "what did you do", "what did u do",
        "tell me what you just did", "tell me what u just did", "what was the last thing you did",
        "last action", "show last action", "what did u do now", "tell me what u just did now", "tell me what you did"
    )):
        res = get_last_action()
        return True, res["message"]

    if any(k in lower_input for k in ("action history", "show history", "recent actions", "what have you done")):
        res = get_action_history()
        return True, res["message"]

    # 1.5 Flow & Compound Multi-Step Workflow Pipeline
    if (
        lower_input.startswith("flow ")
        or lower_input.startswith("run flow")
        or lower_input.startswith("pipeline ")
        or " then " in lower_input
        or " and then " in lower_input
        or " -> " in lower_input
    ):
        q = re.sub(r"^(?:run\s+flow(?::)?|flow(?::)?|pipeline(?::)?)\s*", "", cleaned, flags=re.I).strip()
        res = run_pipeline(q)
        return True, res.get("message")

    # Multi-tab browser orchestration (checked before comma splitting)
    multi_tab = parse_multi_tab_query(cleaned)
    if multi_tab:
        engine = multi_tab.get("engine", "youtube")
        queries = multi_tab.get("queries", [])
        res = batch_search(queries, engine=engine)
        return True, res.get("message")

    # Fast multi-action comma pipeline: e.g. "minimize antigravity, open youtube search bbs, wait 2s, maximize antigravity"
    if "," in cleaned:
        action_prefixes = ("open ", "minimize ", "min ", "maximize ", "max ", "restore ", "focus ", "bring ", "wait ", "pause ", "sleep ", "close ", "play ", "search ")
        subparts = [p.strip() for p in cleaned.split(",") if p.strip()]
        # Require majority of subparts to be action verbs to avoid splitting natural sentences
        action_count = sum(1 for p in subparts if any(p.lower().startswith(pref) for pref in action_prefixes))
        if len(subparts) >= 2 and action_count >= 2 and not parse_multi_tab_query(cleaned):
            res = run_pipeline(cleaned)
            return True, res.get("message")

    # 2. "where is <tool>?" / "where <tool>" handling
    where_target = extract_where_target(user_input)
    if where_target:
        result = locate_executable(where_target)
        if result.get("success") and result.get("name"):
            loc_type = result.get("type", "")
            name = result.get("name", where_target)
            target = result.get("target", "")
            matches = result.get("matches", [])

            type_labels = {
                "appid": "Windows packaged app",
                "shortcut": "Shortcut",
                "exe": "Executable",
            }
            type_label = type_labels.get(loc_type, loc_type or "Unknown")

            lines = [f"Application: {name}", f"Type: {type_label}"]
            if loc_type == "appid":
                lines.append(f"AppID: {target}")
            elif loc_type == "exe" and matches:
                if len(matches) == 1:
                    lines.append(f"Location: {matches[0]}")
                else:
                    lines.append("Locations:")
                    for m in matches:
                        lines.append(f"  {m}")
            elif target:
                lines.append(f"Location: {target}")

            return True, "\n".join(lines)
        return True, result.get("message", f"I couldn't locate '{where_target}' on this system.")

    # 3. "is <app> running?" handling
    running_target = extract_is_running_target(user_input)
    if running_target:
        result = is_application_running(running_target)
        if result.get("success"):
            if result.get("running"):
                return True, f"Yes, {result.get('name')} is running."
            return True, f"No, {result.get('name')} is not running."
        return True, result.get("message", f"Failed to check if {running_target} is running.")

    # 4. Show running applications handling
    if lower_input in ("show running apps", "list running apps", "running apps"):
        result = get_running_applications()
        if result.get("success"):
            apps = result.get("apps", [])
            if apps:
                app_lines = "\n".join(f"- {app['name']}" for app in apps)
                return True, f"Running applications:\n{app_lines}"
            return True, "No running applications found."
        return True, result.get("message", "Failed to inspect running applications.")

    # 5. MIO Eyes (Visual Grounding & Element Interaction)
    if lower_input in ("eye status", "eyes status", "check eyes", "eye security", "eyes"):
        if not eyes:
            return True, "MIO Eyes subsystem is not installed or available."
        status = eyes.get_status()
        shutter = "LOCKED (Secure)" if status.get("shutter_locked") else "OPEN (Inspecting)"
        return True, f"👁️ MIO Eyes: Shutter [{shutter}] | Privacy Shield: Active ({status.get('blacklisted_process_count')} protected apps, {status.get('sensitive_keyword_count')} sensitive keywords)"

    if lower_input.startswith("double click ") or lower_input.startswith("double-click "):
        target = re.sub(r"^(double click|double-click)\s+(?:on\s+)?", "", cleaned, flags=re.I).strip()
        if eyes and target:
            res = eyes.click_element(target, double_click=True)
            if res.get("success"):
                coords = res.get("coordinates", {})
                return True, f"👁️ ✋ Located '{target}' via {res.get('method')} and double-clicked at ({coords.get('x')}, {coords.get('y')})."
            return True, res.get("error", f"Could not find '{target}' on screen.")
        return True, "MIO Eyes subsystem unavailable."

    if lower_input.startswith("click on ") or lower_input.startswith("click "):
        target = re.sub(r"^click\s+(?:on\s+)?", "", cleaned, flags=re.I).strip()
        # Avoid intercepting audio click if any
        if eyes and target:
            res = eyes.click_element(target)
            if res.get("success"):
                coords = res.get("coordinates", {})
                return True, f"👁️ ✋ Located '{target}' via {res.get('method')} and clicked at ({coords.get('x')}, {coords.get('y')})."
            return True, res.get("error", f"Could not find '{target}' on screen.")

    type_into_m = re.match(r"^type\s+['\"]?(.+?)['\"]?\s+(?:into|in)\s+['\"]?(.+?)['\"]?$", cleaned, flags=re.I)
    if type_into_m and eyes:
        text_to_type = type_into_m.group(1).strip()
        field_target = type_into_m.group(2).strip()
        # Don't intercept if it's youtube type command
        if not ("youtube" in lower_input and "and play" in lower_input):
            res = eyes.type_into(field_target, text_to_type)
            if res.get("success"):
                return True, f"👁️ ✋ Focused '{field_target}' and typed text successfully."
            return True, res.get("error", f"Could not find field '{field_target}' on screen.")


    drag_m = re.match(r"^drag\s+['\"]?(.+?)['\"]?\s+to\s+['\"]?(.+?)['\"]?$", cleaned, flags=re.I)
    if drag_m and eyes:
        src_query = drag_m.group(1).strip()
        dest_query = drag_m.group(2).strip()
        res = eyes.drag_element(src_query, target_query=dest_query)
        if res.get("success"):
            return True, f"👁️ ✋ Successfully dragged '{src_query}' to '{dest_query}'."
        return True, res.get("error", f"Could not complete drag from '{src_query}' to '{dest_query}'.")

    if lower_input in ("read dialog", "read error", "read alert", "what is on the screen", "read screen", "read prompt"):
        if eyes:
            res = eyes.read_dialog()
            if res.get("success"):
                btns = ", ".join(b["name"] for b in res.get("buttons", [])) or "None"
                return True, f"👁️ On-Screen Dialog: '{res.get('window_title')}'\nMessage: {res.get('message')}\nAvailable Buttons: [{btns}]"
            return True, res.get("error", "No active dialog found on screen.")
        return True, "MIO Eyes subsystem unavailable."

    # 6. Media & Audio Hands
    if lower_input.startswith("speak "):
        txt = cleaned[6:].strip()
        res = speak_text(txt)
        return True, res.get("message")
    if lower_input in ("show audio devices", "list audio devices", "audio devices"):
        res = list_audio_devices()
        return True, res.get("message")
    if lower_input in ("mute", "unmute", "toggle mute"):
        res = toggle_mute()
        return True, res.get("message")
    if lower_input in ("volume up", "turn up volume", "increase volume"):
        res = volume_up()
        return True, res.get("message")
    if lower_input in ("volume down", "turn down volume", "decrease volume"):
        res = volume_down()
        return True, res.get("message")
    vol_match = re.search(r"^(set volume to|set volume|volume)\s+(\d+)\%?$", lower_input)
    if vol_match:
        res = set_volume(vol_match.group(2))
        return True, res.get("message")
    if lower_input in ("play", "pause", "play pause", "resume"):
        res = media_play_pause()
        return True, res.get("message")
    if lower_input in ("next track", "skip track", "next song", "next"):
        res = media_next()
        return True, res.get("message")
    if lower_input in ("previous track", "prev track", "previous song", "prev"):
        res = media_prev()
        return True, res.get("message")
    if lower_input in ("stop media", "stop music", "stop playback"):
        res = media_stop()
        return True, res.get("message")

    # 6. Clipboard Hands
    if lower_input in ("show clipboard", "read clipboard", "get clipboard", "clipboard"):
        res = get_clipboard_text()
        return True, res.get("message")
    if lower_input == "clear clipboard":
        res = clear_clipboard()
        return True, res.get("message")
    if lower_input in ("clipboard formats", "show clipboard formats"):
        res = get_clipboard_formats()
        return True, res.get("message")
    if lower_input.startswith("append to clipboard "):
        app_txt = cleaned[20:].strip()
        res = append_clipboard_text(app_txt)
        return True, res.get("message")
    if lower_input.startswith("copy to clipboard "):
        text_to_copy = cleaned[18:].strip()
        res = set_clipboard_text(text_to_copy)
        return True, res.get("message")
    if lower_input.startswith("copy text "):
        text_to_copy = cleaned[10:].strip()
        res = set_clipboard_text(text_to_copy)
        return True, res.get("message")

    # 7. Hotkeys & Input Hands
    if lower_input in ("show desktop", "minimize all"):
        res = show_desktop()
        return True, res.get("message")
    if lower_input in ("open task manager", "task manager"):
        res = open_task_manager()
        return True, res.get("message")
    if lower_input in ("switch app", "alt tab", "switch application"):
        res = switch_app_alt_tab()
        return True, res.get("message")
    if lower_input in ("open explorer", "open file explorer", "file explorer"):
        res = open_file_explorer()
        return True, res.get("message")
    if lower_input in ("open settings", "windows settings"):
        res = open_windows_settings()
        return True, res.get("message")
    if lower_input in ("open run", "run dialog"):
        res = open_run_dialog()
        return True, res.get("message")
    if lower_input in ("close window", "close active window"):
        res = close_active_window()
        return True, res.get("message")
    if lower_input.startswith("type "):
        text_to_type = cleaned[5:]
        res = type_text(text_to_type)
        return True, res.get("message")
    if lower_input.startswith("press hotkey ") or lower_input.startswith("hotkey "):
        raw_keys = re.sub(r"^(press hotkey|hotkey)\s+", "", cleaned, flags=re.I).strip()
        parts = [p.strip() for p in re.split(r"[\+\s]+", raw_keys) if p.strip()]
        res = send_hotkey(parts)
        return True, res.get("message")
    if lower_input.startswith("press key ") or lower_input.startswith("press "):
        k = re.sub(r"^(press key|press)\s+", "", cleaned, flags=re.I).strip()
        res = press_key(k)
        return True, res.get("message")

    # 8. Power & Session Hands
    if lower_input in ("lock screen", "lock workstation", "lock computer", "lock pc"):
        res = lock_workstation()
        return True, res.get("message")
    if lower_input in ("turn off screen", "turn off monitor", "sleep monitor", "screen off"):
        res = turn_off_screen()
        return True, res.get("message")
    if lower_input in ("sleep", "sleep pc", "sleep system"):
        res = sleep_system()
        return True, res.get("message")
    if lower_input in ("hibernate", "hibernate pc"):
        res = hibernate_system()
        return True, res.get("message")
    if lower_input in ("power plan", "active power plan", "show power plan"):
        res = get_active_power_plan()
        return True, res.get("message")
    if lower_input.startswith("schedule shutdown "):
        sec_str = cleaned[18:].strip()
        try:
            res = schedule_shutdown(int(sec_str))
            return True, res.get("message")
        except ValueError:
            return True, "Please specify seconds for shutdown. Example: 'schedule shutdown 60'"
    if lower_input in ("cancel shutdown", "abort shutdown"):
        res = cancel_shutdown()
        return True, res.get("message")
    if lower_input in ("show battery", "battery status", "battery", "power status", "show power"):
        res = get_battery_status()
        return True, res.get("message")


    # 9. Screen Capture Hands
    if lower_input in ("take screenshot", "screenshot", "capture screen"):
        res = take_screenshot()
        return True, res.get("message")
    if lower_input.startswith("screenshot ") or lower_input.startswith("take screenshot "):
        custom_name = re.sub(r"^(screenshot|take screenshot)\s+", "", cleaned, flags=re.I).strip()
        res = take_screenshot(custom_name)
        return True, res.get("message")

    # 10. Notifications & Audio Chimes
    if lower_input.startswith("play chime") or lower_input.startswith("play sound"):
        snd_type = re.sub(r"^(play chime|play sound)\s*", "", lower_input).strip() or "asterisk"
        res = play_chime(snd_type)
        return True, res.get("message")
    if lower_input.startswith("notify ") or lower_input.startswith("show notification "):
        raw_msg = re.sub(r"^(notify|show notification)\s+", "", cleaned, flags=re.I).strip()
        if "|" in raw_msg:
            title_part, msg_part = raw_msg.split("|", 1)
            res = show_notification(title_part.strip(), msg_part.strip())
        else:
            res = show_notification("MIO Alert", raw_msg)
        return True, res.get("message")

    # 11. Browser & Web Search Hands
    if lower_input in ("show default browser", "default browser", "what is my default browser"):
        res = get_default_browser()
        return True, res.get("message")
    if lower_input.startswith("open with chrome "):
        target_url = cleaned[17:].strip()
        res = open_with_browser(target_url, "chrome")
        return True, res.get("message")
    if lower_input.startswith("open with edge "):
        target_url = cleaned[15:].strip()
        res = open_with_browser(target_url, "edge")
        return True, res.get("message")
    if lower_input.startswith("open with brave "):
        target_url = cleaned[16:].strip()
        res = open_with_browser(target_url, "brave")
        return True, res.get("message")
    if lower_input.startswith("open with firefox "):
        target_url = cleaned[18:].strip()
        res = open_with_browser(target_url, "firefox")
        return True, res.get("message")
    if lower_input.startswith("open url ") or lower_input.startswith("browse "):
        target_url = re.sub(r"^(open url|browse)\s+", "", cleaned, flags=re.I).strip()
        res = open_url(target_url)
        return True, res.get("message")
    if lower_input.startswith("open incognito") or lower_input.startswith("incognito"):
        target_url = re.sub(r"^(open incognito|incognito)\s*", "", cleaned, flags=re.I).strip()
        res = open_incognito(target_url)
        return True, res.get("message")

    # Multi-tab browser orchestration (e.g. "open 4 youtube tabs and search for techno gamer in first, bbs in second, triggered insan in 3rd and mr beast in 4th")
    multi_tab = parse_multi_tab_query(cleaned)
    if multi_tab:
        engine = multi_tab.get("engine", "youtube")
        queries = multi_tab.get("queries", [])
        res = batch_search(queries, engine=engine)
        return True, res.get("message")

    # A. "search [for] <query> on/in/using (google|bing|duckduckgo|youtube|yahoo|web)"
    # Handles: "search for ai news on google", "search ai news on bing"
    search_on = re.match(
        r"^search(?:\s+for)?\s+(.+?)\s+(?:on|in|using)\s+(google|bing|duckduckgo|ddg|youtube|yahoo|wiki|wikipedia|web|browser)$",
        cleaned,
        flags=re.IGNORECASE
    )
    if search_on:
        query_val = search_on.group(1).strip()
        engine_val = search_on.group(2).strip().lower()
        if engine_val in ("web", "browser"):
            engine_val = "google"
        elif engine_val in ("wiki", "wikipedia"):
            engine_val = "wikipedia"
        res = search_web(query_val, engine=engine_val)
        return True, res.get("message")

    # B. Compound search: "open (google|bing|browser|chrome|brave|edge) [in browser] [and] (type|search for|search) <query>"
    # Handles: "open google in browser and search for ai news", "open browser and search for ai news", etc.
    compound_search = re.match(
        r"^open\s+(google|bing|duckduckgo|ddg|yahoo|wiki|wikipedia|browser|chrome|brave|edge|firefox)?(?:\s+in\s+browser)?\s*(?:and\s+)?(?:type|search\s+for|search)\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE
    )
    if compound_search:
        engine_raw = (compound_search.group(1) or "google").strip().lower()
        search_query = compound_search.group(2).strip()
        if engine_raw in ("browser", "chrome", "brave", "edge", "firefox"):
            engine_name = "google"
        elif engine_raw in ("wiki", "wikipedia"):
            engine_name = "wikipedia"
        else:
            engine_name = engine_raw or "google"
        res = search_web(search_query, engine=engine_name)
        return True, res.get("message")

    # C. "google <query>"
    # Handles: "google ai news", "google who won the game"
    if lower_input.startswith("google "):
        q = cleaned[7:].strip()
        res = search_web(q, engine="google")
        return True, res.get("message")

    # D. "open <site> in browser" or "browse <site>"
    # Handles: "open google in browser", "open reddit in browser", "open github in browser"
    open_in_browser = re.match(r"^(?:open|browse)\s+(.+?)\s+in\s+browser$", cleaned, flags=re.IGNORECASE)
    if open_in_browser:
        target_site = open_in_browser.group(1).strip()
        res = open_website(target_site)
        return True, res.get("message")

    # E. Specific engine prefixes
    if lower_input.startswith("search youtube for "):
        q = cleaned[19:].strip()
        res = search_web(q, engine="youtube")
        return True, res.get("message")
    if lower_input.startswith("search bing for "):
        q = cleaned[16:].strip()
        res = search_web(q, engine="bing")
        return True, res.get("message")
    if lower_input.startswith("search google for "):
        q = cleaned[18:].strip()
        res = search_web(q, engine="google")
        return True, res.get("message")
    if lower_input.startswith("search for ") or lower_input.startswith("search "):
        q = re.sub(r"^(search for|search)\s+", "", cleaned, flags=re.I).strip()
        res = search_web(q, engine="google")
        return True, res.get("message")

    # 11.5 YouTube Hands (Search, Cue Playback & Controls)
    # Pattern: "open youtube type <query> and play (video )?at <timestamp>"
    # e.g.: "open youtube type this and play video at 2 minute"
    # e.g.: "open youtube search bbs" -> searches YouTube, does not auto-play
    yt_type_play = re.match(
        r"^(?:open\s+youtube\s+(?:and\s+)?(?:type|search\s+for|search)\s+)(.+?)(?:\s+and\s+play(?:\s+video)?\s+at\s+(.+))?$",
        cleaned,
        flags=re.IGNORECASE
    )
    if yt_type_play:
        query_val = yt_type_play.group(1).strip()
        time_val = yt_type_play.group(2)
        if time_val is not None or "play" in cleaned.lower():
            timestamp = time_val.strip() if time_val else 0
            res = search_and_play_youtube(query_val, timestamp=timestamp)
        else:
            res = search_web(query_val, engine="youtube")
        return True, res.get("message")

    # Pattern: "play <query> on youtube (at <timestamp>)?"
    # e.g.: "play lofi hip hop on youtube at 2 minute"
    yt_play_on = re.match(
        r"^play\s+(.+?)\s+on\s+youtube(?:\s+at\s+(.+))?$",
        cleaned,
        flags=re.IGNORECASE
    )
    if yt_play_on:
        query_val = yt_play_on.group(1).strip()
        time_val = yt_play_on.group(2)
        timestamp = time_val.strip() if time_val else 0
        res = search_and_play_youtube(query_val, timestamp=timestamp)
        return True, res.get("message")

    # Pattern: "open youtube" or "youtube"
    if lower_input in ("open youtube", "youtube"):
        res = open_youtube()
        return True, res.get("message")

    # Pattern: "open youtube <query or url> (at <timestamp>)?"
    if lower_input.startswith("open youtube "):
        rest = cleaned[13:].strip()
        time_split = re.search(r"\s+at\s+([\w\d\:\s]+)$", rest, flags=re.IGNORECASE)
        if time_split:
            target = rest[:time_split.start()].strip()
            t_val = time_split.group(1).strip()
            res = search_and_play_youtube(target, timestamp=t_val)
        elif rest.lower().startswith("play "):
            play_target = rest[5:].strip()
            res = search_and_play_youtube(play_target)
        elif rest.lower().startswith("search "):
            search_target = rest[7:].strip()
            res = search_web(search_target, engine="youtube")
        else:
            # Default to search results page
            res = open_youtube(query=rest)
        return True, res.get("message")

    # Pattern: "youtube play", "youtube pause", "youtube mute", "youtube fullscreen", "youtube forward 30s", "youtube rewind 20s"
    if lower_input.startswith("youtube "):
        ctrl_action = lower_input[8:].strip()
        sec_m = re.search(r"(\d+)", ctrl_action)
        secs = int(sec_m.group(1)) if sec_m else 0
        act_word = re.sub(r"\d+.*$", "", ctrl_action).strip()
        res = control_youtube(act_word or ctrl_action, seconds=secs)
        return True, res.get("message")

    # 12. Mouse Control Hands
    if lower_input in ("get cursor pos", "cursor pos", "cursor position", "mouse pos", "mouse position"):
        res = get_cursor_position()
        return True, res.get("message")
    if lower_input.startswith("drag to ") or lower_input.startswith("drag mouse to "):
        coords = re.sub(r"^(drag to|drag mouse to)\s*", "", lower_input).strip()
        parts = re.split(r"[,\s]+", coords)
        if len(parts) >= 2:
            res = drag_to(parts[0], parts[1])
            return True, res.get("message")
        return True, "Please provide X and Y coordinates to drag to. Example: 'drag to 600 400'"
    if lower_input.startswith("move cursor ") or lower_input.startswith("move mouse "):
        coords = re.sub(r"^(move cursor to|move mouse to|move cursor|move mouse)\s*", "", lower_input).strip()
        parts = re.split(r"[,\s]+", coords)
        if len(parts) >= 2:
            res = move_cursor(parts[0], parts[1])
            return True, res.get("message")
        return True, "Please provide X and Y coordinates. Example: 'move cursor 500 300'"
    if lower_input in ("right click", "right-click"):
        res = right_click()
        return True, res.get("message")
    if lower_input in ("double click", "double-click"):
        res = double_click()
        return True, res.get("message")
    if lower_input in ("click", "click mouse", "left click"):
        res = click("left")
        return True, res.get("message")
    if lower_input.startswith("scroll up"):
        amount_match = re.search(r"scroll up\s+(\d+)", lower_input)
        val = int(amount_match.group(1)) if amount_match else 120
        res = mouse_scroll(val)
        return True, res.get("message")
    if lower_input.startswith("scroll down"):
        amount_match = re.search(r"scroll down\s+(\d+)", lower_input)
        val = -(int(amount_match.group(1))) if amount_match else -120
        res = mouse_scroll(val)
        return True, res.get("message")
    if lower_input.startswith("scroll ") or lower_input.startswith("mouse scroll "):
        amt = re.sub(r"^(scroll|mouse scroll)\s*", "", lower_input).strip()
        try:
            res = mouse_scroll(int(amt))
            return True, res.get("message")
        except ValueError:
            return True, "Please specify a scroll amount. Example: 'scroll up' or 'scroll -120'"

    # 13. File Archive Hands (Zip / Tar / Testing)
    if lower_input.startswith("create tar ") or lower_input.startswith("tar "):
        raw_cmd = re.sub(r"^(create tar|tar)\s+", "", cleaned, flags=re.I).strip()
        if " to " in raw_cmd:
            src_part, dest_part = raw_cmd.split(" to ", 1)
            res = create_tar(src_part.strip(), dest_part.strip())
        else:
            res = create_tar(raw_cmd)
        return True, res.get("message")
    if lower_input.startswith("test archive ") or lower_input.startswith("verify archive "):
        raw_arch = re.sub(r"^(test archive|verify archive)\s+", "", cleaned, flags=re.I).strip()
        res = test_archive(raw_arch)
        return True, res.get("message")
    if lower_input.startswith("zip ") or lower_input.startswith("compress "):
        raw_cmd = re.sub(r"^(zip|compress)\s+", "", cleaned, flags=re.I).strip()
        if " to " in raw_cmd:
            src_part, dest_part = raw_cmd.split(" to ", 1)
            res = create_zip(src_part.strip(), dest_part.strip())
        else:
            res = create_zip(raw_cmd)
        return True, res.get("message")
    if lower_input.startswith("unzip ") or lower_input.startswith("extract "):
        raw_cmd = re.sub(r"^(unzip|extract)\s+", "", cleaned, flags=re.I).strip()
        if " to " in raw_cmd:
            src_part, dest_part = raw_cmd.split(" to ", 1)
            res = extract_zip(src_part.strip(), dest_part.strip())
        else:
            res = extract_zip(raw_cmd)
        return True, res.get("message")
    if lower_input.startswith("list zip ") or lower_input.startswith("inspect zip "):
        raw_zip = re.sub(r"^(list zip|inspect zip)\s+", "", cleaned, flags=re.I).strip()
        res = list_zip_contents(raw_zip)
        if res.get("success"):
            files = res.get("files", [])
            lines = [res.get("message", "")]
            for f in files[:15]:
                d_marker = "[DIR] " if f.get("is_dir") else ""
                lines.append(f"  - {d_marker}{f.get('filename')} ({f.get('file_size')} bytes)")
            if len(files) > 15:
                lines.append(f"  ... and {len(files) - 15} more files.")
            return True, "\n".join(lines)
        return True, res.get("message")


    # 14. Windows Settings & Personalization
    if lower_input in ("show wallpaper", "get wallpaper", "wallpaper"):
        res = get_wallpaper()
        return True, res.get("message")
    if lower_input.startswith("set wallpaper "):
        wp_path = cleaned[14:].strip()
        res = set_wallpaper(wp_path)
        return True, res.get("message")
    if lower_input in ("enable transparency", "transparency on"):
        res = set_transparency_effects(True)
        return True, res.get("message")
    if lower_input in ("disable transparency", "transparency off"):
        res = set_transparency_effects(False)
        return True, res.get("message")
    if lower_input in ("show theme", "get theme", "theme", "what theme"):
        res = get_theme_mode()
        return True, res.get("message")
    if lower_input in ("set theme dark", "dark mode", "enable dark mode", "set dark mode"):
        res = set_theme_mode("dark")
        return True, res.get("message")
    if lower_input in ("set theme light", "light mode", "enable light mode", "set light mode"):
        res = set_theme_mode("light")
        return True, res.get("message")
    if lower_input in ("show accent color", "accent color", "get accent color"):
        res = get_accent_color()
        return True, res.get("message")

    # 15. Timers, Uptime & Stopwatch
    if lower_input.startswith("start stopwatch"):
        sw_name = re.sub(r"^start stopwatch\s*", "", cleaned, flags=re.I).strip() or "default"
        res = start_stopwatch(sw_name)
        return True, res.get("message")
    if lower_input.startswith("lap stopwatch"):
        sw_name = re.sub(r"^lap stopwatch\s*", "", cleaned, flags=re.I).strip() or "default"
        res = lap_stopwatch(sw_name)
        return True, res.get("message")
    if lower_input.startswith("stop stopwatch"):
        sw_name = re.sub(r"^stop stopwatch\s*", "", cleaned, flags=re.I).strip() or "default"
        res = stop_stopwatch(sw_name)
        return True, res.get("message")
    if lower_input in ("system uptime", "uptime", "show uptime"):
        res = get_system_uptime()
        return True, res.get("message")
    if lower_input.startswith("set timer ") or lower_input.startswith("timer "):
        remainder = re.sub(r"^(set timer|timer)\s+", "", cleaned, flags=re.I).strip()
        parts = remainder.split(maxsplit=1)
        sec_str = parts[0]
        label = parts[1] if len(parts) > 1 else "Timer"
        try:
            sec_val = int(sec_str)
            res = start_timer(sec_val, label)
            return True, res.get("message")
        except ValueError:
            return True, "Please specify duration in seconds. Example: 'set timer 60 Pizza'"
    if lower_input in ("show timers", "active timers", "list timers"):
        res = list_active_timers()
        return True, res.get("message")

    # 16. Display Brightness Hands
    if lower_input.startswith("fade brightness "):
        f_val = cleaned[16:].strip()
        try:
            res = fade_brightness(int(f_val))
            return True, res.get("message")
        except ValueError:
            pass
    if lower_input in ("show brightness", "brightness", "get brightness"):
        res = get_brightness()
        return True, res.get("message")
    bright_match = re.search(r"^(set brightness to|set brightness|brightness)\s+(\d+)\%?$", lower_input)
    if bright_match:
        res = set_brightness(bright_match.group(2))
        return True, res.get("message")
    if lower_input in ("brightness up", "increase brightness", "brighter"):
        res = increase_brightness()
        return True, res.get("message")
    if lower_input in ("brightness down", "decrease brightness", "dim screen", "dim brightness"):
        res = decrease_brightness()
        return True, res.get("message")

    # 17. Wi-Fi Tools & DNS
    if lower_input.startswith("connect wifi ") or lower_input.startswith("connect to wifi "):
        ssid = re.sub(r"^(connect wifi|connect to wifi)\s+", "", cleaned, flags=re.I).strip()
        res = connect_to_wifi(ssid)
        return True, res.get("message")
    if lower_input in ("disconnect wifi", "disconnect from wifi"):
        res = disconnect_wifi()
        return True, res.get("message")
    if lower_input.startswith("forget wifi ") or lower_input.startswith("delete wifi "):
        ssid = re.sub(r"^(forget wifi|delete wifi)\s+", "", cleaned, flags=re.I).strip()
        res = delete_wifi_profile(ssid)
        return True, res.get("message")
    if lower_input in ("show saved wifi", "saved wifi", "wifi profiles", "list wifi profiles", "show wifi profiles"):
        res = get_saved_wifi_profiles()
        return True, res.get("message")
    if lower_input.startswith("wifi password for ") or lower_input.startswith("wifi password "):
        ssid_name = re.sub(r"^(wifi password for|wifi password)\s+", "", cleaned, flags=re.I).strip()
        res = get_wifi_password(ssid_name)
        return True, res.get("message")
    if lower_input in ("scan wifi", "scan networks", "available wifi", "show available wifi", "nearby wifi"):
        res = scan_wifi_networks()
        if res.get("success"):
            networks = res.get("networks", [])
            lines = [res.get("message", "")]
            for n in networks[:12]:
                lines.append(f"  - {n.get('ssid')} (Signal: {n.get('signal')})")
            if len(networks) > 12:
                lines.append(f"  ... and {len(networks) - 12} more networks.")
            return True, "\n".join(lines)
        return True, res.get("message")
    if lower_input in ("flush dns", "flush dns cache", "clear dns", "clear dns cache"):
        res = flush_dns_cache()
        return True, res.get("message")

    # 18. Windows Services Management
    if lower_input.startswith("restart service "):
        svc = cleaned[16:].strip()
        res = restart_service(svc)
        return True, res.get("message")
    if lower_input.startswith("start service "):
        svc = cleaned[14:].strip()
        res = start_service(svc)
        return True, res.get("message")
    if lower_input.startswith("stop service "):
        svc = cleaned[13:].strip()
        res = stop_service(svc)
        return True, res.get("message")
    if lower_input.startswith("service status ") or lower_input.startswith("status of service "):
        svc = re.sub(r"^(service status|status of service)\s+", "", cleaned, flags=re.I).strip()
        res = get_service_status(svc)
        return True, res.get("message")
    if lower_input.startswith("service description "):
        svc = cleaned[20:].strip()
        res = get_service_description(svc)
        return True, res.get("message")
    if lower_input.startswith("list services") or lower_input.startswith("show services"):
        filt = re.sub(r"^(list services|show services)\s*", "", cleaned, flags=re.I).strip()
        res = list_services(filt)
        if res.get("success"):
            services = res.get("services", [])
            lines = [res.get("message", "")]
            for s in services[:15]:
                lines.append(f"  - [{s.get('state')}] {s.get('name')} ({s.get('display_name')})")
            if len(services) > 15:
                lines.append(f"  ... and {len(services) - 15} more services.")
            return True, "\n".join(lines)
        return True, res.get("message")

    # 19. Installed Software Inventory
    if lower_input.startswith("uninstall command for ") or lower_input.startswith("uninstall command "):
        app_q = re.sub(r"^(uninstall command for|uninstall command)\s+", "", cleaned, flags=re.I).strip()
        res = get_app_uninstall_command(app_q)
        return True, res.get("message")
    if lower_input.startswith("app version ") or lower_input.startswith("version of "):
        app_q = re.sub(r"^(app version|version of)\s+", "", cleaned, flags=re.I).strip()
        res = get_app_version(app_q)
        return True, res.get("message")
    if lower_input.startswith("installed software") or lower_input.startswith("show installed apps") or lower_input.startswith("list installed apps") or lower_input.startswith("installed apps"):
        app_q = re.sub(r"^(installed software|show installed apps|list installed apps|installed apps)\s*", "", cleaned, flags=re.I).strip()
        res = list_installed_software(app_q)
        if res.get("success"):
            apps = res.get("apps", [])
            lines = [res.get("message", "")]
            for a in apps[:15]:
                lines.append(f"  - {a.get('name')} v{a.get('version')} ({a.get('publisher')})")
            if len(apps) > 15:
                lines.append(f"  ... and {len(apps) - 15} more applications.")
            return True, "\n".join(lines)
        return True, res.get("message")

    # 20. Cryptographic File Hashes & Checksums
    if lower_input.startswith("compare files "):
        remainder = cleaned[14:].strip()
        if " and " in remainder:
            f1, f2 = remainder.split(" and ", 1)
            res = compare_files(f1.strip(), f2.strip())
            return True, res.get("message")
    if lower_input.startswith("hash text "):
        txt = cleaned[10:].strip()
        res = hash_text(txt)
        return True, res.get("message")
    if lower_input.startswith("verify checksum "):
        remainder = cleaned[16:].strip()
        parts = remainder.split(maxsplit=1)
        if len(parts) == 2:
            res = verify_checksum(parts[0], parts[1])
            return True, res.get("message")
        return True, "Please provide file path and expected hash. Example: 'verify checksum app.zip a1b2c3...'"
    if lower_input.startswith("sha256 ") or lower_input.startswith("hash sha256 "):
        f_path = re.sub(r"^(sha256|hash sha256)\s+", "", cleaned, flags=re.I).strip()
        res = hash_file(f_path, "sha256")
        return True, res.get("message")
    if lower_input.startswith("md5 ") or lower_input.startswith("hash md5 "):
        f_path = re.sub(r"^(md5|hash md5)\s+", "", cleaned, flags=re.I).strip()
        res = hash_file(f_path, "md5")
        return True, res.get("message")
    if lower_input.startswith("hash file ") or lower_input.startswith("hash "):
        remainder = re.sub(r"^(hash file|hash)\s+", "", cleaned, flags=re.I).strip()
        parts = remainder.split()
        if len(parts) >= 2 and parts[-1].lower() in ("sha256", "md5", "sha1", "sha512"):
            f_path = " ".join(parts[:-1])
            algo = parts[-1]
            res = hash_file(f_path, algo)
        else:
            res = hash_file(remainder, "sha256")
        return True, res.get("message")

    # 21. Display & Multi-Monitor Metrics
    if lower_input in ("detailed monitors", "show monitors detail", "list monitors detail", "monitors detail"):
        res = get_monitors_detail()
        return True, res.get("message")
    if lower_input in ("display modes", "screen refresh rate", "refresh rate"):
        res = get_display_modes()
        return True, res.get("message")
    if lower_input in ("show display info", "display info", "screen resolution", "display resolution", "resolution", "monitors", "show monitors"):
        res = get_display_info()
        return True, res.get("message")

    # 22. Storage Drives & Removable USBs
    if lower_input in ("check drive space", "check disk space", "drive warnings", "low disk space"):
        res = check_drive_space_warning()
        return True, res.get("message")
    if lower_input.startswith("eject drive ") or lower_input.startswith("eject usb "):
        drv = re.sub(r"^(eject drive|eject usb)\s+", "", cleaned, flags=re.I).strip()
        res = eject_usb_drive(drv)
        return True, res.get("message")
    if lower_input in ("show usb drives", "usb drives", "removable drives", "show removable drives", "list usb"):
        res = get_removable_drives()
        return True, res.get("message")
    if lower_input in ("show drives", "list drives", "drives", "disk drives"):
        res = list_drives()
        return True, res.get("message")

    # 26. Self-Healing commands
    if lower_input in ("auto heal", "heal system", "self heal", "auto heal system", "heal pc", "system heal"):
        res = auto_heal_system()
        return True, res.get("message")
    if lower_input in ("trim ram", "trim memory", "free ram", "heal ram", "clean ram"):
        res = trim_all_memory()
        return True, res.get("message")
    if lower_input in ("heal network", "fix internet", "flush dns and reconnect"):
        res = heal_network()
        return True, res.get("message")
    if lower_input in ("check frozen apps", "hung windows", "frozen windows", "detect hung windows"):
        res = detect_hung_windows()
        return True, res.get("message")
    if lower_input in ("heal cache", "clean temp files", "clean cache", "heal temp"):
        res = heal_temp_cache()
        return True, res.get("message")

    # 10. System Information commands
    if lower_input in ("show system info", "system info"):
        res = get_system_info()
        return True, res.get("message")
    if lower_input in ("show cpu usage", "cpu usage", "show cpu", "cpu"):
        res = get_cpu_usage()
        return True, res.get("message")
    if lower_input in ("show cpu details", "cpu details", "cpu info"):
        res = get_cpu_details()
        return True, res.get("message")
    if lower_input in ("show motherboard info", "motherboard info", "motherboard", "show motherboard"):
        res = get_motherboard_info()
        return True, res.get("message")
    if lower_input in ("show ram usage", "ram usage", "show ram", "ram", "memory usage"):
        res = get_ram_usage()
        return True, res.get("message")
    if lower_input in ("show disk space", "disk space", "show disk", "disk"):
        res = get_disk_space("C:\\")
        return True, res.get("message")
    if lower_input in ("show gpu info", "gpu info"):
        res = get_gpu_info()
        return True, res.get("message")
    if lower_input in ("show gpu usage", "gpu usage", "gpu"):
        res = get_gpu_usage()
        return True, res.get("message")

    # 11. Ports commands
    if lower_input in ("show listening ports", "listening ports", "show ports", "ports"):
        res = get_listening_ports()
        return True, res.get("message")
    if lower_input.startswith("kill port ") or lower_input.startswith("free port "):
        port_str = re.sub(r"^(kill port|free port)\s+", "", lower_input).strip()
        res = kill_port_process(port_str)
        return True, res.get("message")
    if lower_input.startswith("what is using port ") or lower_input.startswith("what is on port "):
        port_str = re.sub(r"^(what is using port|what is on port)\s+", "", lower_input).strip()
        res = what_is_using_port(port_str)
        return True, res.get("message")
    if lower_input.startswith("is port ") and (lower_input.endswith(" free") or lower_input.endswith(" available")):
        match = re.search(r"^is port\s+(\d+)\s+(free|available)$", lower_input)
        if match:
            res = is_port_free(match.group(1))
            return True, res.get("message")

    # 12. Network commands
    if lower_input in ("show network info", "network info", "network"):
        res = get_network_info()
        return True, res.get("message")
    if lower_input in ("show public ip", "public ip", "get public ip", "my public ip", "whats my public ip"):
        res = get_public_ip()
        return True, res.get("message")
    if lower_input in ("show ip address", "ip address", "ip", "show ip"):
        res = get_ip_address()
        return True, res.get("message")
    if lower_input in ("show wifi info", "wifi info", "wifi"):
        res = get_wifi_info()
        return True, res.get("message")
    if lower_input in ("am i connected to internet", "am i connected to the internet", "is internet connected", "check internet"):
        res = is_connected_to_internet()
        return True, res.get("message")
    if lower_input.startswith("ping "):
        target_host = cleaned[5:].strip()
        res = ping_host(target_host)
        return True, res.get("message")

    # 13. Window management commands
    if lower_input.startswith("snap left ") or (lower_input.startswith("snap ") and lower_input.endswith(" left")):
        target = re.sub(r"^snap left\s+", "", cleaned, flags=re.IGNORECASE)
        target = re.sub(r"^snap\s+", "", target, flags=re.IGNORECASE)
        target = re.sub(r"\s+left$", "", target, flags=re.IGNORECASE).strip()
        res = snap_window(target, "left")
        return True, res.get("message")
    if lower_input.startswith("snap right ") or (lower_input.startswith("snap ") and lower_input.endswith(" right")):
        target = re.sub(r"^snap right\s+", "", cleaned, flags=re.IGNORECASE)
        target = re.sub(r"^snap\s+", "", target, flags=re.IGNORECASE)
        target = re.sub(r"\s+right$", "", target, flags=re.IGNORECASE).strip()
        res = snap_window(target, "right")
        return True, res.get("message")
    if lower_input.startswith("pin ") or lower_input.startswith("pin on top ") or lower_input.startswith("always on top "):
        target = re.sub(r"^(pin on top|pin|always on top)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = set_always_on_top(target, True)
        return True, res.get("message")
    if lower_input.startswith("unpin ") or lower_input.startswith("unpin from top "):
        target = re.sub(r"^(unpin from top|unpin)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = set_always_on_top(target, False)
        return True, res.get("message")
    if lower_input.startswith("minimize "):
        target_app = cleaned[9:].strip()
        res = minimize_window(target_app)
        return True, res.get("message")
    if lower_input.startswith("maximize "):
        target_app = cleaned[9:].strip()
        res = maximize_window(target_app)
        return True, res.get("message")
    if lower_input.startswith("restore "):
        target_app = cleaned[8:].strip()
        res = restore_window(target_app)
        return True, res.get("message")
    if lower_input.startswith("bring ") and (lower_input.endswith(" to front") or lower_input.endswith(" forward")):
        target = re.sub(r"^bring\s+", "", cleaned, flags=re.IGNORECASE)
        target = re.sub(r"\s+(to front|forward)$", "", target, flags=re.IGNORECASE).strip()
        res = bring_to_foreground(target)
        return True, res.get("message")
    if lower_input.startswith("switch to "):
        target = cleaned[10:].strip()
        res = bring_to_foreground(target)
        return True, res.get("message")
    if lower_input.startswith("show windows for ") or lower_input.startswith("list windows for "):
        target = re.sub(r"^(show windows for|list windows for)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = list_windows(target)
        return True, res.get("message")
    if lower_input in ("show windows", "list windows"):
        res = list_windows()
        return True, res.get("message")

    # 14. Application & Process lifecycle: close, restart, kill, top
    if lower_input in ("show top processes", "top processes", "top memory processes", "top memory"):
        res = get_top_processes(10)
        return True, res.get("message")
    if lower_input.startswith("kill process ") or lower_input.startswith("kill "):
        target = re.sub(r"^(kill process|kill)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        if not target.startswith("port "):
            res = kill_process(target)
            return True, res.get("message")
    if lower_input.startswith("close "):
        target_app = cleaned[6:].strip()
        res = close_application(target_app)
        return True, res.get("message")
    if lower_input.startswith("restart "):
        target_app = cleaned[8:].strip()
        res = restart_application(target_app)
        return True, res.get("message")

    # 15. Filesystem: list, create, copy, move, rename, delete, find, head, tail, folder size
    if lower_input.startswith("read head ") or lower_input.startswith("head "):
        target = re.sub(r"^(read head|head)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = read_file_head(target)
        return True, res.get("message")
    if lower_input.startswith("read tail ") or lower_input.startswith("tail "):
        target = re.sub(r"^(read tail|tail)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = read_file_tail(target)
        return True, res.get("message")
    if lower_input.startswith("folder size ") or lower_input.startswith("size of folder ") or lower_input.startswith("folder size of "):
        target = re.sub(r"^(folder size of|size of folder|folder size)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = get_folder_size(target)
        return True, res.get("message")
    if lower_input.startswith("show files in ") or lower_input.startswith("list files in "):
        folder_query = cleaned[14:].strip()
        if not folder_query:
            return True, "Please specify a location. Example: 'show files in downloads'"
        result = list_files(folder_query)
        if result.get("success"):
            items = result.get("items", [])
            loc_title = result.get("location", folder_query)
            if items:
                items_lines = "\n".join(f"- {item}" for item in items)
                return True, f"{loc_title}:\n{items_lines}"
            return True, f"No files found in {loc_title}."
        return True, result.get("message", f"Failed to list files in {folder_query}.")

    if lower_input in ("organize desktop", "clean desktop", "clean up desktop"):
        res = organize_desktop()
        return True, res.get("message")

    if lower_input.startswith("organize folder ") or lower_input.startswith("organize "):
        target = re.sub(r"^organize(\s+folder)?\s+", "", lower_input).strip()
        res = organize_folder(target)
        return True, res.get("message")

    if lower_input.startswith("search files ") or lower_input.startswith("find files "):
        pat = re.sub(r"^(search|find)\s+files\s+", "", lower_input).strip()
        res = search_files(pat)
        return True, res.get("message")

    if lower_input in ("work mode", "focus mode", "enter work mode"):
        res = set_work_mode()
        return True, res.get("message")

    if lower_input in ("chill mode", "relax mode", "enter chill mode"):
        res = set_chill_mode()
        return True, res.get("message")

    if lower_input.startswith("terminal ") or lower_input.startswith("cmd ") or lower_input.startswith("exec ") or lower_input.startswith("powershell "):
        cmd_str = re.sub(r"^(terminal|cmd|exec|powershell)\s+", "", cleaned, flags=re.I).strip()
        res = run_terminal_command(cmd_str)
        return True, res.get("message")

    if lower_input in ("what song is playing", "current song", "now playing", "media info", "what is playing", "song info"):
        res = get_current_media_info()
        return True, res.get("message")

    if lower_input in ("mute mic", "toggle mic", "unmute mic", "toggle microphone", "mute microphone"):
        res = toggle_microphone_mute()
        return True, res.get("message")

    if lower_input.startswith("read webpage ") or lower_input.startswith("fetch webpage "):
        w_url = re.sub(r"^(read|fetch)\s+webpage\s+", "", cleaned, flags=re.I).strip()
        res = fetch_webpage_text(w_url)
        if res.get("success"):
            return True, f"📄 {res.get('title')}:\n{res.get('text')[:600]}..."
        return True, res.get("message")

    if lower_input.startswith("create folder "):
        remainder = cleaned[14:].strip()
        match = re.search(r"^(.*?)\s+in\s+(.*)$", remainder, re.IGNORECASE)
        if not match:
            return True, "Please use the format: 'create folder <name> in <location>'"
        folder_name = match.group(1).strip()
        location_name = match.group(2).strip()
        result = create_folder(folder_name, location_name)
        if result.get("success"):
            if result.get("already_exists"):
                return True, result.get("message")
            return True, f"✅ {result.get('message')}"
        return True, result.get("message", f"Failed to create folder '{folder_name}'.")

    if lower_input.startswith("copy "):
        remainder = cleaned[5:].strip()
        match = re.search(r"^(.*?)\s+to\s+(.*)$", remainder, re.IGNORECASE)
        if not match:
            return True, "Please use the format: 'copy <file or folder> to <location>'"
        source_query = match.group(1).strip()
        location_name = match.group(2).strip()
        result = copy_file_or_folder(source_query, location_name)
        return True, result.get("message", f"Failed to copy '{source_query}'.")

    if lower_input.startswith("move "):
        remainder = cleaned[5:].strip()
        match = re.search(r"^(.*?)\s+to\s+(.*)$", remainder, re.IGNORECASE)
        if not match:
            return True, "Please use the format: 'move <file or folder> to <location>'"
        source_query = match.group(1).strip()
        location_name = match.group(2).strip()
        result = move_file_or_folder(source_query, location_name)
        return True, result.get("message", f"Failed to move '{source_query}'.")

    if lower_input.startswith("rename "):
        remainder = cleaned[7:].strip()
        match = re.search(r"^(.*?)\s+to\s+(.*)$", remainder, re.IGNORECASE)
        if not match:
            return True, "Please use the format: 'rename <file or folder> to <new name>'"
        source_query = match.group(1).strip()
        new_name = match.group(2).strip()
        result = rename_file_or_folder(source_query, new_name)
        return True, result.get("message", f"Failed to rename '{source_query}'.")

    if lower_input.startswith("delete "):
        target = cleaned[7:].strip()
        result = delete_file_or_folder(target)
        return True, result.get("message", f"Failed to delete '{target}'.")

    if lower_input.startswith("find "):
        query = cleaned[5:].strip()
        if not query:
            return True, "Please specify what to find. Example: 'find report.pdf'"
        result = find_file_or_folder(query)
        if result.get("success"):
            matches = result.get("matches", [])
            if matches:
                matches_lines = "\n".join(f"- {m}" for m in matches)
                return True, f"Found:\n{matches_lines}"
            return True, f"No matches found for '{query}'."
        return True, result.get("message", f"Failed to search for '{query}'.")

    # 16. Open command handling
    if lower_input.startswith("open as admin ") or lower_input.startswith("run as admin "):
        target = re.sub(r"^(open as admin|run as admin)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        res = open_application_as_admin(target)
        return True, res.get("message")

    if lower_input.startswith("open file "):
        target = cleaned[10:].strip()
        res = open_file_with_default_app(target)
        return True, res.get("message")

    if lower_input.startswith("open "):
        raw_target = cleaned[5:].strip()
        if not raw_target:
            return True, "Please specify an application to open. Example: 'open calculator'"

        # Check if the target is actually a website, web portal, or compound web task
        lower_target = raw_target.lower()
        domain_exts = (".com", ".org", ".net", ".io", ".ai", ".co", ".in", ".edu", ".gov", ".app", ".dev", ".xyz", ".me")
        is_web_target = (
            " in browser" in lower_target
            or " and search" in lower_target
            or lower_target.startswith("http://")
            or lower_target.startswith("https://")
            or lower_target.startswith("www.")
            or any(lower_target.endswith(ext) or f"{ext}/" in lower_target for ext in domain_exts)
            or lower_target in POPULAR_SITES
        )

        if is_web_target:
            # Check for embedded search: "open google and search for ai news"
            search_m = re.search(r"^(.*?)(?:\s+in\s+browser)?\s+and\s+search(?:\s+for)?\s+(.+)$", raw_target, flags=re.I)
            if search_m:
                eng = search_m.group(1).strip().lower()
                sq = search_m.group(2).strip()
                eng_name = eng if eng in ("google", "bing", "duckduckgo", "youtube", "yahoo") else "google"
                res = search_web(sq, engine=eng_name)
                return True, res.get("message")

            res = open_website(raw_target)
            return True, res.get("message")

        result = open_application(raw_target)
        if result.get("success"):
            return True, f"✅ {result.get('message')}"
        return True, result.get("message")

    if lower_input == "open":
        return True, "Please specify an application to open. Example: 'open calculator'"



    return True, (
        f"I don't know how to do '{cleaned}'.\n"
        "Try: open <app>, search <query>, play <song> on youtube, set volume 50,\n"
        "     take screenshot, show clipboard, show battery, trim ram, auto heal,\n"
        "     organize desktop, work mode, chill mode, minimize <app>, close <app>"
    )


def handle_command(user_input: str) -> tuple[bool, str | None]:
    """
    Parses and handles a single user input command, automatically recording actions to memory.

    Returns:
        tuple[bool, str | None]: (should_continue, message)
    """
    should_continue, message = _execute_command(user_input)
    if message and user_input:
        record_action(user_input, message)
    return should_continue, message


def run_agent():
    """Runs the interactive terminal interface."""
    print("MIO System Agent ready.")
    print("Type 'exit' to stop.\n")

    while True:
        try:
            user_input = input("MIO > ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        should_continue, message = handle_command(user_input)
        if message:
            record_action(user_input, message)
            print(message)
            if not should_continue:
                break
            print()
        elif not should_continue:
            break


if __name__ == "__main__":
    run_agent()
