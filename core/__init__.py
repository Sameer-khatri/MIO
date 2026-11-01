"""
MIO Core Runtime - Central Orchestration, Master Registry & Natural Language Router
"""
import os
import sys

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_MIO_DIR = os.path.dirname(_CORE_DIR)

for _p in [_CORE_DIR, _MIO_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .agent import handle_command, run_agent
from .registry import (
    HAND_KITS,
    TOOL_CATALOG,
    list_kits,
    get_kit,
    list_all_tools,
    get_tool_module,
    execute_action,
    execute_tool,
    execute_workflow,
    get_schemas,
)

from .history import (
    record_action,
    get_recent_actions,
    get_last_action,
    get_history_summary,
    clear_history,
)

__all__ = [
    "handle_command",
    "run_agent",
    "HAND_KITS",
    "TOOL_CATALOG",
    "list_kits",
    "get_kit",
    "list_all_tools",
    "get_tool_module",
    "execute_action",
    "execute_tool",
    "execute_workflow",
    "get_schemas",
    "record_action",
    "get_recent_actions",
    "get_last_action",
    "get_history_summary",
    "clear_history",
]
