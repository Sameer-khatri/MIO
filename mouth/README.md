# MIO Mouth - Vocal Speech Synthesis Subsystem

> **Architecture Role:** Dedicated Vocal Expression & Speech Synthesis Organ  
> **Dependencies:** 100% Native Python standard library + Windows SAPI 5 / OneCore. Zero `pip` dependencies.

---

## 1. Overview

**MIO Mouth** is MIO's dedicated vocal output organ, fully decoupled from MIO Hands and MIO Eyes:
- **Eyes:** Perceives screen visual state, OCR, and accessibility hierarchy.
- **Hands:** Interacts physically with the OS (mouse, keyboard, files, windows, terminal, network).
- **Mouth:** Expresses natural speech, provides spoken feedback, announces completions, and handles vocal tone and cadence.

---

## 2. Key Capabilities

1. **Native Offline Synthesis:** Uses Windows built-in speech engines (`SAPI.SpVoice`). No internet connection or cloud API keys required.
2. **Multi-Voice Persona Selection:** Automatically discovers installed voices (e.g. *Microsoft Zira*, *Microsoft David*, *Microsoft Mark*), and allows instant switching by name or gender.
3. **Speed & Volume Control:** Granular control over speed rate (`-10` to `+10`) and volume (`0` to `100`).
4. **Zero-Latency Speech Interruption:** `mouth.stop()` immediately terminates active speech when the user speaks or commands another action.
5. **Background Asynchronous Speech:** Plays speech asynchronously by default so agent execution loops and UI are never blocked.

---

## 3. Quick Usage

```python
import mouth

# Simple speech
mouth.say("Hello, I am MIO.")

# Custom voice & speed
mouth.speak("Desktop organized successfully.", voice="Zira", rate=1, volume=90)

# Check installed voices
voices = mouth.list_installed_voices()
for v in voices:
    print(v["name"], v["gender"], v["engine"])

# Stop speech immediately
mouth.stop()
```
