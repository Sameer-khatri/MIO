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


def resolve_destination(query: str) -> dict:
    """Resolve a real destination folder without trusting unresolved paths or memory."""
    from tools.applications import (
        find_in_memory,
        forget_memory,
        load_memory,
        mark_memory_verified,
        remember_path,
        validate_memory_record,
    )

    if not query or not isinstance(query, str):
        return {"success": False, "path": "", "matches": [], "message": "Invalid destination specified."}

    cleaned = query.strip()
    if not cleaned:
        return {"success": False, "path": "", "matches": [], "message": "Invalid destination specified."}

    normalized = cleaned.lower()
    if normalized in FRIENDLY_LOCATIONS:
        friendly_path = resolve_location(normalized)
        if os.path.isdir(friendly_path):
            return {"success": True, "path": friendly_path, "matches": [friendly_path], "message": f"Using {cleaned}."}
        return {"success": False, "path": friendly_path, "matches": [], "message": f"Location '{cleaned}' not found."}

    expanded = os.path.abspath(os.path.expanduser(os.path.expandvars(cleaned)))
    direct_candidates = [expanded]
    if not os.path.isabs(cleaned):
        direct_candidates.extend([
            os.path.join(os.getcwd(), cleaned),
            os.path.join(os.path.expanduser("~"), cleaned),
        ])
        path_parts = cleaned.replace("/", os.path.sep).split(os.path.sep)
        if path_parts and path_parts[0].lower() in FRIENDLY_LOCATIONS:
            friendly_base = resolve_location(path_parts[0].lower())
            nested_part = os.path.join(*path_parts[1:]) if len(path_parts) > 1 else ""
            if friendly_base:
                direct_candidates.append(os.path.join(friendly_base, nested_part))
        for location_name in FRIENDLY_LOCATIONS:
            base = resolve_location(location_name)
            if base:
                direct_candidates.append(os.path.join(base, cleaned))

    direct_matches = []
    for candidate in direct_candidates:
        if os.path.isdir(candidate) and os.path.normcase(os.path.abspath(candidate)) not in {
            os.path.normcase(path) for path in direct_matches
        }:
            direct_matches.append(os.path.abspath(candidate))
    if len(direct_matches) == 1:
        remember_path(os.path.basename(direct_matches[0]), direct_matches[0])
        return {"success": True, "path": direct_matches[0], "matches": direct_matches, "message": f"Using '{cleaned}'."}
    if len(direct_matches) > 1:
        return _ambiguous_destination_result(cleaned, direct_matches)

    memory = load_memory()
    memory_key, memory_record = find_in_memory(normalized, memory)
    if memory_record and memory_record.get("record_type") == "path":
        remembered_path = memory_record.get("target", "")
        if validate_memory_record(memory_record) and os.path.isdir(remembered_path):
            mark_memory_verified(memory_key)
            return {"success": True, "path": remembered_path, "matches": [remembered_path], "message": f"Using remembered folder '{cleaned}'."}
        forget_memory(memory_key)

    search_result = find_file_or_folder(cleaned)
    folder_matches = [path for path in search_result.get("matches", []) if os.path.isdir(path)]
    unique_matches = []
    seen = set()
    for path in folder_matches:
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            unique_matches.append(path)

    if len(unique_matches) == 1:
        remember_path(cleaned, unique_matches[0])
        return {"success": True, "path": unique_matches[0], "matches": unique_matches, "message": f"Using '{cleaned}'."}
    if len(unique_matches) > 1:
        return _ambiguous_destination_result(cleaned, unique_matches)

    return {"success": False, "path": "", "matches": [], "message": f"Destination folder '{cleaned}' not found."}


def _ambiguous_destination_result(query: str, matches: list[str]) -> dict:
    match_lines = "\n".join(f"- {match}" for match in matches)
    return {
        "success": False,
        "path": "",
        "matches": matches,
        "message": f"I found multiple destination folders for '{query}':\n{match_lines}\nPlease be more specific.",
    }


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

    direct_query = os.path.abspath(os.path.expanduser(os.path.expandvars(cleaned)))
    if os.path.exists(direct_query):
        return {
            "success": True,
            "query": cleaned,
            "matches": [direct_query],
            "message": "Found 1 match.",
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
        raw_base = os.path.basename(p)
        if raw_base == cleaned:
            name_rank = 0
        elif base == norm_query:
            name_rank = 1
        elif base.startswith(norm_query):
            name_rank = 2
        else:
            name_rank = 3
        depth = p.rstrip(os.path.sep).count(os.path.sep)
        return (name_rank, depth, len(p))

    sorted_matches = sorted(cached_matches + matches, key=match_priority)

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
    """Creates a new folder inside a resolved destination folder."""
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

    destination = resolve_destination(location)
    resolved_loc = destination.get("path", "") if destination.get("success") else ""
    if not resolved_loc:
        return {
            "success": False,
            "message": destination.get("message", f"Location '{location}' not found."),
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


def copy_file_or_folder(source_query: str, location: str) -> dict:
    """Copies one discovered file or folder into a resolved destination without overwriting."""
    from tools.applications import remember_path

    if not source_query or not isinstance(source_query, str):
        return {
            "success": False,
            "source": "",
            "destination": "",
            "message": "Invalid source specified.",
        }

    if not location or not isinstance(location, str):
        return {
            "success": False,
            "source": source_query,
            "destination": "",
            "message": "Invalid destination specified.",
        }

    clean_source = source_query.strip()
    clean_location = location.strip()
    destination = resolve_destination(clean_location)
    destination_root = destination.get("path", "") if destination.get("success") else ""
    if not destination_root:
        return {
            "success": False,
            "source": clean_source,
            "destination": "",
            "message": destination.get("message", f"Location '{clean_location}' not found."),
        }

    found = find_file_or_folder(clean_source)
    found_matches = found.get("matches", []) if found.get("success") else []
    matches = []
    for match in found_matches:
        destination_candidate = os.path.join(destination_root, os.path.basename(match))
        if os.path.abspath(match).lower() == os.path.abspath(destination_candidate).lower():
            continue
        matches.append(match)

    if not matches and found_matches:
        existing_name = os.path.basename(found_matches[0])
        destination_path = os.path.join(destination_root, existing_name)
        if os.path.exists(destination_path):
            return {
                "success": False,
                "source": found_matches[0],
                "destination": destination_path,
                "message": f"A file or folder named '{existing_name}' already exists in {clean_location}.",
            }

    if not matches:
        return {
            "success": False,
            "source": clean_source,
            "destination": "",
            "message": f"I couldn't find '{clean_source}'.",
        }

    if len(matches) > 1:
        match_lines = "\n".join(f"- {match}" for match in matches)
        return {
            "success": False,
            "source": clean_source,
            "destination": "",
            "matches": matches,
            "message": f"I found multiple matches for '{clean_source}':\n{match_lines}\nPlease be more specific.",
        }

    source_path = matches[0]
    if not os.path.exists(source_path):
        return {
            "success": False,
            "source": source_path,
            "destination": "",
            "message": f"I couldn't find '{clean_source}'.",
        }

    destination_path = os.path.join(destination_root, os.path.basename(source_path))
    source_key = os.path.normcase(os.path.abspath(source_path))
    destination_root_key = os.path.normcase(os.path.abspath(destination_root))
    destination_key = os.path.normcase(os.path.abspath(destination_path))
    if source_key == destination_key or source_key == destination_root_key:
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": "The source and destination are the same location.",
        }
    if os.path.isdir(source_path):
        try:
            if os.path.commonpath([source_key, destination_root_key]) == source_key:
                return {
                    "success": False,
                    "source": source_path,
                    "destination": destination_path,
                    "message": "A folder cannot be copied into itself or one of its child folders.",
                }
        except ValueError:
            pass
    if os.path.exists(destination_path):
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": f"A file or folder named '{os.path.basename(source_path)}' already exists in {clean_location}.",
        }

    try:
        if os.path.isdir(source_path):
            shutil.copytree(source_path, destination_path)
        else:
            shutil.copy2(source_path, destination_path)
    except Exception as error:
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": str(error),
        }

    if not os.path.exists(destination_path):
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": f"Copy verification failed for '{clean_source}'.",
        }

    remember_path(os.path.basename(destination_path), destination_path)
    return {
        "success": True,
        "source": source_path,
        "destination": destination_path,
        "message": f"Copied '{os.path.basename(source_path)}' to {clean_location}.",
    }


def _resolve_single_source(source_query: str, excluded_destination_root: str | None = None) -> tuple[str | None, dict | None]:
    """Resolve exactly one existing source, preserving ambiguity details."""
    found = find_file_or_folder(source_query)
    raw_matches = [path for path in found.get("matches", []) if os.path.exists(path)] if found.get("success") else []
    matches = raw_matches
    if excluded_destination_root:
        matches = [
            path for path in raw_matches
            if os.path.normcase(os.path.abspath(path)) != os.path.normcase(
                os.path.abspath(os.path.join(excluded_destination_root, os.path.basename(path)))
            )
        ]
    if not matches:
        if raw_matches and excluded_destination_root:
            return None, {
                "success": False,
                "source": raw_matches[0],
                "message": "The source and destination are the same location.",
            }
        return None, {
            "success": False,
            "source": source_query,
            "message": f"I couldn't find '{source_query}'.",
        }
    if len(matches) > 1:
        match_lines = "\n".join(f"- {match}" for match in matches)
        return None, {
            "success": False,
            "source": source_query,
            "matches": matches,
            "message": f"I found multiple matches for '{source_query}':\n{match_lines}\nPlease be more specific.",
        }
    return matches[0], None


def _update_path_memory(old_path: str, new_path: str, display_name: str | None = None) -> None:
    """Update one remembered path in place, retaining its aliases."""
    from tools.applications import load_memory, remember_path

    memory = load_memory()
    old_key = os.path.normcase(os.path.abspath(old_path))
    for key, record in memory.items():
        target = record.get("target", "")
        if os.path.normcase(os.path.abspath(target)) == old_key:
            aliases = list(record.get("aliases", []))
            remember_path(
                key,
                new_path,
                name=display_name or record.get("name") or os.path.basename(new_path),
                aliases=aliases,
            )
            return
    remember_path(os.path.basename(new_path), new_path, name=display_name)


def move_file_or_folder(source_query: str, location: str) -> dict:
    """Move exactly one source into a resolved destination without overwriting."""
    if not source_query or not isinstance(source_query, str):
        return {"success": False, "source": "", "destination": "", "message": "Invalid source specified."}
    if not location or not isinstance(location, str):
        return {"success": False, "source": source_query, "destination": "", "message": "Invalid destination specified."}

    clean_source = source_query.strip()
    destination = resolve_destination(location.strip())
    destination_root = destination.get("path", "") if destination.get("success") else ""
    if not destination_root:
        return {
            "success": False,
            "source": clean_source,
            "destination": "",
            "message": destination.get("message", f"Location '{location}' not found."),
        }

    source_path, error = _resolve_single_source(clean_source, destination_root)
    if error:
        error["destination"] = ""
        return error

    destination_path = os.path.join(destination_root, os.path.basename(source_path))
    source_key = os.path.normcase(os.path.abspath(source_path))
    destination_root_key = os.path.normcase(os.path.abspath(destination_root))
    destination_key = os.path.normcase(os.path.abspath(destination_path))
    if source_key == destination_key or source_key == destination_root_key:
        return {"success": False, "source": source_path, "destination": destination_path, "message": "The source and destination are the same location."}
    if os.path.isdir(source_path):
        try:
            if os.path.commonpath([source_key, destination_root_key]) == source_key:
                return {"success": False, "source": source_path, "destination": destination_path, "message": "A folder cannot be moved into itself or one of its child folders."}
        except ValueError:
            pass
    if os.path.exists(destination_path):
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": f"A file or folder named '{os.path.basename(source_path)}' already exists in {location.strip()}.",
        }

    try:
        shutil.move(source_path, destination_path)
    except Exception as error:
        return {"success": False, "source": source_path, "destination": destination_path, "message": str(error)}

    if os.path.exists(source_path) or not os.path.exists(destination_path):
        return {
            "success": False,
            "source": source_path,
            "destination": destination_path,
            "message": "Move verification failed.",
        }

    _update_path_memory(source_path, destination_path)
    return {"success": True, "source": source_path, "destination": destination_path, "message": "Moved successfully."}


def _valid_rename_name(name: str) -> bool:
    """Check a simple Windows filename without accepting path syntax."""
    invalid_chars = '<>:"/\\|?*'
    return bool(name) and name not in (".", "..") and not any(char in name for char in invalid_chars) and not any(ord(char) < 32 for char in name) and name == name.rstrip(" .")


def rename_file_or_folder(source_query: str, new_name: str) -> dict:
    """Rename exactly one source using a validated simple filename."""
    if not source_query or not isinstance(source_query, str):
        return {"success": False, "old_path": "", "new_path": "", "message": "Invalid source specified."}
    clean_source = source_query.strip()
    clean_name = new_name.strip() if isinstance(new_name, str) else ""
    if not _valid_rename_name(clean_name):
        return {"success": False, "old_path": "", "new_path": "", "message": "Invalid rename target. Use a simple Windows filename."}

    source_path, error = _resolve_single_source(clean_source)
    if error:
        error["old_path"] = ""
        error["new_path"] = ""
        return error

    if os.path.isfile(source_path) and not os.path.splitext(clean_name)[1]:
        clean_name += os.path.splitext(source_path)[1]
    new_path = os.path.join(os.path.dirname(source_path), clean_name)
    if os.path.normcase(os.path.abspath(source_path)) == os.path.normcase(os.path.abspath(new_path)):
        return {"success": False, "old_path": source_path, "new_path": new_path, "message": "The source and destination are the same location."}
    if os.path.exists(new_path):
        return {"success": False, "old_path": source_path, "new_path": new_path, "message": f"A file or folder named '{os.path.basename(new_path)}' already exists."}

    try:
        os.rename(source_path, new_path)
    except Exception as error:
        return {"success": False, "old_path": source_path, "new_path": new_path, "message": str(error)}

    if os.path.exists(source_path) or not os.path.exists(new_path):
        return {"success": False, "old_path": source_path, "new_path": new_path, "message": "Rename verification failed."}

    _update_path_memory(source_path, new_path, display_name=os.path.basename(new_path))
    return {"success": True, "old_path": source_path, "new_path": new_path, "message": "Renamed successfully."}


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


def _recycle_path(path: str) -> bool:
    """Executes safe move to Windows Recycle Bin via SHFileOperationW."""
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        op = SHFILEOPSTRUCTW()
        op.wFunc = 0x0003  # FO_DELETE
        op.pFrom = path + "\0\0"
        op.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400  # FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

        ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        return ret == 0
    except Exception:
        return False


def delete_file_or_folder(source_query: str) -> dict:
    """
    Safely moves a target file or folder to the Windows Recycle Bin.
    Protects Windows system directories, user roots, repo paths, and .git directories.
    """
    if not source_query or not isinstance(source_query, str):
        return {
            "success": False,
            "target": "",
            "message": "Invalid file or folder specified."
        }

    clean_source = source_query.strip()
    source_path, error = _resolve_single_source(clean_source)
    if error:
        return error

    abs_source = os.path.abspath(source_path)
    norm_source = os.path.normcase(abs_source)

    # Protected paths check
    repo_root = os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    user_home = os.path.normcase(os.path.expanduser("~"))
    win_dir = os.path.normcase(os.environ.get("SystemRoot", "C:\\Windows"))
    prog_files = os.path.normcase(os.environ.get("ProgramFiles", "C:\\Program Files"))
    prog_files_x86 = os.path.normcase(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))

    protected_roots = [user_home, win_dir, prog_files, prog_files_x86, repo_root]
    # Check if target is a root drive (e.g. C:\)
    if norm_source.endswith(":\\") or norm_source.endswith(":/") or len(norm_source) <= 3:
        return {
            "success": False,
            "target": abs_source,
            "message": f"Safety restriction: Cannot delete root drive '{abs_source}'."
        }

    # User home directory root check (e.g. C:\Users\Username)
    if norm_source == user_home:
        return {
            "success": False,
            "target": abs_source,
            "message": f"Safety restriction: Cannot delete user root directory '{abs_source}'."
        }

    # Protected system & repo subtrees
    system_subtrees = [win_dir, prog_files, prog_files_x86, repo_root]
    for p in system_subtrees:
        if norm_source == p or norm_source.startswith(p + os.sep) or norm_source.startswith(p + "/"):
            return {
                "success": False,
                "target": abs_source,
                "message": f"Safety restriction: Cannot delete protected system path '{abs_source}'."
            }

    if ".git" in abs_source.split(os.sep):
        return {
            "success": False,
            "target": abs_source,
            "message": f"Safety restriction: Cannot delete git repository files in '{abs_source}'."
        }

    if not _recycle_path(abs_source) or os.path.exists(abs_source):
        return {
            "success": False,
            "target": abs_source,
            "message": f"Failed to recycle '{os.path.basename(abs_source)}'."
        }

    # Remove from memory if it was tracked
    try:
        from tools.applications import load_memory, forget_memory
        mem = load_memory()
        for k, v in mem.items():
            if os.path.normcase(os.path.abspath(v.get("target", ""))) == norm_source:
                forget_memory(k)
                break
    except Exception:
        pass

    return {
        "success": True,
        "target": abs_source,
        "message": f"Sent '{os.path.basename(abs_source)}' to the Recycle Bin."
    }


def read_file_head(file_path: str, num_lines: int = 20) -> dict:
    """
    Reads the first N lines from a text, code, or log file.
    """
    if not file_path or not isinstance(file_path, str):
        return {"success": False, "message": "File path is required."}

    norm_path = os.path.abspath(os.path.expanduser(file_path.strip()))
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        return {"success": False, "message": f"File does not exist: '{norm_path}'"}

    lines = []
    try:
        with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(max(1, int(num_lines))):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\r\n"))

        return {
            "success": True,
            "file": norm_path,
            "lines_read": len(lines),
            "line_count": len(lines),
            "content": "\n".join(lines),
            "message": f"--- First {len(lines)} lines of {os.path.basename(norm_path)} ---\n" + "\n".join(lines)
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to read file: {err}"}


def read_file_tail(file_path: str, num_lines: int = 20) -> dict:
    """
    Reads the last N lines from a text, code, or log file.
    """
    if not file_path or not isinstance(file_path, str):
        return {"success": False, "message": "File path is required."}

    norm_path = os.path.abspath(os.path.expanduser(file_path.strip()))
    if not os.path.exists(norm_path) or not os.path.isfile(norm_path):
        return {"success": False, "message": f"File does not exist: '{norm_path}'"}

    max_lines = max(1, int(num_lines))
    lines = []
    try:
        with open(norm_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        tail_lines = [l.rstrip("\r\n") for l in lines[-max_lines:]]
        return {
            "success": True,
            "file": norm_path,
            "lines_read": len(tail_lines),
            "line_count": len(tail_lines),
            "content": "\n".join(tail_lines),
            "message": f"--- Last {len(tail_lines)} lines of {os.path.basename(norm_path)} ---\n" + "\n".join(tail_lines)
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to read file: {err}"}


def get_folder_size(folder_path: str) -> dict:
    """
    Recursively computes the total disk footprint and item count of any directory.
    """
    if not folder_path or not isinstance(folder_path, str):
        return {"success": False, "message": "Folder path is required."}

    norm_path = os.path.abspath(os.path.expanduser(folder_path.strip()))
    if not os.path.exists(norm_path) or not os.path.isdir(norm_path):
        return {"success": False, "message": f"Folder does not exist: '{norm_path}'"}

    total_bytes = 0
    file_count = 0
    dir_count = 0

    try:
        for root, dirs, files in os.walk(norm_path):
            dir_count += len(dirs)
            for f in files:
                file_count += 1
                try:
                    fp = os.path.join(root, f)
                    total_bytes += os.path.getsize(fp)
                except (OSError, FileNotFoundError):
                    pass

        size_mb = round(total_bytes / (1024 ** 2), 2)
        size_gb = round(total_bytes / (1024 ** 3), 3)

        return {
            "success": True,
            "folder": norm_path,
            "total_bytes": total_bytes,
            "size_bytes": total_bytes,
            "size_mb": size_mb,
            "size_gb": size_gb,
            "file_count": file_count,
            "directory_count": dir_count,
            "message": f"Folder '{os.path.basename(norm_path)}': {size_mb} MB ({file_count} files, {dir_count} subfolders)."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to compute folder size: {err}"}




