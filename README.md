# MIO (Machine Intelligence Operator)

An autonomous multi-agent AI ecosystem for local Windows operating system automation, hardware guardian care, and desktop intelligence. Zero external `pip` dependencies — 100% native Python standard library and Win32 ctypes.

---

## Architecture Overview

MIO decouples **Hands** (physical OS manipulation instruments) from **People** (autonomous specialized personas):

```text
mio/
├── hands/                    # MIO'S HANDS (Operating System Manipulation Instruments)
│   ├── sensory/              # SENSORY HAND (Sight, Sound & Visual Environment)
│   │   ├── screen.py         # Full & region screenshots, PNG dimensions
│   │   ├── display.py        # Monitor metrics, multi-monitor enumeration, refresh rates
│   │   ├── audio.py          # Master volume, media controls, SAPI text-to-speech, audio endpoints
│   │   ├── brightness.py     # Display brightness levels and smooth fading
│   │   └── notifications.py  # Toast notifications, audio chimes, frequency beeps
│   │
│   ├── action/               # ACTION HAND (Physical Interaction & Input)
│   │   ├── mouse.py          # Moves, clicks, double-clicks, drag-and-drop, scroll
│   │   ├── input.py          # Hotkeys (Win+E, Win+I, Alt+F4), SendInput typing, single key press
│   │   └── clipboard.py      # Read/write/append clipboard, inspect formats
│   │
│   ├── control/              # CONTROL HAND (Applications & Windows)
│   │   ├── applications.py   # Start Menu indexing, registry app paths, app memory learning, auto-launch
│   │   ├── windows.py        # Window minimize/maximize/restore, snap left/right, pin on top, focus
│   │   ├── processes.py      # Process listing, running verification, kill process, top memory hogs
│   │   └── installed_apps.py # Registry software lookup, version query, uninstall strings
│   │
│   ├── storage/              # STORAGE HAND (Filesystem, Drives & Hasher)
│   │   ├── filesystem.py     # List, create, copy, move, rename, delete, head/tail, folder size
│   │   ├── archive.py        # Zip/Tar creation, extraction (Zip-Slip safe), integrity testing
│   │   ├── drives.py         # Disk usage, removable USBs, space warnings, safe USB eject
│   │   └── hasher.py         # MD5/SHA1/SHA256 checksums, text hashing, file comparison
│   │
│   └── connectivity/         # CONNECTIVITY HAND (Network, Web & System Services)
│       ├── network.py        # Local IP, public WAN IP, ping latency, Wi-Fi info, connection check
│       ├── wifi_tools.py     # Wi-Fi scanning, saved profiles, password recovery, connect, forget
│       ├── ports.py          # Listening ports, process on port, kill port blocker, remote port scan
│       ├── browser.py        # Default browser detection, direct URL, YouTube cue & play, web directory
│       ├── power.py          # Battery status, workstation lock, screen off, sleep, hibernate, shutdown
│       ├── settings.py       # Dark/light theme toggle, wallpaper get/set, transparency
│       ├── services.py       # Windows services status, start, stop, restart, startup config
│       ├── system_info.py    # CPU/RAM/GPU usage, physical cores, motherboard BIOS, uptime
│       ├── timer.py          # Countdown timers, system uptime, precision stopwatches
│       └── healer.py         # Autonomous self-healing: RAM trim, hung recovery, DNS flush, temp purge
│
├── people/                   # MIO PEOPLE (Specialized Autonomous Personas)
│   └── aegis/                # DR. AEGIS (Autonomous Laptop Doctor & Hardware Guardian)
│       ├── aegis.py          # Hardware clinic diagnostics, 0-100 health score, prescriptions & treatments
│       ├── antivirus.py      # Aegis Shield Antivirus: LOLBin detection, beacon auditing, quarantine vault
│       └── sentinel.py       # 24/7 autonomous background health & threat monitor daemon
├── eyes/                     # MIO'S EYES (Visual Perception & On-Screen Grounding)
│   ├── guard.py              # Mechanical privacy shutter, app blacklists & PII redaction
│   ├── ocr.py                # Native Windows WinRT offline OCR engine & bounding boxes
│   ├── ui_tree.py            # Windows native accessibility UI Automation tree inspector
│   ├── locator.py            # Hybrid UI tree + OCR on-screen element locator
│   ├── reader.py             # Active dialog prompt, modal alert, & regional screen reader
│   └── __init__.py           # High-level visual API (see, click_element, type_into, read_dialog)
│
├── core/                     # CORE RUNTIME & DISPATCH
│   ├── agent.py              # System Agent CLI & Natural Language Router
│   ├── registry.py           # Master Tool Inventory, Hand Kits catalog & Workflow Orchestrator
│   └── app_memory.json       # Learned application aliases & paths
│
├── tests/                    # CENTRALIZED TEST SUITE
│   ├── test_hands.py         # 133+ automated unit tests for all Hands & natural language routing
│   ├── test_eyes.py          # 18 privacy shield, shutter, OCR, UI tree & collaboration tests
│   ├── test_registry.py      # Dynamic tool catalog, schemas & workflow execution tests
│   └── test_aegis.py         # Clinic diagnostics, scoring algorithms & antivirus tests
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## The 5 Hand Kits (Complete Capabilities)

### 1. Sensory Hand (`hands/sensory/`)
Perceives screen visual state, display metrics, audio devices, and user notifications.
- **`screen`**: Fullscreen and bounding-box region PNG screenshots, image dimension inspection.
- **`display`**: Primary display metrics, multi-monitor enumeration, virtual desktop resolution, refresh rate display modes.
- **`audio`**: Master volume control, mute toggling, SAPI text-to-speech synthesis, media playback controls (`play`, `pause`, `next`, `prev`, `stop`), audio device listing.
- **`brightness`**: Display brightness query and set (0–100%), incremental step changes, smooth brightness fading.
- **`notifications`**: Native Windows desktop toast alerts, audio chimes (`asterisk`, `exclamation`, `hand`), frequency beeps, sound patterns.

### 2. Action Hand (`hands/action/`)
Interacts physically with the operating system via cursor, keyboard, and clipboard.
- **`mouse`**: Absolute and relative cursor movement, left, right, and double clicks, smooth drag-and-drop, vertical mouse scrolling.
- **`input`**: Global hotkey simulation (Win+D, Win+E, Win+I, Alt+F4, Alt+Tab, Task Manager), SendInput unicode typing, single key presses (`press_key('k')`, `press_key('enter')`).
- **`clipboard`**: System clipboard read, write, append, clear, and active clipboard format inspection.

### 3. Control Hand (`hands/control/`)
Manages installed software, process lifecycles, and desktop windows.
- **`applications`**: Deep Start Menu indexing, Registry `App Paths` discovery, self-learning application memory cache (`app_memory.json`), launch as Administrator, default file association launching.
- **`windows`**: Top-level window enumeration, minimize, maximize, restore, bring to foreground, split-screen window snapping (`snap_window('left')`), always-on-top pinning (`pin on top`).
- **`processes`**: Running process query, process verification by name or PID, terminate process, top CPU/RAM consuming process rankings.
- **`installed_apps`**: Scans 32-bit and 64-bit Windows Uninstall registry keys for complete software inventory, software versions, and official uninstall command strings.

### 4. Storage Hand (`hands/storage/`)
Manages files, directories, compression archives, and cryptographic integrity.
- **`filesystem`**: File listing, recursive wildcard search, folder creation, copy, move, rename, delete, head/tail inspection, recursive folder size calculation.
- **`archive`**: Zip compression and extraction (with built-in Zip-Slip directory traversal protection), Tar/Tar.gz archive creation, archive integrity validation.
- **`drives`**: Drive enumeration (fixed disks, network shares, optical), disk space percentage warnings, removable USB drive detection, safe USB ejection.
- **`hasher`**: Cryptographic file and string hashing (MD5, SHA1, SHA256), checksum validation, file content comparison.

### 5. Connectivity Hand (`hands/connectivity/`)
Manages networking, wireless profiles, open ports, web browser automation, power states, and system self-healing.
- **`network`**: Private LAN IP, public WAN IP, Wi-Fi adapter details, internet ping latency and packet loss.
- **`wifi_tools`**: Live Wi-Fi network scanning, saved profile extraction, cleartext Wi-Fi password recovery, network connect, disconnect, forget profile, DNS resolver cache flushing.
- **`ports`**: Active TCP/UDP listening port enumeration, identifying process holding a port, terminating port blockers, remote port reachability testing.
- **`browser`**: Default browser detection, direct URL launching, private/incognito mode, YouTube top-video resolution, YouTube precision timestamp cueing (`&t=120s`), universal YouTube keyboard playback shortcuts (`k`, `f`, `m`, `j`, `l`), built-in popular web directory (`POPULAR_SITES`), compound web search routing.
- **`power`**: Battery charge and AC line state, workstation lock, monitor standby, sleep, hibernate, timed shutdown/restart scheduling and abort.
- **`settings`**: Windows Dark/Light theme query and toggle, active wallpaper query and set, transparency effects toggle.
- **`services`**: Windows Service Control Manager queries, service start, stop, restart, startup type configuration (`Automatic`, `Manual`, `Disabled`).
- **`system_info`**: CPU load percentage, RAM load, GPU name and memory, motherboard model and manufacturer, system uptime.
- **`timer`**: High-precision stopwatch (lap, stop), background countdown timers with toast notifications.
- **`healer`**: Autonomous OS self-healing: process working set memory trimming (`EmptyWorkingSet`), hung window detection (`IsHungAppWindow`), DNS resolver cache purging, temporary cache cleanup.

---

## MIO People (Autonomous Personas)

### Dr. Aegis — Autonomous Laptop Doctor & Hardware Guardian (`people/aegis/`)
Dr. Aegis is an autonomous physician persona dedicated to laptop longevity, thermal safety, boot performance, and system hygiene.

- **Objective Health Score (0–100)**:
  Evaluates 5 hardware and OS pillars:
  1. *Battery Wear & AC Health*: Charge level, battery wear estimate, power plan configuration.
  2. *Memory Pressure*: Committed memory headroom, active paging.
  3. *Disk Clutter*: Free space thresholds, temp cache bloat.
  4. *Thermal & CPU State*: CPU idle vs. active load, thermal throttling indicators.
  5. *Boot Bottlenecks*: Registry startup items classified by boot impact (High, Medium, Low).
- **Clinical Consultations**:
  Interactive terminal consultation interface for asking questions (`"how is my battery"`, `"clean cache"`, `"trim ram"`, `"scan startup"`).
- **Aegis Shield Antivirus (`antivirus.py`)**:
  - *Process Parentage Auditing*: Detects masquerading processes, suspicious child processes (e.g. Word spawning PowerShell), and LOLBin execution.
  - *Network Beacon Detection*: Scans active outbound connections for unknown processes phoning home on unusual ports.
  - *Double-Extension Hunter*: Detects deceptive file names (`document.pdf.exe`).
  - *Cryptographic Quarantine Vault*: Safely isolates malicious files in `.quarantine/` with XOR byte masking to prevent accidental execution.
- **Sentinel 24/7 Monitor (`sentinel.py`)**:
  Background daemon monitoring system vitals in real-time. Triggers automated emergency prescriptions when RAM exceeds 90% or thermal spikes occur.

---

## Current Capabilities vs. Limits

| Area | Current Capabilities | Current Limits |
| :--- | :--- | :--- |
| **Dependencies** | 100% native Python standard library + Win32 ctypes. Zero `pip install` required. | Windows only (uses Win32 API, PowerShell, netsh). |
| **Execution** | Natural language routing, macro workflows (`execute_workflow`), direct function execution (`execute_action`). | Does not yet execute multi-turn conversational planning from an external LLM. |
| **Browser Control** | Direct URL launching, precision YouTube playback cueing (`&t=120s`), media key simulation (`k`, `f`, `m`). | Does not use DOM scraping/CDP (Chrome DevTools Protocol) for complex form interaction. |
| **Vision** | Fullscreen and region PNG screenshots. | Visual OCR / object detection on screen requires human or multimodal model evaluation. |
| **Security** | Process heuristic analysis, network beacon detection, double-extension hunting, quarantine vault. | Signatureless zero-day kernel driver rootkit detection is outside scope. |

---

## Future Roadmap

1. **Multimodal Vision Hand**:
   - Integrate local ONNX / Windows OCR for recognizing UI text and button coordinates visually on screen without relying on DOM elements.
2. **Additional MIO People**:
   - *Dev Buddy*: Autonomous code review, Git branch management, and build triage persona.
   - *Scribe*: Autonomous meeting transcription, clipboard note synthesis, and daily report generator.
3. **Local LLM Brain Integration**:
   - Native integration with local model runners (Ollama / Llama.cpp) providing autonomous reasoning loops for multi-step goals.
4. **Desktop Overlay Interface**:
   - Lightweight, glassmorphic floating HUD built in Tauri/Rust communicating with MIO's Hands over local IPC.

---

## Quick Start & Verification

### Run Natural Language Hand Command
```powershell
python -c "from core.agent import handle_command; print(handle_command('open youtube type believer song and play video at 2 minute')[1])"
# Output: Playing 'believer song' on YouTube at 02:00 (https://www.youtube.com/watch?v=W0DM5lcj6mw&t=120s).
```

### Consult Dr. Aegis (Laptop Doctor)
```powershell
python people/aegis/aegis.py
```

### Run Automated Unit Test Suites
```powershell
# Run Master Registry & Workflow Tests
python -m unittest tests.test_registry

# Run Dr. Aegis & Antivirus Tests
python -m unittest tests.test_aegis

# Run Hands & Command Routing Tests
python -m unittest tests.test_hands.TestSystemAgent.test_web_and_compound_search_dispatch tests.test_hands.TestSystemAgent.test_youtube_agent_command_dispatch tests.test_hands.TestSystemAgent.test_youtube_tools
```
