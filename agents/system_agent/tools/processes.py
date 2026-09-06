import csv
import io
import json
import subprocess


KNOWN_PROCESS_NAMES = {
    "chrome": "Google Chrome",
    "brave": "Brave",
    "msedge": "Microsoft Edge",
    "code": "Visual Studio Code",
    "whatsapp.root": "WhatsApp",
    "whatsapp": "WhatsApp",
    "antigravity ide": "Antigravity IDE",
    "antigravity": "Antigravity",
    "notepad": "Notepad",
    "calc": "Calculator",
    "calculator": "Calculator",
    "calculatorapp": "Calculator",
    "mspaint": "Paint",
    "paintapp": "Paint",
    "spotify": "Spotify",
    "discord": "Discord",
    "obsidian": "Obsidian",
    "ollama": "Ollama",
    "cmd": "Command Prompt",
    "powershell": "PowerShell",
    "windowsterminal": "Windows Terminal",
    "explorer": "File Explorer",
    "taskmgr": "Task Manager",
    "chatgpt": "ChatGPT",
    "manus": "Manus",
}

IGNORED_PROCESS_NAMES = {
    "applicationframehost",
    "systemsettings",
    "textinputhost",
    "searchhost",
    "startmenuexperiencehost",
    "shellhost",
    "lockapp",
    "widgets",
    "dwm",
    "svchost",
    "runtimebroker",
    "dllhost",
    "taskhostw",
    "conhost",
    "crossdeviceservice",
    "crossdeviceresume",
    "nvcontainer",
    "nvdisplay.container",
    "nvsphelper64",
    "nvidia overlay",
    "rtkauduservice64",
    "asus_framework",
    "asusosd",
    "asushotkey",
    "ashotplugctrl",
    "asussmartdisplaycontrol",
    "asmonitorcontrol",
    "armourysocketserver",
    "armourycreate.usersessionhelper",
    "armourycreate.usersessionhelper.exe",
    "asusoptimizationstartuptask",
    "wshhelper",
    "atieclxx",
    "msedgewebview2",
    "translucenttb",
}


def get_friendly_name(process_name: str, window_title: str) -> str:
    """Derives a clean friendly application name from process name and window title."""
    clean_proc = process_name.strip().lower().replace(".exe", "")

    # 1. Check known mappings
    if clean_proc in KNOWN_PROCESS_NAMES:
        return KNOWN_PROCESS_NAMES[clean_proc]

    # 2. Check app_memory.json if available
    try:
        from tools.applications import load_memory
        memory = load_memory()
        for k, v in memory.items():
            if clean_proc in k or clean_proc in v.get("name", "").lower():
                return v.get("name", "")
            target = v.get("target", "").lower()
            if f"{clean_proc}.exe" in target or f"{clean_proc}.lnk" in target:
                return v.get("name", "")
    except Exception:
        pass

    # 3. Clean from Window Title if structured (e.g. "PRIMEX - Antigravity IDE" -> "Antigravity IDE")
    if " - " in window_title:
        parts = window_title.split(" - ")
        candidate = parts[-1].strip()
        if candidate and len(candidate) > 1 and not candidate.startswith("http"):
            return candidate

    # 4. Fallback to capitalized process name
    return process_name.title()


def _get_apps_from_powershell() -> list[dict]:
    """Attempts to inspect visible applications via PowerShell Get-Process."""
    ps_cmd = (
        "Get-Process | "
        "Where-Object MainWindowTitle | "
        "Select-Object Id, ProcessName, MainWindowTitle | "
        "ConvertTo-Json -Compress"
    )
    output = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        text=True,
        encoding="utf-8",
        stderr=subprocess.DEVNULL,
        timeout=5
    )
    if not output.strip():
        return []
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    results = []
    for item in data:
        results.append({
            "pid": item.get("Id", 0),
            "process_name": item.get("ProcessName", ""),
            "window_title": item.get("MainWindowTitle", "")
        })
    return results


def _get_apps_from_tasklist() -> list[dict]:
    """Inspects visible applications across all user sessions using tasklist."""
    output = subprocess.check_output(
        ["tasklist", "/v", "/fo", "csv"],
        text=True,
        encoding="utf-8",
        errors="ignore",
        stderr=subprocess.DEVNULL,
        timeout=10
    )
    if not output.strip():
        return []
    reader = csv.DictReader(io.StringIO(output))
    results = []
    for row in reader:
        win_title = (row.get("Window Title") or "").strip()
        image_name = (row.get("Image Name") or "").strip()
        pid_str = (row.get("PID") or "").strip()
        try:
            pid = int(pid_str)
        except ValueError:
            pid = 0
        results.append({
            "pid": pid,
            "process_name": image_name,
            "window_title": win_title
        })
    return results


def get_running_applications() -> dict:
    """
    Inspects running Windows applications with visible windows.
    Returns:
        dict: {
            "success": bool,
            "apps": list of dicts [{"name": str, "process_name": str, "pid": int}],
            "message": str
        }
    """
    try:
        errors = []
        raw_apps = []

        try:
            raw_apps = _get_apps_from_powershell()
        except Exception as err:
            errors.append(err)

        if not raw_apps:
            try:
                raw_apps = _get_apps_from_tasklist()
            except Exception as err:
                errors.append(err)

        if not raw_apps and len(errors) == 2:
            return {
                "success": False,
                "apps": [],
                "message": str(errors[0])
            }

        apps_dict = {}

        for item in raw_apps:
            pid = item.get("pid", 0)
            proc_name = item.get("process_name", "").strip()
            win_title = item.get("window_title", "").strip()

            if not proc_name or not win_title or win_title in ("N/A", "OleMainThreadWndName", "OLEChannelWnd"):
                continue

            clean_proc = proc_name.lower().replace(".exe", "")

            if clean_proc in IGNORED_PROCESS_NAMES:
                continue

            if win_title.lower() in ("dwm notification window", "smartdc", "nvsvc", "start", "search", "quick settings"):
                continue

            friendly_name = get_friendly_name(clean_proc, win_title)
            norm_name = friendly_name.strip().lower()

            if norm_name not in apps_dict:
                apps_dict[norm_name] = {
                    "name": friendly_name,
                    "process_name": clean_proc,
                    "pid": pid
                }

        unique_apps = sorted(list(apps_dict.values()), key=lambda x: x["name"])

        return {
            "success": True,
            "apps": unique_apps,
            "message": f"{len(unique_apps)} running applications found." if unique_apps else "No running applications found."
        }

    except Exception as error:
        return {
            "success": False,
            "apps": [],
            "message": str(error)
        }


def is_application_running(query: str) -> dict:
    """
    Checks whether a specific application is currently running.
    Returns:
        dict: {
            "success": bool,
            "running": bool,
            "name": str,
            "message": str
        }
    """
    if not query or not isinstance(query, str):
        return {
            "success": False,
            "running": False,
            "name": "",
            "message": "Invalid application name provided."
        }

    clean_query = query.strip().rstrip("?").strip()
    if not clean_query:
        return {
            "success": False,
            "running": False,
            "name": "",
            "message": "Invalid application name provided."
        }

    # Resolve aliases and friendly name for query
    alias_target = clean_query
    try:
        from tools.applications import ALIASES, load_memory
        alias_target = ALIASES.get(clean_query.lower(), clean_query)
    except Exception:
        pass

    display_name = KNOWN_PROCESS_NAMES.get(clean_query.lower()) or KNOWN_PROCESS_NAMES.get(alias_target.lower())
    if not display_name:
        try:
            from tools.applications import load_memory
            memory = load_memory()
            for k, v in memory.items():
                if clean_query.lower() == k or alias_target.lower() == k or clean_query.lower() in [a.lower() for a in v.get("aliases", [])]:
                    display_name = v.get("name")
                    break
        except Exception:
            pass

    if not display_name:
        display_name = alias_target if alias_target != clean_query else clean_query.title()

    # Reuse running applications detection
    running_res = get_running_applications()
    if not running_res.get("success"):
        return {
            "success": False,
            "running": False,
            "name": display_name,
            "message": running_res.get("message", "Failed to inspect running applications.")
        }

    running_apps = running_res.get("apps", [])
    norm_query = clean_query.lower()
    norm_alias = alias_target.lower()
    norm_display = display_name.lower()

    # 1. Exact match against running apps
    for app in running_apps:
        app_name_norm = app["name"].lower()
        proc_name_norm = app["process_name"].lower()
        if norm_query == app_name_norm or norm_alias == app_name_norm or norm_display == app_name_norm or norm_query == proc_name_norm:
            return {
                "success": True,
                "running": True,
                "name": app["name"],
                "message": f"{app['name']} is running."
            }

    # 2. Partial / substring match against running apps
    for app in running_apps:
        app_name_norm = app["name"].lower()
        proc_name_norm = app["process_name"].lower()
        if (norm_query in app_name_norm or norm_alias in app_name_norm or app_name_norm in norm_query) or (norm_query in proc_name_norm):
            return {
                "success": True,
                "running": True,
                "name": app["name"],
                "message": f"{app['name']} is running."
            }

    # 3. Not running
    return {
        "success": True,
        "running": False,
        "name": display_name,
        "message": f"{display_name} is not running."
    }
