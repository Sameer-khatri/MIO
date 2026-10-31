"""
MIO System Agent Package
"""

try:
    from .registry import (
        HAND_KITS,
        TOOL_CATALOG,
        list_kits,
        get_kit,
        list_all_tools,
        execute_action,
        get_schemas,
    )
except ImportError:
    from registry import (
        HAND_KITS,
        TOOL_CATALOG,
        list_kits,
        get_kit,
        list_all_tools,
        execute_action,
        get_schemas,
    )

__all__ = [
    "HAND_KITS",
    "TOOL_CATALOG",
    "list_kits",
    "get_kit",
    "list_all_tools",
    "execute_action",
    "get_schemas",
]
