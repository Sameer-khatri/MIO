import subprocess
import re


def list_services(filter_name: str = "") -> dict:
    """
    Lists Windows services, their display names, and current states (RUNNING, STOPPED).
    Optionally filters by service name or display name.
    """
    try:
        output = subprocess.check_output(
            ["sc.exe", "query", "type=", "service", "state=", "all"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        services = []
        curr_name = ""
        curr_display = ""
        curr_state = ""

        filter_lower = filter_name.strip().lower()

        for line in output.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("SERVICE_NAME:"):
                curr_name = line_strip.split(":", 1)[1].strip()
            elif line_strip.startswith("DISPLAY_NAME:"):
                curr_display = line_strip.split(":", 1)[1].strip()
            elif line_strip.startswith("STATE"):
                parts = line_strip.split(":", 1)[1].strip().split()
                curr_state = parts[1] if len(parts) > 1 else parts[0]

                if curr_name:
                    if not filter_lower or (filter_lower in curr_name.lower() or filter_lower in curr_display.lower()):
                        services.append({
                            "name": curr_name,
                            "display_name": curr_display,
                            "state": curr_state
                        })
                    curr_name = ""
                    curr_display = ""
                    curr_state = ""

        return {
            "success": True,
            "count": len(services),
            "services": services,
            "message": f"Found {len(services)} service(s)."
        }
    except Exception as err:
        return {
            "success": False,
            "services": [],
            "message": f"Failed to list services: {err}"
        }


def get_service_status(service_name: str) -> dict:
    """
    Retrieves the status of a specific Windows service.
    """
    if not service_name or not isinstance(service_name, str):
        return {"success": False, "message": "Service name is required."}

    clean_name = service_name.strip()
    try:
        output = subprocess.check_output(
            ["sc.exe", "query", clean_name],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        state = "UNKNOWN"
        for line in output.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("STATE"):
                parts = line_strip.split(":", 1)[1].strip().split()
                state = parts[1] if len(parts) > 1 else parts[0]
                break

        is_running = (state.upper() == "RUNNING")
        return {
            "success": True,
            "name": clean_name,
            "state": state,
            "running": is_running,
            "message": f"Service '{clean_name}' is {state}."
        }
    except Exception as err:
        return {
            "success": False,
            "name": clean_name,
            "running": False,
            "message": f"Service '{clean_name}' not found or inaccessible: {err}"
        }


def start_service(service_name: str) -> dict:
    """Starts a Windows service."""
    if not service_name or not isinstance(service_name, str):
        return {"success": False, "message": "Service name is required."}

    clean_name = service_name.strip()
    try:
        output = subprocess.check_output(
            ["sc.exe", "start", clean_name],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {
            "success": True,
            "name": clean_name,
            "message": f"Start signal sent to service '{clean_name}'. Output: {output.strip()}"
        }
    except subprocess.CalledProcessError as err:
        return {
            "success": False,
            "name": clean_name,
            "message": f"Failed to start '{clean_name}': {err.output.strip() if err.output else err}"
        }


def stop_service(service_name: str) -> dict:
    """Stops a running Windows service."""
    if not service_name or not isinstance(service_name, str):
        return {"success": False, "message": "Service name is required."}

    clean_name = service_name.strip()
    try:
        output = subprocess.check_output(
            ["sc.exe", "stop", clean_name],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {
            "success": True,
            "name": clean_name,
            "message": f"Stop signal sent to service '{clean_name}'. Output: {output.strip()}"
        }
    except subprocess.CalledProcessError as err:
        return {
            "success": False,
            "name": clean_name,
            "message": f"Failed to stop '{clean_name}': {err.output.strip() if err.output else err}"
        }


def restart_service(service_name: str) -> dict:
    """Restarts a Windows service by issuing stop then start."""
    stop_res = stop_service(service_name)
    start_res = start_service(service_name)
    return {
        "success": start_res.get("success", False),
        "name": service_name,
        "message": f"Restarted '{service_name}'." if start_res.get("success") else f"Stop: {stop_res.get('message')} | Start: {start_res.get('message')}"
    }
