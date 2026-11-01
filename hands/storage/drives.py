import ctypes
import os
import shutil
import subprocess

try:
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    kernel32 = None

DRIVE_TYPES = {
    0: "Unknown",
    1: "No Root Directory",
    2: "Removable (USB/SD)",
    3: "Fixed (HDD/SSD)",
    4: "Network Drive",
    5: "CD-ROM/DVD",
    6: "RAM Disk"
}


def list_drives() -> dict:
    """
    Lists all connected storage drives, drive types (Fixed, USB Removable, Network),
    volume labels, file system types, and available storage capacities.
    """
    if not kernel32:
        return {"success": False, "message": "kernel32 is unavailable."}

    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        drive_type_code = kernel32.GetDriveTypeW(root)
        if drive_type_code <= 1:
            continue

        type_label = DRIVE_TYPES.get(drive_type_code, "Unknown")
        is_removable = (drive_type_code == 2)

        vol_name_buf = ctypes.create_unicode_buffer(261)
        fs_name_buf = ctypes.create_unicode_buffer(261)
        serial_num = ctypes.c_ulong()
        max_component_len = ctypes.c_ulong()
        fs_flags = ctypes.c_ulong()

        vol_name = ""
        fs_type = ""
        if kernel32.GetVolumeInformationW(
            root,
            vol_name_buf,
            ctypes.sizeof(vol_name_buf),
            ctypes.byref(serial_num),
            ctypes.byref(max_component_len),
            ctypes.byref(fs_flags),
            fs_name_buf,
            ctypes.sizeof(fs_name_buf)
        ):
            vol_name = vol_name_buf.value
            fs_type = fs_name_buf.value

        total_gb = 0.0
        free_gb = 0.0
        used_percent = 0.0
        try:
            usage = shutil.disk_usage(root)
            total_gb = round(usage.total / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)
            if total_gb > 0:
                used_percent = round(((usage.total - usage.free) / usage.total) * 100, 1)
        except Exception:
            pass

        drives.append({
            "letter": letter,
            "root": root,
            "name": vol_name or "Local Disk",
            "type": type_label,
            "is_removable": is_removable,
            "filesystem": fs_type or "NTFS",
            "total_gb": total_gb,
            "free_gb": free_gb,
            "used_percent": used_percent
        })

    return {
        "success": True,
        "count": len(drives),
        "drives": drives,
        "message": f"Found {len(drives)} drive(s): " + ", ".join(f"{d['root']} ({d['name']}, {d['free_gb']}GB free)" for d in drives)
    }


def get_removable_drives() -> dict:
    """
    Filters and returns only connected USB flash drives and removable media.
    """
    res = list_drives()
    if not res.get("success"):
        return res

    removable = [d for d in res.get("drives", []) if d.get("is_removable")]
    return {
        "success": True,
        "count": len(removable),
        "drives": removable,
        "message": f"{len(removable)} removable USB drive(s) connected: " + (", ".join(d['root'] for d in removable) if removable else "None")
    }


def check_drive_space_warning(threshold_percent: int = 10) -> dict:
    """
    Scans all fixed drives and flags any that have less than threshold_percent free disk space remaining.
    """
    res = list_drives()
    if not res.get("success"):
        return res

    warnings = []
    for d in res.get("drives", []):
        free_pct = 100.0 - d.get("used_percent", 0.0)
        if free_pct < threshold_percent and d.get("total_gb", 0) > 0:
            warnings.append({
                "drive": d.get("device", d.get("root", "Unknown")),
                "free_gb": d.get("free_gb", 0),
                "free_percent": round(free_pct, 1)
            })

    if warnings:
        warn_str = ", ".join(f"{w['drive']} ({w['free_percent']}% free, {w['free_gb']} GB)" for w in warnings)
        return {
            "success": True,
            "has_warnings": True,
            "warnings": warnings,
            "message": f"CRITICAL: Low disk space detected on: {warn_str}."
        }
    return {
        "success": True,
        "has_warnings": False,
        "warnings": [],
        "message": "All storage drives have healthy free space (> 10%)."
    }


def eject_usb_drive(drive_letter: str) -> dict:
    """
    Safely dismounts and ejects a removable USB drive.
    """
    clean_letter = drive_letter.strip().upper().rstrip(":\\")
    if len(clean_letter) != 1 or not clean_letter.isalpha():
        return {"success": False, "message": f"Invalid drive letter: '{drive_letter}'."}

    ps_cmd = (
        f"$drive = '{clean_letter}:'; "
        f"$vol = Get-Volume -DriveLetter '{clean_letter}' -ErrorAction SilentlyContinue; "
        f"if ($vol) {{ (New-Object -ComObject Shell.Application).NameSpace(17).ParseName($drive).InvokeVerb('Eject'); 'Ejected' }} else {{ 'NotFound' }}"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()

        if "Ejected" in output:
            return {
                "success": True,
                "drive": f"{clean_letter}:\\",
                "message": f"Drive {clean_letter}:\\ was safely ejected."
            }
        return {
            "success": False,
            "drive": f"{clean_letter}:\\",
            "message": f"Drive {clean_letter}:\\ could not be ejected or was not found."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to eject drive: {err}"}
