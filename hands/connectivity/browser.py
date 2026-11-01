import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
import winreg


BROWSER_EXECUTABLES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "brave": "brave.exe",
    "firefox": "firefox.exe",
}

# Recency sort param: sorts YouTube results by upload date (newest first)
_YT_SORT_UPLOAD_DATE = "&sp=CAI%253D"
_RECENCY_WORDS = frozenset(("latest", "recent", "new", "newest", "today"))


def _yt_sort_param(query: str) -> str:
    """Returns YouTube upload-date sort param if recency keywords are in query."""
    return _YT_SORT_UPLOAD_DATE if any(w in query.lower().split() for w in _RECENCY_WORDS) else ""


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
        lower_q = clean_q.lower()
        sort_param = "&sp=CAI%253D" if any(w in lower_q.split() for w in ("latest", "recent", "new", "newest")) else ""
        search_url = f"https://www.youtube.com/results?search_query={encoded}{sort_param}"
    elif "bing" in engine_norm:
        search_url = f"https://www.bing.com/search?q={encoded}"
    elif "duck" in engine_norm or "ddg" in engine_norm:
        search_url = f"https://duckduckgo.com/?q={encoded}"
    elif "wiki" in engine_norm:
        search_url = f"https://en.wikipedia.org/wiki/Special:Search?search={encoded}"
    elif "yahoo" in engine_norm:
        search_url = f"https://search.yahoo.com/search?p={encoded}"
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


def open_multiple_tabs(urls: list[str], delay_between: float = 0.2) -> dict:
    """
    Opens multiple URLs in separate tabs in the user's default browser.
    """
    if not urls:
        return {"success": False, "count": 0, "message": "No URLs provided."}

    opened = []
    for i, u in enumerate(urls):
        res = open_url(u)
        if res.get("success"):
            opened.append(u)
        if i < len(urls) - 1 and delay_between > 0:
            time.sleep(delay_between)

    return {
        "success": len(opened) == len(urls),
        "total": len(urls),
        "opened_count": len(opened),
        "urls": opened,
        "message": f"Opened {len(opened)}/{len(urls)} tabs in browser."
    }


def batch_search(queries: list[str], engine: str = "youtube", delay_between: float = 0.2) -> dict:
    """
    Opens a separate browser tab for each search query on the specified search engine.
    """
    if not queries:
        return {"success": False, "count": 0, "message": "No queries provided."}

    urls = []
    engine_norm = engine.strip().lower()

    for q in queries:
        clean_q = q.strip()
        # If the item looks like a URL or domain, open directly
        if clean_q.startswith("http://") or clean_q.startswith("https://") or ("." in clean_q and "/" not in clean_q.split(".")[0]):
            urls.append(clean_q)
            continue

        encoded = urllib.parse.quote_plus(clean_q)
        if "youtube" in engine_norm or "yt" in engine_norm:
            lower_q = clean_q.lower()
            sort_param = "&sp=CAI%253D" if any(w in lower_q.split() for w in ("latest", "recent", "new", "newest")) else ""
            urls.append(f"https://www.youtube.com/results?search_query={encoded}{sort_param}")
        elif "bing" in engine_norm:
            urls.append(f"https://www.bing.com/search?q={encoded}")
        elif "duck" in engine_norm or "ddg" in engine_norm:
            urls.append(f"https://duckduckgo.com/?q={encoded}")
        elif "wiki" in engine_norm:
            urls.append(f"https://en.wikipedia.org/wiki/Special:Search?search={encoded}")
        else:
            urls.append(f"https://www.google.com/search?q={encoded}")

    res = open_multiple_tabs(urls, delay_between=delay_between)
    res["engine"] = engine_norm
    res["queries"] = queries
    query_lines = "\n".join(f"  {i}. {q}" for i, q in enumerate(queries, 1))
    res["message"] = f"Opened {len(res.get('urls', []))} {engine_norm.title()} tabs:\n{query_lines}"
    return res


def parse_multi_tab_query(user_input: str) -> dict | None:
    """
    Parses natural language requests to open multiple tabs.
    Handles:
      - 'open 4 youtube tabs and search for techno gamer in first, bbs in second, triggered insan in 3rd and mr beast in 4th'
      - 'open 3 tabs for techno gamer, bbs, and mr beast on youtube'
      - 'open 2 tabs: github.com, google.com'
    """
    cleaned = user_input.strip()
    lower = cleaned.lower()
    if not any(k in lower for k in ("tab", "tabs")):
        return None

    engine = "google"
    if "youtube" in lower or "yt" in lower:
        engine = "youtube"
    elif "bing" in lower:
        engine = "bing"
    elif "duck" in lower or "ddg" in lower:
        engine = "duckduckgo"
    elif "wiki" in lower:
        engine = "wikipedia"

    ordinal_words = {
        "1st": 1, "first": 1, "one": 1, "1": 1,
        "2nd": 2, "second": 2, "two": 2, "2": 2,
        "3rd": 3, "third": 3, "three": 3, "3": 3,
        "4th": 4, "fourth": 4, "four": 4, "4": 4,
        "5th": 5, "fifth": 5, "five": 5, "5": 5,
        "6th": 6, "sixth": 6, "six": 6, "6": 6,
        "7th": 7, "seventh": 7, "seven": 7, "7": 7,
        "8th": 8, "eighth": 8, "eight": 8, "8": 8,
    }

    ord_pattern = re.compile(
        r"(.+?)\s+(?:in|as|on)\s+(1st|first|one|1|2nd|second|two|2|3rd|third|three|3|4th|fourth|four|4|5th|fifth|five|5|6th|sixth|six|6|7th|seventh|seven|7|8th|eighth|eight|8)",
        re.IGNORECASE
    )
    if ord_pattern.search(cleaned):
        m = re.search(r"(?:search(?:\s+for)?|tabs(?:\s+for|\s*:)?)\s+(.+)$", cleaned, re.IGNORECASE)
        payload = m.group(1).strip() if m else cleaned
        norm_payload = re.sub(r",?\s+and\s+(?=[^,]+?\s+(?:in|as|on)\s+\w+)", ", ", payload, flags=re.I)
        chunks = [c.strip() for c in norm_payload.split(",") if c.strip()]
        parsed = {}
        for c in chunks:
            match = ord_pattern.search(c)
            if match:
                q_text = match.group(1).strip()
                q_text = re.sub(r"^(?:and\s+)?(?:search(?:\s+for)?|open|for)\s+", "", q_text, flags=re.I).strip()
                idx = ordinal_words.get(match.group(2).lower(), 99)
                parsed[idx] = q_text
        if parsed:
            return {"engine": engine, "queries": [parsed[k] for k in sorted(parsed.keys())]}

    # List check: 'tabs for A, B, C' or 'tabs: A, B, C'
    list_m = re.search(r"(?:tabs\s+(?:for|with|of|search|and\s+search(?:\s+for)?)|tabs\s*:)\s+(.+)$", cleaned, re.IGNORECASE)
    if list_m:
        raw_list = list_m.group(1).strip()
        raw_list = re.sub(r"\s+on\s+(?:youtube|google|bing|browser)$", "", raw_list, flags=re.I).strip()
        items = [i.strip() for i in re.split(r",|\s+and\s+", raw_list) if i.strip()]
        if len(items) >= 2:
            return {"engine": engine, "queries": items}

    return None


POPULAR_SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "reddit": "https://www.reddit.com",
    "chatgpt": "https://chatgpt.com",
    "openai": "https://openai.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "wikipedia": "https://www.wikipedia.org",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "linkedin": "https://www.linkedin.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "stackoverflow": "https://stackoverflow.com",
    "duckduckgo": "https://duckduckgo.com",
    "bing": "https://www.bing.com",
    "yahoo": "https://www.yahoo.com",
    "claude": "https://claude.ai",
    "perplexity": "https://www.perplexity.ai",
    "gemini": "https://gemini.google.com",
    "spotify": "https://open.spotify.com",
    "twitch": "https://www.twitch.tv",
    "discord": "https://discord.com/app",
    "notion": "https://www.notion.so",
}


def open_website(site_or_url: str) -> dict:
    """
    Resolves popular website names or URLs and opens them directly in the user's browser.
    Handles 'github', 'google', 'reddit', 'chatgpt', 'youtube', or full URLs like 'reddit.com'.
    """
    if not site_or_url or not isinstance(site_or_url, str):
        return {"success": False, "message": "Website name or URL required."}

    clean = site_or_url.strip()
    lower = clean.lower().rstrip("/").replace("in browser", "").replace("website", "").replace("site", "").strip()

    if lower in POPULAR_SITES:
        target_url = POPULAR_SITES[lower]
        res = open_url(target_url)
        res["site"] = lower
        res["message"] = f"Opened {lower.title()} ({target_url}) in default browser."
        return res

    # Check for domain extensions (e.g. github.com, news.ycombinator.com)
    domain_exts = (".com", ".org", ".net", ".io", ".ai", ".co", ".in", ".edu", ".gov", ".app", ".dev", ".xyz", ".me")
    if any(lower.endswith(ext) or f"{ext}/" in lower for ext in domain_exts):
        target_url = clean if clean.startswith("http://") or clean.startswith("https://") else f"https://{clean}"
        res = open_url(target_url)
        res["site"] = clean
        res["message"] = f"Opened '{clean}' in default browser."
        return res

    if clean.startswith("http://") or clean.startswith("https://") or clean.startswith("www."):
        res = open_url(clean)
        return res

    # Fallback: Google search for this website
    return search_web(clean, engine="google")


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
        lower_q = clean_q.lower()
        encoded = urllib.parse.quote_plus(clean_q)
        sort_param = "&sp=CAI%253D" if any(w in lower_q.split() for w in ("latest", "recent", "new", "newest")) else ""
        search_url = f"https://www.youtube.com/results?search_query={encoded}{sort_param}"

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


def get_top_youtube_video_id(query: str) -> str | None:
    """
    Resolves the top YouTube video ID for a search query without any API keys.
    Applies upload-date sort when recency keywords are detected so the
    newest video is always the first result returned.
    """
    if not query or not isinstance(query, str):
        return None
    try:
        clean_q = query.strip()
        encoded = __import__("urllib.parse", fromlist=["quote_plus"]).quote_plus(clean_q)
        sort_param = _yt_sort_param(clean_q)
        search_url = f"https://www.youtube.com/results?search_query={encoded}{sort_param}"
        import urllib.request
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        seen: set[str] = set()
        for vid in __import__("re").findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html):
            if len(vid) == 11 and vid not in seen:
                seen.add(vid)
                return vid
    except Exception:
        pass
    return None
    try:
        clean_q = query.strip()
        lower_q = clean_q.lower()
        encoded = urllib.parse.quote_plus(clean_q)
        sort_param = "&sp=CAI%253D" if any(w in lower_q.split() for w in ("latest", "recent", "new", "newest")) else ""
        search_url = f"https://www.youtube.com/results?search_query={encoded}{sort_param}"
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            html = response.read().decode("utf-8", errors="ignore")

        matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html) or re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
        for vid in matches:
            if len(vid) == 11 and vid not in ("shorts", "feed", "channel"):
                return vid
    except Exception:
        pass
    return None


def search_and_play_youtube(query: str, timestamp: str | int = 0, direct_play: bool = True) -> dict:
    """
    High-level orchestrator: Resolves query to the #1 video result, launches the video,
    and cues playback directly at the designated timestamp (e.g. '2 minute' -> 120s).
    """
    if not query or not isinstance(query, str):
        return {"success": False, "message": "Search query or video name required."}

    clean_q = query.strip()
    secs = parse_timestamp(timestamp)

    # Check if query itself contains a URL or video ID
    if "youtube.com" in clean_q or "youtu.be" in clean_q:
        return open_youtube(video_url=clean_q, timestamp=secs)

    if direct_play:
        top_vid = get_top_youtube_video_id(clean_q)
        if top_vid:
            direct_url = f"https://www.youtube.com/watch?v={top_vid}"
            res = open_youtube(video_url=direct_url, timestamp=secs)
            time_msg = f" at {_format_time(secs)}" if secs > 0 else ""
            res["query"] = clean_q
            res["video_id"] = top_vid
            res["message"] = f"Playing '{clean_q}' on YouTube{time_msg} ({res.get('url')})."
            return res

    # Fallback to search results page
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
        from hands.control.windows import _get_all_windows, user32
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
        from hands.action.input import send_hotkey

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
                from hands.control.windows import bring_to_foreground
                for b in ["brave", "chrome", "edge", "firefox", "opera"]:
                    if bring_to_foreground(b).get("success"):
                        time.sleep(0.3)
                        break
            except Exception:
                pass

            # 3. Press '/' to focus YouTube search bar
            from hands.action.input import press_key, type_text
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


def fetch_webpage_text(url: str, max_chars: int = 5000) -> dict:
    """
    Fetches a webpage via HTTP request without opening a browser window.
    Extracts page title, headings, and clean readable body text.
    Zero external dependencies (uses standard library urllib & html.parser).
    """
    import html
    import re
    import urllib.request
    from html.parser import HTMLParser

    if not url or not isinstance(url, str):
        return {"success": False, "message": "Valid URL is required."}

    target_url = url.strip()
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        target_url = "https://" + target_url

    class CleanTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title = ""
            self.in_title = False
            self.in_script = False
            self.text_parts = []
            self.links = []

        def handle_starttag(self, tag, attrs):
            if tag.lower() == "title":
                self.in_title = True
            elif tag.lower() in ("script", "style", "noscript"):
                self.in_script = True
            elif tag.lower() == "a":
                href = dict(attrs).get("href")
                if href and href.startswith("http"):
                    self.links.append(href)

        def handle_endtag(self, tag):
            if tag.lower() == "title":
                self.in_title = False
            elif tag.lower() in ("script", "style", "noscript"):
                self.in_script = False
            elif tag.lower() in ("p", "div", "br", "h1", "h2", "h3", "h4", "li"):
                self.text_parts.append("\n")

        def handle_data(self, data):
            if self.in_title:
                self.title += data
            elif not self.in_script:
                cleaned = data.strip()
                if cleaned:
                    self.text_parts.append(cleaned + " ")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get_content_type()
            if "text/html" not in content_type and "text/plain" not in content_type:
                return {
                    "success": False,
                    "url": target_url,
                    "content_type": content_type,
                    "message": f"Unsupported content type: {content_type} (expected HTML or text)."
                }
            raw_html = resp.read().decode("utf-8", errors="replace")

        parser = CleanTextExtractor()
        parser.feed(raw_html)

        raw_text = "".join(parser.text_parts)
        # Normalize whitespace
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
        trimmed_text = cleaned_text[:max_chars]

        title = html.unescape(parser.title).strip() or target_url
        return {
            "success": True,
            "url": target_url,
            "title": title,
            "text": trimmed_text,
            "char_count": len(trimmed_text),
            "links_sample": parser.links[:10],
            "message": f"Fetched '{title}' ({len(trimmed_text)} characters)."
        }
    except Exception as err:
        return {"success": False, "url": target_url, "message": f"Failed to fetch webpage: {err}"}


def search_web_summary(query: str, max_results: int = 5) -> dict:
    """
    Performs an instant web search and returns structured search results (titles, links, snippets)
    without opening browser windows, ideal for AI Brain factual grounding.
    """
    import html
    import json
    import re
    import urllib.parse
    import urllib.request

    if not query or not isinstance(query, str):
        return {"success": False, "results": [], "message": "Search query is required."}

    clean_q = query.strip()
    encoded = urllib.parse.quote_plus(clean_q)
    # DuckDuckGo Lite / HTML API
    api_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        results = []
        # Check abstract
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", clean_q),
                "url": data.get("AbstractURL", ""),
                "snippet": data.get("AbstractText", ""),
            })

        # Check related topics
        for item in data.get("RelatedTopics", []):
            if isinstance(item, dict) and "Text" in item and "FirstURL" in item:
                results.append({
                    "title": item.get("Text", "").split(" - ")[0],
                    "url": item.get("FirstURL", ""),
                    "snippet": item.get("Text", ""),
                })
            if len(results) >= max_results:
                break

        if results:
            return {
                "success": True,
                "query": clean_q,
                "count": len(results),
                "results": results,
                "message": f"Found {len(results)} search result(s) for '{clean_q}'."
            }

        # Fallback to direct web link
        web_link = f"https://duckduckgo.com/?q={encoded}"
        return {
            "success": True,
            "query": clean_q,
            "count": 1,
            "results": [{"title": clean_q, "url": web_link, "snippet": f"Web search for {clean_q}"}],
            "message": f"Web search link ready for '{clean_q}'."
        }
    except Exception as err:
        return {"success": False, "query": clean_q, "results": [], "message": f"Web search error: {err}"}

