import os
import subprocess
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
