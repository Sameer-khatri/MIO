"""
MIO Mouth - Speech Synthesis & Vocal Output Engine (mouth.speaker)

Provides offline Windows speech synthesis using native SAPI 5 SpVoice.
Supports voice personality switching (Zira, David, Mark), speed rate control,
volume leveling, background async speech, and zero-latency speech interruption/stop.
"""

import subprocess
import threading
import time
from typing import Any

from mouth.voices import list_installed_voices, get_default_voice, find_voice

# Vocal settings state
_SETTINGS_LOCK = threading.Lock()
_CURRENT_SETTINGS = {
    "voice": "Microsoft Zira Desktop",
    "rate": 0,       # -10 (slowest) to +10 (fastest)
    "volume": 100,   # 0 to 100
}

# Process tracking for active speech interruption
_PROCESS_LOCK = threading.Lock()
_ACTIVE_PROCESS: subprocess.Popen | None = None


def get_voice_settings() -> dict[str, Any]:
    """Returns the current voice persona, speed rate, and volume settings."""
    with _SETTINGS_LOCK:
        return dict(_CURRENT_SETTINGS)


def set_voice(voice_name: str) -> dict[str, Any]:
    """Sets the preferred vocal persona (e.g., 'zira', 'david', 'female', 'male')."""
    matched = find_voice(voice_name)
    if not matched:
        return {
            "success": False,
            "message": f"Could not find installed voice matching '{voice_name}'."
        }

    with _SETTINGS_LOCK:
        _CURRENT_SETTINGS["voice"] = matched["name"]

    return {
        "success": True,
        "voice": matched["name"],
        "gender": matched["gender"],
        "message": f"Mouth voice set to {matched['name']} ({matched['gender']})."
    }


def set_rate(rate: int) -> dict[str, Any]:
    """Sets the speech rate/speed from -10 (slowest) to +10 (fastest)."""
    try:
        val = int(rate)
    except (ValueError, TypeError):
        return {"success": False, "message": "Speech rate must be an integer between -10 and 10."}

    clamped = max(-10, min(10, val))
    with _SETTINGS_LOCK:
        _CURRENT_SETTINGS["rate"] = clamped

    return {"success": True, "rate": clamped, "message": f"Speech rate set to {clamped}."}


def set_volume(volume: int) -> dict[str, Any]:
    """Sets the speech volume from 0 to 100."""
    try:
        val = int(volume)
    except (ValueError, TypeError):
        return {"success": False, "message": "Speech volume must be an integer between 0 and 100."}

    clamped = max(0, min(100, val))
    with _SETTINGS_LOCK:
        _CURRENT_SETTINGS["volume"] = clamped

    return {"success": True, "volume": clamped, "message": f"Speech volume set to {clamped}%."}


def stop() -> dict[str, Any]:
    """
    Instantly interrupts and halts any active speech in progress.
    """
    global _ACTIVE_PROCESS
    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
            try:
                _ACTIVE_PROCESS.terminate()
                _ACTIVE_PROCESS.kill()
            except Exception:
                pass
            _ACTIVE_PROCESS = None
            return {"success": True, "stopped": True, "message": "Active speech interrupted."}

    return {"success": True, "stopped": False, "message": "Mouth is not currently speaking."}


def is_speaking() -> bool:
    """Returns True if MIO is currently speaking."""
    with _PROCESS_LOCK:
        if _ACTIVE_PROCESS and _ACTIVE_PROCESS.poll() is None:
            return True
    return False


def speak(
    text: str,
    voice: str | None = None,
    rate: int | None = None,
    volume: int | None = None,
    async_speech: bool = True,
) -> dict[str, Any]:
    """
    Synthesizes and speaks text out loud through the default audio endpoint.

    Args:
        text: The text string to speak.
        voice: Voice name or persona (defaults to current active setting).
        rate: Speed rate from -10 to +10 (defaults to current setting).
        volume: Volume percentage from 0 to 100 (defaults to current setting).
        async_speech: If True, plays in background without blocking; if False, blocks until speech finishes.
    """
    global _ACTIVE_PROCESS

    if not text or not isinstance(text, str):
        return {"success": False, "message": "Text to speak must be a non-empty string."}

    clean_text = text.strip()
    if not clean_text:
        return {"success": False, "message": "Text to speak cannot be blank."}

    with _SETTINGS_LOCK:
        target_voice = voice or _CURRENT_SETTINGS["voice"]
        target_rate = rate if rate is not None else _CURRENT_SETTINGS["rate"]
        target_vol = volume if volume is not None else _CURRENT_SETTINGS["volume"]

    # Match voice description
    v_info = find_voice(target_voice)
    voice_filter = v_info["name"] if v_info else target_voice

    # Escape quotes for PowerShell string literal
    safe_text = clean_text.replace("'", "''")
    safe_voice = voice_filter.replace("'", "''")

    ps_script = (
        f"$sp = New-Object -ComObject SAPI.SpVoice; "
        f"if ('{safe_voice}') {{ "
        f"  foreach ($v in $sp.GetVoices()) {{ "
        f"    if ($v.GetDescription() -like '*{safe_voice}*' -or $v.Id -like '*{safe_voice}*') {{ "
        f"      $sp.Voice = $v; break "
        f"    }} "
        f"  }} "
        f"}} "
        f"$sp.Rate = {int(target_rate)}; "
        f"$sp.Volume = {int(target_vol)}; "
        f"[void]$sp.Speak('{safe_text}')"
    )

    # Stop any currently active speech before starting new utterance
    stop()

    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with _PROCESS_LOCK:
            _ACTIVE_PROCESS = proc

        if not async_speech:
            proc.wait(timeout=30)
            with _PROCESS_LOCK:
                _ACTIVE_PROCESS = None
            return {
                "success": True,
                "text": clean_text,
                "voice": voice_filter,
                "rate": target_rate,
                "volume": target_vol,
                "mode": "blocking",
                "message": f"Finished speaking: \"{clean_text[:60]}\""
            }

        return {
            "success": True,
            "text": clean_text,
            "voice": voice_filter,
            "rate": target_rate,
            "volume": target_vol,
            "mode": "async",
            "message": f"Speaking: \"{clean_text[:60]}\""
        }

    except Exception as err:
        return {
            "success": False,
            "text": clean_text,
            "message": f"Failed to speak text: {err}"
        }


# Instant convenience alias
say = speak
