import ctypes
import os
import shutil

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
    # Check drive letters A-Z
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
        try:
            usage = shutil.disk_usage(root)
            total_gb = round(usage.total / (1024 ** 3), 2)
            free_gb = round(usage.free / (1024 ** 3), 2)
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
            "free_gb": free_gb
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
