import os
import re
import sys

# Ensure UTF-8 console output for emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure tools module can be imported cleanly
sys_agent_dir = os.path.dirname(os.path.abspath(__file__))
if sys_agent_dir not in sys.path:
    sys.path.insert(0, sys_agent_dir)

from tools.applications import open_application
from tools.processes import get_running_applications, is_application_running
from tools.filesystem import (
    list_files,
    find_file_or_folder,
    create_folder,
    copy_file_or_folder,
    move_file_or_folder,
    rename_file_or_folder,
    delete_file_or_folder,
    locate_executable,
)
from tools.windows import (
    list_windows,
    minimize_window,
    maximize_window,
    restore_window,
    bring_to_foreground,
    close_application,
    restart_application,
)
from tools.system_info import (
    get_system_info,
    get_cpu_usage,
    get_ram_usage,
    get_disk_space,
    get_gpu_info,
    get_gpu_usage,
)
from tools.ports import (
    get_listening_ports,
    what_is_using_port,
    is_port_free,
)
from tools.network import (
    get_network_info,
    get_ip_address,
    get_wifi_info,
    is_connected_to_internet,
    ping_host,
)
from tools.audio import (
    set_volume,
    volume_up,
    volume_down,
    toggle_mute,
    media_play_pause,
    media_next,
    media_prev,
    media_stop,
)
from tools.clipboard import (
    get_clipboard_text,
    set_clipboard_text,
    clear_clipboard,
)
from tools.input import (
    show_desktop,
    open_task_manager,
    switch_app_alt_tab,
    send_hotkey,
    type_text,
)
from tools.power import (
    lock_workstation,
    turn_off_screen,
    get_battery_status,
)
from tools.screen import (
    take_screenshot,
)
from tools.notifications import (
    play_chime,
    show_notification,
)
from tools.browser import (
    open_url,
    search_web,
    open_incognito,
)
from tools.mouse import (
    get_cursor_position,
    move_cursor,
    click,
    right_click,
    double_click,
    mouse_scroll,
)
from tools.archive import (
    create_zip,
    extract_zip,
    list_zip_contents,
)
from tools.settings import (
    get_theme_mode,
    set_theme_mode,
    get_accent_color,
)
from tools.timer import (
    get_system_uptime,
    start_timer,
    list_active_timers,
)
from tools.brightness import (
    get_brightness,
    set_brightness,
    increase_brightness,
    decrease_brightness,
)
from tools.wifi_tools import (
    get_saved_wifi_profiles,
    get_wifi_password,
    scan_wifi_networks,
    flush_dns_cache,
)
from tools.services import (
    list_services,
    get_service_status,
    start_service,
    stop_service,
    restart_service,
)
from tools.installed_apps import (
    list_installed_software,
    get_app_version,
)
from tools.hasher import (
    hash_file,
    verify_checksum,
)
from tools.display import (
    get_display_info,
)
from tools.drives import (
    list_drives,
    get_removable_drives,
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


def handle_command(user_input: str) -> tuple[bool, str | None]:
    """
    Parses and handles a single user input command.

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

    # 5. Media & Audio Hands
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
    if lower_input.startswith("type "):
        text_to_type = cleaned[5:]
        res = type_text(text_to_type)
        return True, res.get("message")
    if lower_input.startswith("press hotkey ") or lower_input.startswith("hotkey "):
        raw_keys = re.sub(r"^(press hotkey|hotkey)\s+", "", cleaned, flags=re.I).strip()
        parts = [p.strip() for p in re.split(r"[\+\s]+", raw_keys) if p.strip()]
        res = send_hotkey(parts)
        return True, res.get("message")

    # 8. Power & Session Hands
    if lower_input in ("lock screen", "lock workstation", "lock computer", "lock pc"):
        res = lock_workstation()
        return True, res.get("message")
    if lower_input in ("turn off screen", "turn off monitor", "sleep monitor", "screen off"):
        res = turn_off_screen()
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
    if lower_input.startswith("open url ") or lower_input.startswith("browse "):
        target_url = re.sub(r"^(open url|browse)\s+", "", cleaned, flags=re.I).strip()
        res = open_url(target_url)
        return True, res.get("message")
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
    if lower_input.startswith("open incognito") or lower_input.startswith("incognito"):
        target_url = re.sub(r"^(open incognito|incognito)\s*", "", cleaned, flags=re.I).strip()
        res = open_incognito(target_url)
        return True, res.get("message")

    # 12. Mouse Control Hands
    if lower_input in ("get cursor pos", "cursor pos", "cursor position", "mouse pos", "mouse position"):
        res = get_cursor_position()
        return True, res.get("message")
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

    # 13. File Archive Hands (Zip / Unzip)
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

    # 15. Timers & Uptime
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
    if lower_input in ("show display info", "display info", "screen resolution", "display resolution", "resolution", "monitors", "show monitors"):
        res = get_display_info()
        return True, res.get("message")

    # 22. Storage Drives & Removable USBs
    if lower_input in ("show usb drives", "usb drives", "removable drives", "show removable drives", "list usb"):
        res = get_removable_drives()
        return True, res.get("message")
    if lower_input in ("show drives", "list drives", "drives", "disk drives"):
        res = list_drives()
        return True, res.get("message")



    # 10. System Information commands
    if lower_input in ("show system info", "system info"):
        res = get_system_info()
        return True, res.get("message")
    if lower_input in ("show cpu usage", "cpu usage", "show cpu", "cpu"):
        res = get_cpu_usage()
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

    # 14. Application lifecycle: close & restart
    if lower_input.startswith("close "):
        target_app = cleaned[6:].strip()
        res = close_application(target_app)
        return True, res.get("message")
    if lower_input.startswith("restart "):
        target_app = cleaned[8:].strip()
        res = restart_application(target_app)
        return True, res.get("message")

    # 15. Filesystem: list, create, copy, move, rename, delete, find
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
    if lower_input.startswith("open "):
        raw_target = cleaned[5:].strip()
        if not raw_target:
            return True, "Please specify an application to open. Example: 'open calculator'"

        result = open_application(raw_target)
        if result.get("success"):
            return True, f"✅ {result.get('message')}"
        return True, result.get("message")

    if lower_input == "open":
        return True, "Please specify an application to open. Example: 'open calculator'"

    return True, f"Unknown command: '{cleaned}'. Type 'open <app>', 'set volume <x>', 'take screenshot', 'show clipboard', 'show desktop', 'show battery', etc."


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
            print(message)
            if not should_continue:
                break
            print()
        elif not should_continue:
            break


if __name__ == "__main__":
    run_agent()
