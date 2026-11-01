# MIO Eyes: Visual Perception & On-Screen Grounding

MIO's visual perception organ. Operates as an independent, modular subsystem alongside **Hands** and **People** to give MIO eyes while guaranteeing absolute privacy, zero passive surveillance, and zero external `pip` dependencies.

---

## 🔒 Privacy & Safety Core: The Safe-Eye Architecture

```
                 [ User Explicit Command ]
                            │
                            ▼
              ┌───────────────────────────┐
              │   SHUTTER GUARD (LOCKED)  │ ◄── Permanently locked by default
              └─────────────┬─────────────┘
                            │ Single-frame on-demand unlock
                            ▼
              ┌───────────────────────────┐
              │      PRIVACY SHIELD       │ ◄── Blocks Password Managers & Banking
              └─────────────┬─────────────┘
                            │ Target window verified safe
                            ▼
              ┌───────────────────────────┐
              │    HYBRID LOCATOR & OCR   │ ◄── UI Automation + Offline WinRT OCR
              └─────────────┬─────────────┘
                            │ Exact (x, y) coordinates extracted
                            ▼
              ┌───────────────────────────┐
              │   EPHEMERAL PURGE & LOCK  │ ◄── Memory wiped, shutter locked
              └───────────────────────────┘
```

1. **Mechanical Shutter Guard (`eyes/guard.py`)**:
   - The Eye is **physically locked by default**.
   - It **never watches passively** in the background, records video, or streams frames.
   - It unlocks only for the exact duration of an explicit function call (e.g. `click_element("Skip Ad")`) and relocks immediately.
2. **Window-Scoped Privacy Shield**:
   - Blocks inspection of password managers (`Bitwarden`, `1Password`, `KeePass`, `Proton Pass`, `LastPass`).
   - Blocks banking portals and credential dialogs.
   - Blocks browser windows matching `Incognito` or `Private Browsing`.
3. **Automatic PII Redaction**:
   - Extracted text masks credit card numbers, authorization tokens, bearer headers, API keys, and SSNs.
4. **Ephemeral RAM Buffer**:
   - Zero image files are persisted to disk. Frame buffers are wiped immediately after coordinate extraction.

---

## 🛠️ The Eyes Subsystem (`eyes/`)

| Module | Purpose | Native Technology |
| :--- | :--- | :--- |
| **`guard.py`** | Mechanical Shutter, App Blacklist, and PII Redaction | Pure Python + regex filters |
| **`ocr.py`** | Offline visual text recognition and word coordinate bounding boxes | Windows Runtime `Windows.Media.Ocr.OcrEngine` |
| **`ui_tree.py`** | Structural accessibility tree discovery (buttons, edits, menus) | Windows `System.Windows.Automation` (UIAutomationClient) |
| **`locator.py`** | Hybrid locator combining UI tree structure with OCR visual fallback | UI Automation + WinRT OCR + Display metrics |
| **`reader.py`** | Reads active dialog prompts, error alerts, and regional text | UI Automation + WinRT OCR |
| **`__init__.py`** | High-level API coordinating Eyes with Action Hands & People | Public gateway |

---

## 🤝 Hands, Eyes & People Working Together

### 1. Eyes + Hands Collaboration
```python
import eyes

# Eyes locates the button, Action Hand moves the cursor and clicks
eyes.click_element("Skip Ad")

# Eyes locates the input field, Action Hand focuses it and types
eyes.type_into("Search", "believer song")
```

### 2. People (Dr. Aegis) using Eyes
```python
from people.aegis.aegis import AegisDoctor

doc = AegisDoctor()
# Dr. Aegis visually inspects an on-screen hardware prompt or driver warning
diagnosis = doc.doctor_consult("Doctor, what is this warning on my screen?")
print(diagnosis["doctor_diagnosis"])
```

### 3. Natural Language Dispatch via Core Agent
```python
from core.agent import handle_command

# Click buttons on screen
handle_command("click Skip Ad")

# Double-click icons or entries
handle_command("double click Setup")

# Type into on-screen inputs
handle_command("type 'hello world' into Search")

# Read dialogs or alerts
handle_command("read dialog")

# Check mechanical shutter status
handle_command("eye status")
```
