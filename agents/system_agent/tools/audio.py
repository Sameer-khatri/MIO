import ctypes
import time
from ctypes import wintypes

try:
    user32 = ctypes.windll.user32
except AttributeError:
    user32 = None

# Windows Virtual Key Codes for Media & Volume
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _press_key(vk_code: int) -> bool:
    """Simulates a key press and release using keybd_event."""
    if not user32:
        return False
    try:
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(vk_code, 0, 2, 0)
        return True
    except Exception:
        return False


def set_volume(percent: int | str) -> dict:
    """
    Sets the system master volume to the target percentage (0-100%).
    Calibrates to 0% and then steps up to the target volume level.
    """
    try:
        val = int(str(percent).strip().rstrip("%"))
        val = max(0, min(100, val))
    except (ValueError, TypeError):
        return {
            "success": False,
            "volume_percent": 0,
            "message": f"Invalid volume value: '{percent}'. Please specify a number between 0 and 100."
        }

    if not user32:
        return {"success": False, "volume_percent": val, "message": "user32 is unavailable."}

    # Reset volume to 0 by pressing volume down 50 times (each step is 2%)
    for _ in range(50):
        _press_key(VK_VOLUME_DOWN)

    # Step up to desired level (val // 2 steps)
    steps = int(round(val / 2.0))
    for _ in range(steps):
        _press_key(VK_VOLUME_UP)

    return {
        "success": True,
        "volume_percent": val,
        "message": f"Volume set to {val}%."
    }


def volume_up(steps: int = 5) -> dict:
    """Increases system volume by the specified number of steps (default 5 steps ~10%)."""
    count = max(1, min(50, steps))
    for _ in range(count):
        _press_key(VK_VOLUME_UP)
    return {
        "success": True,
        "message": f"Increased volume by {count * 2}%."
    }


def volume_down(steps: int = 5) -> dict:
    """Decreases system volume by the specified number of steps (default 5 steps ~10%)."""
    count = max(1, min(50, steps))
    for _ in range(count):
        _press_key(VK_VOLUME_DOWN)
    return {
        "success": True,
        "message": f"Decreased volume by {count * 2}%."
    }


def toggle_mute() -> dict:
    """Toggles master volume mute on or off."""
    if _press_key(VK_VOLUME_MUTE):
        return {
            "success": True,
            "message": "Toggled volume mute."
        }
    return {
        "success": False,
        "message": "Failed to toggle volume mute."
    }


def media_play_pause() -> dict:
    """Simulates media play/pause hardware key."""
    if _press_key(VK_MEDIA_PLAY_PAUSE):
        return {"success": True, "message": "Media play/pause triggered."}
    return {"success": False, "message": "Failed to trigger media play/pause."}


def media_next() -> dict:
    """Simulates media skip next track hardware key."""
    if _press_key(VK_MEDIA_NEXT_TRACK):
        return {"success": True, "message": "Skipped to next media track."}
    return {"success": False, "message": "Failed to trigger next track."}


def media_prev() -> dict:
    """Simulates media previous track hardware key."""
    if _press_key(VK_MEDIA_PREV_TRACK):
        return {"success": True, "message": "Returned to previous media track."}
    return {"success": False, "message": "Failed to trigger previous track."}


def media_stop() -> dict:
    """Simulates media stop playback hardware key."""
    if _press_key(VK_MEDIA_STOP):
        return {"success": True, "message": "Stopped media playback."}
    return {"success": False, "message": "Failed to trigger media stop."}
