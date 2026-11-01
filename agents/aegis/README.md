# Aegis - Standalone Laptop Doctor & Hardware Guardian

**Aegis** is an autonomous, standalone laptop health diagnostics, preventative triage, 24/7 background telemetry sentinel, and native antivirus security guardian for Windows laptops and workstations.

It is completely decoupled from core MIO with **zero external pip dependencies** (pure standard library and native Windows Win32 APIs).

---

## Capabilities & Architecture

```text
agents/aegis/
├── aegis.py            # Complete AegisDoctor engine & interactive consultation CLI
├── antivirus.py        # Aegis Shield: Process masquerading, persistence hunter & quarantine vault
├── sentinel.py         # Aegis Sentinel: Continuous 24/7 background telemetry & auto-RAM healing
├── test_aegis.py       # 17 Automated unit tests covering all diagnostics, antivirus & sentinel
└── README.md           # Documentation & usage guide
```

### 1. Hardware Vitals & Diagnostics
- **Battery Health & Power Run-Time**: Native `GetSystemPowerStatus` queries AC/DC power source, charge percent, charging states, critical low warning, and estimated battery run-time minutes.
- **Startup Clutter & Boot Impact Triage**: Inspects Windows Run keys (`HKCU` & `HKLM`) and classifies startup applications against known high/medium boot bottlenecks (Steam, Riot Client, Discord, Torrent clients, OneDrive, Chrome background).
- **Thermal & CPU Profiling**: Instant `GetSystemTimes` CPU load delta calculation, active Windows power plan scheme lookup (`powercfg /getactivescheme`), and thermal envelope warning.
- **Memory Pressure & Memory Leak Detection**: `GlobalMemoryStatusEx` physical RAM load, committed headroom, and fast process CSV analysis finding the top 5 memory consumers.
- **Storage & Temp Hygiene**: Main `C:\` partition free space analysis and bounded `%TEMP%` clutter scan.

### 2. Aegis Shield: Native Antivirus & Threat Hunter
- **Process Masquerading Detection**: Flags fake system binaries (e.g. `svchost.exe`, `csrss.exe`, `lsass.exe`) executing outside `C:\Windows\System32`.
- **Stealth Persistence Hunter**: Scans Windows Run/RunOnce keys for scripts, temp folder launches, and hidden encoded PowerShell commands (`-w hidden -enc`).
- **Deceptive File Heuristics**: Detects double extensions (`.pdf.exe`, `.docx.vbs`, `.xlsx.bat`) and PE executable binaries (`MZ`) disguised as documents or images.
- **Safe Quarantine Vault**: Neutralizes threats by renaming with `.aegis_quarantined` into an isolated sandbox vault (`.quarantine/`).

### 3. Aegis Sentinel: Continuous 24/7 Background Surveyor
- **Autonomous RAM Pressure Reliever**: Monitors RAM continuously; when RAM exceeds 85%, silently executes native `EmptyWorkingSet` trimming to prevent OS freeze and logs reclaimed memory.
- **Charger & Power Alert**: Detects charger unplug, low battery (<20%), or critical drain (<10%).
- **Thermal Spike Guard**: Detects runaway CPU usage (>85%) before fans get locked at max RPM.
- **Rolling Alert Log**: Real-time telemetry log recording all events, disconnects, and auto-heal actions.

### 4. Objective Laptop Health Score (0 - 100)
Calculates a weighted, objective health score and assigns a clear medical grade:
- **`S-Tier` (90 - 100)**: Peak condition with ample headroom.
- **`A` (80 - 89)**: Healthy condition with minor optimization potential.
- **`B` (65 - 79)**: Moderate bloat, startup friction, or elevated RAM usage.
- **`C` (50 - 64)**: Noticeable resource strain needing attention.
- **`D` (< 50)**: Critical degradation; risk of thermal throttling or freeze-ups.

### 5. Medical Prescriptions & One-Click Cures
- `apply_treatment("ram")`: Trims idle working sets across user processes without killing apps.
- `apply_treatment("dns")`: Flushes Windows DNS resolver cache.
- `apply_treatment("cache")`: Purges stale temporary files older than 1 hour.
- `apply_treatment("all")`: Combined treatment showing health score improvement.

---

## Interactive Doctor CLI Commands

Run Aegis directly in your terminal:
```bash
python agents/aegis/aegis.py
```

### Direct Commands:
| Command | What it does |
|---|---|
| **`scan`** | Full antivirus audit (process masquerading, persistence, stealth commands) |
| **`scan <path>`** | Scans specific file or folder for malware signatures & deceptive headers |
| **`quarantine <path>`** | Safely isolates suspicious file into quarantine sandbox vault |
| **`quarantine list`** | Lists all files currently held in quarantine |
| **`survey on`** | Starts Sentinel continuous 24/7 background telemetry & auto-RAM trimming |
| **`survey off`** | Stops Sentinel background monitoring |
| **`survey`** | Displays Sentinel live status card, uptime, and recent alert log |
| **`ram`** | Trims RAM working sets across apps and shows exact MB/GB freed |
| **`startup`** | Lists all startup applications and their boot impact ratings |
| **`heal`** | Executes full triage treatment (RAM trim + DNS flush + cache purge) |
| **`score`** | Displays complete clinic report card and 0-100 health score |
| **`<text>`** | Type any complaint in plain English (*"laptop is hot"*, *"battery dying fast"*, etc.) |
