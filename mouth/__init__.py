"""
MIO MOUTH: Vocal Speech Synthesis & Auditory Output Subsystem
==============================================================
Provides high-fidelity, local offline speech synthesis for MIO.
Operates as a dedicated, standalone organ alongside MIO Eyes and MIO Hands.

Key Operations:
- speak(text, voice, rate, volume, async_speech): Speaks text through speakers with customizable persona.
- say(text): Instant asynchronous speech shorthand.
- stop(): Instantly halts/interrupts active speech in progress.
- is_speaking(): Checks whether MIO is actively speaking.
- list_installed_voices(): Discovers all installed Windows SAPI & OneCore voices (Zira, David, Mark).
- set_voice(name): Switches active vocal persona.
- set_rate(rate): Sets speech speed (-10 to +10).
- set_volume(volume): Sets speech volume (0 to 100).
- get_voice_settings(): Returns current vocal settings.
"""

from mouth.speaker import (
    speak,
    say,
    stop,
    is_speaking,
    set_voice,
    set_rate,
    set_volume,
    get_voice_settings,
)
from mouth.voices import (
    list_installed_voices,
    get_default_voice,
    find_voice,
)

__all__ = [
    "speak",
    "say",
    "stop",
    "is_speaking",
    "set_voice",
    "set_rate",
    "set_volume",
    "get_voice_settings",
    "list_installed_voices",
    "get_default_voice",
    "find_voice",
]
