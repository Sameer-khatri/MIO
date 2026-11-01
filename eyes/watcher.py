"""
MIO Eyes - Visual Watcher & Screen Change Detection Engine (eyes.watcher)

Monitors screen areas for visual change, animation stabilization, and state transitions.
Enables autonomous agents to confirm that clicks or keystrokes produced actual visual changes
(e.g., page loaded, dialog closed, progress bar updated).
"""

import hashlib
import time
from typing import Any

from hands.sensory.screen import take_screenshot, take_region_screenshot


def get_screen_hash(region: tuple[int, int, int, int] | None = None) -> dict[str, Any]:
    """
    Computes a cryptographic visual fingerprint (SHA256) of the screen or specified region.
    region: (x, y, width, height) or None for full screen.
    """
    try:
        if region:
            x, y, w, h = region
            res = take_region_screenshot(x=x, y=y, width=w, height=h)
        else:
            res = take_screenshot()

        if not res.get("success"):
            return {"success": False, "hash": "", "message": res.get("message", "Screenshot failed.")}

        img_path = res.get("file_path", "")
        with open(img_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()

        return {
            "success": True,
            "hash": digest,
            "region": region,
            "file_path": img_path,
            "message": f"Visual hash: {digest[:16]}..."
        }
    except Exception as err:
        return {"success": False, "hash": "", "message": f"Failed to compute screen hash: {err}"}


def wait_for_visual_change(
    region: tuple[int, int, int, int] | None = None,
    timeout: float = 5.0,
    poll_interval: float = 0.15,
) -> dict[str, Any]:
    """
    Waits until the screen or target region visually changes from its initial state.
    Returns as soon as visual mutation is detected, or failure on timeout.
    """
    t0 = time.perf_counter()
    init_res = get_screen_hash(region)
    if not init_res.get("success"):
        return {"success": False, "changed": False, "message": "Failed to capture baseline screen."}

    initial_hash = init_res["hash"]

    while (time.perf_counter() - t0) < timeout:
        time.sleep(poll_interval)
        current = get_screen_hash(region)
        if current.get("success") and current["hash"] != initial_hash:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "success": True,
                "changed": True,
                "elapsed_ms": elapsed_ms,
                "old_hash": initial_hash[:12],
                "new_hash": current["hash"][:12],
                "message": f"Visual change detected after {elapsed_ms}ms."
            }

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "success": False,
        "changed": False,
        "elapsed_ms": elapsed_ms,
        "message": f"No visual change detected within {timeout}s ({elapsed_ms}ms)."
    }


def wait_for_screen_stabilize(
    region: tuple[int, int, int, int] | None = None,
    stable_duration: float = 0.4,
    timeout: float = 6.0,
    poll_interval: float = 0.1,
) -> dict[str, Any]:
    """
    Waits until visual animations or rendering settle (zero visual diff for stable_duration seconds).
    Ideal after opening heavy web pages, switching apps, or launching applications.
    """
    t0 = time.perf_counter()
    last_hash = None
    stable_since = None

    while (time.perf_counter() - t0) < timeout:
        current = get_screen_hash(region)
        if not current.get("success"):
            time.sleep(poll_interval)
            continue

        h = current["hash"]
        now = time.perf_counter()

        if h == last_hash:
            if stable_since is None:
                stable_since = now
            elif (now - stable_since) >= stable_duration:
                elapsed_ms = round((now - t0) * 1000, 1)
                return {
                    "success": True,
                    "stable": True,
                    "elapsed_ms": elapsed_ms,
                    "stable_duration": stable_duration,
                    "message": f"Screen stabilized for {stable_duration}s (total wait: {elapsed_ms}ms)."
                }
        else:
            last_hash = h
            stable_since = now

        time.sleep(poll_interval)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "success": False,
        "stable": False,
        "elapsed_ms": elapsed_ms,
        "message": f"Screen did not stabilize within {timeout}s."
    }
