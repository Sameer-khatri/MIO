# MIO

An autonomous multi-agent AI ecosystem for local workflow and OS automation. Seamlessly bridging OS-level operations, physical desktop hands, and future intelligence layers.

---

## Workspace Structure

The project is cleanly structured into decoupled, zero-external-dependency autonomous agents:

```text
mio/
├── agents/
│   │
│   ├── system_agent/           # MIO's Hands (Windows OS Execution Engine)
│   │   ├── registry.py         # Master Inventory Registry & Hand Kits catalog
│   │   ├── inventory.py        # Import alias for registry.py
│   │   ├── agent.py            # Terminal interactive command loop
│   │   ├── app_memory.json     # Local machine application aliases & memory (git-ignored)
│   │   │
│   │   ├── tools/              # 26 Decoupled Standalone Tools (Python Stdlib Only)
│   │   │   ├── screen.py       # Full & region screenshots, PNG dimensions
│   │   │   ├── mouse.py        # Moves, clicks, drag-and-drop, scroll
│   │   │   ├── input.py        # Hotkeys (Win+E, Win+I, Alt+F4) & typing
│   │   │   ├── audio.py        # Volume, media keys, SAPI speech synthesis
│   │   │   ├── display.py      # Monitor metrics, multi-monitor enumeration, refresh rates
│   │   │   ├── brightness.py   # Display brightness levels and fading
│   │   │   ├── notifications.py# Toast notifications, chimes, frequency beeps
│   │   │   ├── clipboard.py    # Read/write/append clipboard, inspect formats
│   │   │   ├── filesystem.py   # List, create, copy, move, rename, delete, head/tail, folder size
│   │   │   ├── archive.py      # Zip/Tar creation, extraction (Zip-Slip safe), integrity testing
│   │   │   ├── drives.py       # Disk usage, removable USBs, space warnings, USB eject
│   │   │   ├── hasher.py       # MD5/SHA1/SHA256 checksums, text hashing, file comparison
│   │   │   ├── network.py      # Local IP, public WAN IP, ping latency, Wi-Fi info
│   │   │   ├── wifi_tools.py   # Wi-Fi scanning, saved profiles, password recovery, connect
│   │   │   ├── ports.py        # Listening ports, process on port, kill port blocker, port scan
│   │   │   ├── browser.py      # Default browser, incognito windows, specific browser routing
│   │   │   ├── power.py        # Battery status, workstation lock, screen off, sleep, hibernate
│   │   │   ├── settings.py     # Dark/light theme toggle, wallpaper get/set, transparency
│   │   │   ├── services.py     # Windows services status, start, stop, restart, startup config
│   │   │   ├── system_info.py  # CPU/RAM/GPU usage, physical cores, motherboard BIOS
│   │   │   ├── processes.py    # Process listing, running verification, kill process, top RAM
│   │   │   ├── windows.py      # Window minimize/maximize/restore, resize, snap left/right, pin on top
│   │   │   ├── applications.py # Launch apps, run as Administrator, default file associations
│   │   │   ├── installed_apps.py# Registry software lookup, version query, uninstall strings
│   │   │   ├── timer.py        # Countdown timers, system uptime, precision stopwatches
│   │   │   └── healer.py       # Self-healing: RAM trim, hung window recovery, DNS flush, cache purge
│   │   │
│   │   └── tests/              # 136 Automated Unit Tests (100% Passing)
│   │       ├── test_registry.py
│   │       └── test_system_agent.py
│   │
│   └── aegis/                  # Autonomous Laptop Doctor & Hardware Guardian
│       ├── aegis.py            # Hardware vitals, 0-100 health score, prescriptions & treatments
│       ├── test_aegis.py       # 12 Automated Unit Tests (100% Passing)
│       └── README.md           # Aegis architecture & clinic consultation guide
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Running the Unit Tests

All 26 tools, the master inventory registry, and the Aegis doctor suite run with **zero external pip dependencies** (pure Python standard library & Windows native APIs):

```bash
# Run System Agent & Master Registry Unit Tests (136 tests)
python -m unittest discover -s agents/system_agent/tests -v

# Run Aegis Laptop Doctor Unit Tests (12 tests)
python -m unittest agents/aegis/test_aegis.py -v
```

---

## Running the Agents

### System Agent (Hands Execution Loop)
```bash
python agents/system_agent/agent.py
```

### Aegis (Laptop Doctor Consultation CLI)
```bash
python agents/aegis/aegis.py
```
