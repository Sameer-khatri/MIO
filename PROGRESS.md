# MIO (Modular Intelligent Operating Agent) - Project Progress & Architecture Log

> **Current Status:** Phase 2 Complete (Native Hands, Eyes, Mouth, and Ears Subsystems 100% Operational)  
> **Test Suite:** 226 / 226 Passing (100% Pass Rate, 0 Failures, 0 Errors)  
> **Next Milestone:** Phase 3 — LLM Brain Layer Integration (Function Calling & Structured Reasoning)

---

## 1. Project Overview & Philosophy

MIO is a local-first, zero-dependency, high-performance operating system agent built specifically for Windows. Unlike brittle macro scripts or simulated keyboard bots, MIO operates directly on native OS APIs (`win32`, `ctypes`, `winreg`, Windows WinRT, Windows Accessibility Tree, Windows SAPI/OneCore, and PowerShell).

### Core Design Rules
1. **Tools are deterministic execution primitives:** Clean inputs, structured JSON outputs, proper error boundaries, and zero fake intelligence.
2. **Modular bodily separation:** Hands (motor action & manipulation), Eyes (visual perception & OCR), Mouth (vocal speech synthesis), and Ears (speech-to-text hearing) are strictly decoupled, standalone organs.
3. **Execution memory is mandatory:** Every action, latency, and status is recorded into an audit log so the agent can introspect and answer *"tell me what you just did"*.
4. **Safety first:** Low-level catastrophic commands (formatting drives, deleting OS directories) are blocked at the kernel boundary.

---

## 2. Architecture & Subsystems

```
MIO/
├── core/                   # Central runtime, registry, history, and CLI dispatcher
│   ├── registry.py         # Master catalog of 29 tools & JSON function schemas
│   ├── history.py          # Action memory, audit trail, and introspection buffer
│   ├── agent.py            # CLI command dispatcher & REPL loop
│   └── __init__.py         # Core exports
├── hands/                  # Motor Execution & Native OS Action Kits (29 Standalone Native Tools)
│   ├── sensory/            # Screen capture, displays, audio SMTC, brightness, notifications
│   ├── action/             # Direct mouse clicks/drags, keyboard hotkeys, clipboard
│   ├── control/            # Windows, processes, applications, installed software, flow, terminal
│   ├── storage/            # Filesystem, desktop organize, search, archives, drives, hasher
│   └── connectivity/       # Wi-Fi passwords, ports, headless browser/web, power, services, healer
├── eyes/                   # Visual Perception, OCR & UI Grounding
│   ├── ocr.py              # Native Windows WinRT OCR (offline text recognition)
│   ├── ui_tree.py          # Windows UIAutomationClient accessibility hierarchy
│   ├── locator.py          # Hybrid UI-tree + OCR element grounding
│   ├── watcher.py          # Visual screen hash diffing & animation stabilization
│   ├── reader.py           # Dialog/alert text and button extraction
│   └── guard.py            # Hardware privacy shutter (blocks sensitive windows)
├── mouth/                  # Vocal Speech Synthesis & Auditory Output (Decoupled Organ)
│   ├── speaker.py          # speak(), say(), stop(), rate/volume controls, async interruptible queue
│   ├── voices.py           # SAPI 5 & OneCore voice discovery (Zira, David, Mark)
│   ├── README.md           # Vocal subsystem docs and persona guide
│   └── __init__.py         # Clean unified vocal API
├── ears/                   # Auditory Perception & Speech-to-Text (Decoupled Organ)
│   ├── listener.py         # listen(), listen_for(), listen_background(), stop_listening()
│   ├── devices.py          # Hardware microphone discovery (winmm) & System.Speech recognizer query
│   ├── README.md           # Auditory subsystem docs and privacy guide
│   └── __init__.py         # Clean unified hearing API
├── people/                 # Autonomous Personas
│   └── aegis/              # Dr. Aegis (Autonomous hardware doctor & security shield)
└── tests/                  # 226 Automated Unit Tests across all subsystems
```

---

## 3. What Was Fixed & Cleaned Out

| Removed / Fixed | Reason |
| :--- | :--- |
| **`intent.py` & `test_intent.py`** | Removed all brittle regex-based fuzzy intent matching. Tools now execute deterministically without fake pseudo-AI heuristics. |
| **`virtual_human.py` & `human.py`** | Eliminated redundant persona wrappers and non-essential abstraction bloat. |
| **Mouse Scroll Interception** | Fixed a collision between vision grounding and direct action mouse handlers in `agent.py`. |
| **Theme Setting Collision** | Added standardized aliases `set_windows_theme = set_theme_mode` and `get_windows_theme`. |
| **Mouse Alias** | Added `scroll = mouse_scroll` for seamless tool-calling compatibility. |
| **Runtime Cache Isolation** | Added `core/action_history.json` and temp vaults to `.gitignore` to prevent tracking runtime logs. |

---

## 4. Newly Added & Power-Upgraded Capabilities

### A. Execution History & Action Memory ([core/history.py](core/history.py))
- In-memory rolling buffer (last 100 actions) + persistent disk cache.
- Records timestamp, tool name, action name, arguments, return status, and duration in milliseconds.
- Enables contextual conversational queries:
  - *"tell me what u just did now"* -> Accurately reports the exact last tool and result.
  - *"history"* / *"recent actions"* -> Summarizes recent execution audit log.

### B. Isolated Terminal & Shell Engine ([hands/control/terminal.py](hands/control/terminal.py))
- `run_command(cmd, timeout=30, shell='powershell')`: Safe subprocess execution with stdout/stderr capture and exit code checks.
- `run_powershell_script(script_text)`: Multi-line PowerShell dispatch.
- `get_environment_variable` / `set_environment_variable`: Process and Windows user registry variable management.
- Guardrail: Blocks catastrophic destructive commands (`format`, system directory wipes).

### C. Desktop & Folder Organizer ([hands/storage/filesystem.py](hands/storage/filesystem.py))
- `organize_folder(path)` / `organize_desktop()`: Automatically categorizes loose desktop files into `Images`, `Documents`, `Audio`, `Videos`, `Archives`, `Code`, and `Installers`.
- Collision handling: Renames duplicates cleanly (`file (1).ext`) without overwriting.
- Shortcut protection: Leaves `.lnk` and `.url` shortcuts on the desktop.

### D. Fast Recursive File Search ([hands/storage/filesystem.py](hands/storage/filesystem.py))
- `search_files(pattern, root_dir='desktop', max_results=50)`: Recursive wildcard search with size and path metadata.

### E. Media Metadata & Microphone Guard ([hands/sensory/audio.py](hands/sensory/audio.py))
- `get_current_media_info()`: Queries Windows SMTC for real-time track title, artist, album, and playback status from Spotify, Chrome, etc.
- `toggle_microphone_mute()`: Toggles system-wide recording microphone mute.

### F. Headless Web Page Reading & Search ([hands/connectivity/browser.py](hands/connectivity/browser.py))
- `fetch_webpage_text(url, max_chars=5000)`: Fetches URLs without launching browser windows, cleans scripts/styles, and extracts readable text and links.
- `search_web_summary(query, max_results=5)`: Instant structured search results (titles, snippets, links).

### G. Visual Watcher & Screen Diff ([eyes/watcher.py](eyes/watcher.py))
- `get_screen_hash(region=None)`: Fast SHA-256 visual hashing of the screen or specific region.
- `wait_for_visual_change(timeout=5.0)`: Detects when clicks or keystrokes cause visual UI mutation.
- `wait_for_screen_stabilize(stable_duration=0.4)`: Waits until animations or page renders settle.

### H. Work & Chill Preset Modes ([hands/control/flow.py](hands/control/flow.py))
- `set_work_mode()`: Mutes volume to 20%, enables Windows Dark Theme, and trims background RAM.
- `set_chill_mode(play_music=False)`: Sets volume to 40% with optional ambient live audio.

### I. MIO Mouth & Vocal Speech Synthesis ([mouth/](mouth/))
- **Dedicated Standalone Organ:** Built completely detached from `hands/` to keep motor action and vocal expression strictly separated.
- `speak(text, voice, rate, volume, async_speech)`: Speaks text aloud using Windows SAPI 5 or OneCore voices.
- `say(text)`: Non-blocking background speech shorthand.
- `stop()`: Zero-latency voice interruption (terminates active speech subprocess).
- `is_speaking()`: Checks if MIO is currently talking.
- `list_installed_voices()`: Discovers all installed Windows speech tokens (`Microsoft David Desktop`, `Microsoft Zira Desktop`, `Microsoft Mark`).
- `set_voice()`, `set_rate()`, `set_volume()`, `get_voice_settings()`: Full vocal configuration.

### J. MIO Ears & Auditory Perception ([ears/](ears/))
- **Dedicated Standalone Organ:** Built completely detached from `mouth/` and `hands/` for zero-dependency hearing.
- `listen(timeout, phrase_limit)`: Open-ended speech dictation listening via Windows native `System.Speech.Recognition`.
- `listen_for(phrases, timeout)`: Fast, high-accuracy grammar choice matching for voice commands (`["yes", "no", "stop", "open notepad"]`).
- `listen_background(callback)`: Non-blocking background speech listener thread with callback invocation.
- `stop_listening()`: Gracefully halts background listening daemon.
- `is_listening()`: Checks if MIO is currently listening.
- `list_microphones()`: Discovers all hardware microphone devices via `winmm.dll`.
- `get_recognizer_info()`: Queries Windows Speech Recognition engine status (`MS-1033-80-DESK`, `en-US`).

---

## 5. Master Tool Inventory (29 Tools across 5 Kits)

| Kit | Tools Included | Primary Capabilities |
| :--- | :--- | :--- |
| **Sensory** | `screen`, `display`, `audio`, `brightness`, `notifications` | Screenshots, multi-monitor metrics, volume/media/mic, brightness fade, toast alerts |
| **Action** | `mouse`, `input`, `clipboard` | Cursor move/click/drag/scroll, keyboard shortcuts, typing, clipboard read/write |
| **Control** | `applications`, `windows`, `processes`, `installed_apps`, `flow`, `terminal` | Window management, process lifecycle, installed apps, task pipelines, shell commands |
| **Storage** | `filesystem`, `archive`, `drives`, `hasher` | File CRUD, desktop organize, file search, zip/tar archives, USB ejection, file hashes |
| **Connectivity** | `network`, `wifi_tools`, `ports`, `browser`, `power`, `settings`, `services`, `system_info`, `timer`, `healer` | IP/ping, Wi-Fi passwords, port killing, browser tabs & web fetch, sleep/battery, theme/wallpaper, service management, hardware specs, RAM auto-heal |

---

## 6. Test Suite Verification

All tests run via Python's standard `unittest` framework:

```bash
python -m unittest discover tests
```

```
Ran 226 tests in 108.412s

OK (100% Passing, 0 Failures, 0 Errors)
```

### Test Coverage Files
- `tests/test_hands.py`: 120+ tests covering all 5 Hand Kits
- `tests/test_eyes.py`: 21 tests covering OCR, UI Automation, grounding, and element clicks
- `tests/test_aegis.py`: 17 tests covering Dr. Aegis antivirus, sentinel, and diagnosis
- `tests/test_power_hands_and_eyes.py`: 14 tests covering terminal execution, media metadata, web reading, and visual watcher
- `tests/test_mouth.py`: 10 tests covering voice enumeration, clamping/settings, async speech, and speech stop
- `tests/test_ears.py`: 10 tests covering microphone discovery, recognizer query, listen timeouts, grammar matching, and daemon listener
- `tests/test_history.py`: 8 tests covering action memory, conversational introspection, and desktop organizing
- `tests/test_registry.py`: 7 tests covering dynamic loading, catalog integrity, and schema generation
- `tests/test_flow.py`: 6 tests covering pipelined compound workflows

---

## 7. Next Milestone: Phase 3 — The Brain Layer

With MIO's bodily senses and motor organs 100% operational:
- **Hands:** Physical OS action & tool kits (29 tools)
- **Eyes:** Visual screen perception & OCR grounding
- **Mouth:** Vocal speech synthesis & audio output
- **Ears:** Auditory hearing & voice perception

The next step is connecting the **LLM Brain Layer**:
1. **Model-Agnostic LLM Gateway:** Support local models (Ollama, LM Studio) or cloud models (OpenAI, Anthropic, Gemini).
2. **Dynamic Schema Feeding:** Stream `core.registry.get_schemas()` into the function-calling layer.
3. **Autonomous Perception-Action ReAct Loop:**
   - Hear user voice -> Transcribe via `ears` -> Reason in Brain -> See screen via `eyes` -> Act via `hands` -> Speak response via `mouth`.


