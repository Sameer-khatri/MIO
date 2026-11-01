"""
MIO Ears: Vocal & Audio Perception Engine (Whisper + SAPI Dual Engine)
=====================================================================
Provides high-accuracy offline speech recognition and auditory hearing for MIO.
Uses the modern Neural Whisper model (`faster-whisper-base`) as the primary engine
for human-level accuracy across all accents, with automatic fallback to native
Windows SAPI (`System.Speech`).

Key Functions:
- listen(timeout, engine): Listens to microphone and transcribes speech.
- listen_for(phrases, timeout, engine): Listens and matches targeted voice commands.
- listen_background(callback): Continuous background listening thread.
- stop_listening(): Stops any active background listening.
- is_listening(): Returns True if MIO is actively listening.
"""

import json
import os
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional, Any

_listening_lock = threading.Lock()
_background_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_is_listening_active = False

_whisper_model = None
_whisper_lock = threading.Lock()


def _get_whisper_model():
    """
    Lazy-loads the local Whisper neural model into memory.
    Cached across subsequent listen calls for sub-second performance.
    """
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            except Exception:
                _whisper_model = False
        return _whisper_model if _whisper_model is not False else None


def _listen_sapi(timeout: float, phrase_limit: float) -> Dict[str, Any]:
    """
    Fallback: Uses legacy Windows System.Speech dictation recognizer.
    """
    start_time = time.time()
    ps_script = f"""
Add-Type -AssemblyName System.Speech
try {{
    $engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new()
    $grammar = [System.Speech.Recognition.DictationGrammar]::new()
    $engine.LoadGrammar($grammar)
    $engine.SetInputToDefaultAudioDevice()
    $engine.InitialSilenceTimeout = [System.TimeSpan]::FromSeconds({timeout})
    $engine.EndSilenceTimeout = [System.TimeSpan]::FromSeconds(1.2)
    $engine.EndSilenceTimeoutAmbiguous = [System.TimeSpan]::FromSeconds(1.2)
    
    $timeout = [System.TimeSpan]::FromSeconds({timeout})
    $res = $engine.Recognize($timeout)
    
    if ($res -and $res.Text) {{
        $outObj = [PSCustomObject]@{{
            status = 'heard'
            text = $res.Text
            confidence = [math]::Round($res.Confidence, 3)
            engine = 'sapi'
        }}
    }} else {{
        $outObj = [PSCustomObject]@{{
            status = 'silence'
            text = ''
            confidence = 0.0
            engine = 'sapi'
        }}
    }}
    $engine.Dispose()
    $outObj | ConvertTo-Json -Compress
}} catch {{
    $errObj = [PSCustomObject]@{{
        status = 'error'
        text = ''
        confidence = 0.0
        engine = 'sapi'
        error = $_.Exception.Message
    }}
    $errObj | ConvertTo-Json -Compress
}}
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(timeout + phrase_limit + 5),
        )
        elapsed = round(time.time() - start_time, 2)
        raw = proc.stdout.strip()
        if raw:
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    data["duration"] = elapsed
                    return data
        return {
            "status": "silence",
            "text": "",
            "confidence": 0.0,
            "engine": "sapi",
            "duration": elapsed,
        }
    except Exception as e:
        return {
            "status": "error",
            "text": "",
            "confidence": 0.0,
            "engine": "sapi",
            "duration": round(time.time() - start_time, 2),
            "error": str(e),
        }


def _listen_for_sapi(phrases: List[str], timeout: float) -> Dict[str, Any]:
    """
    Fallback: Uses legacy Windows System.Speech targeted grammar.
    """
    sanitized = []
    for p in phrases:
        if p and p.strip():
            clean = p.replace('"', '').replace("'", "''").strip()
            if clean:
                sanitized.append(f"'{clean}'")
    if not sanitized:
        return {"status": "error", "text": "", "confidence": 0.0, "engine": "sapi", "duration": 0.0, "error": "Phrases empty"}
    quoted_phrases = ", ".join(sanitized)
    start_time = time.time()
    
    ps_script = f"""
Add-Type -AssemblyName System.Speech
try {{
    $engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new()
    $choices = [System.Speech.Recognition.Choices]::new()
    $choices.Add([string[]]@({quoted_phrases}))
    
    $builder = [System.Speech.Recognition.GrammarBuilder]::new($choices)
    $grammar = [System.Speech.Recognition.Grammar]::new($builder)
    $engine.LoadGrammar($grammar)
    $engine.SetInputToDefaultAudioDevice()
    $engine.InitialSilenceTimeout = [System.TimeSpan]::FromSeconds({timeout})
    $engine.EndSilenceTimeout = [System.TimeSpan]::FromSeconds(1.2)
    $engine.EndSilenceTimeoutAmbiguous = [System.TimeSpan]::FromSeconds(1.2)
    
    $timeout = [System.TimeSpan]::FromSeconds({timeout})
    $res = $engine.Recognize($timeout)
    
    if ($res -and $res.Text) {{
        $outObj = [PSCustomObject]@{{
            status = 'heard'
            text = $res.Text
            confidence = [math]::Round($res.Confidence, 3)
            engine = 'sapi'
        }}
    }} else {{
        $outObj = [PSCustomObject]@{{
            status = 'silence'
            text = ''
            confidence = 0.0
            engine = 'sapi'
        }}
    }}
    $engine.Dispose()
    $outObj | ConvertTo-Json -Compress
}} catch {{
    $errObj = [PSCustomObject]@{{
        status = 'error'
        text = ''
        confidence = 0.0
        engine = 'sapi'
        error = $_.Exception.Message
    }}
    $errObj | ConvertTo-Json -Compress
}}
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(timeout + 5),
        )
        elapsed = round(time.time() - start_time, 2)
        raw = proc.stdout.strip()
        if raw:
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    data["duration"] = elapsed
                    return data
        return {
            "status": "silence",
            "text": "",
            "confidence": 0.0,
            "engine": "sapi",
            "duration": elapsed,
        }
    except Exception as e:
        return {
            "status": "error",
            "text": "",
            "confidence": 0.0,
            "engine": "sapi",
            "duration": round(time.time() - start_time, 2),
            "error": str(e),
        }


def listen(timeout: float = 4.0, phrase_limit: float = 10.0, engine: str = "whisper") -> Dict[str, Any]:
    """
    Listens to the default microphone and transcribes spoken speech.
    
    Args:
        timeout: Seconds to record / wait for speech (default 4.0, clamped 0.5 - 60.0).
        phrase_limit: Maximum duration in seconds for spoken phrase.
        engine: 'whisper' (default, high-accuracy neural) or 'sapi' (Windows native fallback).
        
    Returns:
        Dict: {
            "status": "heard" | "silence" | "error",
            "text": str,
            "confidence": float,
            "engine": "whisper" | "sapi",
            "duration": float
        }
    """
    timeout = max(0.5, min(float(timeout), 60.0))
    phrase_limit = max(1.0, min(float(phrase_limit), 60.0))
    start_time = time.time()

    if engine == "whisper":
        whisper = _get_whisper_model()
        if whisper:
            try:
                from ears.capture import record_pcm_to_file
                wav_path, rec_dur = record_pcm_to_file(duration_seconds=timeout)
                
                segments, info = whisper.transcribe(
                    wav_path,
                    beam_size=3,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
                    initial_prompt="Sameer is speaking to MIO assistant: hello, sameer, yes, no, open, stop, start, desktop, files, terminal, status.",
                )
                text = " ".join([s.text for s in segments]).strip()
                
                # Cleanup ephemeral audio buffer
                try:
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                except Exception:
                    pass
                
                elapsed = round(time.time() - start_time, 2)
                prob = getattr(info, "language_probability", 0.95)
                if text:
                    return {
                        "status": "heard",
                        "text": text,
                        "confidence": round(float(prob), 3),
                        "engine": "whisper",
                        "duration": elapsed,
                    }
                else:
                    return {
                        "status": "silence",
                        "text": "",
                        "confidence": 0.0,
                        "engine": "whisper",
                        "duration": elapsed,
                    }
            except Exception:
                # If whisper or recording fails, fall back cleanly to SAPI
                pass

    return _listen_sapi(timeout=timeout, phrase_limit=phrase_limit)


def listen_for(phrases: List[str], timeout: float = 4.0, engine: str = "whisper") -> Dict[str, Any]:
    """
    Listens specifically for a predetermined list of phrases or keywords.
    Provides fast, human-level accuracy across accents using Whisper or SAPI.
    
    Args:
        phrases: List of target phrases (e.g. ["yes", "no", "stop", "sameer"])
        timeout: Seconds to record / wait for match.
        engine: 'whisper' (default) or 'sapi'.
    """
    if not phrases:
        return {"status": "error", "text": "", "confidence": 0.0, "duration": 0.0, "error": "No phrases provided"}

    if engine == "whisper":
        heard = listen(timeout=timeout, engine="whisper")
        if heard.get("status") == "heard" and heard.get("text"):
            raw_text = heard["text"].lower().strip()
            # Clean punctuation from transcribed text
            cleaned_raw = "".join(c for c in raw_text if c.isalnum() or c.isspace())
            tokens = cleaned_raw.split()
            
            # Check for matches
            best_match = None
            for p in phrases:
                clean_p = p.lower().strip()
                if clean_p in cleaned_raw or clean_p in tokens:
                    best_match = p
                    break
            
            if best_match:
                return {
                    "status": "heard",
                    "text": best_match,
                    "raw_text": heard["text"],
                    "confidence": heard.get("confidence", 0.95),
                    "engine": "whisper",
                    "duration": heard.get("duration", 0.0),
                }
            else:
                return {
                    "status": "heard",
                    "text": heard["text"],
                    "matched": False,
                    "confidence": heard.get("confidence", 0.95),
                    "engine": "whisper",
                    "duration": heard.get("duration", 0.0),
                }
        return heard

    return _listen_for_sapi(phrases=phrases, timeout=timeout)


def _background_worker(callback: Callable[[Dict[str, Any]], None], timeout_per_phrase: float) -> None:
    global _is_listening_active
    while not _stop_event.is_set():
        try:
            res = listen(timeout=timeout_per_phrase)
            if _stop_event.is_set():
                break
            if res.get("status") == "heard" and res.get("text"):
                try:
                    callback(res)
                except Exception:
                    pass
        except Exception:
            time.sleep(0.5)
    _is_listening_active = False


def listen_background(callback: Callable[[Dict[str, Any]], None], timeout_per_phrase: float = 3.0) -> bool:
    """
    Starts continuous background listening on a daemon thread.
    Invokes callback(result_dict) whenever speech is recognized.
    """
    global _background_thread, _stop_event, _is_listening_active
    with _listening_lock:
        if _is_listening_active:
            return False
        _stop_event.clear()
        _is_listening_active = True
        _background_thread = threading.Thread(
            target=_background_worker,
            args=(callback, timeout_per_phrase),
            daemon=True,
        )
        _background_thread.start()
        return True


def stop_listening() -> bool:
    """
    Stops active background listening.
    """
    global _is_listening_active, _background_thread
    with _listening_lock:
        if not _is_listening_active:
            return False
        _stop_event.set()
        _is_listening_active = False
        return True


def is_listening() -> bool:
    """
    Returns True if MIO is actively listening in the background.
    """
    return _is_listening_active
