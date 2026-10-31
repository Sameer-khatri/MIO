# MIO System Agent & Hands Inventory

The **MIO System Agent** is MIO's execution body—the physical and digital "hands" that interact directly with the local Windows operating system. It provides 25 completely decoupled, zero-dependency tools organized into 5 modular **Hand Kits**, exposed through a centralized **Inventory Registry**.

---

## Architecture & Folder Structure

```text
agents/system_agent/
│
├── registry.py                 # Master Inventory Catalog, Hand Kit definitions & dynamic dispatcher
├── inventory.py                # Direct alias for registry.py
├── agent.py                    # Terminal interactive interface (command loop)
├── app_memory.json             # Local machine app memory & alias database (git-ignored)
│
├── tools/                      # 25 Standalone, Decoupled Windows Tools
│   │
│   ├── [Sensory Hand]
│   ├── screen.py               # Screenshots (full & bounding-box regions) + PNG binary dimension parser
│   ├── display.py              # Primary display info, multi-monitor enumeration & refresh rates (Hz)
│   ├── audio.py                # Master volume, media playback keys, SAPI text-to-speech & audio devices
│   ├── brightness.py           # Screen brightness levels, stepping, and smooth fading
│   ├── notifications.py        # Desktop toast alerts, audio chimes, frequency beeps & sound patterns
│   │
│   ├── [Action Hand]
│   ├── mouse.py                # Cursor coordinates, relative moves, clicks, scroll, and drag-and-drop
│   ├── input.py                # Keyboard combos, OS hotkeys (Win+E, Win+I, Alt+F4), and SendInput typing
│   ├── clipboard.py            # Clipboard read/write/append/clear & clipboard format inspection
│   │
│   ├── [Control Hand]
│   ├── applications.py         # Launch apps, run as Administrator, open files & manage app memory
│   ├── windows.py              # Enumerate windows, minimize, maximize, restore, focus, resize & snap
│   ├── processes.py            # Process listing, running verification, process termination & top RAM users
│   ├── installed_apps.py       # Windows Registry software scanner, version lookup & uninstall strings
│   │
│   ├── [Storage Hand]
│   ├── filesystem.py           # List, create, copy, move, rename, recycle bin delete, head/tail & folder size
│   ├── archive.py              # Create/extract zip (with Zip-Slip safety), tar/tar.gz & test archive integrity
│   ├── drives.py               # Storage drives, removable USB listing, space warnings & safe USB eject
│   ├── hasher.py               # Cryptographic hashes (MD5, SHA1, SHA256), verification & byte-by-byte compare
│   │
│   └── [Connectivity Hand]
│       ├── network.py          # Local IP, public WAN IP, ping latency/packet loss & Wi-Fi interface status
│       ├── wifi_tools.py       # Scan networks, list saved profiles, extract cleartext passwords & connect
│       ├── ports.py            # Listening ports, process lookup on port, kill port blocker & port scanner
│       ├── browser.py          # Default browser, incognito windows, specific browser routing & batch tabs
│       ├── power.py            # Battery status, workstation lock, screen off, sleep, hibernate & power plan
│       ├── settings.py         # Dark/light theme query & toggle, desktop wallpaper get/set & transparency
│       ├── services.py         # Windows services list, status, start, stop, restart & startup configuration
│       ├── system_info.py      # CPU usage/cores/threads, RAM capacity/load, GPU specs & motherboard BIOS
│       └── timer.py            # Countdown timers with sound, system uptime duration & multi-lap stopwatch
│
└── tests/
    ├── test_registry.py        # Tests for Hand Kits, catalog enumeration & dynamic action dispatch
    └── test_system_agent.py    # Exhaustive unit test suite covering all 25 tools (128 tests)
```

---

## The 5 Modular Hand Kits

| Kit Name | Identity | Member Tools | Primary Purpose |
|---|---|---|---|
| **`sensory`** | **Sensory Hand** | `screen`, `display`, `audio`, `brightness`, `notifications` | Sees the screen, inspects monitors, speaks via SAPI, plays sound patterns, and adjusts display brightness. |
| **`action`** | **Action Hand** | `mouse`, `input`, `clipboard` | Moves cursor, performs clicks and smooth drag-and-drops, triggers keyboard hotkeys, types text, and reads/writes clipboard. |
| **`control`** | **Control Hand** | `applications`, `windows`, `processes`, `installed_apps` | Opens apps (standard and admin), snaps/pins windows, terminates processes, and discovers installed software. |
| **`storage`** | **Storage Hand** | `filesystem`, `archive`, `drives`, `hasher` | Manipulates files and folders safely, computes folder sizes, creates/tests archives, and verifies cryptographic checksums. |
| **`connectivity`** | **Connectivity Hand** | `network`, `wifi_tools`, `ports`, `browser`, `power`, `settings`, `services`, `system_info`, `timer` | Manages internet reachability, Wi-Fi connections, open ports, web browser sessions, power states, and Windows services. |

---

## Dynamic Execution (No Hardcoded Commands Needed)

Any AI brain, sub-agent, or external script can execute actions directly without parsing text command strings:

```python
from agents.system_agent.registry import execute_action, list_kits, get_schemas

# 1. Take a screenshot
execute_action("screen", "take_screenshot")

# 2. Kill whatever process is blocking port 3000
execute_action("ports", "kill_port_process", port=3000)

# 3. Snap an application window to the right half of the screen
execute_action("windows", "snap_window", app_name="Notepad", side="right")

# 4. Generate AI tool schemas (OpenAI / Gemini / Ollama compatible)
schemas = get_schemas("sensory")
```

---

## Test Verification

The entire System Agent suite is covered by automated unit tests:
```bash
python -m unittest discover -s agents/system_agent/tests -v
```
**Status: 134 tests passing (100% OK).**
