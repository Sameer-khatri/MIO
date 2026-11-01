"""
MIO Ears: Microphone & Speech Recognizer Device Hardware Layer
===============================================================
Discovers and inspects physical microphone hardware and native Windows
speech recognition engines without external dependencies.
"""

import ctypes
import os
import subprocess
import json
from typing import Dict, List, Optional, Any

class WAVEINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", ctypes.c_ushort),
        ("wPid", ctypes.c_ushort),
        ("vDriverVersion", ctypes.c_uint),
        ("szPname", ctypes.c_wchar * 32),
        ("dwFormats", ctypes.c_ulong),
        ("wChannels", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
    ]


def list_microphones() -> List[Dict[str, Any]]:
    """
    Enumerates all installed audio recording devices (microphones)
    using the Windows Multimedia (winmm.dll) API.
    
    Returns:
        List of dicts: [{"id": 0, "name": "Microphone Array", "channels": 2}, ...]
    """
    devices = []
    try:
        winmm = ctypes.windll.winmm
        num_devs = winmm.waveInGetNumDevs()
        for dev_id in range(num_devs):
            caps = WAVEINCAPSW()
            res = winmm.waveInGetDevCapsW(dev_id, ctypes.byref(caps), ctypes.sizeof(caps))
            if res == 0:
                devices.append({
                    "id": dev_id,
                    "name": caps.szPname.strip(),
                    "channels": int(caps.wChannels),
                    "formats": int(caps.dwFormats),
                })
    except Exception as e:
        devices.append({"id": -1, "name": f"Error querying devices: {e}", "channels": 0, "formats": 0})
    return devices


def is_microphone_available() -> bool:
    """
    Checks if at least one audio input device is available.
    """
    try:
        winmm = ctypes.windll.winmm
        return winmm.waveInGetNumDevs() > 0
    except Exception:
        return False


def get_default_microphone() -> Optional[Dict[str, Any]]:
    """
    Returns the primary (default) recording device.
    """
    devs = list_microphones()
    if devs and devs[0]["id"] >= 0:
        return devs[0]
    return None


def get_recognizer_info() -> Dict[str, Any]:
    """
    Discovers installed Windows native speech recognition engines (System.Speech).
    
    Returns:
        Dict containing installed engines, primary engine ID, culture, and readiness.
    """
    ps_cmd = """
Add-Type -AssemblyName System.Speech
$recs = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
$list = @()
foreach ($r in $recs) {
    $list += [PSCustomObject]@{
        Id = $r.Id
        Name = $r.Name
        Culture = $r.Culture.Name
        Description = $r.Description
    }
}
$list | ConvertTo-Json -Compress
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        out = res.stdout.strip()
        if out:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            return {
                "available": True,
                "count": len(data),
                "primary": data[0] if data else None,
                "engines": data,
            }
    except Exception as e:
        return {
            "available": False,
            "count": 0,
            "primary": None,
            "engines": [],
            "error": str(e),
        }
    return {
        "available": False,
        "count": 0,
        "primary": None,
        "engines": [],
    }
