import ctypes
import datetime
import threading
import time

try:
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    kernel32 = None

_active_timers = {}
_stopwatches = {}


def get_system_uptime() -> dict:
    """
    Retrieves the system uptime since last boot using GetTickCount64.
    """
    if not kernel32:
        return {"success": False, "message": "kernel32 is unavailable."}

    try:
        kernel32.GetTickCount64.restype = ctypes.c_uint64
        uptime_ms = kernel32.GetTickCount64()
        uptime_sec = uptime_ms // 1000

        days, remainder = divmod(uptime_sec, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        formatted = ", ".join(parts)
        return {
            "success": True,
            "uptime_seconds": uptime_sec,
            "uptime_milliseconds": uptime_ms,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "formatted": formatted,
            "message": f"System Uptime: {formatted}"
        }
    except Exception as err:
        return {
            "success": False,
            "uptime_seconds": 0,
            "message": f"Failed to retrieve system uptime: {err}"
        }


def _timer_worker(seconds: int, label: str):
    time.sleep(seconds)
    _active_timers.pop(label, None)
    try:
        from tools.notifications import show_notification
        show_notification(f"Timer Alert: {label}", f"Your timer for {seconds} seconds has completed!", with_chime=True)
    except Exception:
        pass


def start_timer(seconds: int, label: str = "Timer") -> dict:
    """
    Sets a countdown timer that notifies when completed.
    Runs asynchronously in the background.
    """
    try:
        sec = int(seconds)
    except (ValueError, TypeError):
        return {"success": False, "message": f"Invalid duration in seconds: '{seconds}'."}

    if sec <= 0:
        return {"success": False, "message": "Timer duration must be greater than 0 seconds."}

    clean_label = label.strip() if label else "Timer"
    if clean_label in _active_timers and _active_timers[clean_label].is_alive():
        return {
            "success": False,
            "message": f"A timer labeled '{clean_label}' is already running."
        }

    t = threading.Thread(target=_timer_worker, args=(sec, clean_label), daemon=True)
    _active_timers[clean_label] = t
    t.start()

    finish_time = datetime.datetime.now() + datetime.timedelta(seconds=sec)
    time_str = finish_time.strftime("%I:%M:%S %p")

    return {
        "success": True,
        "label": clean_label,
        "duration_seconds": sec,
        "finish_time": time_str,
        "message": f"Timer '{clean_label}' started for {sec}s (will ring at {time_str})."
    }


def list_active_timers() -> dict:
    """Lists currently active background countdown timers."""
    active = [k for k, v in _active_timers.items() if v.is_alive()]
    return {
        "success": True,
        "count": len(active),
        "timers": active,
        "message": f"{len(active)} active timer(s): {', '.join(active) if active else 'None'}"
    }


def start_stopwatch(name: str = "default") -> dict:
    """
    Starts a precision stopwatch.
    """
    clean_name = name.strip().lower()
    _stopwatches[clean_name] = {
        "start": time.perf_counter(),
        "laps": [],
        "created_at": datetime.datetime.now().strftime("%I:%M:%S %p")
    }
    return {
        "success": True,
        "name": clean_name,
        "message": f"Stopwatch '{clean_name}' started at {_stopwatches[clean_name]['created_at']}."
    }


def lap_stopwatch(name: str = "default") -> dict:
    """
    Records a lap timestamp on a running stopwatch.
    """
    clean_name = name.strip().lower()
    sw = _stopwatches.get(clean_name)
    if not sw:
        return {"success": False, "message": f"Stopwatch '{clean_name}' is not running."}

    elapsed = round(time.perf_counter() - sw["start"], 2)
    sw["laps"].append(elapsed)
    return {
        "success": True,
        "lap_number": len(sw["laps"]),
        "elapsed_seconds": elapsed,
        "message": f"Lap {len(sw['laps'])} for '{clean_name}': {elapsed}s"
    }


def stop_stopwatch(name: str = "default") -> dict:
    """
    Stops a stopwatch and returns total elapsed time.
    """
    clean_name = name.strip().lower()
    sw = _stopwatches.pop(clean_name, None)
    if not sw:
        return {"success": False, "message": f"Stopwatch '{clean_name}' is not running."}

    elapsed = round(time.perf_counter() - sw["start"], 2)
    return {
        "success": True,
        "name": clean_name,
        "elapsed_seconds": elapsed,
        "total_seconds": elapsed,
        "total_laps": len(sw["laps"]),
        "message": f"Stopwatch '{clean_name}' stopped: {elapsed} seconds ({len(sw['laps'])} laps)."
    }
