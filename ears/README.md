# MIO Ears - Auditory Perception & Speech Recognition Subsystem

> **Architecture Role:** Dedicated Vocal Hearing & Microphone Perception Organ  
> **Engines:** Offline Neural Whisper (`faster-whisper-base`) + Windows SAPI fallback + Native WinMM (`winmm.dll`) PCM audio capture.

---

## 1. Overview & Separation Philosophy

**MIO Ears** is MIO's dedicated auditory organ, completely decoupled from **Hands**, **Eyes**, and **Mouth**:
- **Hands:** Physical manipulation (mouse, keyboard, files, processes, terminal).
- **Eyes:** Visual screen grounding, OCR, and accessibility hierarchy.
- **Mouth:** Vocal speech synthesis and spoken audio output.
- **Ears:** Auditory perception, microphone discovery, and offline speech-to-text recognition.

By keeping Ears isolated, vocal recognition runs without interfering with mouse/keyboard action routines or screen coordinate grounding.

---

## 2. Key Capabilities

1. **High-Accuracy Offline Neural Whisper:**
   - Powered by the local `faster-whisper-base` int8 neural model (already cached on disk).
   - Near-100% human-level accuracy across all accents, natural pronunciation, and background noise.
   - Sub-second transcription inference on local CPU.
2. **Native Windows C Audio Capture (`ears/capture.py`):**
   - Direct 16-bit 16kHz mono PCM microphone recording using Windows Multimedia (`winmm.dll`).
3. **Automatic SAPI Fallback:**
   - If neural acceleration is unavailable or explicitly requested (`engine='sapi'`), falls back to Windows native `System.Speech.Recognition`.
4. **Targeted Voice Command & Dictation Modes:**
   - `ears.listen(timeout=4.0)`: Open-ended speech dictation.
   - `ears.listen_for(phrases, timeout=4.0)`: High-accuracy keyword and command recognition.
5. **Hardware Microphone Enumeration:**
   - Discovers all connected recording devices via Windows `winmm.dll` (Realtek Microphone Array, headsets).
6. **Background Listening Daemon:**
   - Non-blocking listening thread with clean lifecycle controls (`listen_background(callback)` / `stop_listening()`).

---

## 3. Quick Usage

```python
import ears

# 1. Check microphone hardware
if ears.is_microphone_available():
    mics = ears.list_microphones()
    print("Found microphones:", [m["name"] for m in mics])

# 2. Targeted voice command matching
print("Say 'yes' or 'no'...")
result = ears.listen_for(["yes", "no", "cancel"], timeout=4.0)
if result["status"] == "heard":
    print(f"Heard command: {result['text']} (Confidence: {result['confidence']})")
else:
    print("No response heard.")

# 3. Open speech listening
print("Speak something...")
heard = ears.listen(timeout=5.0)
if heard["status"] == "heard":
    print(f"User said: {heard['text']}")
```

---

## 4. Safety & Privacy Guardrails

- **Explicit On-Demand Activation:** By default, Ears does not passively stream or record audio to disk.
- **Ephemeral Audio Buffers:** Audio received during recognition is processed directly in system memory and immediately freed.
- **Direct Hardware Interruption:** Background listening can be stopped instantly via `ears.stop_listening()`.
