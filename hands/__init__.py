"""
MIO Hands - Modular Operating System Capability Engine

Organized into 5 Core Hand Kits:
1. Sensory Hand (Sight, Sound & Display)
2. Action Hand (Mouse, Keyboard & Clipboard)
3. Control Hand (Applications & Windows)
4. Storage Hand (Filesystem, Drives & Hasher)
5. Connectivity Hand (Network, Web & System Services)
"""

import os
import sys

_HANDS_DIR = os.path.dirname(os.path.abspath(__file__))
_SUBDIRS = ["sensory", "action", "control", "storage", "connectivity"]

for _sub in [_HANDS_DIR] + [os.path.join(_HANDS_DIR, s) for s in _SUBDIRS]:
    if _sub not in sys.path:
        sys.path.insert(0, _sub)

# Sensory Hand
from hands.sensory import screen, display, audio, brightness, notifications

# Action Hand
from hands.action import mouse, input, clipboard

# Control Hand
from hands.control import applications, windows, processes, installed_apps, flow, terminal

# Storage Hand
from hands.storage import filesystem, archive, drives, hasher

# Connectivity Hand
from hands.connectivity import (
    network,
    wifi_tools,
    ports,
    browser,
    power,
    settings,
    services,
    system_info,
    timer,
    healer,
)

__all__ = [
    # Sensory
    "screen", "display", "audio", "brightness", "notifications",
    # Action
    "mouse", "input", "clipboard",
    # Control
    "applications", "windows", "processes", "installed_apps", "flow", "terminal",
    # Storage
    "filesystem", "archive", "drives", "hasher",
    # Connectivity
    "network", "wifi_tools", "ports", "browser", "power", "settings",
    "services", "system_info", "timer", "healer",
]
