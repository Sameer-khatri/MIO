import ctypes
import json
import os
import platform
import shutil
import subprocess
import time
from ctypes import wintypes

try:
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    kernel32 = None

_last_idle_time = 0
_last_kernel_time = 0
_last_user_time = 0
_last_sample_timestamp = 0.0


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]

    def to_uint64(self) -> int:
        return (self.dwHighDateTime << 32) | self.dwLowDateTime


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def get_cpu_usage() -> dict:
    """Calculates instantaneous CPU usage percentage using GetSystemTimes."""
    global _last_idle_time, _last_kernel_time, _last_user_time, _last_sample_timestamp

    if not kernel32:
        return {"success": False, "cpu_usage_percent": 0.0, "message": "kernel32 is unavailable."}

    idle_ft = FILETIME()
    kernel_ft = FILETIME()
    user_ft = FILETIME()

    try:
        if not kernel32.GetSystemTimes(ctypes.byref(idle_ft), ctypes.byref(kernel_ft), ctypes.byref(user_ft)):
            return {"success": False, "cpu_usage_percent": 0.0, "message": "Failed to read system times."}

        curr_idle = idle_ft.to_uint64()
        curr_kernel = kernel_ft.to_uint64()
        curr_user = user_ft.to_uint64()
        curr_ts = time.time()

        if _last_sample_timestamp == 0.0 or (curr_ts - _last_sample_timestamp) > 10.0:
            time.sleep(0.08)
            kernel32.GetSystemTimes(ctypes.byref(idle_ft), ctypes.byref(kernel_ft), ctypes.byref(user_ft))
            t1_idle, t1_kernel, t1_user = idle_ft.to_uint64(), kernel_ft.to_uint64(), user_ft.to_uint64()

            delta_idle = t1_idle - curr_idle
            delta_kernel = t1_kernel - curr_kernel
            delta_user = t1_user - curr_user

            _last_idle_time = t1_idle
            _last_kernel_time = t1_kernel
            _last_user_time = t1_user
            _last_sample_timestamp = time.time()
        else:
            delta_idle = curr_idle - _last_idle_time
            delta_kernel = curr_kernel - _last_kernel_time
            delta_user = curr_user - _last_user_time

            _last_idle_time = curr_idle
            _last_kernel_time = curr_kernel
            _last_user_time = curr_user
            _last_sample_timestamp = curr_ts

        total_system = delta_kernel + delta_user
        if total_system <= 0:
            cpu_percent = 0.0
        else:
            cpu_percent = round(((total_system - delta_idle) / total_system) * 100.0, 1)

        cpu_percent = max(0.0, min(100.0, cpu_percent))
        return {
            "success": True,
            "cpu_usage_percent": cpu_percent,
            "message": f"CPU Usage: {cpu_percent}%"
        }
    except Exception as err:
        return {"success": False, "cpu_usage_percent": 0.0, "message": f"Failed to compute CPU usage: {err}"}


def get_cpu_details() -> dict:
    """Retrieves processor model name, core counts, and clock speed via WMI."""
    ps_cmd = "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | ConvertTo-Json"
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        ).strip()
        data = json.loads(output)
        if isinstance(data, list):
            data = data[0]
        return {
            "success": True,
            "name": data.get("Name", "").strip(),
            "cores": data.get("NumberOfCores"),
            "physical_cores": data.get("NumberOfCores"),
            "threads": data.get("NumberOfLogicalProcessors"),
            "logical_processors": data.get("NumberOfLogicalProcessors"),
            "max_clock_mhz": data.get("MaxClockSpeed"),
            "message": f"{data.get('Name', '').strip()} ({data.get('NumberOfCores')} Cores, {data.get('NumberOfLogicalProcessors')} Threads)"
        }
    except Exception as err:
        return {"success": False, "message": f"Could not read CPU details: {err}"}


def get_ram_usage() -> dict:
    """Reads system physical memory (RAM) statistics."""
    if not kernel32:
        return {"success": False, "message": "kernel32 is unavailable."}

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return {"success": False, "message": "GlobalMemoryStatusEx call failed."}

    total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
    avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
    used_gb = round(total_gb - avail_gb, 2)
    load_pct = stat.dwMemoryLoad

    return {
        "success": True,
        "load_percent": load_pct,
        "total_gb": total_gb,
        "used_gb": used_gb,
        "available_gb": avail_gb,
        "message": f"RAM Usage: {load_pct}% used ({used_gb} GB / {total_gb} GB, {avail_gb} GB available)"
    }


def get_disk_space(path: str = "C:\\") -> dict:
    """Checks disk space usage for a given drive root path."""
    try:
        total, used, free = shutil.disk_usage(path)
        total_gb = round(total / (1024 ** 3), 2)
        used_gb = round(used / (1024 ** 3), 2)
        free_gb = round(free / (1024 ** 3), 2)
        used_pct = round((used / total) * 100.0, 1)

        return {
            "success": True,
            "path": path,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "used_percent": used_pct,
            "message": f"Disk ({path}): {used_pct}% used ({used_gb} GB / {total_gb} GB, {free_gb} GB free)"
        }
    except Exception as err:
        return {"success": False, "path": path, "message": f"Failed to inspect disk '{path}': {err}"}


def get_gpu_info() -> dict:
    """Reads GPU information using nvidia-smi or Windows WMI."""
    nvsmi = shutil.which("nvidia-smi")
    if nvsmi:
        try:
            out = subprocess.check_output(
                [nvsmi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            if out:
                first = out.splitlines()[0]
                parts = [p.strip() for p in first.split(",")]
                gpu_name = parts[0]
                mem_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                mem_gb = round(mem_mb / 1024.0, 2) if mem_mb else None
                return {
                    "success": True,
                    "name": gpu_name,
                    "memory_total_gb": mem_gb,
                    "driver": "NVIDIA",
                    "message": f"GPU: {gpu_name}" + (f" ({mem_gb} GB VRAM)" if mem_gb else "")
                }
        except Exception:
            pass

    ps_cmd = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        names = [line.strip() for line in output.splitlines() if line.strip()]
        if names:
            gpu_str = ", ".join(names)
            return {
                "success": True,
                "name": gpu_str,
                "driver": "Windows WMI",
                "message": f"GPU(s): {gpu_str}"
            }
    except Exception:
        pass

    return {"success": False, "name": "Unknown", "message": "No GPU detected or query unavailable."}


def get_gpu_usage() -> dict:
    """Reads instantaneous GPU utilization and VRAM usage."""
    nvsmi = shutil.which("nvidia-smi")
    if nvsmi:
        try:
            out = subprocess.check_output(
                [nvsmi, "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            if out:
                parts = [p.strip() for p in out.splitlines()[0].split(",")]
                name = parts[0]
                util_pct = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                used_mb = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                total_mb = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0

                return {
                    "success": True,
                    "name": name,
                    "gpu_usage_percent": util_pct,
                    "vram_used_mb": used_mb,
                    "vram_total_mb": total_mb,
                    "message": f"GPU ({name}): {util_pct}% load | VRAM: {used_mb}MB / {total_mb}MB"
                }
        except Exception:
            pass
    return {"success": False, "message": "Instantaneous GPU utilization is only available for NVIDIA GPUs via nvidia-smi."}


def get_motherboard_info() -> dict:
    """Retrieves Motherboard manufacturer, model, and BIOS info via WMI."""
    ps_cmd = (
        "$b = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product; "
        "$bios = Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate; "
        "@{ Manufacturer=$b.Manufacturer; Product=$b.Product; BiosVersion=$bios.SMBIOSBIOSVersion } | ConvertTo-Json"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        ).strip()
        data = json.loads(output)
        if isinstance(data, list):
            data = data[0] if data else {}
        return {
            "success": True,
            "motherboard": data,
            "manufacturer": data.get("Manufacturer", "").strip(),
            "product": data.get("Product", "").strip(),
            "bios_version": data.get("BiosVersion", "").strip(),
            "message": f"Motherboard: {data.get('Manufacturer', '')} {data.get('Product', '')} (BIOS: {data.get('BiosVersion', '')})"
        }
    except Exception as err:
        return {"success": False, "message": f"Could not query motherboard info: {err}"}


def get_system_info() -> dict:
    """Aggregates an executive summary of the entire computer hardware and OS."""
    os_name = f"{platform.system()} {platform.release()} ({platform.version()})"
    proc_name = platform.processor() or "Unknown CPU"

    cpu_res = get_cpu_usage()
    ram_res = get_ram_usage()
    disk_res = get_disk_space("C:\\")
    gpu_res = get_gpu_info()

    lines = [
        f"OS: {os_name}",
        f"Processor: {proc_name}",
        f"CPU Load: {cpu_res.get('cpu_usage_percent', 0.0)}%",
        f"RAM: {ram_res.get('load_percent', 0)}% used ({ram_res.get('used_gb', 0)} GB / {ram_res.get('total_gb', 0)} GB)",
        f"Disk (C:): {disk_res.get('used_percent', 0)}% used ({disk_res.get('free_gb', 0)} GB free)",
        f"Graphics: {gpu_res.get('message', 'None')}"
    ]

    return {
        "success": True,
        "os": os_name,
        "processor": proc_name,
        "cpu": cpu_res,
        "ram": ram_res,
        "disk": disk_res,
        "gpu": gpu_res,
        "message": "System Specifications:\n" + "\n".join(f"- {l}" for l in lines)
    }
