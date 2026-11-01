# MIO (Machine Intelligence Operator)

An autonomous, local-first operating system execution engine for Windows. Zero external `pip` dependencies — built 100% on the Python standard library, native Win32 `ctypes`, `winreg`, Windows WinRT OCR, and the Windows Accessibility Tree.

---

## Architecture Overview

MIO strictly separates **Hands** (physical operating system manipulation instruments), **Eyes** (perceptual screen grounding & OCR), **Core** (action memory & tool catalog), and **People** (specialized autonomous personas like Dr. Aegis):

```text
mio/
├── core/                     # CORE RUNTIME & DISPATCH
│   ├── registry.py           # Master Tool Inventory (29 tools), schemas & execution gateway
│   ├── history.py            # Action memory, audit trail & conversational introspection
│   ├── agent.py              # System Agent CLI & command dispatcher
│   └── app_memory.json       # Learned application paths & aliases
│
├── hands/                    # MIO'S HANDS (Operating System Manipulation Instruments)
│   ├── sensory/              # SENSORY HAND (Sight, Sound & Visual Environment)
│   │   ├── screen.py         # Full & region screenshots, PNG dimensions
│   │   ├── display.py        # Monitor metrics, multi-monitor enumeration, refresh rates, DPI
│   │   ├── audio.py          # Master volume, SMTC active media metadata, mic mute, SAPI TTS
│   │   ├── brightness.py     # Display brightness query and set, smooth brightness fading
│   │   └── notifications.py  # Toast notifications, audio chimes, frequency beeps
│   │
│   ├── action/               # ACTION HAND (Physical Interaction & Input)
│   │   ├── mouse.py          # Moves, clicks, double-clicks, drag-and-drop, scroll
│   │   ├── input.py          # Hotkeys (Win+E, Win+I, Alt+F4), SendInput typing, single key press
│   │   └── clipboard.py      # Read/write/append clipboard, inspect active clipboard formats
│   │
│   ├── control/              # CONTROL HAND (Applications, Windows & Terminal)
│   │   ├── applications.py   # Start Menu indexing, registry App Paths, auto-launch as Admin
│   │   ├── windows.py        # Minimize, maximize, restore, split snap, pin on top, foreground focus
│   │   ├── processes.py      # Process listing, PID check, kill process, top memory consumers
│   │   ├── installed_apps.py # 32/64-bit software registry scanner, version query, uninstall commands
│   │   ├── terminal.py       # Isolated PowerShell/CMD execution, timeout guards, env variables
│   │   └── flow.py           # Pipelined workflow chaining, adaptive window sync, work/chill modes
│   │
│   ├── storage/              # STORAGE HAND (Filesystem, Drives & Hasher)
│   │   ├── filesystem.py     # File CRUD, desktop auto-organize, recursive file search, folder size
│   │   ├── archive.py        # Zip/Tar creation, extraction (Zip-Slip protected), integrity checks
│   │   ├── drives.py         # Disk usage, removable USBs, space warnings, safe USB eject
│   │   └── hasher.py         # MD5/SHA1/SHA256 checksums, text hashing, file comparison
│   │
│   └── connectivity/         # CONNECTIVITY HAND (Network, Web & System Services)
│       ├── network.py        # Local IP, public WAN IP, ping latency, Wi-Fi info, connection check
│       ├── wifi_tools.py     # Wi-Fi scanning, saved profiles, cleartext password recovery, connect
│       ├── ports.py          # Listening ports, process on port, kill port blocker, remote port scan
│       ├── browser.py        # Browser tab routing, YouTube playback, headless web page text & search
│       ├── power.py          # Battery status, workstation lock, screen off, sleep, hibernate, shutdown
│       ├── settings.py       # Dark/light theme toggle, wallpaper get/set, transparency
│       ├── services.py       # Windows services status, start, stop, restart, startup config
│       ├── system_info.py    # CPU/RAM/GPU usage, physical cores, motherboard BIOS, uptime
│       ├── timer.py          # Countdown timers, system uptime, precision stopwatches
│       └── healer.py         # Autonomous self-healing: RAM trim, hung recovery, DNS flush, temp purge
│
├── eyes/                     # MIO'S EYES (Visual Perception & On-Screen Grounding)
│   ├── ocr.py                # Native Windows WinRT offline OCR engine & bounding boxes
│   ├── ui_tree.py            # Windows native accessibility UI Automation tree inspector
│   ├── locator.py            # Hybrid UI tree + OCR on-screen element locator & coordinate grounding
│   ├── watcher.py            # Visual screen hash diffing & animation stabilization detector
│   ├── reader.py             # Active dialog prompt, modal alert & regional screen reader
│   ├── guard.py              # Hardware privacy shutter & PII redaction (password/banking protection)
│   └── __init__.py           # Unified visual API (see, click_element, type_into, read_dialog, wait_for_change)
│
├── mouth/                    # MIO'S MOUTH (Vocal Speech Synthesis & Auditory Output)
│   ├── speaker.py            # speak(), say(), stop(), speech rate/volume, async interruptible queue
│   ├── voices.py             # SAPI 5 & OneCore voice discovery (Zira, David, Mark)
│   ├── README.md             # Vocal subsystem documentation & persona guide
│   └── __init__.py           # Unified vocal API exports
│
├── ears/                     # MIO'S EARS (Vocal Hearing & Speech Recognition)
│   ├── listener.py           # listen(), listen_for(), listen_background(), stop_listening()
│   ├── devices.py            # Hardware microphone discovery (winmm) & System.Speech recognizer query
│   ├── README.md             # Auditory subsystem documentation & privacy guide
│   └── __init__.py           # Unified auditory API exports
│
├── people/                   # MIO PEOPLE (Specialized Autonomous Personas)
│   └── aegis/                # DR. AEGIS (Autonomous Laptop Doctor & Hardware Guardian)
│       ├── aegis.py          # Hardware clinic diagnostics, 0-100 health score, prescriptions & treatments
│       ├── antivirus.py      # Aegis Shield Antivirus: LOLBin detection, beacon auditing, quarantine vault
│       └── sentinel.py       # 24/7 autonomous background health & threat monitor daemon
│
└── tests/                    # 226 PASSING AUTOMATED UNIT TESTS
    ├── test_hands.py         # Comprehensive unit tests for all 5 Hand Kits
    ├── test_eyes.py          # Perception tests (OCR, UI Automation, grounding, privacy shutter)
    ├── test_mouth.py         # Vocal speech synthesis, voice enumeration & stop tests
    ├── test_ears.py          # Speech recognition, microphone discovery & listener daemon tests
    ├── test_history.py       # Action memory, audit trail & conversational introspection tests
    ├── test_power_hands_and_eyes.py # Terminal, media SMTC, web reading & visual watcher tests
    ├── test_flow.py          # Compound multi-step task workflow pipeline tests
    ├── test_registry.py      # Dynamic tool catalog, schemas & workflow execution tests
    └── test_aegis.py         # Clinic diagnostics, scoring algorithms & antivirus tests
```

---

## The 5 Hand Kits (29 Master Tools)

### 1. Sensory Hand (`hands/sensory/`)
Perceives screen visual state, display metrics, audio devices, and user notifications.
- **`screen`**: Fullscreen and bounding-box region PNG screenshots, image dimension inspection.
- **`display`**: Primary display metrics, multi-monitor enumeration, virtual desktop resolution, DPI scaling.
- **`audio`**: Master volume control, mute toggling, SAPI text-to-speech synthesis, media playback controls (`play`, `pause`, `next`, `prev`, `stop`), Windows SMTC real-time song title/artist metadata query (`get_current_media_info`), and microphone mute (`toggle_microphone_mute`).
- **`brightness`**: Display brightness query and set (0–100%), incremental step changes, smooth brightness fading.
- **`notifications`**: Native Windows desktop toast alerts, audio chimes (`asterisk`, `exclamation`, `hand`), frequency beeps, sound patterns.

### 2. Action Hand (`hands/action/`)
Interacts physically with the operating system via cursor, keyboard, and clipboard.
- **`mouse`**: Absolute and relative cursor movement, left, right, and double clicks, smooth drag-and-drop, vertical mouse scrolling (`scroll`).
- **`input`**: Global hotkey simulation (Win+D, Win+E, Win+I, Alt+F4, Alt+Tab, Task Manager), SendInput unicode typing, single key presses (`press_key('k')`, `press_key('enter')`).
- **`clipboard`**: System clipboard read, write, append, clear, and active clipboard format inspection.

### 3. Control Hand (`hands/control/`)
Manages installed software, process lifecycles, desktop windows, workflows, and shell execution.
- **`applications`**: Deep Start Menu indexing, Registry `App Paths` discovery, self-learning application memory cache (`app_memory.json`), launch as Administrator, default file association launching.
- **`windows`**: Top-level window enumeration, minimize, maximize, restore, bring to foreground, split-screen window snapping (`snap_window('left')`), always-on-top pinning (`pin on top`).
- **`processes`**: Running process query, process verification by name or PID, terminate process, top CPU/RAM consuming process rankings.
- **`installed_apps`**: Scans 32-bit and 64-bit Windows Uninstall registry keys for software inventory, versions, and official uninstall command strings.
- **`terminal`**: Safe shell command execution (PowerShell or CMD) with stdout/stderr capture, exit codes, timeout guards, and environment variable get/set.
- **`flow`**: Pipelined multi-step task execution, event-driven window state synchronization, and preset modes (`set_work_mode`, `set_chill_mode`).

### 4. Storage Hand (`hands/storage/`)
Manages files, directories, compression archives, and cryptographic integrity.
- **`filesystem`**: File listing, folder creation, safe copy/move/rename, Recycle Bin deletion, head/tail inspection, recursive folder sizing, automatic Desktop/Folder categorization (`organize_desktop`, `organize_folder`), and recursive wildcard file search (`search_files`).
- **`archive`**: Zip compression and extraction (with built-in Zip-Slip directory traversal protection), Tar/Tar.gz archive creation, archive integrity validation.
- **`drives`**: Drive enumeration (fixed disks, network shares, optical), disk space percentage warnings, removable USB drive detection, safe USB ejection.
- **`hasher`**: Cryptographic file and string hashing (MD5, SHA1, SHA256), checksum validation, file content comparison.

### 5. Connectivity Hand (`hands/connectivity/`)
Manages networking, wireless profiles, open ports, web browser automation, power states, and system self-healing.
- **`network`**: Private LAN IP, public WAN IP, Wi-Fi adapter details, internet ping latency and packet loss.
- **`wifi_tools`**: Live Wi-Fi network scanning, saved profile extraction, cleartext Wi-Fi password recovery, network connect, disconnect, forget profile, DNS resolver cache flushing.
- **`ports`**: Active TCP/UDP listening port enumeration, identifying process holding a port, terminating port blockers, remote port reachability testing.
- **`browser`**: Default browser detection, direct URL launching, private/incognito mode, YouTube top-video resolution, YouTube precision timestamp cueing (`&t=120s`), headless web page text extraction (`fetch_webpage_text`), and instant search summaries (`search_web_summary`).
- **`power`**: Battery charge and AC line state, workstation lock, monitor standby, sleep, hibernate, timed shutdown/restart scheduling and abort.
- **`settings`**: Windows Dark/Light theme query and toggle, active wallpaper query and set, transparency effects toggle.
- **`services`**: Windows Service Control Manager queries, service start, stop, restart, startup type configuration (`Automatic`, `Manual`, `Disabled`).
- **`system_info`**: CPU load percentage, RAM load, GPU name and memory, motherboard model and manufacturer, system uptime.
- **`timer`**: High-precision stopwatch (lap, stop), background countdown timers with toast notifications.
- **`healer`**: Autonomous OS self-healing: process working set memory trimming (`EmptyWorkingSet`), hung window detection (`IsHungAppWindow`), DNS resolver cache purging, temporary cache cleanup.

---

## Action Memory & Conversational Introspection (`core/history.py`)

Every tool executed across MIO is logged with timestamp, tool name, action, parameters, execution duration, and return status into an audit buffer:

```bash
MIO > organize desktop
Organized Desktop: Moved 5 loose files into categorized folders (Images: 2, Documents: 3).

MIO > tell me what u just did now
Just now, I executed: 'organize desktop'. Result:
Organized Desktop: Moved 5 loose files into categorized folders (Images: 2, Documents: 3).

MIO > show history
Recent Actions (2):
- [16:48:58] 'organize desktop' -> Organized Desktop: Moved 5 loose files...
- [16:48:45] 'set volume 50' -> Master volume set to 50%.
```

---

## MIO Eyes (Visual Perception & On-Screen Grounding)

MIO's Eyes provide native visual grounding without cloud dependencies:
1. **Windows WinRT OCR (`eyes/ocr.py`)**: Uses Windows 10/11 native offline OCR engine (`Windows.Media.Ocr.OcrEngine`) to locate text and buttons on screen with pixel-accurate bounding boxes.
2. **Windows Accessibility Tree (`eyes/ui_tree.py`)**: Queries Windows `UIAutomationClient` to locate structural UI elements (Buttons, Edit fields, Checkboxes, Menus).
3. **Screen Watcher (`eyes/watcher.py`)**: Computes SHA-256 visual hashes to detect when clicks mutate the screen (`wait_for_visual_change`) or when animations settle (`wait_for_screen_stabilize`).
4. **Privacy Shutter (`eyes/guard.py`)**: Hardware shutter that automatically blinds the vision engine when sensitive windows (passwords, KeePass, banking) are active.

---

## MIO Mouth (Vocal Speech Synthesis & Auditory Output)

MIO's Mouth (`mouth/`) operates as a completely decoupled, standalone vocal organ separate from `hands/`:
- **`speak(text, voice, rate, volume, async_speech)`**: Vocalizes text using native Windows SAPI 5 or OneCore voices (`Microsoft Zira Desktop`, `Microsoft David Desktop`, `Microsoft Mark`).
- **`say(text)`**: Non-blocking asynchronous vocalization for smooth multi-tasking.
- **`stop()`**: Instant voice interruption (stops talking in 0ms).
- **`is_speaking()`**: Real-time state check of active speech playback.
- **`list_installed_voices()`**: Auto-discovers all installed vocal tokens in Windows registry.
- **`set_voice(name)` / `set_rate(rate)` / `set_volume(volume)`**: Configurable persona settings.

---

## MIO Ears (Vocal Hearing & Auditory Perception)

MIO's Ears (`ears/`) operates as an independent auditory perception organ for microphone capture and speech recognition:
- **`listen(timeout, phrase_limit)`**: Open-ended spoken speech dictation using native Windows `System.Speech.Recognition`.
- **`listen_for(phrases, timeout)`**: Targeted keyword and command recognition with near-100% accuracy (`["yes", "no", "stop", "open chrome"]`).
- **`listen_background(callback)`**: Background speech recognition daemon thread with callback triggers.
- **`stop_listening()`**: Instantly cancels active background listening daemon.
- **`list_microphones()`**: Hardware enumeration of all recording devices via Windows `winmm.dll`.
- **`get_recognizer_info()`**: Queries installed speech recognizer engines (`MS-1033-80-DESK`, `en-US`).

---

## MIO People: Dr. Aegis (Autonomous Laptop Doctor)

Dr. Aegis (`people/aegis/`) is an autonomous physician persona dedicated to laptop longevity and system safety:
- **Objective Health Score (0–100)**: Evaluates Battery Wear, Memory Pressure, Disk Clutter, Thermals, and Boot Bottlenecks.
- **Aegis Shield Antivirus (`antivirus.py`)**: Process parentage auditing (LOLBin execution), network beacon detection, double-extension hunting, and cryptographic XOR-masked quarantine vault (`.quarantine/`).
- **Sentinel Daemon (`sentinel.py`)**: Background vital monitor that triggers automatic treatments when memory pressure spikes.

---

## Verification & Automated Test Suite

All 226 automated tests run via Python's standard `unittest` framework:

```powershell
python -m unittest discover tests
```

```text
Ran 226 tests in 108.412s

OK (100% Passing, 0 Failures, 0 Errors)
```

---

## Next Milestone: Phase 3 — The Brain Layer

With MIO's physical **Hands** (action), **Eyes** (vision), **Mouth** (speech), and **Ears** (hearing) 100% completed:
- Model-agnostic LLM integration (Ollama, LM Studio, OpenAI, Anthropic, Gemini)
- Dynamic schema injection via `core.registry.get_schemas()`
- Autonomous multi-modal ReAct loop (Hear -> See -> Reason -> Act -> Speak).


