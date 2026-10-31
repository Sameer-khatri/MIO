import csv
import io
import re
import socket
import subprocess


def _get_process_map() -> dict[int, str]:
    """Builds a PID -> process name lookup table using tasklist."""
    proc_map = {}
    try:
        out = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        reader = csv.reader(io.StringIO(out))
        for row in reader:
            if len(row) >= 2:
                name = row[0].strip()
                try:
                    pid = int(row[1].strip())
                    proc_map[pid] = name
                except ValueError:
                    continue
    except Exception:
        pass
    return proc_map


def get_listening_ports() -> dict:
    """
    Returns all actively listening TCP and UDP ports on the system.
    """
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.DEVNULL,
            timeout=8
        )
        proc_map = _get_process_map()
        ports = []
        seen = set()

        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) >= 4 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                local_addr = parts[1]
                pid_str = parts[-1]
                try:
                    pid = int(pid_str)
                except ValueError:
                    pid = 0

                # Extract port from local_addr (e.g. 0.0.0.0:8080 or [::]:8080)
                port_match = re.search(r":(\d+)$", local_addr)
                if port_match:
                    port_num = int(port_match.group(1))
                    key = ("TCP", port_num, pid)
                    if key not in seen:
                        seen.add(key)
                        proc_name = proc_map.get(pid, f"PID {pid}" if pid > 0 else "System")
                        ports.append({
                            "protocol": "TCP",
                            "address": local_addr,
                            "port": port_num,
                            "pid": pid,
                            "process_name": proc_name
                        })

        ports.sort(key=lambda x: x["port"])

        if ports:
            summary_lines = [f"- Port {p['port']} (TCP) — {p['process_name']} (PID {p['pid']})" for p in ports[:25]]
            if len(ports) > 25:
                summary_lines.append(f"... and {len(ports) - 25} more ports.")
            msg = f"Listening Ports ({len(ports)} found):\n" + "\n".join(summary_lines)
        else:
            msg = "No active listening ports detected."

        return {
            "success": True,
            "count": len(ports),
            "ports": ports,
            "message": msg
        }
    except Exception as err:
        return {
            "success": False,
            "count": 0,
            "ports": [],
            "message": f"Failed to retrieve listening ports: {err}"
        }


def what_is_using_port(port: int | str) -> dict:
    """
    Identifies which application/PID is using a specific port.
    """
    try:
        port_num = int(str(port).strip())
    except (ValueError, TypeError):
        return {
            "success": False,
            "port": 0,
            "in_use": False,
            "message": f"Invalid port number: '{port}'."
        }

    listening_result = get_listening_ports()
    if not listening_result.get("success"):
        return {
            "success": False,
            "port": port_num,
            "in_use": False,
            "message": listening_result.get("message", "Failed to query network ports.")
        }

    matched = [p for p in listening_result.get("ports", []) if p["port"] == port_num]

    if matched:
        first = matched[0]
        proc = first["process_name"]
        pid = first["pid"]
        proto = first["protocol"]
        return {
            "success": True,
            "port": port_num,
            "in_use": True,
            "protocol": proto,
            "pid": pid,
            "process_name": proc,
            "message": f"Port {port_num} is in use by {proc} (PID {pid}, {proto})."
        }

    return {
        "success": True,
        "port": port_num,
        "in_use": False,
        "pid": None,
        "process_name": None,
        "message": f"Port {port_num} is not in use."
    }


def is_port_free(port: int | str) -> dict:
    """
    Checks if a local TCP port is available to be bound.
    """
    try:
        port_num = int(str(port).strip())
        if port_num < 1 or port_num > 65535:
            raise ValueError()
    except (ValueError, TypeError):
        return {
            "success": False,
            "port": 0,
            "free": False,
            "message": f"Invalid port number: '{port}'. Valid ports are 1–65535."
        }

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.bind(("127.0.0.1", port_num))
        is_free = True
    except OSError:
        is_free = False
    finally:
        sock.close()

    if is_free:
        return {
            "success": True,
            "port": port_num,
            "free": True,
            "message": f"Port {port_num} is free."
        }
    else:
        # Check what is using it for helpful context
        detail = what_is_using_port(port_num)
        proc_str = f" by {detail.get('process_name')}" if detail.get("in_use") and detail.get("process_name") else ""
        return {
            "success": True,
            "port": port_num,
            "free": False,
            "message": f"Port {port_num} is currently in use{proc_str}."
        }
