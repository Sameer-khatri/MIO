"""
MIO System Agent - Master Tool Inventory & Hand Kit Registry

This module acts as the central catalog and execution gateway for all 25 standalone tools.
It organizes MIO's capabilities into 5 modular Hand Kits and provides direct,
command-free dynamic execution for any reasoning engine or AI brain.
"""

import importlib
import inspect
import os
import sys

# Ensure tools module can be imported cleanly
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)


# =============================================================================
# Hand Kits Organization (5 Logical Packs)
# =============================================================================

HAND_KITS = {
    "sensory": {
        "name": "Sensory Hand (Sight, Sound & Display)",
        "description": "Perceives the screen, monitors, audio, and visual environment.",
        "tools": ["screen", "display", "audio", "brightness", "notifications"],
    },
    "action": {
        "name": "Action Hand (Mouse, Keyboard & Clipboard)",
        "description": "Interacts physically with the desktop via clicks, hotkeys, typing, and clipboard.",
        "tools": ["mouse", "input", "clipboard"],
    },
    "control": {
        "name": "Control Hand (Applications & Windows)",
        "description": "Controls active desktop windows, software execution, process lifecycles, and installed apps.",
        "tools": ["applications", "windows", "processes", "installed_apps"],
    },
    "storage": {
        "name": "Storage Hand (Filesystem, Drives & Archives)",
        "description": "Manages files, folders, disks, compression archives, and cryptographic hashes.",
        "tools": ["filesystem", "archive", "drives", "hasher"],
    },
    "connectivity": {
        "name": "Connectivity Hand (Network, Web & System Services)",
        "description": "Handles internet, Wi-Fi, network ports, browser sessions, power states, services, self-healing, and hardware specs.",
        "tools": ["network", "wifi_tools", "ports", "browser", "power", "settings", "services", "system_info", "timer", "healer"],
    },
}


# =============================================================================
# Tool Metadata Catalog (All 25 Tools)
# =============================================================================

TOOL_CATALOG = {
    # Sensory Hand
    "screen": {
        "kit": "sensory",
        "description": "Screen capture, bounding-box region screenshot, and PNG dimension inspection.",
        "primary_actions": ["take_screenshot", "take_region_screenshot", "get_image_dimensions"],
    },
    "display": {
        "kit": "sensory",
        "description": "Primary display metrics, multi-monitor enumeration, and refresh rate display modes.",
        "primary_actions": ["get_display_info", "get_monitors_detail", "get_display_modes"],
    },
    "audio": {
        "kit": "sensory",
        "description": "Master volume control, media playback keys, SAPI text-to-speech, and audio device listing.",
        "primary_actions": ["set_volume", "volume_up", "volume_down", "toggle_mute", "speak_text", "list_audio_devices", "media_play_pause", "media_next", "media_prev", "media_stop"],
    },
    "brightness": {
        "kit": "sensory",
        "description": "Read and set display brightness, incremental steps, and smooth brightness fading.",
        "primary_actions": ["get_brightness", "set_brightness", "increase_brightness", "decrease_brightness", "fade_brightness"],
    },
    "notifications": {
        "kit": "sensory",
        "description": "Windows desktop toast notifications, audio chimes, frequency beeps, and sound patterns.",
        "primary_actions": ["show_notification", "play_chime", "beep", "play_sound_pattern"],
    },

    # Action Hand
    "mouse": {
        "kit": "action",
        "description": "Cursor coordinates, absolute and relative moves, clicks, scroll, and smooth drag-and-drop.",
        "primary_actions": ["get_cursor_position", "move_cursor", "move_relative", "click", "double_click", "right_click", "drag_to", "scroll"],
    },
    "input": {
        "kit": "action",
        "description": "Global hotkey combinations, standard shortcut triggers (Win+E, Win+I, Alt+F4), and SendInput typing.",
        "primary_actions": ["send_hotkey", "press_key", "type_text", "show_desktop", "open_task_manager", "switch_app_alt_tab", "open_file_explorer", "open_windows_settings", "open_run_dialog", "close_active_window", "select_all", "copy_selection", "paste_selection"],
    },
    "clipboard": {
        "kit": "action",
        "description": "Read, write, append, and clear Windows system clipboard, and inspect active formats.",
        "primary_actions": ["get_clipboard_text", "set_clipboard_text", "append_clipboard_text", "clear_clipboard", "get_clipboard_formats"],
    },

    # Control Hand
    "applications": {
        "kit": "control",
        "description": "Discover, open, elevate to admin, open file associations, and manage learned application memory.",
        "primary_actions": ["open_application", "open_application_as_admin", "open_file_with_default_app", "close_application", "restart_application", "list_known_applications"],
    },
    "windows": {
        "kit": "control",
        "description": "Enumerate windows, minimize, maximize, restore, foreground focus, resize, snap, and Always-on-Top.",
        "primary_actions": ["list_windows", "minimize_window", "maximize_window", "restore_window", "bring_to_foreground", "move_and_resize_window", "snap_window", "set_always_on_top"],
    },
    "processes": {
        "kit": "control",
        "description": "Inspect running processes, check active execution, kill processes, and inspect top RAM consumers.",
        "primary_actions": ["get_running_applications", "is_application_running", "kill_process", "get_top_processes"],
    },
    "installed_apps": {
        "kit": "control",
        "description": "Registry-based installed desktop software scanner, version lookup, and uninstall commands.",
        "primary_actions": ["list_installed_software", "get_app_version", "get_app_uninstall_command"],
    },

    # Storage Hand
    "filesystem": {
        "kit": "storage",
        "description": "List files, create folders, safe move, copy, rename, delete to Recycle Bin, head/tail, and folder size.",
        "primary_actions": ["list_files", "find_file_or_folder", "create_folder", "copy_file_or_folder", "move_file_or_folder", "rename_file_or_folder", "delete_file_or_folder", "read_file_head", "read_file_tail", "get_folder_size"],
    },
    "archive": {
        "kit": "storage",
        "description": "Create and extract Zip archives with Zip-Slip protection, create Tar/Tar.gz, and test integrity.",
        "primary_actions": ["create_zip", "extract_zip", "inspect_zip", "create_tar", "test_archive"],
    },
    "drives": {
        "kit": "storage",
        "description": "Inspect mounted disks, list removable USB drives, low space warnings, and safe USB ejection.",
        "primary_actions": ["list_drives", "get_removable_drives", "check_drive_space_warning", "eject_usb_drive"],
    },
    "hasher": {
        "kit": "storage",
        "description": "Cryptographic file hashes (MD5, SHA1, SHA256), checksum verification, text hashing, and file compare.",
        "primary_actions": ["hash_file", "verify_checksum", "hash_text", "compare_files"],
    },

    # Connectivity Hand
    "network": {
        "kit": "connectivity",
        "description": "Private local IP, public WAN IP, ping latency/loss checks, Wi-Fi adapter info, and internet status.",
        "primary_actions": ["get_network_info", "get_ip_address", "get_public_ip", "get_wifi_info", "is_connected_to_internet", "ping_host"],
    },
    "wifi_tools": {
        "kit": "connectivity",
        "description": "Scan Wi-Fi networks, list saved profiles, extract cleartext passwords, connect, and disconnect.",
        "primary_actions": ["scan_wifi_networks", "get_saved_wifi_profiles", "get_wifi_password", "connect_to_wifi", "disconnect_wifi", "delete_wifi_profile"],
    },
    "ports": {
        "kit": "connectivity",
        "description": "Inspect listening ports, identify process on port, kill port-blocking process, and remote port scan.",
        "primary_actions": ["get_listening_ports", "what_is_using_port", "is_port_free", "kill_port_process", "scan_remote_port"],
    },
    "browser": {
        "kit": "connectivity",
        "description": "Open default browser, launch incognito/private windows, route to specific browser, and batch tabs.",
        "primary_actions": ["open_url", "search_web", "open_website", "open_incognito", "open_with_browser", "open_multiple_urls", "get_default_browser", "open_youtube", "search_and_play_youtube", "control_youtube", "open_youtube_and_type"],
    },
    "power": {
        "kit": "connectivity",
        "description": "Battery status, lock PC, screen standby, sleep, hibernate, shutdown timers, and power scheme.",
        "primary_actions": ["get_battery_status", "lock_workstation", "turn_off_screen", "sleep_system", "hibernate_system", "schedule_shutdown", "schedule_restart", "cancel_shutdown", "get_active_power_plan"],
    },
    "settings": {
        "kit": "connectivity",
        "description": "Windows dark/light theme query & toggle, wallpaper get/set, and transparency effects toggle.",
        "primary_actions": ["get_windows_theme", "set_windows_theme", "get_wallpaper", "set_wallpaper", "set_transparency_effects"],
    },
    "services": {
        "kit": "connectivity",
        "description": "List Windows services, query service status, start, stop, restart, startup mode, and description.",
        "primary_actions": ["list_services", "get_service_status", "start_service", "stop_service", "restart_service", "set_service_startup", "get_service_description"],
    },
    "system_info": {
        "kit": "connectivity",
        "description": "CPU usage & cores/threads/clock, RAM load & capacity, disk space, GPU info, and motherboard BIOS.",
        "primary_actions": ["get_system_info", "get_cpu_usage", "get_cpu_details", "get_ram_usage", "get_disk_space", "get_gpu_info", "get_gpu_usage", "get_motherboard_info"],
    },
    "timer": {
        "kit": "connectivity",
        "description": "Background countdown timers with alert sound, Windows uptime duration, and precision stopwatches.",
        "primary_actions": ["start_countdown_timer", "list_active_timers", "get_uptime", "start_stopwatch", "lap_stopwatch", "stop_stopwatch"],
    },
    "healer": {
        "kit": "connectivity",
        "description": "Windows self-healing engine: RAM trimming, hung window recovery, DNS flush, port healing, and temp cache cleanup.",
        "primary_actions": ["auto_heal_system", "trim_all_memory", "trim_process_memory", "detect_hung_windows", "heal_network", "heal_stuck_ports", "heal_temp_cache"],
    },
}


# =============================================================================
# Registry Query & Execution APIs
# =============================================================================

def list_kits() -> dict:
    """Returns the 5 high-level Hand Kits and their constituent tool names."""
    return {
        "success": True,
        "kits": {
            kit_id: {
                "name": info["name"],
                "description": info["description"],
                "tool_count": len(info["tools"]),
                "tools": info["tools"],
            }
            for kit_id, info in HAND_KITS.items()
        }
    }


def get_kit(kit_name: str) -> dict:
    """Retrieves detailed catalog metadata for all tools within a specific Hand Kit."""
    norm_name = kit_name.strip().lower()
    if norm_name not in HAND_KITS:
        return {
            "success": False,
            "message": f"Unknown kit '{kit_name}'. Available kits: {list(HAND_KITS.keys())}"
        }

    kit_meta = HAND_KITS[norm_name]
    tools_in_kit = {}
    for t_name in kit_meta["tools"]:
        tools_in_kit[t_name] = TOOL_CATALOG.get(t_name, {})

    return {
        "success": True,
        "kit": norm_name,
        "name": kit_meta["name"],
        "description": kit_meta["description"],
        "tools": tools_in_kit
    }


def list_all_tools() -> dict:
    """Returns a comprehensive index of all 25 registered tools with their primary actions."""
    return {
        "success": True,
        "total_tools": len(TOOL_CATALOG),
        "tools": TOOL_CATALOG
    }


def get_tool_module(tool_name: str):
    """Dynamically loads and returns a tool module from tools/."""
    clean_name = tool_name.strip().lower()
    if clean_name not in TOOL_CATALOG:
        raise ValueError(f"Tool '{clean_name}' is not in the MIO inventory.")

    try:
        return importlib.import_module(f"agents.system_agent.tools.{clean_name}")
    except ImportError:
        return importlib.import_module(f"tools.{clean_name}")


def execute_action(tool_name: str, action_name: str, **kwargs) -> dict:
    """
    Direct Execution Gateway:
    Dynamically routes a request directly to the target tool and action without
    requiring hardcoded command strings.
    """
    clean_tool = tool_name.strip().lower()
    clean_action = action_name.strip().lower()

    if clean_tool not in TOOL_CATALOG:
        return {
            "success": False,
            "message": f"Tool '{tool_name}' not found in inventory. Available tools: {len(TOOL_CATALOG)}"
        }

    try:
        mod = get_tool_module(clean_tool)
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to load module for tool '{clean_tool}': {err}"
        }

    # Find the function on the module (case-insensitive)
    func = None
    for attr_name in dir(mod):
        if attr_name.lower() == clean_action and callable(getattr(mod, attr_name)):
            func = getattr(mod, attr_name)
            break

    if not func:
        return {
            "success": False,
            "message": f"Action '{action_name}' does not exist on tool '{clean_tool}'."
        }

    try:
        result = func(**kwargs)
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}
    except TypeError as err:
        return {
            "success": False,
            "message": f"Parameter mismatch calling '{clean_tool}.{clean_action}': {err}"
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Error executing '{clean_tool}.{clean_action}': {err}"
        }


# Convenient alias
execute_tool = execute_action


def execute_workflow(steps: list[dict]) -> dict:
    """
    Executes a sequential multi-step workflow across MIO's Hands.
    Each step should be a dictionary:
    {
        "tool": "browser",
        "action": "open_youtube",
        "args": {"query": "lofi", "timestamp": "2 minute"},
        "ignore_error": False,  # optional
        "delay": 0.5            # optional delay in seconds after step
    }
    """
    if not steps or not isinstance(steps, (list, tuple)):
        return {"success": False, "executed_steps": 0, "message": "Steps list cannot be empty."}

    import time
    results = []
    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            return {
                "success": False,
                "executed_steps": len(results),
                "total_steps": len(steps),
                "results": results,
                "message": f"Step #{idx} must be a dictionary."
            }

        tool = step.get("tool", "")
        action = step.get("action", "")
        args = step.get("args", {})
        ignore_err = step.get("ignore_error", False)
        delay = float(step.get("delay", 0))

        res = execute_action(tool, action, **args)
        results.append({
            "step": idx,
            "tool": tool,
            "action": action,
            "success": res.get("success", False),
            "result": res
        })

        if not res.get("success", False) and not ignore_err:
            return {
                "success": False,
                "failed_step": idx,
                "executed_steps": len(results),
                "total_steps": len(steps),
                "results": results,
                "message": f"Workflow failed at step #{idx} ({tool}.{action}): {res.get('message', 'Unknown error')}"
            }

        if delay > 0:
            time.sleep(delay)

    return {
        "success": True,
        "executed_steps": len(results),
        "total_steps": len(steps),
        "results": results,
        "message": f"Successfully executed all {len(results)} workflow step(s)."
    }


def get_schemas(kit_name: str = None) -> list[dict]:
    """
    Generates standard function calling schemas (OpenAI / Ollama / Gemini compatible)
    for all tools or tools within a designated Hand Kit.
    """
    selected_tools = (
        HAND_KITS[kit_name.lower()]["tools"]
        if kit_name and kit_name.lower() in HAND_KITS
        else list(TOOL_CATALOG.keys())
    )

    schemas = []
    for t_name in selected_tools:
        try:
            mod = get_tool_module(t_name)
        except Exception:
            continue

        actions = TOOL_CATALOG.get(t_name, {}).get("primary_actions", [])
        for act in actions:
            func = getattr(mod, act, None)
            if not func or not callable(func):
                continue

            doc = inspect.getdoc(func) or f"Executes {act} on {t_name}."
            sig = inspect.signature(func)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                param_type = "string"
                if param.annotation in (int, float):
                    param_type = "number"
                elif param.annotation is bool:
                    param_type = "boolean"
                elif param.annotation in (list, tuple):
                    param_type = "array"

                properties[param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}"
                }
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            schemas.append({
                "type": "function",
                "function": {
                    "name": f"{t_name}__{act}",
                    "description": doc.split("\n")[0].strip(),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })

    return schemas
