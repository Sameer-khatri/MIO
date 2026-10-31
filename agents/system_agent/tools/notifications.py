import os
import subprocess
import time
import winsound


def play_chime(sound_type: str = "asterisk") -> dict:
    """
    Plays a native Windows system alert chime.
    Supported types: 'asterisk', 'exclamation', 'hand' (error), 'question', 'ok'.
    """
    sound_map = {
        "asterisk": winsound.MB_ICONASTERISK,
        "info": winsound.MB_ICONASTERISK,
        "exclamation": winsound.MB_ICONEXCLAMATION,
        "warning": winsound.MB_ICONEXCLAMATION,
        "hand": winsound.MB_ICONHAND,
        "error": winsound.MB_ICONHAND,
        "question": winsound.MB_ICONQUESTION,
        "ok": winsound.MB_OK,
    }
    sound_flag = sound_map.get(sound_type.lower().strip(), winsound.MB_ICONASTERISK)
    try:
        winsound.MessageBeep(sound_flag)
        return {
            "success": True,
            "sound": sound_type,
            "message": f"Played Windows '{sound_type}' chime."
        }
    except Exception as err:
        return {
            "success": False,
            "sound": sound_type,
            "message": f"Failed to play chime: {err}"
        }


def beep(frequency_hz: int = 1000, duration_ms: int = 250) -> dict:
    """
    Plays a hardware speaker tone at the exact specified frequency and duration.
    """
    try:
        freq = max(37, min(32767, int(frequency_hz)))
        dur = max(10, min(5000, int(duration_ms)))
        winsound.Beep(freq, dur)
        return {
            "success": True,
            "frequency_hz": freq,
            "duration_ms": dur,
            "message": f"Played beep tone: {freq} Hz for {dur} ms."
        }
    except Exception as err:
        return {"success": False, "message": f"Failed to play beep: {err}"}


def play_sound_pattern(pattern_name: str = "success") -> dict:
    """
    Plays composed audio patterns for clear user feedback:
    'success' (ascending chord), 'error' (descending alert), 'alarm' (triple pulse).
    """
    p_norm = pattern_name.strip().lower()
    try:
        if p_norm == "success":
            for f in (523, 659, 784):  # C5, E5, G5 major triad
                winsound.Beep(f, 80)
                time.sleep(0.01)
        elif p_norm == "error":
            for f in (440, 349):  # A4, F4
                winsound.Beep(f, 150)
                time.sleep(0.02)
        elif p_norm in ("alarm", "alert"):
            for _ in range(3):
                winsound.Beep(1200, 90)
                time.sleep(0.05)
        else:
            return {
                "success": False,
                "pattern": p_norm,
                "message": f"Unknown sound pattern: '{pattern_name}'. Supported patterns: 'success', 'error', 'alarm', 'alert'."
            }

        return {
            "success": True,
            "pattern": p_norm,
            "message": f"Played '{p_norm}' sound sequence."
        }
    except Exception as err:
        return {"success": False, "pattern": p_norm, "message": f"Could not play sound pattern: {err}"}


def show_notification(title: str, message: str, with_chime: bool = True) -> dict:
    """
    Displays a native Windows desktop balloon toast notification.
    """
    clean_title = title.strip() if title else "MIO System Agent"
    clean_msg = message.strip() if message else ""

    if with_chime:
        play_chime("asterisk")

    # Use PowerShell NotifyIcon balloon tip
    ps_cmd = (
        f"[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
        f"[void][System.Reflection.Assembly]::LoadWithPartialName('System.Drawing');"
        f"$obj = New-Object System.Windows.Forms.NotifyIcon;"
        f"$obj.Icon = [System.Drawing.SystemIcons]::Information;"
        f"$obj.BalloonTipTitle = '{clean_title}';"
        f"$obj.BalloonTipText = '{clean_msg}';"
        f"$obj.Visible = $True;"
        f"$obj.ShowBalloonTip(5000);"
    )

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {
            "success": True,
            "title": clean_title,
            "body": clean_msg,
            "message": f"Notification sent: [{clean_title}] {clean_msg}"
        }
    except Exception as err:
        return {
            "success": False,
            "title": clean_title,
            "body": clean_msg,
            "message": f"Failed to show notification: {err}"
        }
