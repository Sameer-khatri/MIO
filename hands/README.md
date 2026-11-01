# MIO Hands - Operating System Manipulation & Motor Action Engine

> **Architecture Role:** Physical OS Manipulation & Motor Control Subsystem  
> **Tool Inventory:** 29 Native Tools across 5 Kits  
> **Dependencies:** 100% Native Python standard library + Win32 ctypes, winreg, and PowerShell. Zero external `pip` dependencies.

---

## 1. Overview & Decoupling Philosophy

**MIO Hands** is the motor execution organ of MIO. It handles all physical and system-level manipulation of the Windows environment:
- **Hands:** Physical interaction, window management, keyboard/mouse input, files, network, shell execution, and hardware controls.
- **Eyes:** Visual perception, OCR, UI tree inspection, coordinate grounding, and visual diffing.
- **Mouth:** Vocal speech synthesis, voice personas, rate/volume adjustment, and audio output.
- **Ears:** Microphone capture, audio metering, and voice hearing.

Hands are strictly decoupled: they never perform visual OCR (delegated to Eyes) or vocal speech output (delegated to Mouth). Each tool in Hands operates as a deterministic, high-performance primitive with structured inputs and JSON return types.

---

## 2. Architecture: The 5 Hand Kits

```
hands/
├── sensory/          # SENSORY KIT: Sight, Sound, Display & Toast Alerts
│   ├── screen.py     # Fullscreen & bounding-box PNG screenshots, dimension checks
│   ├── display.py    # Monitor metrics, multi-display enumeration, refresh rates, DPI scaling
│   ├── audio.py      # Master volume, mute toggles, Windows SMTC real-time media metadata, mic mute
│   ├── brightness.py # Display brightness query/set, smooth brightness fading
│   └── notifications.py # Desktop toast alerts, audio chimes, frequency tone beeps
│
├── action/           # ACTION KIT: Physical Mouse, Keyboard & Clipboard Manipulation
│   ├── mouse.py      # Move cursor, left/right/double clicks, drag-and-drop, vertical mouse scroll
│   ├── input.py      # Global hotkeys (Win+E, Win+I, Alt+F4), SendInput unicode typing, single key press
│   └── clipboard.py  # System clipboard read/write/append, active clipboard format inspection
│
├── control/          # CONTROL KIT: Windows, Processes, Applications & Shell Execution
│   ├── applications.py # Start Menu index, Registry App Paths, run as Administrator
│   ├── windows.py    # Minimize, maximize, restore, split-screen snap, pin always-on-top, focus
│   ├── processes.py  # Running processes query, PID verification, terminate process, top RAM/CPU rankings
│   ├── installed_apps.py # 32/64-bit software registry scanner, version detection, uninstall command extraction
│   ├── terminal.py   # Isolated PowerShell/CMD execution, exit code verification, environment variables
│   └── flow.py       # Pipelined compound task execution, window synchronization, work/chill preset modes
│
├── storage/          # STORAGE KIT: Filesystem, Archives, Drives & Cryptographic Hashes
│   ├── filesystem.py # File CRUD, desktop auto-organize, recursive file search, folder sizing
│   ├── archive.py    # Zip/Tar archives, extraction with Zip-Slip path traversal protection
│   ├── drives.py     # Fixed/removable disk drives, capacity warnings, safe USB drive ejection
│   └── hasher.py     # MD5, SHA-1, SHA-256 checksums, text hashing, cryptographic file diffing
│
└── connectivity/     # CONNECTIVITY KIT: Networking, Wireless, Ports, Web & System Self-Healing
    ├── network.py    # Local LAN IP, public WAN IP, ping latency, network adapter state
    ├── wifi_tools.py # Live Wi-Fi scanning, saved profiles, cleartext password recovery, connect/forget
    ├── ports.py      # Active TCP/UDP listening ports, port holding process identification, kill port blocker
    ├── browser.py    # Browser routing, YouTube resolution with timestamp cueing, headless web text & search
    ├── power.py      # Battery state, AC status, lock screen, monitor standby, sleep, hibernate, shutdown
    ├── settings.py   # Windows Dark/Light theme toggle, desktop wallpaper query/set, transparency effects
    ├── services.py   # Windows Service Control Manager queries, start/stop/restart, startup type configuration
    ├── system_info.py # CPU/RAM/GPU load, physical cores, motherboard BIOS info, system uptime
    ├── timer.py      # Background countdown timers with toast notifications, precision stopwatches
    └── healer.py     # Autonomous OS self-healing: RAM trim (EmptyWorkingSet), hung window recovery, DNS flush
```

---

## 3. Quick Usage

All tools can be imported directly from their respective kits or via the unified `hands` package:

```python
import hands

# 1. Action: Mouse & Typing
hands.mouse.move(500, 300)
hands.mouse.click()
hands.input.type_text("Hello World")
hands.input.press_hotkey(["win", "d"])

# 2. Control: Window & App Management
hands.applications.launch_app("notepad")
hands.windows.snap_window("left")
hands.flow.set_work_mode()

# 3. Storage: Desktop Organizing & File Search
hands.filesystem.organize_desktop()
matches = hands.filesystem.search_files("*.pdf", root_dir="desktop")

# 4. Connectivity: Network & Power
battery = hands.power.get_battery_status()
wifi_pass = hands.wifi_tools.get_saved_wifi_passwords()
headless_text = hands.browser.fetch_webpage_text("https://example.com")

# 5. Sensory: Display & Notifications
hands.brightness.set_brightness(75)
hands.notifications.send_toast("MIO", "All systems operational.")
```

---

## 4. Safety & System Protection Guardrails

1. **Destructive Command Guard (`hands/control/terminal.py`):**
   - Commands attempting to format disks (`format c:`), wipe system partitions (`rmdir /s /q c:\windows`), or delete boot structures are intercepted and blocked.
2. **Directory Traversal (Zip-Slip) Defense (`hands/storage/archive.py`):**
   - Archive extraction validates every internal archive path against canonical destination bounds to eliminate arbitrary file overwrites.
3. **Collision-Safe File Operations (`hands/storage/filesystem.py`):**
   - File reorganization automatically resolves filename collisions with incremental indices (`file (1).ext`) instead of blindly overwriting existing files.
4. **Isolated Process Boundaries:**
   - Background tasks and shell commands enforce execution timeouts to prevent hanging background subagents.
