import ctypes
import json
import subprocess
import threading

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_key(vk_code: int):
    if user32:
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, 2, 0)


def set_volume(level: int) -> dict:
    """
    Sets master audio volume to a specific percentage (0-100).
    """
    try:
        val = int(level)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid volume level: '{level}'."}

    val = max(0, min(100, val))
    normalized = val / 100.0

    ps_cmd = (
        f"$w = Add-Type -Name W -PassThru -MemberDefinition "
        f"'[DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);'; "
        f"[AudioEndpoint]::SetMasterVolume({normalized})"
    )

    script = (
        f"$obj = New-Object -ComObject WScript.Shell; "
        f"for ($i=0; $i -lt 50; $i++) {{ $obj.SendKeys([char]174) }}; "
        f"$steps = [math]::Round({val} / 2); "
        f"for ($i=0; $i -lt $steps; $i++) {{ $obj.SendKeys([char]175) }}"
    )

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {
            "success": True,
            "volume": val,
            "volume_percent": val,
            "message": f"Master volume set to {val}%."
        }
    except Exception as err:
        return {
            "success": False,
            "volume": val,
            "message": f"Failed to set volume: {err}"
        }


def volume_up(steps: int = 5) -> dict:
    """Increases volume by steps (default ~10%)."""
    for _ in range(steps):
        _send_key(VK_VOLUME_UP)
    return {"success": True, "message": f"Volume increased by {steps * 2}%."}


def volume_down(steps: int = 5) -> dict:
    """Decreases volume by steps (default ~10%)."""
    for _ in range(steps):
        _send_key(VK_VOLUME_DOWN)
    return {"success": True, "message": f"Volume decreased by {steps * 2}%."}


def toggle_mute() -> dict:
    """Toggles master audio mute on/off."""
    _send_key(VK_VOLUME_MUTE)
    return {"success": True, "message": "Toggled master audio mute."}


def media_play_pause() -> dict:
    """Sends global Play/Pause media key event."""
    _send_key(VK_MEDIA_PLAY_PAUSE)
    return {"success": True, "message": "Media Play/Pause toggled."}


def media_next() -> dict:
    """Sends global Next Track media key event."""
    _send_key(VK_MEDIA_NEXT_TRACK)
    return {"success": True, "message": "Skipped to next media track."}


def media_prev() -> dict:
    """Sends global Previous Track media key event."""
    _send_key(VK_MEDIA_PREV_TRACK)
    return {"success": True, "message": "Skipped to previous media track."}


def media_stop() -> dict:
    """Sends global Stop media key event."""
    _send_key(VK_MEDIA_STOP)
    return {"success": True, "message": "Media playback stopped."}


def speak_text(text: str, async_speech: bool = True) -> dict:
    """
    Speaks text out loud using native Windows Speech API (SAPI).
    Zero external dependencies.
    """
    if not text or not isinstance(text, str):
        return {"success": False, "message": "Text to speak cannot be empty."}

    clean_text = text.strip()
    # Escape quotes
    safe_text = clean_text.replace("'", "''")
    ps_cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{safe_text}')"

    def _worker():
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    if async_speech:
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return {
            "success": True,
            "text": clean_text,
            "message": f"Speaking: \"{clean_text}\""
        }
    else:
        _worker()
        return {
            "success": True,
            "text": clean_text,
            "message": f"Finished speaking: \"{clean_text}\""
        }


def list_audio_devices() -> dict:
    """
    Queries installed audio playback and recording hardware endpoints via WMI.
    """
    ps_cmd = "Get-CimInstance Win32_SoundDevice | Select-Object Name, Manufacturer, Status | ConvertTo-Json"
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore"
        ).strip()

        devices = []
        if output:
            data = json.loads(output)
            if isinstance(data, dict):
                devices = [data]
            elif isinstance(data, list):
                devices = data

        return {
            "success": True,
            "count": len(devices),
            "devices": devices,
            "message": f"Detected {len(devices)} audio device(s): " + ", ".join(d.get("Name", "Audio Device") for d in devices[:4])
        }
    except Exception as err:
        return {
            "success": False,
            "devices": [],
            "message": f"Failed to list audio devices: {err}"
        }
