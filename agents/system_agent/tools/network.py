import re
import socket
import subprocess


def is_connected_to_internet(timeout: float = 2.0) -> dict:
    """
    Checks if the local machine has active internet connectivity by testing DNS endpoints.
    """
    test_endpoints = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("208.67.222.222", 53), # OpenDNS
    ]
    for ip, port in test_endpoints:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((ip, port))
            sock.close()
            return {
                "success": True,
                "connected": True,
                "message": "Yes, you are connected to the internet."
            }
        except OSError:
            sock.close()
            continue

    return {
        "success": True,
        "connected": False,
        "message": "No, there is no active internet connection detected."
    }


def get_wifi_info() -> dict:
    """
    Retrieves Wi-Fi adapter state, connected SSID, and signal quality via netsh.
    """
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.DEVNULL,
            timeout=5
        )

        state_match = re.search(r"^\s*State\s*:\s*(.+)$", out, re.M)
        ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.M)
        signal_match = re.search(r"^\s*Signal\s*:\s*(.+)$", out, re.M)
        radio_match = re.search(r"^\s*Radio type\s*:\s*(.+)$", out, re.M)

        state = state_match.group(1).strip() if state_match else "disconnected"
        ssid = ssid_match.group(1).strip() if ssid_match else ""
        signal = signal_match.group(1).strip() if signal_match else ""
        radio = radio_match.group(1).strip() if radio_match else ""

        is_connected = state.lower() == "connected"

        lines = [f"Wi-Fi State: {state}"]
        if ssid:
            lines.append(f"Network (SSID): {ssid}")
        if signal:
            lines.append(f"Signal Strength: {signal}")
        if radio:
            lines.append(f"Radio Type: {radio}")

        return {
            "success": True,
            "connected": is_connected,
            "state": state,
            "ssid": ssid,
            "signal": signal,
            "radio_type": radio,
            "message": "\n".join(lines) if is_connected else "Wi-Fi is disconnected or unavailable."
        }
    except Exception as err:
        return {
            "success": False,
            "connected": False,
            "state": "unknown",
            "ssid": "",
            "signal": "",
            "radio_type": "",
            "message": f"Failed to retrieve Wi-Fi info: {err}"
        }


def get_ip_address() -> dict:
    """
    Retrieves local hostname and active IPv4 addresses.
    """
    try:
        hostname = socket.gethostname()
        ip_list = []
        try:
            _, _, ips = socket.gethostbyname_ex(hostname)
            ip_list = [ip for ip in ips if not ip.startswith("127.")]
        except Exception:
            pass

        if not ip_list:
            # Fallback test socket to detect primary outbound IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("10.255.255.255", 1))
                ip_list = [sock.getsockname()[0]]
            except Exception:
                ip_list = ["127.0.0.1"]
            finally:
                sock.close()

        primary_ip = ip_list[0] if ip_list else "Unknown"

        lines = [f"Host: {hostname}"]
        if len(ip_list) == 1:
            lines.append(f"Local IP: {primary_ip}")
        else:
            lines.append(f"Primary IP: {primary_ip}")
            lines.append("All Local IPs: " + ", ".join(ip_list))

        return {
            "success": True,
            "hostname": hostname,
            "primary_ip": primary_ip,
            "ips": ip_list,
            "message": "\n".join(lines)
        }
    except Exception as err:
        return {
            "success": False,
            "hostname": "",
            "primary_ip": "",
            "ips": [],
            "message": f"Failed to retrieve IP address: {err}"
        }


def get_network_info() -> dict:
    """
    Aggregates IP configuration, Wi-Fi status, and internet reachability.
    """
    ip_res = get_ip_address()
    wifi_res = get_wifi_info()
    net_res = is_connected_to_internet()

    lines = [
        f"Host: {ip_res.get('hostname', 'Unknown')}",
        f"Local IP: {ip_res.get('primary_ip', 'Unknown')}",
        f"Wi-Fi: {wifi_res.get('ssid', 'Disconnected') or 'Disconnected'} ({wifi_res.get('signal', 'N/A')})",
        f"Internet: {'Connected' if net_res.get('connected') else 'Offline'}"
    ]

    return {
        "success": True,
        "ip_info": ip_res,
        "wifi_info": wifi_res,
        "internet": net_res,
        "message": "\n".join(lines)
    }


def ping_host(host: str, count: int = 2) -> dict:
    """
    Pings a target host safely without shell invocation.
    Validates host against strict hostname/IP pattern to prevent injection.
    """
    if not host or not isinstance(host, str):
        return {
            "success": False,
            "host": "",
            "message": "Invalid host specified."
        }

    clean_host = host.strip().lower()

    # Strict hostname/IP validation
    if not re.match(r"^[a-zA-Z0-9.-]+$", clean_host) or clean_host.startswith("-") or clean_host.startswith("."):
        return {
            "success": False,
            "host": clean_host,
            "message": f"Invalid host format: '{clean_host}'. Only valid hostnames or IP addresses allowed."
        }

    safe_count = max(1, min(10, count))

    try:
        out = subprocess.check_output(
            ["ping", "-n", str(safe_count), clean_host],
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.STDOUT,
            timeout=10
        )

        loss_match = re.search(r"(\d+)%\s*loss", out, re.I)
        loss_pct = int(loss_match.group(1)) if loss_match else (100 if "timed out" in out.lower() or "unreachable" in out.lower() else 0)

        avg_match = re.search(r"Average\s*=\s*(\d+)ms", out, re.I)
        avg_ms = int(avg_match.group(1)) if avg_match else None

        reachable = loss_pct < 100

        if reachable:
            speed_str = f", average latency {avg_ms}ms" if avg_ms is not None else ""
            msg = f"Ping to {clean_host} succeeded ({loss_pct}% loss{speed_str})."
        else:
            msg = f"Ping to {clean_host} failed (100% packet loss / unreachable)."

        return {
            "success": True,
            "host": clean_host,
            "reachable": reachable,
            "loss_percent": loss_pct,
            "average_ms": avg_ms,
            "message": msg
        }
    except subprocess.TimeoutExpired:
        return {
            "success": True,
            "host": clean_host,
            "reachable": False,
            "loss_percent": 100,
            "average_ms": None,
            "message": f"Ping to {clean_host} timed out."
        }
    except Exception as err:
        return {
            "success": False,
            "host": clean_host,
            "reachable": False,
            "loss_percent": 100,
            "average_ms": None,
            "message": f"Failed to ping '{clean_host}': {err}"
        }
