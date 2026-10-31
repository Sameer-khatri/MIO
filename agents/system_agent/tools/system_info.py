import ctypes
import os
import platform
import shutil
import subprocess
import time

try:
    from ctypes import wintypes
except ImportError:
    wintypes = None


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", ctypes.c_uint),
        ("dwHighDateTime", ctypes.c_uint),
    ]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


def get_cpu_usage() -> dict:
    """Reads current system-wide CPU usage percentage."""
    try:
        kernel32 = ctypes.windll.kernel32
        idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
        if not kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1)):
            raise RuntimeError("GetSystemTimes call failed.")

        time.sleep(0.1)

        idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
        if not kernel32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2)):
            raise RuntimeError("GetSystemTimes call failed.")

        idle = _filetime_to_int(idle2) - _filetime_to_int(idle1)
        kernel = _filetime_to_int(kernel2) - _filetime_to_int(kernel1)
        user = _filetime_to_int(user2) - _filetime_to_int(user1)
        total = kernel + user

        if total <= 0:
            pct = 0.0
        else:
            pct = round(((total - idle) / total) * 100.0, 1)
            pct = max(0.0, min(100.0, pct))

        return {
            "success": True,
            "cpu_usage_percent": pct,
            "message": f"CPU Usage: {pct}%"
        }
    except Exception as err:
        return {
            "success": False,
            "cpu_usage_percent": 0.0,
            "message": f"Failed to retrieve CPU usage: {err}"
        }


def get_ram_usage() -> dict:
    """Reads total, used, and available physical RAM."""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            raise RuntimeError("GlobalMemoryStatusEx call failed.")

        total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
        avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
        used_gb = round(total_gb - avail_gb, 2)
        load_pct = int(stat.dwMemoryLoad)

        return {
            "success": True,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "available_gb": avail_gb,
            "usage_percent": load_pct,
            "message": f"RAM Usage: {used_gb} GB / {total_gb} GB ({load_pct}%)"
        }
    except Exception as err:
        return {
            "success": False,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "available_gb": 0.0,
            "usage_percent": 0,
            "message": f"Failed to retrieve RAM usage: {err}"
        }


def get_disk_space(path: str = "C:\\") -> dict:
    """Reads disk space information for the target drive or directory."""
    try:
        clean_path = path.strip() if path else "C:\\"
        if len(clean_path) == 1 and clean_path.isalpha():
            clean_path = f"{clean_path.upper()}:\\"

        usage = shutil.disk_usage(clean_path)
        total_gb = round(usage.total / (1024 ** 3), 1)
        used_gb = round(usage.used / (1024 ** 3), 1)
        free_gb = round(usage.free / (1024 ** 3), 1)
        pct = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0.0

        return {
            "success": True,
            "drive": clean_path,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "usage_percent": pct,
            "message": f"Disk ({clean_path}): {used_gb} GB used / {total_gb} GB total ({free_gb} GB free, {pct}% used)"
        }
    except Exception as err:
        return {
            "success": False,
            "drive": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "usage_percent": 0.0,
            "message": f"Failed to read disk space for '{path}': {err}"
        }


def get_gpu_info() -> dict:
    """Reads installed GPU model name and total video memory."""
    # 1. Try nvidia-smi if present
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5
            ).strip()
            if out:
                parts = [p.strip() for p in out.split(",")]
                name = parts[0]
                total_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                total_gb = round(total_mb / 1024, 2)
                return {
                    "success": True,
                    "name": name,
                    "memory_total_gb": total_gb,
                    "vendor": "NVIDIA",
                    "message": f"GPU: {name} ({total_gb} GB VRAM)" if total_gb > 0 else f"GPU: {name}"
                }
        except Exception:
            pass

    # 2. Fallback to PowerShell Win32_VideoController
    try:
        ps_cmd = "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ', '"
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5
        ).strip()
        if out:
            return {
                "success": True,
                "name": out,
                "memory_total_gb": 0.0,
                "vendor": "Unknown",
                "message": f"GPU: {out}"
            }
    except Exception:
        pass

    return {
        "success": False,
        "name": "",
        "memory_total_gb": 0.0,
        "vendor": "Unknown",
        "message": "No GPU information found."
    }


def get_gpu_usage() -> dict:
    """Reads GPU utilization percentage and VRAM usage."""
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5
            ).strip()
            if out:
                parts = [p.strip() for p in out.split(",")]
                name = parts[0]
                gpu_util = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                mem_used = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                mem_total = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                used_gb = round(mem_used / 1024, 2)
                total_gb = round(mem_total / 1024, 2)

                return {
                    "success": True,
                    "name": name,
                    "gpu_usage_percent": gpu_util,
                    "memory_used_gb": used_gb,
                    "memory_total_gb": total_gb,
                    "message": f"GPU Usage ({name}): {gpu_util}% | VRAM: {used_gb} GB / {total_gb} GB"
                }
        except Exception as err:
            return {
                "success": False,
                "gpu_usage_percent": 0,
                "message": f"Failed to read GPU usage: {err}"
            }

    # If no nvidia-smi, check general GPU availability
    info = get_gpu_info()
    if info.get("success"):
        return {
            "success": True,
            "name": info.get("name"),
            "gpu_usage_percent": 0,
            "message": f"GPU: {info.get('name')} (live utilization metrics require NVIDIA drivers)"
        }

    return {
        "success": False,
        "gpu_usage_percent": 0,
        "message": "GPU utilization monitor unavailable."
    }


def get_system_info() -> dict:
    """Aggregates comprehensive system facts (OS, CPU, RAM, Disk, GPU)."""
    cpu_res = get_cpu_usage()
    ram_res = get_ram_usage()
    disk_res = get_disk_space("C:\\")
    gpu_res = get_gpu_info()

    os_info = f"{platform.system()} {platform.release()} (Build {platform.version()})"
    cpu_model = platform.processor() or "Unknown CPU"

    lines = [
        f"OS: {os_info}",
        f"Processor: {cpu_model}",
        f"CPU Load: {cpu_res.get('cpu_usage_percent', 0)}%",
        f"RAM: {ram_res.get('used_gb', 0)} GB / {ram_res.get('total_gb', 0)} GB ({ram_res.get('usage_percent', 0)}%)",
        f"Disk (C:): {disk_res.get('used_gb', 0)} GB / {disk_res.get('total_gb', 0)} GB ({disk_res.get('free_gb', 0)} GB free)",
    ]
    if gpu_res.get("success"):
        lines.append(f"GPU: {gpu_res.get('name')}")

    return {
        "success": True,
        "os": os_info,
        "processor": cpu_model,
        "cpu": cpu_res,
        "ram": ram_res,
        "disk": disk_res,
        "gpu": gpu_res,
        "message": "\n".join(lines)
    }
