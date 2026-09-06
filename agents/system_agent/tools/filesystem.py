import os
import pathlib
import shutil
import subprocess


FRIENDLY_LOCATIONS = {
    "desktop": lambda: os.path.join(os.path.expanduser("~"), "Desktop"),
    "downloads": lambda: os.path.join(os.path.expanduser("~"), "Downloads"),
    "documents": lambda: os.path.join(os.path.expanduser("~"), "Documents"),
    "pictures": lambda: os.path.join(os.path.expanduser("~"), "Pictures"),
    "videos": lambda: os.path.join(os.path.expanduser("~"), "Videos"),
    "music": lambda: os.path.join(os.path.expanduser("~"), "Music"),
    "home": lambda: os.path.expanduser("~"),
}


def resolve_location(location_name: str) -> str | None:
    """Resolves friendly folder names or paths to an absolute filesystem path."""
    if not location_name or not isinstance(location_name, str):
        return None

    cleaned = location_name.strip()
    norm = cleaned.lower()

    if norm in FRIENDLY_LOCATIONS:
        return FRIENDLY_LOCATIONS[norm]()

    expanded = os.path.expanduser(os.path.expandvars(cleaned))
    if os.path.isabs(expanded):
        return expanded

    home_candidate = os.path.join(os.path.expanduser("~"), cleaned)
    if os.path.exists(home_candidate):
        return home_candidate

    return os.path.abspath(cleaned)


def list_files(location: str) -> dict:
    """Lists files and folders in a friendly location or folder path."""
    if not location or not isinstance(location, str):
        return {
            "success": False,
            "location": str(location),
            "path": "",
            "items": [],
            "message": "Invalid location specified."
        }

    resolved_path = resolve_location(location)
    if not resolved_path or not os.path.exists(resolved_path):
        return {
            "success": False,
            "location": location,
            "path": resolved_path or "",
            "items": [],
            "message": f"Location '{location}' not found."
        }

    if not os.path.isdir(resolved_path):
        return {
            "success": False,
            "location": location,
            "path": resolved_path,
            "items": [],
            "message": f"'{location}' is not a directory."
        }

    try:
        entries = sorted(os.listdir(resolved_path))
        display_name = location.strip().capitalize() if location.lower() in FRIENDLY_LOCATIONS else os.path.basename(resolved_path) or location
        return {
            "success": True,
            "location": display_name,
            "path": resolved_path,
            "items": entries,
            "message": f"{len(entries)} items found in {display_name}." if entries else f"No files found in {display_name}."
        }
    except Exception as error:
        return {
            "success": False,
            "location": location,
            "path": resolved_path,
            "items": [],
            "message": str(error)
        }


def find_file_or_folder(query: str, max_depth: int = 3) -> dict:
    """Searches user folders and repository area for matching files or folders."""
    from tools.applications import (
        find_in_memory,
        forget_memory,
        load_memory,
        mark_memory_verified,
        normalize_name,
        remember_path,
        validate_memory_record,
    )

    if not query or not isinstance(query, str):
        return {
            "success": False,
            "query": "",
            "matches": [],
            "message": "Invalid search query."
        }

    cleaned = query.strip()
    norm_query = cleaned.lower()

    # Clean suffixes like " folder", " directory", " file"
    for suffix in [" folder", " directory", " file"]:
        if norm_query.endswith(suffix):
            norm_query = norm_query[:-len(suffix)].strip()
            break

    if not norm_query:
        return {
            "success": False,
            "query": cleaned,
            "matches": [],
            "message": "Invalid search query."
        }

    cached_matches = []
    stale_aliases = []
    memory = load_memory()
    cached_key, cached_record = find_in_memory(norm_query, memory)
    if cached_record and cached_record.get("record_type") == "path":
        cached_target = cached_record.get("target", "")
        if validate_memory_record(cached_record):
            cached_matches.append(cached_target)
            mark_memory_verified(cached_key)
        else:
            stale_aliases = [cached_key, cached_record.get("name", ""), *cached_record.get("aliases", [])]
            forget_memory(cached_key)

    search_roots = []
    for loc in ["desktop", "documents", "downloads"]:
        p = resolve_location(loc)
        if p and os.path.exists(p) and p not in search_roots:
            search_roots.append(p)

    cwd = os.getcwd()
    if cwd not in search_roots:
        search_roots.append(cwd)

    matches = []
    seen = {m.lower() for m in cached_matches}
    ignored_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "appdata"}

    for root_dir in search_roots:
        root_depth = root_dir.rstrip(os.path.sep).count(os.path.sep)
        for current_root, dirs, files in os.walk(root_dir):
            current_depth = current_root.rstrip(os.path.sep).count(os.path.sep) - root_depth
            if current_depth > max_depth:
                del dirs[:]
                continue

            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs and not d.startswith(".")]

            for d in dirs:
                if norm_query in d.lower():
                    full_path = os.path.join(current_root, d)
                    if full_path.lower() not in seen:
                        seen.add(full_path.lower())
                        matches.append(full_path)

            for f in files:
                if norm_query in f.lower():
                    full_path = os.path.join(current_root, f)
                    if full_path.lower() not in seen:
                        seen.add(full_path.lower())
                        matches.append(full_path)

    def match_priority(p):
        base = os.path.basename(p).lower()
        is_exact = base == norm_query
        return (not is_exact, len(p))

    sorted_matches = cached_matches + sorted(matches, key=match_priority)

    for match in sorted_matches:
        if os.path.basename(match).lower() == norm_query:
            remember_path(cleaned, match, aliases=stale_aliases)
            break

    return {
        "success": True,
        "query": cleaned,
        "matches": sorted_matches,
        "message": f"Found {len(sorted_matches)} match(es)." if sorted_matches else f"No matches found for '{cleaned}'."
    }


def create_folder(folder_name: str, location: str) -> dict:
    """Creates a new folder in the specified friendly location or directory path."""
    if not folder_name or not isinstance(folder_name, str):
        return {
            "success": False,
            "message": "Invalid folder name provided.",
            "path": ""
        }

    clean_name = folder_name.strip()
    if not clean_name:
        return {
            "success": False,
            "message": "Invalid folder name provided.",
            "path": ""
        }

    resolved_loc = resolve_location(location)
    if not resolved_loc or not os.path.exists(resolved_loc):
        return {
            "success": False,
            "message": f"Location '{location}' not found.",
            "path": ""
        }

    target_path = os.path.join(resolved_loc, clean_name)

    if os.path.exists(target_path):
        return {
            "success": True,
            "already_exists": True,
            "message": f"Folder '{clean_name}' already exists.",
            "path": target_path
        }

    try:
        os.makedirs(target_path, exist_ok=True)
        return {
            "success": True,
            "message": f"Folder '{clean_name}' created successfully.",
            "path": target_path
        }
    except Exception as error:
        return {
            "success": False,
            "message": str(error),
            "path": target_path
        }


def _path_lookup(query: str) -> list[str]:
    """Finds all unique executable paths for *query* on the Windows PATH."""
    matches = []
    seen: set[str] = set()

    primary = shutil.which(query)
    if primary:
        abs_primary = os.path.abspath(primary)
        if os.path.exists(abs_primary) and abs_primary.lower() not in seen:
            seen.add(abs_primary.lower())
            matches.append(abs_primary)

    try:
        output = subprocess.check_output(
            ["where.exe", query],
            text=True, encoding="utf-8", errors="ignore",
            stderr=subprocess.DEVNULL, timeout=5,
        )
        for line in output.splitlines():
            line_str = line.strip()
            if line_str and os.path.exists(line_str):
                abs_line = os.path.abspath(line_str)
                if abs_line.lower() not in seen:
                    seen.add(abs_line.lower())
                    matches.append(abs_line)
    except Exception:
        pass

    return matches


def locate_executable(query: str) -> dict:
    """
    Locates an application or executable using ALL System Agent knowledge:
      1. app_memory.json
      2. Built-in apps / aliases
      3. Windows PATH (shutil.which + where.exe)
      4. Start Menu shortcuts
      5. Registry App Paths
      6. Windows packaged apps (Get-StartApps)

    Returns a dict describing what was found and its type.
    """
    from tools.applications import (
        load_memory, find_in_memory, normalize_name,
        forget_memory, mark_memory_verified, remember_application, validate_memory_record,
        BUILTIN_APPS, ALIASES,
        _get_start_menu_shortcuts, _get_registry_app_paths,
        _get_packaged_start_apps, _get_path_executable,
    )

    if not query or not isinstance(query, str):
        return {
            "success": False,
            "query": "",
            "type": None,
            "name": None,
            "target": None,
            "matches": [],
            "message": "Invalid name provided.",
        }

    clean_query = query.strip().rstrip("?").strip()
    if not clean_query:
        return {
            "success": False,
            "query": "",
            "type": None,
            "name": None,
            "target": None,
            "matches": [],
            "message": "Invalid name provided.",
        }

    norm_query = normalize_name(clean_query)

    # Resolve alias first
    alias_target = ALIASES.get(norm_query, clean_query)
    norm_alias = normalize_name(alias_target)

    def _make_result(name, launch_method, target, extra_matches=None):
        type_labels = {
            "appid": "Windows packaged app",
            "shortcut": "Shortcut",
            "exe": "Executable",
        }
        return {
            "success": True,
            "query": clean_query,
            "type": launch_method,
            "name": name,
            "target": target,
            "matches": extra_matches or [target] if target else [],
            "message": f"Found {name}.",
        }

    # ---- 1. app_memory.json ------------------------------------------------
    memory = load_memory()
    stale_aliases = []
    for search_term in (norm_query, norm_alias):
        canonical_key, record = find_in_memory(search_term, memory)
        if record:
            if validate_memory_record(record):
                mark_memory_verified(canonical_key)
                return _make_result(
                    record.get("name", clean_query),
                    record.get("launch_method", "exe"),
                    record.get("target", ""),
                )
            stale_aliases = [canonical_key, record.get("name", ""), *record.get("aliases", [])]
            forget_memory(canonical_key)
            break

    # ---- 2. Built-in apps ---------------------------------------------------
    for search_term in (norm_query, norm_alias):
        if search_term in BUILTIN_APPS:
            info = BUILTIN_APPS[search_term]
            remember_application(clean_query, info.get("name", search_term), info.get("launch_method", "exe"), info.get("target", ""), stale_aliases)
            return _make_result(
                info.get("name", search_term),
                info.get("launch_method", "exe"),
                info.get("target", ""),
            )

    # ---- 3. Windows PATH ----------------------------------------------------
    for search_term in (clean_query, alias_target):
        path_matches = _path_lookup(search_term)
        if path_matches:
            remember_application(clean_query, search_term, "exe", path_matches[0], stale_aliases)
            return {
                "success": True,
                "query": clean_query,
                "type": "exe",
                "name": search_term,
                "target": path_matches[0],
                "matches": path_matches,
                "message": f"Found {search_term}.",
            }

    # ---- 4. Start Menu shortcuts --------------------------------------------
    shortcuts = _get_start_menu_shortcuts()
    for name, info in shortcuts.items():
        if normalize_name(name) in (norm_query, norm_alias) or norm_query in normalize_name(name):
            remember_application(clean_query, info.get("name", name), info.get("launch_method", "shortcut"), info.get("target", ""), stale_aliases)
            return _make_result(
                info.get("name", name),
                info.get("launch_method", "shortcut"),
                info.get("target", ""),
            )

    # ---- 5. Registry App Paths ----------------------------------------------
    registry_apps = _get_registry_app_paths()
    for name, info in registry_apps.items():
        if normalize_name(name) in (norm_query, norm_alias) or norm_query in normalize_name(name):
            remember_application(clean_query, info.get("name", name), info.get("launch_method", "exe"), info.get("target", ""), stale_aliases)
            return _make_result(
                info.get("name", name),
                info.get("launch_method", "exe"),
                info.get("target", ""),
            )

    # ---- 6. Packaged / UWP apps (Get-StartApps) ----------------------------
    packaged = _get_packaged_start_apps()
    for name, info in packaged.items():
        if normalize_name(name) in (norm_query, norm_alias) or norm_query in normalize_name(name):
            remember_application(clean_query, info.get("name", name), info.get("launch_method", "appid"), info.get("target", ""), stale_aliases)
            return _make_result(
                info.get("name", name),
                info.get("launch_method", "appid"),
                info.get("target", ""),
            )

    # ---- Not found ----------------------------------------------------------
    return {
        "success": True,
        "query": clean_query,
        "type": None,
        "name": None,
        "target": None,
        "matches": [],
        "message": f"I couldn't locate '{clean_query}' on this system.",
    }


# Keep backward-compatible alias
def locate_executable_in_path(query: str) -> dict:
    """Backward-compatible wrapper; delegates to locate_executable."""
    return locate_executable(query)
