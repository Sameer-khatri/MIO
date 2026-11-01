import subprocess
import re


def get_saved_wifi_profiles() -> dict:
    """
    Retrieves a list of all Wi-Fi profiles saved on this Windows machine.
    """
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "profiles"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        profiles = []
        for line in output.splitlines():
            if "All User Profile" in line or "User Profile" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    p = parts[1].strip()
                    if p:
                        profiles.append(p)

        return {
            "success": True,
            "count": len(profiles),
            "profiles": profiles,
            "message": f"Found {len(profiles)} saved Wi-Fi profile(s): {', '.join(profiles[:10])}{' ...' if len(profiles) > 10 else ''}"
        }
    except Exception as err:
        return {
            "success": False,
            "profiles": [],
            "message": f"Failed to retrieve Wi-Fi profiles: {err}"
        }


def get_wifi_password(ssid: str) -> dict:
    """
    Retrieves the saved cleartext Wi-Fi password for a specific network SSID.
    """
    if not ssid or not isinstance(ssid, str):
        return {"success": False, "message": "Please specify a Wi-Fi SSID name."}

    clean_ssid = ssid.strip()
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "profile", f"name={clean_ssid}", "key=clear"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        password = None
        for line in output.splitlines():
            if "Key Content" in line or "Key content" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    password = parts[1].strip()
                    break

        if password:
            return {
                "success": True,
                "ssid": clean_ssid,
                "password": password,
                "message": f"Wi-Fi Password for '{clean_ssid}': {password}"
            }
        else:
            if "not found" in output.lower():
                return {
                    "success": False,
                    "ssid": clean_ssid,
                    "message": f"Wi-Fi network '{clean_ssid}' not found in saved profiles."
                }
            return {
                "success": True,
                "ssid": clean_ssid,
                "password": None,
                "message": f"Wi-Fi network '{clean_ssid}' has no saved password (open network or 802.1X)."
            }
    except Exception as err:
        return {
            "success": False,
            "ssid": clean_ssid,
            "message": f"Failed to retrieve password for '{clean_ssid}': {err}"
        }


def scan_wifi_networks() -> dict:
    """
    Scans for nearby wireless networks currently in range.
    """
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "networks"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        networks = []
        current_ssid = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SSID ") and ":" in line:
                parts = line.split(":", 1)
                ssid_name = parts[1].strip() if len(parts) > 1 else ""
                current_ssid = ssid_name or "<Hidden SSID>"
            elif line.startswith("Signal") and ":" in line:
                sig_str = line.split(":", 1)[1].strip()
                if current_ssid:
                    networks.append({"ssid": current_ssid, "signal": sig_str})
                    current_ssid = None
            elif line.startswith("Authentication") and ":" in line:
                if current_ssid and not any(n["ssid"] == current_ssid for n in networks):
                    networks.append({"ssid": current_ssid, "signal": "N/A"})
                    current_ssid = None

        unique_networks = list({n["ssid"]: n for n in networks}.values())

        return {
            "success": True,
            "count": len(unique_networks),
            "networks": unique_networks,
            "message": f"Discovered {len(unique_networks)} nearby Wi-Fi network(s)."
        }
    except Exception as err:
        return {
            "success": False,
            "networks": [],
            "message": f"Failed to scan Wi-Fi networks: {err}"
        }


def connect_to_wifi(ssid: str) -> dict:
    """
    Connects to a known saved Wi-Fi network profile.
    """
    clean_ssid = ssid.strip()
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "connect", f"name={clean_ssid}"],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {
            "success": "Connection request was completed" in output or "completed" in output.lower(),
            "ssid": clean_ssid,
            "message": f"Connecting to '{clean_ssid}': {output.strip()}"
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to connect to '{clean_ssid}': {err}"}


def disconnect_wifi() -> dict:
    """Disconnects from currently connected Wi-Fi network."""
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "disconnect"],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {"success": True, "message": "Wi-Fi disconnected."}
    except Exception as err:
        return {"success": False, "message": f"Failed to disconnect Wi-Fi: {err}"}


def delete_wifi_profile(ssid: str) -> dict:
    """Deletes/forgets a saved Wi-Fi profile."""
    clean_ssid = ssid.strip()
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "delete", "profile", f"name={clean_ssid}"],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {"success": True, "message": f"Forgot Wi-Fi network '{clean_ssid}'."}
    except Exception as err:
        return {"success": False, "message": f"Failed to delete Wi-Fi profile: {err}"}


def flush_dns_cache() -> dict:
    """
    Flushes the Windows DNS Resolver Cache (ipconfig /flushdns) to fix internet connectivity
    and stale domain lookups.
    """
    try:
        output = subprocess.check_output(
            ["ipconfig", "/flushdns"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return {
            "success": True,
            "message": "Successfully flushed the Windows DNS Resolver Cache."
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to flush DNS cache: {err}"
        }
