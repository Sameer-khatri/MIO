"""
MIO Core Runtime - Execution History & Action Memory (core.history)

Provides rolling in-memory and persisted audit trails for all executed tools and actions.
Enables the system (and the future Brain layer) to inspect past actions, answer context queries
like "what did you just do?", track execution latency, and enable rollback/auditability.
"""

from datetime import datetime
import json
import os
import threading
from typing import Any

# Maximum number of recent actions kept in memory
MAX_HISTORY_SIZE = 100

_HISTORY_LOCK = threading.Lock()
_ACTION_HISTORY: list[dict[str, Any]] = []

_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "action_history.json")


def _save_history_to_disk() -> None:
    """Best-effort persistence of recent actions to disk."""
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_ACTION_HISTORY[-MAX_HISTORY_SIZE:], f, indent=2, default=str)
    except Exception:
        pass


def _load_history_from_disk() -> None:
    """Loads historical actions from disk if memory is empty."""
    global _ACTION_HISTORY
    if not _ACTION_HISTORY and os.path.exists(_HISTORY_FILE):
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    _ACTION_HISTORY = data[-MAX_HISTORY_SIZE:]
        except Exception:
            pass


# Initialize history from disk on module import
_load_history_from_disk()


def record_action(
    tool_name: str,
    action: str,
    args: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    duration_ms: float = 0.0,
) -> dict[str, Any]:
    """
    Records a completed tool or action execution into the memory buffer.
    """
    now = datetime.now()
    timestamp_iso = now.isoformat()
    timestamp_human = now.strftime("%H:%M:%S")

    entry = {
        "timestamp": timestamp_iso,
        "time": timestamp_human,
        "tool": tool_name,
        "action": action,
        "args": args or {},
        "result": result or {},
        "success": bool(result.get("success", True) if isinstance(result, dict) else True),
        "message": result.get("message", "") if isinstance(result, dict) else str(result),
        "duration_ms": round(float(duration_ms), 1),
    }

    with _HISTORY_LOCK:
        _ACTION_HISTORY.append(entry)
        if len(_ACTION_HISTORY) > MAX_HISTORY_SIZE:
            _ACTION_HISTORY.pop(0)
        _save_history_to_disk()

    return entry


def get_recent_actions(limit: int = 10) -> list[dict[str, Any]]:
    """
    Returns the most recent N executed actions, newest first.
    """
    with _HISTORY_LOCK:
        items = list(_ACTION_HISTORY)
    return items[-limit:][::-1]


def get_last_action() -> dict[str, Any] | None:
    """
    Returns the single most recent action executed, or None if no actions recorded.
    """
    with _HISTORY_LOCK:
        if not _ACTION_HISTORY:
            return None
        return dict(_ACTION_HISTORY[-1])


def get_history_summary(limit: int = 5) -> str:
    """
    Generates a concise, human-readable summary of the last N actions.
    """
    recent = get_recent_actions(limit=limit)
    if not recent:
        return "No recent actions recorded in history."

    lines = [f"📜 Recent Actions ({len(recent)}):"]
    for i, act in enumerate(recent, 1):
        status_icon = "✅" if act.get("success") else "❌"
        msg = act.get("message") or f"{act.get('tool')}.{act.get('action')}"
        t = act.get("time", "")
        lines.append(f"  {i}. [{t}] {status_icon} {act.get('tool')}.{act.get('action')} — {msg}")

    return "\n".join(lines)


def clear_history() -> dict[str, Any]:
    """
    Clears the action history memory buffer and removes persisted history file.
    """
    global _ACTION_HISTORY
    with _HISTORY_LOCK:
        count = len(_ACTION_HISTORY)
        _ACTION_HISTORY = []
        if os.path.exists(_HISTORY_FILE):
            try:
                os.remove(_HISTORY_FILE)
            except Exception:
                pass

    return {
        "success": True,
        "cleared_count": count,
        "message": f"Cleared {count} historical action record(s)."
    }
