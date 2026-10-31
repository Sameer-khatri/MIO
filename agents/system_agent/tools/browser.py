import os
import shutil
import subprocess
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
