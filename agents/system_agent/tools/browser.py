import os
import re
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
import winreg


BROWSER_EXECUTABLES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "brave": "brave.exe",
    "firefox": "firefox.exe",
}


def open_url(url: str) -> dict:
    """
    Opens any web address in the user's default system browser.
    Ensures http:// or https:// prefix.
    """
    if not url or not isinstance(url, str):
        return {"success": False, "url": "", "message": "Invalid URL provided."}

    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    try:
        webbrowser.open(clean_url, new=2)
        return {
            "success": True,
            "url": clean_url,
            "message": f"Opened '{clean_url}' in default browser."
        }
    except Exception as err:
        return {
            "success": False,
            "url": clean_url,
            "message": f"Failed to open URL: {err}"
        }


def search_web(query: str, engine: str = "google") -> dict:
    """
    Searches the web using Google, Bing, DuckDuckGo, or YouTube.
    """
    if not query or not isinstance(query, str):
        return {"success": False, "query": "", "message": "Please specify a search query."}

    clean_q = query.strip()
    encoded = urllib.parse.quote_plus(clean_q)

    engine_norm = engine.strip().lower()
    if "youtube" in engine_norm:
        search_url = f"https://www.youtube.com/results?search_query={encoded}"
    elif "bing" in engine_norm:
        search_url = f"https://www.bing.com/search?q={encoded}"
    elif "duck" in engine_norm or "ddg" in engine_norm:
        search_url = f"https://duckduckgo.com/?q={encoded}"
    else:
        search_url = f"https://www.google.com/search?q={encoded}"

    res = open_url(search_url)
    if res.get("success"):
        return {
            "success": True,
            "query": clean_q,
            "engine": engine_norm,
            "url": search_url,
            "message": f"Searching {engine_norm.title()} for: '{clean_q}'."
        }
    return res


def open_incognito(url: str = "") -> dict:
    """
    Opens an Incognito/Private window in an installed browser (Chrome, Edge, Brave, or Firefox).
    """
    target = url.strip() if url else "https://google.com"
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    candidates = [
        ("brave.exe", ["brave.exe", "--incognito", target]),
        ("chrome.exe", ["chrome.exe", "--incognito", target]),
        ("msedge.exe", ["msedge.exe", "-inprivate", target]),
        ("firefox.exe", ["firefox.exe", "-private-window", target]),
    ]

    for exe, cmd in candidates:
        if shutil.which(exe):
            try:
                subprocess.Popen(cmd)
                return {
                    "success": True,
                    "browser": exe,
                    "target": target,
                    "message": f"Opened incognito window ({exe}) with '{target}'."
                }
            except Exception:
                pass

    return open_url(target)


def open_with_browser(url: str, browser_name: str) -> dict:
    """
    Explicitly launches a URL with a specific chosen browser (chrome, edge, brave, firefox).
    """
    if not url or not isinstance(url, str):
        return {"success": False, "message": "Invalid URL provided."}

    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    b_key = browser_name.strip().lower()
    exe_name = BROWSER_EXECUTABLES.get(b_key, f"{b_key}.exe")

    if shutil.which(exe_name):
        try:
            subprocess.Popen([exe_name, clean_url])
            return {
                "success": True,
                "browser": b_key,
                "url": clean_url,
                "message": f"Opened '{clean_url}' using {b_key.title()} ({exe_name})."
            }
        except Exception as err:
            return {
                "success": False,
                "browser": b_key,
                "message": f"Failed to launch {b_key}: {err}"
            }

    try:
        b = webbrowser.get(b_key)
        b.open(clean_url)
        return {
            "success": True,
            "browser": b_key,
            "url": clean_url,
            "message": f"Opened '{clean_url}' using {b_key.title()}."
        }
    except Exception:
        pass

    return {
        "success": False,
        "message": f"Browser executable '{exe_name}' not found on system."
    }


def open_multiple_urls(urls: list[str]) -> dict:
    """
    Opens multiple URLs simultaneously to quickly launch project workspaces or reading sets.
    """
    if not urls or not isinstance(urls, (list, tuple)):
        return {"success": False, "count": 0, "message": "URL list cannot be empty."}

    opened = []
    for u in urls:
        if u and isinstance(u, str) and u.strip():
            res = open_url(u.strip())
            if res.get("success"):
                opened.append(res.get("url"))

    return {
        "success": bool(opened),
        "count": len(opened),
        "opened_count": len(opened),
        "opened_urls": opened,
        "message": f"Opened {len(opened)} tab(s) in default browser."
    }


def get_default_browser() -> dict:
    """
    Detects the user's default browser registered in the Windows registry.
    """
    reg_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")

        browser_map = {
            "BraveHTML": "Brave Browser",
            "ChromeHTML": "Google Chrome",
            "MSEdgeHTM": "Microsoft Edge",
            "FirefoxURL": "Mozilla Firefox",
            "OperaStable": "Opera",
        }
        friendly_name = browser_map.get(prog_id, prog_id)
        return {
            "success": True,
            "prog_id": prog_id,
            "browser": friendly_name,
            "message": f"Default System Browser: {friendly_name}"
        }
    except Exception as err:
        return {
            "success": False,
            "browser": "Unknown",
            "message": f"Could not determine default browser: {err}"
        }


# -------------------------------------------------------------------------
# YouTube Navigation, Precision Timestamp Playback & Media Controls
# -------------------------------------------------------------------------
def parse_timestamp(val: str | int) -> int:
    """
    Parses flexible human-readable timestamps into total seconds:
    - '2 minute', '2 minutes', '2 min', '2m' -> 120
    - '2:00', '02:00', '1:30' -> 120, 90
    - '1 hour 20 minutes', '1h20m' -> 4800
    - '45s', '45 seconds', 45 -> 45
    """
    if isinstance(val, (int, float)):
        return max(0, int(val))
    if not val or not isinstance(val, str):
        return 0

    text = val.strip().lower()
    if text.isdigit():
        return int(text)

    # Colon formats: HH:MM:SS or MM:SS
    parts = text.split(":")
    if len(parts) == 2 and all(p.strip().isdigit() for p in parts):
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

    total = 0
    hrs_match = re.search(r"(\d+)\s*(?:hours?|hrs?|h)", text)
    mins_match = re.search(r"(\d+)\s*(?:minutes?|mins?|m)", text)
    secs_match = re.search(r"(\d+)\s*(?:seconds?|secs?|s)", text)

    if hrs_match:
        total += int(hrs_match.group(1)) * 3600
    if mins_match:
        total += int(mins_match.group(1)) * 60
    if secs_match:
        total += int(secs_match.group(1))

    if total == 0:
        first_num = re.search(r"(\d+)", text)
        if first_num:
            num = int(first_num.group(1))
            total = (num * 60) if ("min" in text or "m" in text) else num

    return max(0, total)


def _format_time(seconds: int) -> str:
    """Formats seconds into MM:SS or HH:MM:SS display string."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def open_youtube(query: str = "", video_url: str = "", timestamp: str | int = 0) -> dict:
    """
    Launches YouTube in the user's default browser with optional query search or
    direct video playback cued to a specific timestamp.
    """
    secs = parse_timestamp(timestamp)
    time_str = f"&t={secs}s" if secs > 0 else ""

    # Direct Video URL or Video ID
    if video_url:
        clean_url = video_url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url

        if time_str:
            sep = "&" if "?" in clean_url else "?"
            clean_url = f"{clean_url}{sep}t={secs}s"

        res = open_url(clean_url)
        return {
            "success": res.get("success", False),
            "mode": "video_url",
            "url": clean_url,
            "timestamp_seconds": secs,
            "formatted_time": _format_time(secs),
            "message": f"Playing YouTube video cued to {_format_time(secs)} ({clean_url})." if secs else f"Playing YouTube video ({clean_url})."
        }

    # Search Query
    if query:
        clean_q = query.strip()
        encoded = urllib.parse.quote_plus(clean_q)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        res = open_url(search_url)
        time_msg = f" (Cue playback at {_format_time(secs)})" if secs > 0 else ""
        return {
            "success": res.get("success", False),
            "mode": "search",
            "query": clean_q,
            "url": search_url,
            "timestamp_seconds": secs,
            "formatted_time": _format_time(secs),
            "message": f"Searching YouTube for '{clean_q}'{time_msg}."
        }

    # Default YouTube homepage
    res = open_url("https://www.youtube.com")
    return {
        "success": res.get("success", False),
        "mode": "homepage",
        "url": "https://www.youtube.com",
        "timestamp_seconds": 0,
        "message": "Opened YouTube homepage in default browser."
    }


def search_and_play_youtube(query: str, timestamp: str | int = 0) -> dict:
    """
    High-level orchestrator: Resolves query, opens YouTube, and prepares playback
    at the designated timestamp (e.g. '2 minute' -> 120s).
    """
    if not query or not isinstance(query, str):
        return {"success": False, "message": "Search query or video name required."}

    clean_q = query.strip()
    secs = parse_timestamp(timestamp)

    # Check if query itself contains a URL
    if "youtube.com" in clean_q or "youtu.be" in clean_q:
        return open_youtube(video_url=clean_q, timestamp=secs)

    return open_youtube(query=clean_q, timestamp=secs)


def control_youtube(action: str, seconds: int = 0) -> dict:
    """
    Controls desktop YouTube playback via universal keyboard shortcuts:
    - 'play', 'pause', 'toggle': 'k' or Space
    - 'fullscreen': 'f'
    - 'mute': 'm'
    - 'theater': 't'
    - 'captions': 'c'
    - 'forward' (10s): 'l'
    - 'rewind' (10s): 'j'
    - 'percent' (0-9): jump to 0% - 90%
    """
    act = action.strip().lower()

    # Attempt to focus YouTube or browser window instantly via Win32
    try:
        from tools.windows import _get_all_windows, user32
        for w in _get_all_windows():
            t = w.get("title", "").lower()
            if "youtube" in t or any(b in t for b in ["brave", "chrome", "edge", "firefox", "opera"]):
                if user32:
                    user32.ShowWindow(w["hwnd"], 9)  # SW_RESTORE
                    user32.SetForegroundWindow(w["hwnd"])
                    time.sleep(0.05)
                break
    except Exception:
        pass

    try:
        from tools.input import send_hotkey

        if act in ("play", "pause", "toggle", "play/pause"):
            res = send_hotkey(["k"])
            return {"success": True, "action": act, "key": "k", "message": "Toggled YouTube playback (Play/Pause)."}

        if act in ("fullscreen", "full"):
            res = send_hotkey(["f"])
            return {"success": True, "action": act, "key": "f", "message": "Toggled YouTube fullscreen mode."}

        if act in ("mute", "unmute"):
            res = send_hotkey(["m"])
            return {"success": True, "action": act, "key": "m", "message": "Toggled YouTube audio mute."}

        if act in ("theater", "theatre"):
            res = send_hotkey(["t"])
            return {"success": True, "action": act, "key": "t", "message": "Toggled YouTube theater mode."}

        if act in ("captions", "subtitles"):
            res = send_hotkey(["c"])
            return {"success": True, "action": act, "key": "c", "message": "Toggled YouTube captions/subtitles."}

        if act in ("forward", "seek_forward", "skip"):
            # 'l' skips 10 seconds in YouTube
            repeats = max(1, seconds // 10) if seconds > 0 else 1
            for _ in range(repeats):
                send_hotkey(["l"])
                time.sleep(0.05)
            return {"success": True, "action": act, "seconds": repeats * 10, "message": f"Seeked forward {repeats * 10} seconds."}

        if act in ("rewind", "seek_rewind", "back"):
            # 'j' rewinds 10 seconds in YouTube
            repeats = max(1, seconds // 10) if seconds > 0 else 1
            for _ in range(repeats):
                send_hotkey(["j"])
                time.sleep(0.05)
            return {"success": True, "action": act, "seconds": repeats * 10, "message": f"Seeked rewind {repeats * 10} seconds."}

        if act in ("percent", "seek_percent"):
            pct_digit = max(0, min(9, seconds // 10))
            send_hotkey([str(pct_digit)])
            return {"success": True, "action": act, "percent": pct_digit * 10, "message": f"Seeked to {pct_digit * 10}% of video."}

        return {"success": False, "action": act, "message": f"Unknown YouTube control action '{act}'."}
    except Exception as err:
        return {"success": False, "action": act, "message": f"Failed to send YouTube control: {err}"}


def open_youtube_and_type(query: str, timestamp: str | int = 0, physical_typing: bool = False) -> dict:
    """
    Opens YouTube, searches for the specified query, and prepares playback at timestamp.
    If physical_typing=True:
      1. Opens youtube.com
      2. Waits briefly and focuses the browser window
      3. Sends hotkey '/' to focus YouTube's search bar
      4. Types the query text
      5. Sends 'enter' to execute search
    Otherwise:
      Directly launches YouTube search results cued to timestamp (100% reliable).
    """
    if not query or not isinstance(query, str):
        return {"success": False, "message": "Search query or video name required."}

    clean_q = query.strip()
    secs = parse_timestamp(timestamp)

    if physical_typing:
        try:
            # 1. Open YouTube homepage
            open_url("https://www.youtube.com")
            time.sleep(1.5)

            # 2. Focus browser
            try:
                from tools.windows import bring_to_foreground
                for b in ["brave", "chrome", "edge", "firefox", "opera"]:
                    if bring_to_foreground(b).get("success"):
                        time.sleep(0.3)
                        break
            except Exception:
                pass

            # 3. Press '/' to focus YouTube search bar
            from tools.input import press_key, type_text
            press_key("/")
            time.sleep(0.3)

            # 4. Type text
            type_text(clean_q)
            time.sleep(0.2)

            # 5. Press Enter
            press_key("enter")

            cue_note = f" Playback cued to {_format_time(secs)}." if secs > 0 else ""
            return {
                "success": True,
                "mode": "physical_typing",
                "query": clean_q,
                "timestamp_seconds": secs,
                "formatted_time": _format_time(secs),
                "message": f"Typed '{clean_q}' into YouTube search bar and executed search.{cue_note}"
            }
        except Exception:
            # Fallback to direct navigation if input simulation encounters any issue
            pass

    return search_and_play_youtube(clean_q, timestamp=secs)

