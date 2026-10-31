import os
import shutil
import subprocess
import urllib.parse
import webbrowser


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
        webbrowser.open(clean_url, new=2)  # new=2 means open in new tab if possible
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
    Opens an Incognito/Private window in the installed browser (Chrome, Edge, Brave, or Firefox).
    """
    target = url.strip() if url else "https://google.com"
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    # Check available browsers
    candidates = [
        ("chrome.exe", ["chrome.exe", "--incognito", target]),
        ("msedge.exe", ["msedge.exe", "-inprivate", target]),
        ("brave.exe", ["brave.exe", "--incognito", target]),
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

    # Fallback to standard open
    return open_url(target)
