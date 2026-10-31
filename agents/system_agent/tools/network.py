import json
import re
import socket
import subprocess
import urllib.request


def get_ip_address() -> dict:
    """
    Retrieves the local LAN IPv4 address and hostname of this computer.
    """
    try:
        hostname = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()

        return {
            "success": True,
            "hostname": hostname,
            "ip": ip,
            "message": f"Local IP Address: {ip} (Hostname: {hostname})"
        }
    except Exception as err:
        return {
            "success": False,
            "ip": "127.0.0.1",
            "message": f"Failed to retrieve local IP: {err}"
        }


def get_public_ip() -> dict:
    """
    Retrieves the external WAN / public Internet IP address of this network.
    """
    endpoints = [
        "https://api.ipify.org",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com"
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MIO/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode("utf-8", errors="ignore").strip()
                match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", raw)
                if match:
                    ip = match.group(1)
                    return {
                        "success": True,
                        "public_ip": ip,
                        "source": url,
                        "message": f"Public Internet IP: {ip}"
                    }
        except Exception:
            continue

    return {
        "success": False,
        "public_ip": None,
        "message": "Could not determine public IP (no internet access or timeout)."
    }


def is_connected_to_internet() -> dict:
    """
    Checks if computer has active connectivity to the global internet.
    """
    hosts_to_test = [("8.8.8.8", 53), ("1.1.1.1", 53), ("www.google.com", 80)]
    connected = False
    responding_host = None

    for host, port in hosts_to_test:
        try:
            s = socket.create_connection((host, port), timeout=2.0)
            s.close()
            connected = True
            responding_host = host
            break
        except Exception:
            continue

    if connected:
        return {
            "success": True,
            "connected": True,
            "message": f"Internet is connected and active (verified via {responding_host})."
        }
    return {
        "success": True,
        "connected": False,
        "message": "Internet is disconnected (unable to reach external hosts)."
    }


def get_wifi_info() -> dict:
    """
    Retrieves connected Wi-Fi interface details (SSID, BSSID, Radio type, Signal percentage).
    """
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        ssid = None
        signal = None
        state = None
        radio = None

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SSID") and not line.startswith("BSSID"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    ssid = parts[1].strip()
            elif line.startswith("Signal"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    signal = parts[1].strip()
            elif line.startswith("State"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    state = parts[1].strip()
            elif line.startswith("Radio type"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    radio = parts[1].strip()

        if ssid and state == "connected":
            return {
                "success": True,
                "connected": True,
                "ssid": ssid,
                "signal": signal,
                "radio": radio,
                "message": f"Connected to Wi-Fi '{ssid}' (Signal: {signal}, {radio})."
            }
        elif state:
            return {
                "success": True,
                "connected": False,
                "ssid": None,
                "message": f"Wi-Fi is {state} (not connected to any network)."
            }
        return {
            "success": True,
            "connected": False,
            "ssid": None,
            "message": "No active Wi-Fi interface found (wired Ethernet or Wi-Fi disabled)."
        }
    except Exception as err:
        return {
            "success": False,
            "message": f"Failed to inspect Wi-Fi interface: {err}"
        }


def ping_host(target: str, count: int = 2) -> dict:
    """
    Sends safe ICMP ping requests to verify network latency and host reachability.
    """
    if not target or not isinstance(target, str):
        return {"success": False, "message": "Host target is required."}

    clean_target = target.strip()
    if not re.match(r"^[a-zA-Z0-9\.\-_:]+$", clean_target):
        return {"success": False, "message": f"Invalid host name or IP address: '{clean_target}'."}

    num = max(1, min(10, int(count)))
    try:
        output = subprocess.check_output(
            ["ping", "-n", str(num), clean_target],
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        avg_ms = None
        loss_pct = 0
        match_time = re.search(r"Average\s*=\s*(\d+)ms", output)
        if match_time:
            avg_ms = int(match_time.group(1))

        match_loss = re.search(r"\((\d+)%\s*loss\)", output)
        if match_loss:
            loss_pct = int(match_loss.group(1))

        reachable = (loss_pct < 100)
        status_msg = f"Host '{clean_target}' is reachable" if reachable else f"Host '{clean_target}' is unreachable (100% packet loss)"
        if avg_ms is not None:
            status_msg += f" (Latency: {avg_ms} ms, {loss_pct}% loss)."
        else:
            status_msg += f" ({loss_pct}% loss)."

        return {
            "success": True,
            "target": clean_target,
            "reachable": reachable,
            "avg_ms": avg_ms,
            "average_ms": avg_ms,
            "packet_loss_percent": loss_pct,
            "message": status_msg
        }
    except Exception as err:
        return {
            "success": False,
            "target": clean_target,
            "reachable": False,
            "message": f"Ping failed for '{clean_target}': {err}"
        }


def get_network_info() -> dict:
    """
    Provides a comprehensive overview of local IP, public IP, Wi-Fi status, and internet reachability.
    """
    local = get_ip_address()
    pub = get_public_ip()
    wifi = get_wifi_info()
    inet = is_connected_to_internet()

    lines = [
        f"Local IP: {local.get('ip')} ({local.get('hostname')})",
        f"Public IP: {pub.get('public_ip', 'Unavailable')}",
        f"Internet: {'Connected' if inet.get('connected') else 'Disconnected'}",
    ]
    if wifi.get("connected"):
        lines.append(f"Wi-Fi: {wifi.get('ssid')} ({wifi.get('signal')})")
    else:
        lines.append("Wi-Fi: Disconnected")

    return {
        "success": True,
        "local_ip": local.get("ip"),
        "public_ip": pub.get("public_ip"),
        "hostname": local.get("hostname"),
        "wifi": wifi,
        "internet_connected": inet.get("connected"),
        "message": "Network Overview:\n" + "\n".join(f"- {l}" for l in lines)
    }
