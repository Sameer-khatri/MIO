import re
import socket
import subprocess


def _get_process_map() -> dict[int, str]:
    """
    Builds a map of {PID: process_name} using Windows tasklist.
    """
    proc_map = {}
    try:
        output = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip(' "') for p in line.split('","')]
            if len(parts) >= 2:
                name = parts[0]
                try:
                    pid = int(parts[1])
                    proc_map[pid] = name
                except ValueError:
                    pass
    except Exception:
        pass
    return proc_map


def get_listening_ports() -> dict:
    """
    Finds all active TCP and UDP listening ports on this machine and maps them
    to their owning process names and PIDs.
    """
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        proc_map = _get_process_map()
        ports_seen = {}

        for line in output.splitlines():
            line = line.strip()
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    proto = parts[0]
                    local_addr = parts[1]
                    pid_str = parts[4]

                    port_match = re.search(r":(\d+)$", local_addr)
                    if port_match:
                        port_num = int(port_match.group(1))
                        try:
                            pid_num = int(pid_str)
                        except ValueError:
                            pid_num = 0

                        proc_name = proc_map.get(pid_num, "Unknown Process")

                        if port_num not in ports_seen:
                            ports_seen[port_num] = {
                                "port": port_num,
                                "protocol": proto,
                                "pid": pid_num,
                                "process_name": proc_name,
                                "address": local_addr
                            }

        sorted_ports = sorted(ports_seen.values(), key=lambda x: x["port"])

        return {
            "success": True,
            "count": len(sorted_ports),
            "ports": sorted_ports,
            "message": f"Found {len(sorted_ports)} listening port(s): " + ", ".join(f":{p['port']} ({p['process_name']})" for p in sorted_ports[:10]) + (" ..." if len(sorted_ports) > 10 else "")
        }
    except Exception as err:
        return {
            "success": False,
            "ports": [],
            "message": f"Failed to inspect network ports: {err}"
        }


def what_is_using_port(port: int | str) -> dict:
    """
    Identifies which process and PID is actively using a given port number.
    """
    try:
        port_num = int(port)
        if not (1 <= port_num <= 65535):
            return {"success": False, "message": f"Port number out of range (1-65535): {port_num}."}
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid port number: '{port}'."}

    all_ports = get_listening_ports()
    if not all_ports.get("success"):
        return all_ports

    for p in all_ports.get("ports", []):
        if p["port"] == port_num:
            return {
                "success": True,
                "in_use": True,
                "port": port_num,
                "process_name": p.get("process_name", "Unknown"),
                "pid": p.get("pid", 0),
                "protocol": p.get("protocol", "TCP"),
                "address": p.get("address", "0.0.0.0"),
                "message": f"Port {port_num} is IN USE by '{p.get('process_name', 'Unknown')}' (PID: {p.get('pid', 0)})."
            }

    return {
        "success": True,
        "in_use": False,
        "port": port_num,
        "process_name": None,
        "pid": None,
        "message": f"Port {port_num} is FREE (no active listening process)."
    }


def is_port_free(port: int | str) -> dict:
    """
    Checks whether a port is free to bind.
    """
    try:
        port_num = int(port)
        if not (1 <= port_num <= 65535):
            return {"success": False, "message": f"Port number out of range (1-65535): {port_num}."}
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid port number: '{port}'."}

    res = what_is_using_port(port)
    if not res.get("success"):
        return res

    free = not res.get("in_use", True)
    return {
        "success": True,
        "port": res.get("port"),
        "free": free,
        "message": f"Port {res.get('port')} is {'FREE' if free else 'BUSY'}."
    }


def kill_port_process(port: int | str) -> dict:
    """
    Kills the process occupying a specific port number to resolve port collision errors.
    """
    usage = what_is_using_port(port)
    if not usage.get("success"):
        return usage

    if not usage.get("in_use"):
        return {
            "success": True,
            "port": usage.get("port"),
            "message": f"Port {usage.get('port')} is already free."
        }

    pid = usage.get("pid")
    pname = usage.get("process_name")
    if not pid or pid == 0:
        return {"success": False, "message": f"Cannot kill system process on port {usage.get('port')}."}

    try:
        subprocess.check_output(["taskkill", "/F", "/PID", str(pid)], stderr=subprocess.STDOUT)
        return {
            "success": True,
            "port": usage.get("port"),
            "pid": pid,
            "process_name": pname,
            "message": f"Successfully killed '{pname}' (PID: {pid}) occupying port {usage.get('port')}."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to terminate process on port {usage.get('port')}: {err}"}


def scan_remote_port(host: str, port: int, timeout_sec: float = 1.0) -> dict:
    """
    Probes whether a port is open on a target host.
    """
    try:
        p_num = int(port)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid port: {port}"}

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout_sec)
    try:
        s.connect((host, p_num))
        s.close()
        return {
            "success": True,
            "host": host,
            "port": p_num,
            "open": True,
            "is_open": True,
            "message": f"{host}:{p_num} is OPEN."
        }
    except Exception:
        return {
            "success": True,
            "host": host,
            "port": p_num,
            "open": False,
            "is_open": False,
            "message": f"{host}:{p_num} is CLOSED or filtered."
        }
