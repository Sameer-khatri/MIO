# Aegis - Standalone Laptop Doctor & Hardware Guardian

**Aegis** is an autonomous, standalone laptop health diagnostics, preventative triage, and recovery agent for Windows laptops and workstations.

It is designed to be completely decoupled from core MIO with **zero external pip dependencies** (pure standard library and native Windows Win32 APIs).

---

## Capabilities & Architecture

```text
agents/aegis/
├── aegis.py            # Complete AegisDoctor engine & interactive consultation CLI
├── test_aegis.py       # Automated unit tests covering all diagnostic & prescription engines
└── README.md           # Documentation & usage guide
```

### 1. Hardware Vitals & Diagnostics
- **Battery Health & Power Run-Time**: Native `GetSystemPowerStatus` queries AC/DC power source, charge percent, charging states, critical low warning, and estimated battery run-time minutes.
- **Startup Clutter & Boot Impact Triage**: Inspects Windows Run keys (`HKCU` & `HKLM`) and classifies startup applications against known high/medium boot bottlenecks (Steam, Riot Client, Discord, Torrent clients, OneDrive, Chrome background).
- **Thermal & CPU Profiling**: Instant `GetSystemTimes` CPU load delta calculation, active Windows power plan scheme lookup (`powercfg /getactivescheme`), and thermal envelope warning.
- **Memory Pressure & Memory Leak Detection**: `GlobalMemoryStatusEx` physical RAM load, committed headroom, and fast process CSV analysis finding the top 5 memory consumers.
- **Storage & Temp Hygiene**: Main `C:\` partition free space analysis and bounded `%TEMP%` clutter scan.

### 2. Objective Laptop Health Score (0 - 100)
Calculates a weighted, objective health score and assigns a clear medical grade:
- **`S-Tier` (90 - 100)**: Peak condition with ample headroom.
- **`A` (80 - 89)**: Healthy condition with minor optimization potential.
- **`B` (65 - 79)**: Moderate bloat, startup friction, or elevated RAM usage.
- **`C` (50 - 64)**: Noticeable resource strain needing attention.
- **`D` (< 50)**: Critical degradation; risk of thermal throttling or freeze-ups.

### 3. Medical Prescriptions & One-Click Cures
Generates prioritized prescriptions (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`) and provides non-destructive treatments:
- `apply_treatment("ram")`: Trims idle working sets across user processes without killing apps.
- `apply_treatment("dns")`: Flushes Windows DNS resolver cache.
- `apply_treatment("cache")`: Purges stale temporary files older than 1 hour.
- `apply_treatment("all")`: Combined treatment showing health score improvement.

### 4. Natural Language Doctor Consultation
Users can describe symptoms in plain English (e.g. *"laptop is hot and fan is loud"*, *"battery draining fast"*, *"games stuttering"*, *"boot takes forever"*), and Aegis maps complaints directly to targeted hardware diagnostics and remedies.

---

## Quick Usage

### Standalone CLI Mode
```bash
python agents/aegis/aegis.py
```

### Python Programmatic Usage
```python
from agents.aegis.aegis import AegisDoctor

doctor = AegisDoctor()

# Full checkup report card
report = doctor.full_checkup()
print(report["report_card"])

# Doctor consultation
consult = doctor.doctor_consult("battery is dying fast and fans are loud")
print(consult["doctor_verdict"])

# Apply one-click treatment
cure = doctor.apply_treatment("all")
print(cure["message"])
```

### Running Automated Tests
```bash
python -m unittest agents/aegis/test_aegis.py -v
```
