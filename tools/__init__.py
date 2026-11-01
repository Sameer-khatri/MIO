"""
MIO Tools - Namespace Package mapping directly to the 5 Hand Kits:
- hands/sensory
- hands/action
- hands/control
- hands/storage
- hands/connectivity
"""

import os

_HANDS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hands"))

__path__ = [
    os.path.join(_HANDS_DIR, "sensory"),
    os.path.join(_HANDS_DIR, "action"),
    os.path.join(_HANDS_DIR, "control"),
    os.path.join(_HANDS_DIR, "storage"),
    os.path.join(_HANDS_DIR, "connectivity"),
]
