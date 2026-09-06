import json
import os
import shutil
import subprocess
from datetime import datetime, timezone

try:
    import winreg
except ImportError:
    winreg = None

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_memory.json")

BUILTIN_APPS = {
    "calculator": {"name": "calculator", "launch_method": "exe", "target": "calc.exe"},
    "notepad": {"name": "notepad", "launch_method": "exe", "target": "notepad.exe"},
    "explorer": {"name": "explorer", "launch_method": "exe", "target": "explorer.exe"},
    "paint": {"name": "paint", "launch_method": "exe", "target": "mspaint.exe"},
}

ALIASES = {
    "calc": "calculator",
    "file explorer": "explorer",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "chrome": "Google Chrome",
    "antigravity": "Antigravity",
    "spotify": "Spotify",
    "edge": "Microsoft Edge",
}


# ---------------------------------------------------------------------------
# Name Normalization & Memory Helpers
# ---------------------------------------------------------------------------

def normalize_name(text: str) -> str:
    """Normalizes application names: lowercases, strips, and collapses whitespace."""
    if not text or not isinstance(text, str):
        return ""
    return " ".join(text.strip().lower().split())


def _utc_now() -> str:
    """Returns an ISO timestamp for memory metadata."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _infer_record_type(entry: dict) -> str:
    """Infers old memory record types without changing the memory backend."""
    record_type = normalize_name(entry.get("record_type", ""))
    if record_type:
        return record_type
    launch_method = normalize_name(entry.get("launch_method", ""))
    return "path" if launch_method in ("file", "folder", "path") else "application"


def deduplicate_memory(memory: dict) -> dict:
    """
    Deduplicates and migrates memory entries so each real application has only
    ONE canonical memory record with aliases.
    """
    cleaned_memory = {}

    for raw_key, entry in memory.items():
        if not isinstance(entry, dict):
            continue

        target = entry.get("target", "").strip()
        name = entry.get("name", "").strip() or raw_key
        launch_method = entry.get("launch_method", "exe")
        record_type = _infer_record_type(entry)
        last_verified = entry.get("last_verified", "")
        last_updated = entry.get("last_updated", "")
        raw_aliases = entry.get("aliases", [])
        if isinstance(raw_aliases, str):
            raw_aliases = [raw_aliases]

        norm_key = normalize_name(raw_key)
        norm_name = normalize_name(name)
        norm_target = target.lower()

        # Find existing matching record by target, name, or key
        existing_key = None
        for k, v in cleaned_memory.items():
            if (v.get("target", "").strip().lower() == norm_target and norm_target != "") or \
               (normalize_name(v.get("name", "")) == norm_name and norm_name != "") or \
               (k == norm_key):
                existing_key = k
                break

        if existing_key:
            # Merge into existing record
            existing_record = cleaned_memory[existing_key]
            aliases_set = set(existing_record.get("aliases", []))
            if norm_key != existing_key:
                aliases_set.add(norm_key)
            if norm_name != existing_key:
                aliases_set.add(norm_name)
            for a in raw_aliases:
                norm_a = normalize_name(a)
                if norm_a and norm_a != existing_key:
                    aliases_set.add(norm_a)
            existing_record["aliases"] = sorted(list(aliases_set))
            if last_verified and not existing_record.get("last_verified"):
                existing_record["last_verified"] = last_verified
            if last_updated and not existing_record.get("last_updated"):
                existing_record["last_updated"] = last_updated
        else:
            canonical_key = norm_key
            aliases_set = set()
            if norm_name != canonical_key:
                aliases_set.add(norm_name)
            for a in raw_aliases:
                norm_a = normalize_name(a)
                if norm_a and norm_a != canonical_key:
                    aliases_set.add(norm_a)

            cleaned_memory[canonical_key] = {
                "name": name,
                "aliases": sorted(list(aliases_set)),
                "record_type": record_type,
                "launch_method": launch_method,
                "target": target,
                "last_verified": last_verified,
                "last_updated": last_updated,
            }

    return cleaned_memory


def load_memory() -> dict:
    """Loads and auto-deduplicates remembered applications from app_memory.json."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return deduplicate_memory(data)
        except Exception:
            return {}
    return {}


def save_memory(memory: dict) -> None:
    """Saves applications to app_memory.json ensuring deduplication."""
    try:
        cleaned = deduplicate_memory(memory)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=4)
    except Exception:
        pass


def find_in_memory(query: str, memory: dict) -> tuple[str | None, dict | None]:
    """
    Finds an application in memory by canonical key, display name, or alias.
    Returns: (canonical_key, app_record) or (None, None)
    """
    norm_query = normalize_name(query)
    if not norm_query:
        return None, None

    for key, record in memory.items():
        if key == norm_query:
            return key, record
        if normalize_name(record.get("name", "")) == norm_query:
            return key, record
        aliases = [normalize_name(a) for a in record.get("aliases", [])]
        if norm_query in aliases:
            return key, record

    return None, None


def _remember_record(query: str, name: str, launch_method: str, target: str, record_type: str, extra_aliases=None) -> None:
    """
    Saves or updates memory ensuring no duplicate records are created.
    If target, path, AppID, or normalized name already exists, adds the query as an alias.
    """
    memory = load_memory()
    norm_query = normalize_name(query)
    norm_name = normalize_name(name)
    norm_target = target.strip().lower()
    extra_aliases = extra_aliases or []
    timestamp = _utc_now()

    # Check if this target, name, or key already exists
    matched_key = None
    for k, v in memory.items():
        existing_target = v.get("target", "").strip().lower()
        existing_name = normalize_name(v.get("name", ""))
        existing_aliases = [normalize_name(a) for a in v.get("aliases", [])]

        if (existing_target == norm_target and norm_target != "") or \
           (existing_name == norm_name and norm_name != "") or \
           (k == norm_query) or (norm_query in existing_aliases):
            matched_key = k
            break

    if matched_key:
        record = memory[matched_key]
        aliases = set(record.get("aliases", []))
        if norm_query and norm_query != matched_key:
            aliases.add(norm_query)
        for alias in extra_aliases:
            norm_alias = normalize_name(alias)
            if norm_alias and norm_alias != matched_key:
                aliases.add(norm_alias)
        record["aliases"] = sorted(list(aliases))
        record["name"] = name or record.get("name", query)
        record["record_type"] = record_type
        record["target"] = target
        record["launch_method"] = launch_method
        record["last_verified"] = timestamp
        record["last_updated"] = timestamp
    else:
        canonical_key = norm_query
        aliases = set()
        if norm_name and norm_name != canonical_key:
            aliases.add(norm_name)
        for alias in extra_aliases:
            norm_alias = normalize_name(alias)
            if norm_alias and norm_alias != canonical_key:
                aliases.add(norm_alias)
        memory[canonical_key] = {
            "name": name,
            "aliases": sorted(list(aliases)),
            "record_type": record_type,
            "launch_method": launch_method,
            "target": target,
            "last_verified": timestamp,
            "last_updated": timestamp,
        }

    save_memory(memory)


def remember_application(query: str, name: str, launch_method: str, target: str, aliases=None) -> None:
    """Saves or updates application memory after discovery has produced a valid target."""
    _remember_record(query, name, launch_method, target, "application", aliases)


def remember_path(query: str, path: str, name: str | None = None, aliases=None) -> None:
    """Saves or updates stable file/folder/project path memory."""
    display_name = name or os.path.basename(path.rstrip(os.path.sep)) or query
    launch_method = "folder" if os.path.isdir(path) else "file"
    _remember_record(query, display_name, launch_method, path, "path", aliases)


def forget_memory(key: str) -> None:
    """Removes a stale memory record by key, display name, or alias."""
    memory = load_memory()
    norm_key = normalize_name(key)
    found_key, _ = find_in_memory(norm_key, memory)
    target_key = found_key or norm_key

    if target_key in memory:
        del memory[target_key]
        save_memory(memory)


def forget_application(key: str) -> None:
    """Backward-compatible wrapper for removing stale application memory."""
    forget_memory(key)


def _path_exists(target: str, require_file: bool = False) -> bool:
    if not target:
        return False
    expanded = os.path.expanduser(os.path.expandvars(target))
    if require_file:
        return os.path.isfile(expanded)
    return os.path.exists(expanded)


def validate_memory_record(record: dict) -> bool:
    """
    Revalidates remembered information before use.
    Memory is a cache: stale records must be rediscovered instead of trusted.
    """
    if not isinstance(record, dict):
        return False

    target = str(record.get("target", "")).strip()
    if not target:
        return False

    record_type = _infer_record_type(record)
    launch_method = normalize_name(record.get("launch_method", "exe"))

    if record_type == "path" or launch_method in ("file", "folder", "path"):
        return _path_exists(target)

    if launch_method == "shortcut" or target.lower().endswith((".lnk", ".url")):
        return _path_exists(target, require_file=True)

    if launch_method == "appid":
        packaged = _get_packaged_start_apps()
        return any(info.get("target") == target for info in packaged.values())

    if launch_method == "exe":
        if os.path.isabs(target) or os.path.dirname(target):
            return _path_exists(target, require_file=True)
        builtin_targets = {info.get("target", "").lower() for info in BUILTIN_APPS.values()}
        return bool(shutil.which(target) or target.lower() in builtin_targets)

    return _path_exists(target)


def mark_memory_verified(key: str) -> None:
    """Updates last_verified after a remembered record survives revalidation."""
    memory = load_memory()
    found_key, record = find_in_memory(key, memory)
    if found_key and record:
        record["last_verified"] = _utc_now()
        memory[found_key] = record
        save_memory(memory)


# ---------------------------------------------------------------------------
# Launch Execution
# ---------------------------------------------------------------------------

def launch_app(launch_method: str, target: str) -> None:
    """Launches an application based on its launch method (exe, appid, shortcut)."""
    if launch_method == "appid":
        appsfolder_path = f"shell:AppsFolder\\{target}"
        if hasattr(os, "startfile"):
            try:
                os.startfile(appsfolder_path)
                return
            except Exception:
                pass
        subprocess.Popen(
            ["explorer.exe", appsfolder_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )
    elif launch_method == "shortcut" or target.lower().endswith((".lnk", ".url")):
        if hasattr(os, "startfile"):
            try:
                os.startfile(target)
                return
            except Exception:
                pass
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", target],
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )
    else:
        if " " in target and not target.startswith('"'):
            cmd = f'"{target}"'
        else:
            cmd = target
        subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )


# ---------------------------------------------------------------------------
# Windows Application Discovery
# ---------------------------------------------------------------------------

def _get_start_menu_shortcuts() -> dict:
    """Scans Start Menu folders for application shortcuts."""
    shortcuts = {}
    for env_var in ["APPDATA", "PROGRAMDATA"]:
        base = os.environ.get(env_var, "")
        if not base:
            continue
        programs_dir = os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs")
        if not os.path.exists(programs_dir):
            continue

        for root, _, files in os.walk(programs_dir):
            for file in files:
                if file.lower().endswith((".lnk", ".url")):
                    name = os.path.splitext(file)[0].strip()
                    lower_name = name.lower()
                    if any(skip in lower_name for skip in ["uninstall", "help", "readme", "documentation"]):
                        continue
                    shortcuts[name] = {
                        "name": name,
                        "launch_method": "shortcut",
                        "target": os.path.join(root, file)
                    }
    return shortcuts


def _get_registry_app_paths() -> dict:
    """Queries the Windows Registry for registered application paths."""
    registry_apps = {}
    if not winreg:
        return registry_apps

    hkeys = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    subpaths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]

    for hkey in hkeys:
        for subpath in subpaths:
            try:
                with winreg.OpenKey(hkey, subpath) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                raw_path, _ = winreg.QueryValueEx(subkey, "")
                                if raw_path:
                                    clean_path = raw_path.strip().strip('"')
                                    app_name = os.path.splitext(subkey_name)[0].strip()
                                    registry_apps[app_name] = {
                                        "name": app_name,
                                        "launch_method": "exe",
                                        "target": clean_path
                                    }
                        except Exception:
                            continue
            except Exception:
                continue
    return registry_apps


def _get_packaged_start_apps() -> dict:
    """Queries Windows Get-StartApps for packaged/UWP/MSIX applications."""
    start_apps = {}
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
            text=True,
            encoding="utf-8",
            timeout=10,
            stderr=subprocess.DEVNULL
        )
        if not output.strip():
            return start_apps

        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]

        for item in data:
            name = item.get("Name", "").strip()
            app_id = item.get("AppID", "").strip()
            if name and app_id:
                start_apps[name] = {
                    "name": name,
                    "launch_method": "appid",
                    "target": app_id
                }
    except Exception:
        pass
    return start_apps


def _get_path_executable(query: str) -> dict | None:
    """Checks PATH for executable applications."""
    exe_path = shutil.which(query) or shutil.which(f"{query}.exe")
    if exe_path:
        return {
            "name": query,
            "launch_method": "exe",
            "target": exe_path
        }
    return None


def discover_all_applications() -> dict:
    """Discovers all available applications across all Windows sources."""
    discovered = {}

    # 1. Builtin applications
    for key, info in BUILTIN_APPS.items():
        discovered[key] = info

    # 2. Start Menu shortcuts
    for key, info in _get_start_menu_shortcuts().items():
        discovered[key] = info

    # 3. Registry App Paths
    for key, info in _get_registry_app_paths().items():
        if key.lower() not in [k.lower() for k in discovered]:
            discovered[key] = info

    # 4. Packaged Start Apps (Get-StartApps)
    for key, info in _get_packaged_start_apps().items():
        if key.lower() not in [k.lower() for k in discovered]:
            discovered[key] = info

    return discovered


# ---------------------------------------------------------------------------
# Main Application Launcher
# ---------------------------------------------------------------------------

def open_application(app_name: str) -> dict:
    """
    Opens an installed application using memory, aliases, shortcuts, registry, AppIDs, or PATH.
    """
    if not isinstance(app_name, str):
        return {"success": False, "message": "Invalid application name provided."}

    raw_query = app_name.strip()
    norm_query = normalize_name(raw_query)
    if not norm_query:
        return {"success": False, "message": "Invalid application name provided."}

    alias_target = ALIASES.get(norm_query, raw_query)
    norm_alias = normalize_name(alias_target)

    # -----------------------------------------------------------------------
    # Step 1: Check app_memory.json first
    # -----------------------------------------------------------------------
    memory = load_memory()
    stale_aliases = []
    for search_term in (norm_query, norm_alias):
        canonical_key, cached_entry = find_in_memory(search_term, memory)
        if cached_entry:
            if not validate_memory_record(cached_entry):
                stale_aliases = [canonical_key, cached_entry.get("name", ""), *cached_entry.get("aliases", [])]
                forget_memory(canonical_key)
                break
            try:
                launch_app(cached_entry["launch_method"], cached_entry["target"])
                mark_memory_verified(canonical_key)
                # Ensure current search term is registered in aliases
                if norm_query != canonical_key and norm_query not in [normalize_name(a) for a in cached_entry.get("aliases", [])]:
                    remember_application(norm_query, cached_entry["name"], cached_entry["launch_method"], cached_entry["target"])
                return {
                    "success": True,
                    "message": f"{cached_entry['name']} opened successfully."
                }
            except Exception:
                forget_application(canonical_key)
                break

    # -----------------------------------------------------------------------
    # Step 2: Full Discovery
    # -----------------------------------------------------------------------
    all_apps = discover_all_applications()

    # 1. Exact Match Check
    exact_match = None
    for name, info in all_apps.items():
        norm_name = normalize_name(name)
        if norm_name == norm_alias or norm_name == norm_query:
            exact_match = info
            break

    if exact_match:
        try:
            launch_app(exact_match["launch_method"], exact_match["target"])
            remember_application(raw_query, exact_match["name"], exact_match["launch_method"], exact_match["target"], stale_aliases)
            return {
                "success": True,
                "message": f"{exact_match['name']} opened successfully."
            }
        except Exception as error:
            return {"success": False, "message": str(error)}

    # 2. Check PATH executable directly
    path_app = _get_path_executable(raw_query) or _get_path_executable(alias_target)
    if path_app:
        try:
            launch_app(path_app["launch_method"], path_app["target"])
            remember_application(raw_query, path_app["name"], path_app["launch_method"], path_app["target"], stale_aliases)
            return {
                "success": True,
                "message": f"{path_app['name']} opened successfully."
            }
        except Exception as error:
            return {"success": False, "message": str(error)}

    # 3. Partial Match Check
    partial_matches = {}
    for name, info in all_apps.items():
        norm_name = normalize_name(name)
        if norm_query in norm_name or norm_alias in norm_name:
            partial_matches[name] = info

    if len(partial_matches) == 1:
        chosen_name = list(partial_matches.keys())[0]
        chosen_info = partial_matches[chosen_name]
        try:
            launch_app(chosen_info["launch_method"], chosen_info["target"])
            remember_application(raw_query, chosen_info["name"], chosen_info["launch_method"], chosen_info["target"], stale_aliases)
            return {
                "success": True,
                "message": f"{chosen_info['name']} opened successfully."
            }
        except Exception as error:
            return {"success": False, "message": str(error)}
    elif len(partial_matches) > 1:
        sorted_names = sorted(list(partial_matches.keys()))
        numbered_list = "\n".join(f"{i+1}. {name}" for i, name in enumerate(sorted_names))
        return {
            "success": False,
            "message": f"I found multiple applications:\n{numbered_list}"
        }

    # -----------------------------------------------------------------------
    # Step 3: Not Found
    # -----------------------------------------------------------------------
    return {
        "success": False,
        "message": f"I couldn't find an installed application matching '{raw_query}'."
    }
