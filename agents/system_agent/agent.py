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

    # 5. System Information commands
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

    # 6. Ports commands
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

    # 7. Network commands
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

    # 8. Window management commands
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

    # 9. Application lifecycle: close & restart
    if lower_input.startswith("close "):
        target_app = cleaned[6:].strip()
        res = close_application(target_app)
        return True, res.get("message")
    if lower_input.startswith("restart "):
        target_app = cleaned[8:].strip()
        res = restart_application(target_app)
        return True, res.get("message")

    # 10. Filesystem: list, create, copy, move, rename, delete, find
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

    # 11. Open command handling
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

    return True, f"Unknown command: '{cleaned}'. Type 'open <app>', 'where is <tool>?', 'is <app> running?', 'show system info', 'show network info', 'show listening ports', 'close <app>', 'minimize <app>', 'delete <file>', etc."


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
