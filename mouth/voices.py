"""
MIO Mouth - Windows Voice Inventory & Registry Enumeration (mouth.voices)

Discovers all offline SAPI and OneCore speech synthesis voices installed in the Windows OS.
Zero external dependencies (uses standard library winreg).
"""

import os
import winreg
from typing import Any

# Windows Registry paths for installed SAPI and OneCore TTS voices
_SAPI_VOICES_KEY = r"SOFTWARE\Microsoft\Speech\Voices\Tokens"
_ONECORE_VOICES_KEY = r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"


def _parse_voice_token(root_key: int, subkey_path: str, token_name: str, is_onecore: bool = False) -> dict[str, Any] | None:
    """Extracts metadata from a Windows voice token registry key."""
    try:
        with winreg.OpenKey(root_key, f"{subkey_path}\\{token_name}") as token_key:
            display_name = winreg.QueryValue(token_key, "")

            gender = "Unknown"
            age = "Adult"
            language = "en-US"

            # Inspect Attributes subkey if present
            try:
                with winreg.OpenKey(token_key, "Attributes") as attr_key:
                    try:
                        gender = winreg.QueryValueEx(attr_key, "Gender")[0]
                    except (FileNotFoundError, OSError):
                        pass
                    try:
                        age = winreg.QueryValueEx(attr_key, "Age")[0]
                    except (FileNotFoundError, OSError):
                        pass
                    try:
                        language = winreg.QueryValueEx(attr_key, "Language")[0]
                    except (FileNotFoundError, OSError):
                        pass
            except (FileNotFoundError, OSError):
                # Infer gender from name if attribute missing
                lower_name = display_name.lower()
                if "zira" in lower_name or "eva" in lower_name or "hazel" in lower_name or "susan" in lower_name:
                    gender = "Female"
                elif "david" in lower_name or "mark" in lower_name or "george" in lower_name:
                    gender = "Male"

            return {
                "id": token_name,
                "name": display_name,
                "gender": gender,
                "age": age,
                "language": language,
                "engine": "OneCore" if is_onecore else "SAPI5",
                "description": f"{display_name} ({gender}, {engine_label if (engine_label := 'OneCore' if is_onecore else 'SAPI5') else ''})",
            }
    except Exception:
        return None


def list_installed_voices() -> list[dict[str, Any]]:
    """
    Scans the Windows registry and returns all installed text-to-speech voices.
    """
    voices = []
    seen_names = set()

    for subkey_path, is_onecore in [(_SAPI_VOICES_KEY, False), (_ONECORE_VOICES_KEY, True)]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path, 0, winreg.KEY_READ) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    token_name = winreg.EnumKey(key, i)
                    v_meta = _parse_voice_token(winreg.HKEY_LOCAL_MACHINE, subkey_path, token_name, is_onecore=is_onecore)
                    if v_meta and v_meta["name"] not in seen_names:
                        seen_names.add(v_meta["name"])
                        voices.append(v_meta)
        except (FileNotFoundError, OSError):
            continue

    # Fallback to standard Windows defaults if registry query returned nothing
    if not voices:
        voices = [
            {"id": "david", "name": "Microsoft David Desktop", "gender": "Male", "age": "Adult", "language": "en-US", "engine": "SAPI5", "description": "Microsoft David Desktop (Male)"},
            {"id": "zira", "name": "Microsoft Zira Desktop", "gender": "Female", "age": "Adult", "language": "en-US", "engine": "SAPI5", "description": "Microsoft Zira Desktop (Female)"},
        ]

    return voices


def get_default_voice() -> dict[str, Any]:
    """
    Selects the best default vocal persona.
    Prefers natural female voice (e.g. Zira) if available, otherwise first installed voice.
    """
    voices = list_installed_voices()
    for v in voices:
        if v.get("gender") == "Female" or "zira" in v.get("name", "").lower():
            return v
    return voices[0] if voices else {"id": "default", "name": "System Default", "gender": "Female"}


def find_voice(query: str) -> dict[str, Any] | None:
    """
    Matches a voice by name, token ID, or gender (e.g., 'zira', 'david', 'female', 'male').
    """
    if not query or not isinstance(query, str):
        return None

    norm_q = query.strip().lower()
    voices = list_installed_voices()

    # Exact or substring match on name
    for v in voices:
        if norm_q in v.get("name", "").lower() or norm_q in v.get("id", "").lower():
            return v

    # Match on gender
    if norm_q in ("female", "woman", "girl"):
        for v in voices:
            if v.get("gender") == "Female":
                return v

    if norm_q in ("male", "man", "boy"):
        for v in voices:
            if v.get("gender") == "Male":
                return v

    return None
